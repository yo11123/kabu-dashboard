from fastapi import APIRouter
from ..models.schemas import (
    ExecuteRequest,
    ExecuteResponse,
    CheckRequest,
    CheckResponse,
    TestCaseResult,
)
from ..execution.sandbox import execute_code

router = APIRouter()


@router.get("/health")
async def health():
    available_packages = []
    for pkg in ["sklearn", "pandas", "numpy", "matplotlib", "plotly"]:
        try:
            __import__(pkg)
            available_packages.append(pkg)
        except ImportError:
            pass
    return {"status": "ok", "packages": available_packages}


@router.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest):
    result = execute_code(request.code, timeout=request.timeout)
    return ExecuteResponse(
        stdout=result.get("stdout", ""),
        stderr=result.get("stderr", ""),
        error=result.get("error"),
        figures=result.get("figures", []),
        execution_time_ms=result.get("execution_time_ms", 0),
    )


@router.post("/check", response_model=CheckResponse)
async def check(request: CheckRequest):
    results = []

    for tc in request.test_cases:
        if tc.type == "return_value" and tc.call:
            check_code = f"""
{request.code}

_result = {tc.call}
assert _result == {repr(tc.expected)}, f"Expected {repr(tc.expected)}, got {{_result}}"
"""
            exec_result = execute_code(check_code, timeout=10)
            passed = exec_result.get("error") is None
            results.append(TestCaseResult(
                id=tc.id,
                passed=passed,
                actual=str(exec_result.get("stdout", "").strip()),
                error=exec_result.get("error"),
            ))
        elif tc.type == "custom" and tc.check_code:
            check_code = f"{request.code}\n{tc.check_code}"
            exec_result = execute_code(check_code, timeout=10)
            passed = exec_result.get("error") is None
            results.append(TestCaseResult(
                id=tc.id,
                passed=passed,
                error=exec_result.get("error"),
            ))
        elif tc.type == "stdout":
            exec_result = execute_code(request.code, timeout=10)
            stdout = exec_result.get("stdout", "")
            passed = stdout == str(tc.expected)
            results.append(TestCaseResult(
                id=tc.id,
                passed=passed,
                actual=stdout,
                error=None if passed else f'Expected "{tc.expected}", got "{stdout}"',
            ))
        else:
            results.append(TestCaseResult(
                id=tc.id,
                passed=False,
                error="Unsupported test case type",
            ))

    return CheckResponse(
        results=results,
        all_passed=all(r.passed for r in results),
    )
