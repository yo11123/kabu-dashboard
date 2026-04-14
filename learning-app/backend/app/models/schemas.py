from pydantic import BaseModel


class ExecuteRequest(BaseModel):
    code: str
    timeout: int = 30


class ExecuteResponse(BaseModel):
    stdout: str
    stderr: str
    error: str | None = None
    figures: list[str] = []
    execution_time_ms: int = 0


class TestCaseInput(BaseModel):
    id: str
    type: str
    call: str | None = None
    expected: str | int | float | bool | dict | None = None
    check_code: str | None = None


class CheckRequest(BaseModel):
    code: str
    test_cases: list[TestCaseInput]


class TestCaseResult(BaseModel):
    id: str
    passed: bool
    actual: str | None = None
    error: str | None = None


class CheckResponse(BaseModel):
    results: list[TestCaseResult]
    all_passed: bool
