"""Code synthesis evaluator using an OS-enforced, fail-closed sandbox."""

import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from typing import Any, Dict

from .base_evaluator import BaseEvaluator

_WORKER = r'''import json, sys
request = json.load(sys.stdin)
namespace = {}
try:
    candidate = compile(request["code"], "<candidate>", "exec")
except SyntaxError as exc:
    result = {"passed": False, "syntax_valid": False,
              "error": ("SyntaxError: " + str(exc))[:500]}
else:
    try:
        exec(candidate, namespace)
        if request["entry_point"] not in namespace:
            raise NameError("entry point is not defined")
        exec(compile(request["test"], "<tests>", "exec"), namespace)
        check = namespace.get("check")
        if check is not None:
            check(namespace[request["entry_point"]])
        result = {"passed": True, "syntax_valid": True, "error": None}
    except BaseException as exc:
        result = {"passed": False, "syntax_valid": True,
                  "error": (type(exc).__name__ + ": " + str(exc))[:500]}
print(json.dumps(result))
'''


class CodeEvaluator(BaseEvaluator):
    """Use Linux bubblewrap/prlimit; ``syntax_valid`` is None if unverified."""

    def __init__(self, timeout_sec: float = 3.0):
        if not math.isfinite(timeout_sec) or timeout_sec <= 0:
            raise ValueError("timeout_sec must be finite and positive")
        self.timeout_sec = timeout_sec
        self.code_pattern = re.compile(r"```python\s*(.+?)```", re.DOTALL | re.IGNORECASE)

    def extract_code(self, response_text: str, entry_point: str) -> str:
        """Extract Python code containing the function definition."""
        blocks = self.code_pattern.findall(response_text)
        if blocks:
            for block in blocks:
                if f"def {entry_point}" in block:
                    return block
            return blocks[0]
        if f"def {entry_point}" in response_text:
            lines, code_lines, capturing = response_text.splitlines(), [], False
            for line in lines:
                if f"def {entry_point}" in line:
                    capturing = True
                if capturing:
                    code_lines.append(line)
            return "\n".join(code_lines)
        return response_text

    @staticmethod
    def _sandbox_command() -> list[str] | None:
        bwrap, prlimit = shutil.which("bwrap"), shutil.which("prlimit")
        if not bwrap or not prlimit or not sys.platform.startswith("linux"):
            return None
        executable = Path(os.path.realpath(sys.executable))
        python_root = executable.parent.parent
        python_binary = f"/opt/python/bin/{executable.name}"
        if not (python_root / "bin" / executable.name).is_file():
            return None
        return [
            prlimit, "--cpu=2:2", "--as=536870912:536870912",
            "--fsize=1048576:1048576", "--nproc=512:512", "--nofile=32:32",
            "--core=0:0", "--", bwrap, "--die-with-parent", "--unshare-all",
            "--ro-bind", "/usr", "/usr", "--ro-bind", "/bin", "/bin",
            "--ro-bind", "/lib", "/lib", "--ro-bind-try", "/lib64", "/lib64",
            "--dir", "/opt", "--ro-bind", str(python_root), "/opt/python",
            "--proc", "/proc", "--dev", "/dev", "--size", "67108864",
            "--tmpfs", "/tmp",
            "--dir", "/work", "--chdir", "/work", python_binary,
            "-I", "-c", _WORKER,
        ]

    def evaluate(self, item: Dict[str, Any], response_text: str, **kwargs) -> Dict[str, Any]:
        entry_point = item.get("entry_point", "solution")
        test_code = item.get("test", "")
        if not isinstance(response_text, str) or not isinstance(test_code, str) \
                or not isinstance(entry_point, str):
            return {
                "score": 0.0, "passed": False, "syntax_valid": None,
                "error": "InvalidCodeEvaluationInput", "extracted_code": "",
            }
        if len(response_text) + len(test_code) > 1_048_576:
            return {
                "score": 0.0, "passed": False, "syntax_valid": None,
                "error": "SandboxInputTooLarge", "extracted_code": response_text[:200],
            }
        extracted_code = self.extract_code(response_text, entry_point)

        command = self._sandbox_command()
        if command is None:
            return {
                "score": 0.0, "passed": False, "syntax_valid": None,
                "error": "SandboxUnavailable: bwrap and prlimit are required",
                "extracted_code": extracted_code[:200],
            }

        payload = json.dumps({
            "code": extracted_code,
            "test": test_code,
            "entry_point": entry_point,
        })
        if len(payload) > 1_048_576:
            return {
                "score": 0.0, "passed": False, "syntax_valid": None,
                "error": "SandboxInputTooLarge", "extracted_code": extracted_code[:200],
            }
        with tempfile.TemporaryFile() as output:
            try:
                proc = subprocess.Popen(
                    command, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT,
                    env={"PATH": "/usr/bin:/bin", "HOME": "/tmp", "TMPDIR": "/tmp",
                         "LANG": "C", "LC_ALL": "C"}, start_new_session=True,
                )
                proc.communicate(payload.encode("utf-8"), timeout=self.timeout_sec)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
                return {
                    "score": 0.0, "passed": False, "syntax_valid": None,
                    "error": "ExecutionTimeout", "extracted_code": extracted_code[:200],
                }
            except OSError as exc:
                return {
                    "score": 0.0, "passed": False, "syntax_valid": None,
                    "error": f"SandboxError: {exc}", "extracted_code": extracted_code[:200],
                }
            output.seek(0)
            stdout = output.read(1_048_576)
            sandbox_diagnostic = stdout.decode("utf-8", errors="replace")[-300:].strip()
            result_parse_failed = False
            try:
                result = json.loads(stdout.splitlines()[-1])
            except (json.JSONDecodeError, UnicodeDecodeError, IndexError):
                result = {"passed": False, "syntax_valid": None,
                          "error": "ProcessTerminatedWithoutResult"}
                result_parse_failed = True

        if not result_parse_failed and (
            not isinstance(result, dict) or not isinstance(result.get("passed"), bool)
            or not isinstance(result.get("syntax_valid"), bool)
        ):
            result = {"passed": False, "syntax_valid": None,
                      "error": "InvalidSandboxResult"}
        passed = proc.returncode == 0 and result.get("passed", False)
        syntax_valid = result["syntax_valid"]
        return {
            "score": 1.0 if passed else 0.0,
            "passed": passed,
            "syntax_valid": syntax_valid,
            "error": None if passed else result.get("error") or "SandboxProcessFailed",
            **({"sandbox_diagnostic": sandbox_diagnostic} if result_parse_failed
               and sandbox_diagnostic else {}),
            "extracted_code": extracted_code[:200],
        }
