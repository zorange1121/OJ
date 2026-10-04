from services.diagnostics import compilation_feedback, MAX_DIAGNOSTIC_CHARS


def test_feedback_preserves_source_line_and_reason_without_included_test_content():
    text = 'source.asm:3:Error[181] Unknown opcode: "FROBNICATE"\n/app/hidden.in:8:Error[113] secret-input\nTraceback private-data\n'
    feedback = compilation_feedback(text, '')
    assert 'source.asm:3: Error[181]' in feedback
    assert 'FROBNICATE' in feedback
    assert 'secret-input' not in feedback and 'private-data' not in feedback


def test_feedback_removes_paths_terminal_controls_and_limits_output():
    line = '\x1b[31msource.asm:1:Error[105] Cannot open "/app/hidden.inc"\x1b[0m\n'
    feedback = compilation_feedback(line * 1000, '')
    assert '/app/' not in feedback and '\x1b' not in feedback
    assert '[path]' in feedback and len(feedback) <= MAX_DIAGNOSTIC_CHARS


def test_feedback_does_not_publish_unrecognized_tool_output():
    assert 'secret' not in compilation_feedback('secret test-data', '/private/path traceback')
