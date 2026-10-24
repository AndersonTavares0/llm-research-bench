"""Code Synthesis Evaluator (HumanEval+ / MBPP+ methodology).

Evaluates functional correctness by executing generated Python functions against
unit tests inside an isolated execution sandbox with timeout control.
"""

import ast
import multiprocessing
import re
from typing import Any, Dict, List
from .base_evaluator import BaseEvaluator


def _run_test_in_sandbox(code: str, test_code: str, entry_point: str, queue: multiprocessing.Queue):
    """Worker process function to safely execute code without polluting main process."""
    sandbox_globals = {}
    try:
        # Compile candidate code
        compiled_code = compile(code, "<string>", "exec")
        exec(compiled_code, sandbox_globals)

        if entry_point not in sandbox_globals:
            queue.put({"passed": False, "error": f"Entry point '{entry_point}' not defined in output."})
            return

        # Execute test suite
        compiled_test = compile(test_code, "<string>", "exec")
        exec(compiled_test, sandbox_globals)

        # Run check function if standard HumanEval format
        if "check" in sandbox_globals:
            sandbox_globals["check"](sandbox_globals[entry_point])

        queue.put({"passed": True, "error": None})
    except AssertionError as ae:
        queue.put({"passed": False, "error": f"AssertionError: {str(ae)}"})
    except Exception as e:
        queue.put({"passed": False, "error": f"{type(e).__name__}: {str(e)}"})


class CodeEvaluator(BaseEvaluator):
    """Evaluates code generation on HumanEval+ and MBPP+ problems."""

    def __init__(self, timeout_sec: float = 3.0):
        self.timeout_sec = timeout_sec
        self.code_pattern = re.compile(r"```python\s*(.+?)```", re.DOTALL | re.IGNORECASE)

    def extract_code(self, response_text: str, entry_point: str) -> str:
        """Extract Python code containing the function definition."""
        blocks = self.code_pattern.findall(response_text)
        if blocks:
            # Check for block with entry_point
            for block in blocks:
                if f"def {entry_point}" in block:
                    return block
            return blocks[0]

        # If no markdown block, search for def entry_point
        if f"def {entry_point}" in response_text:
            lines = response_text.splitlines()
            code_lines = []
            capturing = False
            for line in lines:
                if f"def {entry_point}" in line:
                    capturing = True
                if capturing:
                    code_lines.append(line)
            return "\n".join(code_lines)

        return response_text

    def evaluate(self, item: Dict[str, Any], response_text: str, **kwargs) -> Dict[str, Any]:
        entry_point = item.get("entry_point", "solution")
        test_code = item.get("test", "")
        extracted_code = self.extract_code(response_text, entry_point)

        # 1. AST Syntax Check
        try:
            ast.parse(extracted_code)
            syntax_valid = True
        except SyntaxError as e:
            return {
                "score": 0.0,
                "passed": False,
                "syntax_valid": False,
                "error": f"SyntaxError: {str(e)}",
                "extracted_code": extracted_code[:200],
            }

        # 2. Execution against unit test assertions in sandbox
        queue = multiprocessing.Queue()
        proc = multiprocessing.Process(
            target=_run_test_in_sandbox,
            args=(extracted_code, test_code, entry_point, queue),
        )
        proc.start()
        proc.join(timeout=self.timeout_sec)

        if proc.is_alive():
            proc.terminate()
            proc.join()
            return {
                "score": 0.0,
                "passed": False,
                "syntax_valid": True,
                "error": "ExecutionTimeout",
                "extracted_code": extracted_code[:200],
            }

        if not queue.empty():
            res = queue.get()
            passed = res["passed"]
            err = res["error"]
        else:
            passed = False
            err = "ProcessTerminatedWithoutResult"

        return {
            "score": 1.0 if passed else 0.0,
            "passed": passed,
            "syntax_valid": True,
            "error": err,
            "extracted_code": extracted_code[:200],
        }
