import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('APP_ENV', 'test')
from services.judge import _docker_run


def main():
    output = ROOT / '.verification'
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='compile-timeout-', dir=output) as directory:
        path = Path(directory)
        (path / 'source.asm').write_text('    PROCESSOR p18f4520\n' + '    NOP\n' * 10000 + '    END\n', encoding='utf-8')
        try:
            _docker_run(path, ['gpasm', '--mpasm-compatible', '-p', 'p18f4520', 'source.asm'], timeout=0.001)
        except subprocess.TimeoutExpired:
            print('PASS real gpasm killed by sandbox watchdog at 1 ms; production budget remains 15 seconds')
        else:
            raise AssertionError('Expected the tiny compiler test budget to expire')


if __name__ == '__main__':
    main()
