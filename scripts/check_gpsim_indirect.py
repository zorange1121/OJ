import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('APP_ENV', 'test')
from services.judge import _docker_run, _parse_key_values

SOURCE = '''    PROCESSOR p18f4520
    #include <p18f4520.inc>
    CONFIG WDT = OFF
    ORG 0
    MOVLB 1
    MOVLW 0x11
    MOVWF 0x100, BANKED
    MOVLW 0x22
    MOVWF 0x101, BANKED
    MOVLW 0x44
    MOVWF 0x103, BANKED
    LFSR 0, 0x100
    MOVLW 0x01
    ADDWF POSTINC0, W
    MOVWF 0x010
    MOVFF FSR0L, 0x011
    MOVLW 0x01
    ADDWF POSTINC0, F
    MOVFF FSR0L, 0x012
    MOVFF 0x101, 0x013
    MOVLW 0x01
    ADDWF PREINC0, W
    MOVWF 0x014
    MOVFF FSR0L, 0x015
    MOVLW 0x01
    ADDWF POSTDEC0, W
    MOVWF 0x016
    MOVFF FSR0L, 0x017
    MOVLW 0xA5
    MOVWF 0x05F
judge_done:
    BRA judge_done
    END
'''
SCRIPT = 'load /app/source.cod\nbreak e judge_done\nbreak c 1000\nrun\ndump r\nquit\n'
EXPECTED = [
    (0x010, '12', 'ADDWF POSTINC0, W result'),
    (0x011, '01', 'ADDWF POSTINC0, W increments FSR0 once'),
    (0x012, '02', 'ADDWF POSTINC0, F increments FSR0 once'),
    (0x013, '23', 'ADDWF POSTINC0, F writes the address it read'),
    (0x014, '45', 'ADDWF PREINC0, W reads after incrementing'),
    (0x015, '03', 'ADDWF PREINC0, W leaves FSR0 incremented'),
    (0x016, '45', 'ADDWF POSTDEC0, W result'),
    (0x017, '02', 'ADDWF POSTDEC0, W decrements FSR0'),
    (0x05F, 'a5', 'program reached judge_done'),
]


def main():
    output = ROOT / '.verification'
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gpsim-indirect-', dir=output) as directory:
        path = Path(directory)
        (path / 'source.asm').write_text(SOURCE, encoding='utf-8')
        (path / '1.in').write_text(SCRIPT, encoding='utf-8')
        compiled = _docker_run(path, ['gpasm', '--mpasm-compatible', '-p', 'p18f4520', 'source.asm'])
        if compiled.returncode:
            raise AssertionError(f'gpasm failed:\n{compiled.stdout}{compiled.stderr}')
        result = _docker_run(path, ['gpsim', '-i', '-p', 'p18f4520', '-c', '1.in'], timeout=10)
        actual = _parse_key_values(result.stdout)
    failures = [f'{meaning}: ram[0x{address:03x}] expected {value}, got {actual.get(f"ram[0x{address:03x}]")}'
                for address, value, meaning in EXPECTED if actual.get(f'ram[0x{address:03x}]') != value]
    if failures:
        raise AssertionError('gpsim indirect addressing mismatch:\n' + '\n'.join(failures))
    print(f'PASS {len(EXPECTED)} ADDWF indirect-addressing checks in {os.environ.get("JUDGE_DOCKER_IMAGE", "pic-judge")}')


if __name__ == '__main__':
    main()
