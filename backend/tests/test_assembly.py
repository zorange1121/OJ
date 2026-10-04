from services.assembly import prepare_source
from services.judge import _parse_key_values
from services.judge import _extract_cycles
from services.assembly import validate_cod
import pytest


def test_mpasm_layout_is_normalized_without_changing_instructions():
    original = '    #include<p18f4520.inc>\n  loop: MOVLW 0x05\n    A MACRO arg\n    local inner\n  inner: MOVWF arg\n    endm\n;    label: unchanged\n'
    assert prepare_source(original) == '    #include <p18f4520.inc>\nloop: MOVLW 0x05\nA MACRO arg\n    local inner\ninner: MOVWF arg\n    endm\n;    label: unchanged\n'


def test_ram_dump_supports_result_addresses():
    values = _parse_key_values('0010:  01 c0 00 00 00 00 00 00 00 00 00 00 00 00 00 00    ................\n')
    assert values['ram[0x010]'] == '01'
    assert values['ram[0x011]'] == 'c0'
    assert _parse_key_values('ram[0x010] = 01\nram[0x011] = c0')['ram[0x011]'] == 'c0'
    assert 'W' not in _parse_key_values('42: NOP ; W = 05\n')
    assert _parse_key_values('W = 05\r\nstatus = 00\r\n') == {'W': '05', 'status': '00'}
    assert _parse_key_values('**gpsim> trisa = 0x65\n')['trisa'] == '0x65'
    assert _extract_cycles('**gpsim> 23 = 0x17\n') == 23
    assert 'trisa' not in _parse_key_values('42: NOP ; **gpsim> trisa = 0x65\n')


def test_cod_rejects_simulator_commands_in_chained_directories():
    data = bytearray(1024)
    data[441:443] = (1).to_bytes(2, 'little')
    validate_cod(data)
    data[512 + 466] = 2
    with pytest.raises(ValueError, match='Embedded'):
        validate_cod(data)


@pytest.mark.parametrize('data', [b'', b'x', bytes(441) + b'\xff\xff' + bytes(69)])
def test_cod_rejects_malformed_directories(data):
    with pytest.raises(ValueError):
        validate_cod(data)


def test_cod_rejects_directory_cycles():
    data = bytearray(1024)
    data[441:443] = (1).to_bytes(2, 'little')
    data[512 + 441:512 + 443] = (1).to_bytes(2, 'little')
    with pytest.raises(ValueError, match='chain'):
        validate_cod(data)
