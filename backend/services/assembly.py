import re


def prepare_source(source: str) -> str:
    source = source.lstrip("\ufeff")
    source = re.sub(r'(?im)^([ \t]*#include)(?=[<"])', r'\1 ', source)
    source = re.sub(r"(?m)^[ \t]+([A-Za-z_][\w]*:)", r"\1", source)
    source = re.sub(r"(?im)^[ \t]+([A-Za-z_][\w]*[ \t]+(?:EQU|MACRO)\b)", r"\1", source)
    return source


def validate_cod(data: bytes) -> None:
    if not data or len(data) % 512:
        raise ValueError("Invalid COD block length")
    block, seen = 0, set()
    while True:
        if block in seen or block * 512 + 512 > len(data):
            raise ValueError("Invalid COD directory chain")
        seen.add(block)
        directory = data[block * 512:(block + 1) * 512]
        if any(directory[466:470]):
            raise ValueError("Embedded simulator commands are not supported")
        block = int.from_bytes(directory[441:443], "little")
        if not block:
            return

