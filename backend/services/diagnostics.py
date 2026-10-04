import re

MAX_DIAGNOSTIC_CHARS = 8000
_DIAGNOSTIC = re.compile(r'^(?:/app/)?source\.asm:(\d+):\s*(Error|Warning)\[(\d+)\]\s*(.*)$', re.IGNORECASE)
_ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
_PATH = re.compile(r'(?:[A-Za-z]:[\\/]|/)[^\s\'"<>]*')


def compilation_feedback(stdout: str, stderr: str) -> str:
    lines = []
    for raw in (stdout + '\n' + stderr).splitlines():
        match = _DIAGNOSTIC.match(_ANSI.sub('', raw))
        if not match:
            continue
        line, level, code, message = match.groups()
        message = ''.join(c for c in message if c.isprintable() and not '\u202a' <= c <= '\u202e' and not '\u2066' <= c <= '\u2069')
        message = _PATH.sub('[path]', message)[:300]
        lines.append(f'source.asm:{line}: {level.title()}[{code}] {message}')
        if len(lines) >= 40:
            lines.append('Further diagnostics omitted.')
            break
    return '\n'.join(lines)[:MAX_DIAGNOSTIC_CHARS] or 'Compilation failed. Check the submitted assembly syntax and supported PIC18F4520 MPASM directives.'
