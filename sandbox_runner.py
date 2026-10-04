import base64
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile


LIMIT = 1024 * 1024


def main():
    timeout = float(sys.argv[1])
    command = sys.argv[2:]
    if not command or command[0] not in {"gpasm", "gpsim"}:
        raise ValueError("Unsupported tool")
    for entry in Path("/input").iterdir():
        destination = Path("/app") / entry.name
        if entry.is_dir():
            shutil.copytree(entry, destination)
        else:
            shutil.copyfile(entry, destination)
    resource.setrlimit(resource.RLIMIT_FSIZE, (LIMIT, LIMIT))
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                   cwd="/app", start_new_session=True)
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, 9)
            process.wait()
            returncode = 124
        stdout.seek(0)
        stderr.seek(0)
        result = {"returncode": returncode,
                  "stdout": stdout.read(LIMIT).decode("utf-8", errors="replace"),
                  "stderr": stderr.read(LIMIT).decode("utf-8", errors="replace")}
    if command[0] == "gpasm" and returncode == 0:
        result["hex"] = base64.b64encode(Path("/app/source.hex").read_bytes()[:LIMIT]).decode("ascii")
        result["cod"] = base64.b64encode(Path("/app/source.cod").read_bytes()[:LIMIT]).decode("ascii")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
