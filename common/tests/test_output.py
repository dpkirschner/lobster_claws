import json
import pytest
from claws_common.output import result, error, fail, crash


def test_result_string(capsys):
    result("hello world")
    captured = capsys.readouterr()
    assert captured.out.strip() == "hello world"
    assert captured.err == ""


def test_result_dict(capsys):
    result({"key": "val"})
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed == {"key": "val"}
    assert captured.err == ""


def test_error_prints_to_stderr(capsys):
    with pytest.raises(SystemExit) as exc_info:
        error("something broke")
    captured = capsys.readouterr()
    assert "Error: something broke" in captured.err
    assert exc_info.value.code == 1


def test_fail_exits_code_1():
    with pytest.raises(SystemExit) as exc_info:
        fail("bad input")
    assert exc_info.value.code == 1


def test_crash_exits_code_2():
    with pytest.raises(SystemExit) as exc_info:
        crash("server down")
    assert exc_info.value.code == 2
