import subprocess
import sys
import tempfile
import time
import base64
import os
import json


def execute_code(code: str, timeout: int = 30) -> dict:
    """Execute Python code in a sandboxed subprocess."""
    start_time = time.time()

    # Wrap user code to capture stdout, stderr, and figures
    wrapper = f'''
import sys
import io
import json

# Capture stdout/stderr
_old_stdout = sys.stdout
_old_stderr = sys.stderr
sys.stdout = _captured_stdout = io.StringIO()
sys.stderr = _captured_stderr = io.StringIO()

_figures = []
_error = None

try:
    # Patch matplotlib to capture figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _orig_show = plt.show
        def _capture_show(*args, **kwargs):
            import base64
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                           facecolor="#0a0f1a", edgecolor="none")
                buf.seek(0)
                _figures.append("data:image/png;base64," + base64.b64encode(buf.read()).decode())
                buf.close()
        plt.show = _capture_show
    except ImportError:
        pass

    # Execute user code
    exec("""{code_escaped}""")

except Exception as e:
    _error = f"{{type(e).__name__}}: {{e}}"

# Restore
sys.stdout = _old_stdout
sys.stderr = _old_stderr

# Also capture any unclosed matplotlib figures
try:
    import matplotlib.pyplot as plt
    import base64
    for fig_num in plt.get_fignums():
        fig = plt.figure(fig_num)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                   facecolor="#0a0f1a", edgecolor="none")
        buf.seek(0)
        _figures.append("data:image/png;base64," + base64.b64encode(buf.read()).decode())
        buf.close()
    plt.close("all")
except Exception:
    pass

result = {{
    "stdout": _captured_stdout.getvalue(),
    "stderr": _captured_stderr.getvalue(),
    "error": _error,
    "figures": _figures,
}}

print(json.dumps(result), file=sys.stdout)
'''

    code_escaped = code.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    wrapper = wrapper.replace('{code_escaped}', code_escaped)

    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False
        ) as f:
            f.write(wrapper)
            temp_path = f.name

        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir(),
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        if result.returncode == 0 and result.stdout.strip():
            try:
                parsed = json.loads(result.stdout.strip().split('\n')[-1])
                parsed["execution_time_ms"] = elapsed_ms
                return parsed
            except json.JSONDecodeError:
                pass

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": f"Process exited with code {result.returncode}" if result.returncode != 0 else None,
            "figures": [],
            "execution_time_ms": elapsed_ms,
        }

    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "stdout": "",
            "stderr": "",
            "error": f"実行がタイムアウトしました（{timeout}秒）",
            "figures": [],
            "execution_time_ms": elapsed_ms,
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "stdout": "",
            "stderr": "",
            "error": str(e),
            "figures": [],
            "execution_time_ms": elapsed_ms,
        }
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass
