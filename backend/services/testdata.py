import re
import stat
import zipfile
from pathlib import PurePosixPath

from .errors import InvalidTestDataError

MAX_EXPANDED_BYTES = 16 * 1024 * 1024
MAX_FILES = 200
KEY_VALUE_RE = re.compile(r"^[ \t]*(\S+)[ \t]*=[ \t]*(\S+)[ \t]*\r?$", re.MULTILINE)


def parse_key_values(text: str) -> dict[str, str]:
    return dict(KEY_VALUE_RE.findall(text))


def validate_archive(archive: zipfile.ZipFile, cases) -> dict[str, bytes]:
    if not 1 <= len(cases) <= 100:
        raise InvalidTestDataError("Provide between 1 and 100 test cases")
    entries = archive.infolist()
    if len(entries) > MAX_FILES or sum(i.file_size for i in entries) > MAX_EXPANDED_BYTES:
        raise InvalidTestDataError("Test archive exceeds size or file count limit")
    files = {}
    seen = set()
    for entry in entries:
        name = entry.orig_filename
        path = PurePosixPath(name)
        if (not name or name.startswith("/") or "\\" in name or ":" in name
                or any(part in ("", ".", "..") for part in name.rstrip("/").split("/"))
                or name.startswith("-") or any(ord(c) < 32 for c in name)
                or stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1):
            raise InvalidTestDataError("Unsafe or encrypted archive entry")
        if path.parts[0].lower().startswith("source.") or path.name.lower().endswith(".log"):
            raise InvalidTestDataError("Archive uses a reserved judge filename")
        normalized = name.rstrip("/").casefold()
        if normalized in seen:
            raise InvalidTestDataError("Duplicate archive entry")
        seen.add(normalized)
        if not entry.is_dir():
            files[name] = archive.read(entry)
    for case in cases:
        if case.input_file in {item.output_file for item in cases}:
            raise InvalidTestDataError("Test scripts and expected answers must use distinct files")
        if case.input_file not in files or case.output_file not in files:
            raise InvalidTestDataError("Test data zip is missing a required file")
        try:
            expected = files[case.output_file].decode("utf-8")
            files[case.input_file].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidTestDataError("Test scripts and answers must be UTF-8") from exc
        if not parse_key_values(expected):
            raise InvalidTestDataError("Expected output must contain at least one key=value pair")
    return files
