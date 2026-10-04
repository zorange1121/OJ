import asyncio
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from starlette.concurrency import run_in_threadpool

from database import SessionLocal
from model import Submission, User
from .deps import get_current_user_id_from_query_token

router = APIRouter(tags=["websocket"])
POLL_INTERVAL_SECONDS = 1
TERMINAL_STATUSES = {"AC", "WA", "TLE", "MLE", "RE", "CE"}


def _snapshot(token: str, submission_id: int) -> dict:
    with SessionLocal() as db:
        user_id = get_current_user_id_from_query_token(token, db)
        submission = db.get(Submission, submission_id)
        if submission is None:
            raise HTTPException(404, "Submission not found")
        if submission.user_id != user_id and not db.get(User, user_id).is_admin:
            raise HTTPException(403, "Submission access denied")
        return {"id": submission.id, "status": submission.status.value,
                "points": submission.points, "cycles": submission.cycles, "time": submission.time,
                "compile_output": submission.compile_output}


@router.websocket("/api/submissions/{submission_id}/ws")
async def submission_status_ws(websocket: WebSocket, submission_id: int, token: str = "") -> None:
    try:
        payload = await run_in_threadpool(_snapshot, token, submission_id)
    except HTTPException as exc:
        await websocket.close(code=4400 + exc.status_code % 100)
        return
    await websocket.accept()
    last_payload = None
    deadline = time.monotonic() + 900
    try:
        while time.monotonic() < deadline:
            if payload != last_payload:
                await websocket.send_json(payload)
                last_payload = payload
            if payload["status"] in TERMINAL_STATUSES:
                await websocket.close()
                return
            try:
                message = await asyncio.wait_for(websocket.receive(), timeout=POLL_INTERVAL_SECONDS)
                if message["type"] == "websocket.disconnect":
                    return
            except asyncio.TimeoutError:
                pass
            payload = await run_in_threadpool(_snapshot, token, submission_id)
        await websocket.close(code=1013)
    except HTTPException as exc:
        await websocket.close(code=4400 + exc.status_code % 100)
    except WebSocketDisconnect:
        pass
