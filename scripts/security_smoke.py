import argparse
import io
import json
from pathlib import Path
import secrets
import subprocess
import time
import zipfile

import httpx
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parent.parent
TERMINAL = {"AC", "WA", "CE", "TLE", "RE", "MLE"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--url", default="http://127.0.0.1:15173")
    parser.add_argument("--faults", action="store_true")
    args = parser.parse_args()
    if not args.project.startswith("picjudge-security-"):
        raise SystemExit("Use a disposable picjudge-security-* project")
    compose = ["docker", "compose", "--env-file", args.env_file, "-p", args.project]
    suffix = secrets.token_hex(4)
    password = secrets.token_hex(20)
    admin_name = f"smoke-admin-{suffix}"
    bootstrap = "import json,sys; from database import SessionLocal; from services.auth import create_user; data=json.load(sys.stdin); db=SessionLocal(); create_user(db,data['name'],data['password'],True); db.close()"
    subprocess.run(compose + ["exec", "-T", "api", "/app/.venv/bin/python", "-c", bootstrap],
                   input=json.dumps({"name": admin_name, "password": password}), text=True, check=True, timeout=30)
    with httpx.Client(base_url=args.url, timeout=30) as client:
        def login(name):
            response = client.post("/api/auth/login", json={"username": name, "password": password})
            assert response.status_code == 200, f"Login returned {response.status_code}"
            return response.json()["access_token"]
        admin_token = login(admin_name)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        names = [f"smoke-owner-{suffix}", f"smoke-other-{suffix}"]
        for name in names:
            response = client.post("/api/users", headers=admin_headers, json={"username": name, "password": password})
            assert response.status_code == 200
        token, other_token = [login(name) for name in names]
        headers = {"Authorization": f"Bearer {token}"}
        def create_problem(data, limit=2):
            windows_data = io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(data)) as original, zipfile.ZipFile(windows_data, 'w') as converted:
                for name in original.namelist():
                    content = original.read(name)
                    if name.endswith('.out'):
                        content = content.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
                    converted.writestr(name, content)
            data = windows_data.getvalue()
            response = client.post("/api/problems", headers=admin_headers,
                data={"name": f"Smoke {suffix}", "description": "Disposable integration test", "time_limit": str(limit),
                      "points": "100", "testcases": json.dumps([{"input_file": "1.in", "output_file": "1.out", "points": 100}])},
                files={"zipfile": ("tests.zip", data, "application/zip")})
            assert response.status_code == 200, f"Create problem returned {response.status_code}: {response.text}"
            return response.json()["id"]
        problem_id = create_problem((ROOT / "sample-data/testdata.zip").read_bytes())
        def submit(source, problem=problem_id):
            response = client.post("/api/submissions", headers=headers, json={"problem_id": problem, "source": source})
            assert response.status_code == 200, f"Submit returned {response.status_code}"
            return response.json()["id"]
        def wait_result(submission_id, expected, timeout=100):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                response = client.get(f"/api/submissions/{submission_id}", headers=headers)
                assert response.status_code == 200
                payload = response.json()
                if payload["status"] in TERMINAL:
                    assert payload["status"] == expected, f"Submission {submission_id}: expected {expected}, got {payload['status']}"
                    print(f"PASS submission {submission_id}: {expected}", flush=True)
                    return payload
                time.sleep(1)
            raise AssertionError(f"Submission {submission_id} never finished")
        source = (ROOT / "sample-data/accepted.asm").read_text(encoding="utf-8")
        accepted_id = submit(source)
        result = wait_result(accepted_id, "AC")
        assert result["cycles"] == 3 and result["points"] == 100
        url = f"/api/submissions/{accepted_id}"
        assert client.get(url).status_code == 401
        assert client.get(url, headers={"Authorization": f"Bearer {other_token}"}).status_code == 403
        assert client.get(url, headers=admin_headers).status_code == 200
        print("PASS submission access control", flush=True)
        ws_url = args.url.replace("http://", "ws://").replace("https://", "wss://") + url + "/ws?token=" + token
        with connect(ws_url, open_timeout=10) as socket:
            assert json.loads(socket.recv(timeout=10))["status"] == "AC"
        print("PASS WebSocket through reverse proxy", flush=True)
        response = client.get(f"/problems/{problem_id}")
        assert response.status_code == 200 and 'id="root"' in response.text
        print("PASS SPA deep link", flush=True)
        for filename, status in [("wrong_answer.asm", "WA"), ("compile_error.asm", "CE")]:
            checked_id = submit((ROOT / "sample-data" / filename).read_text(encoding="utf-8"))
            checked = wait_result(checked_id, status)
            if status == 'CE':
                assert 'source.asm:' in checked['compile_output'] and 'FROBNICATE' in checked['compile_output']
                assert '/app/' not in checked['compile_output']
                feedback_url = args.url.replace('http://','ws://').replace('https://','wss://') + f'/api/submissions/{checked_id}/ws?token=' + token
                with connect(feedback_url, open_timeout=10) as socket:
                    assert json.loads(socket.recv(timeout=10))['compile_output'] == checked['compile_output']
                assert client.get(f'/api/submissions/{checked_id}', headers={'Authorization':f'Bearer {other_token}'}).status_code == 403
                print('PASS compiler feedback through owner API/WebSocket, denied to other user',flush=True)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("1.in", "load /app/source.hex\nrun\nquit\n")
            archive.writestr("1.out", "W = 05\n")
        timeout_problem = create_problem(buffer.getvalue(), limit=1)
        loop = "    PROCESSOR p18f4520\n    #include <p18f4520.inc>\n    CONFIG WDT = OFF\n    CONFIG OSC = INTIO67\n    ORG 0\nloop: BRA loop\n    END\n"
        wait_result(submit(loop, timeout_problem), "TLE")
        injected = source.replace("        END", '        .direct "e", "W = 5"\n        END')
        wait_result(submit(injected), "CE")
        runaway_compile = '    PROCESSOR p18f4520\n    WHILE 1\n    ENDW\n    END\n'
        wait_result(submit(runaway_compile), "CE")
        invalid_script = io.BytesIO()
        with zipfile.ZipFile(invalid_script, 'w') as archive:
            archive.writestr('1.in', 'load /app/missing.hex\nquit\n')
            archive.writestr('1.out', 'W = 05\n')
        wait_result(submit(source, create_problem(invalid_script.getvalue())), 'RE')
        running = subprocess.check_output(["docker", "ps", "-q", "--filter", "ancestor=picjudge-security-sandbox"], text=True).strip()
        assert not running, "A sandbox container remained running after judging"
        print("PASS no running sandbox remains", flush=True)
        if args.faults:
            subprocess.run(compose + ["stop", "rabbitmq"], check=True, timeout=45)
            try:
                recovery_id = submit(source)
                assert client.get(f"/api/submissions/{recovery_id}", headers=headers).json()["status"] == "Pending"
            finally:
                subprocess.run(compose + ["start", "rabbitmq"], check=True, timeout=45)
            wait_result(recovery_id, "AC", timeout=150)
            print("PASS broker outage and durable backlog recovery", flush=True)
            crash_problem = create_problem(buffer.getvalue(), limit=10)
            crashed_id = submit(loop, crash_problem)
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                if client.get(f"/api/submissions/{crashed_id}", headers=headers).json()["status"] == "Running":
                    break
                time.sleep(0.2)
            else:
                raise AssertionError('Worker did not enter Running before crash test')
            active = []
            deadline = time.monotonic() + 10
            while not active and time.monotonic() < deadline:
                active = subprocess.check_output(['docker', 'ps', '-q', '--filter', 'ancestor=picjudge-security-sandbox'], text=True).split()
                if not active:
                    time.sleep(0.2)
            assert active, 'No sandbox found during Running'
            for container in active:
                info = json.loads(subprocess.check_output(['docker', 'inspect', container], text=True))[0]
                host = info['HostConfig']
                assert info['Config']['User'] == '65534:65534'
                assert host['ReadonlyRootfs'] and host['NetworkMode'] == 'none'
                assert host['CapDrop'] == ['ALL'] and 'no-new-privileges' in host['SecurityOpt']
                assert host['Memory'] == 256 * 1024 * 1024 and host['PidsLimit'] == 64
                assert all(not mount['RW'] for mount in info['Mounts'] if mount['Destination'] == '/input')
            print('PASS live sandbox isolation and resource limits', flush=True)
            subprocess.run(compose + ['kill', '-s', 'SIGKILL', 'worker'], check=True, timeout=30)
            try:
                recovery = "import sys; from database import SessionLocal; from model import Submission; from services.queue import publish_submission; db=SessionLocal(); s=db.get(Submission,int(sys.argv[1])); assert s.lease_until>0; s.lease_until=0; db.commit(); db.close(); publish_submission(sid:=int(sys.argv[1])); publish_submission(sid)"
                subprocess.run(compose + ['exec', '-T', 'api', 'python', '-c', recovery, str(crashed_id)], check=True, timeout=30)
            finally:
                subprocess.run(compose + ['start', 'worker'], check=True, timeout=45)
            wait_result(crashed_id, 'TLE', timeout=100)
            duplicate = "import sys; from services.judge import run_judge; from database import SessionLocal; from model import Submission,UserProblemScore; sid=int(sys.argv[1]); run_judge(sid); run_judge(sid); db=SessionLocal(); s=db.get(Submission,sid); assert s.status.value=='AC'; assert db.query(UserProblemScore).filter_by(user_id=s.user_id,problem_id=s.problem_id).count()==1"
            subprocess.run(compose + ['exec', '-T', 'api', 'python', '-c', duplicate, str(accepted_id)], check=True, timeout=30)
            print('PASS worker crash, expired lease, duplicate delivery and score uniqueness', flush=True)
        assert not subprocess.check_output(['docker', 'ps', '-q', '--filter', 'ancestor=picjudge-security-sandbox'], text=True).strip()
    print("All integration checks passed", flush=True)


if __name__ == "__main__":
    main()
