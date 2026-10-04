import json
import os
import logging
import threading
import time
from collections.abc import Callable

import pika

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
QUEUE_NAME = "judge_submissions"
logger = logging.getLogger(__name__)


def _connect() -> pika.BlockingConnection:
    parameters = pika.URLParameters(RABBITMQ_URL)
    parameters.heartbeat = 600
    parameters.blocked_connection_timeout = 10
    parameters.socket_timeout = 5
    return pika.BlockingConnection(parameters)


def publish_submission(submission_id: int) -> None:
    connection = _connect()
    try:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.confirm_delivery()
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps({"submission_id": submission_id}),
            properties=pika.BasicProperties(delivery_mode=2),
            mandatory=True,
        )
    finally:
        connection.close()


def _consume_once(on_submission: Callable[[int], None]) -> None:
    connection = _connect()
    try:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_qos(prefetch_count=1)

        def _callback(ch, method, _properties, body):
            try:
                payload = json.loads(body)
                if type(payload.get("submission_id")) is not int or payload["submission_id"] <= 0:
                    raise ValueError("Invalid submission id")
            except (ValueError, TypeError, AttributeError):
                logger.warning("Discarded malformed judge message")
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return
            try:
                on_submission(payload["submission_id"])
            except Exception:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                raise
            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=_callback)
        channel.start_consuming()
    finally:
        connection.close()


def recover_submissions() -> None:
    from database import SessionLocal
    from model import Submission
    from .judge import ACTIVE_STATUSES, cleanup_stale_workdirs
    cleanup_stale_workdirs()
    with SessionLocal() as db:
        ids = [row[0] for row in db.query(Submission.id).filter(
            Submission.status.in_(ACTIVE_STATUSES), Submission.lease_until < time.time()
        ).order_by(Submission.id).limit(100).all()]
    for submission_id in ids:
        publish_submission(submission_id)


def consume(on_submission: Callable[[int], None]) -> None:
    stop = threading.Event()
    def recovery_loop():
        while not stop.is_set():
            try:
                recover_submissions()
            except Exception:
                logger.exception("Backlog recovery failed; retrying in 30 seconds")
            stop.wait(30)
    thread = threading.Thread(target=recovery_loop, daemon=True)
    thread.start()
    try:
        while True:
            try:
                _consume_once(on_submission)
            except Exception:
                logger.exception("Worker disconnected; reconnecting in 5 seconds")
                time.sleep(5)
    finally:
        stop.set()
