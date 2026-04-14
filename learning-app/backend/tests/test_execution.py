"""Basic tests for the sandbox execution engine."""
from app.execution.sandbox import execute_code


def test_simple_print():
    result = execute_code('print("hello")', timeout=10)
    assert result["stdout"].strip() == "hello"
    assert result["error"] is None


def test_arithmetic():
    result = execute_code('print(1 + 2)', timeout=10)
    assert result["stdout"].strip() == "3"
    assert result["error"] is None


def test_syntax_error():
    result = execute_code('print("unclosed', timeout=10)
    assert result["error"] is not None


def test_timeout():
    result = execute_code('import time; time.sleep(5)', timeout=2)
    assert result["error"] is not None
    assert "タイムアウト" in result["error"]
