"""Agentic and Function Calling Evaluator (BFCL / AgentDojo methodology).

Evaluates schema adherence, tool selection accuracy, argument type validity,
and vulnerability to indirect tool-based injection attacks.
"""

import json
import re
from typing import Any, Dict, List, Optional
from .base_evaluator import BaseEvaluator


class AgentEvaluator(BaseEvaluator):
    """Evaluates agentic function calling against strict schemas."""

    def extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from OpenAI-compatible JSON response or markdown blocks."""
        # 1. Native API tool_calls object
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices and "message" in choices[0]:
                msg = choices[0]["message"]
                if "tool_calls" in msg and msg["tool_calls"]:
                    extracted = []
                    for tc in msg["tool_calls"]:
                        fn = tc.get("function", {})
                        name = fn.get("name", "")
                        args_raw = fn.get("arguments", "{}")
                        try:
                            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                        except json.JSONDecodeError:
                            args = {"_raw_invalid_json": args_raw}
                        extracted.append({"name": name, "arguments": args})
                    return extracted

        # 2. Text-based JSON fallback in content
        text = response if isinstance(response, str) else ""
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices and "message" in choices[0]:
                text = choices[0]["message"].get("content", "") or ""

        # Search for ```json blocks containing name and arguments
        json_pattern = re.compile(r"```(?:json)?\s*(\{.+?\})\s*```", re.DOTALL)
        matches = json_pattern.findall(text)
        extracted = []
        for match in matches:
            try:
                parsed = json.loads(match)
                if "name" in parsed and "arguments" in parsed:
                    extracted.append(parsed)
                elif "function" in parsed:
                    extracted.append(parsed["function"])
            except json.JSONDecodeError:
                pass

        return extracted

    def validate_schema(self, tool_call: Dict[str, Any], tool_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate function arguments against the JSON Schema parameter definition."""
        expected_params = tool_schema.get("parameters", {})
        required_keys = set(expected_params.get("required", []))
        properties = expected_params.get("properties", {})

        actual_args = tool_call.get("arguments", {})
        if not isinstance(actual_args, dict):
            return {"valid": False, "error": "Arguments must be a valid JSON object"}

        actual_keys = set(actual_args.keys())

        # Check required fields
        missing_required = required_keys - actual_keys
        if missing_required:
            return {"valid": False, "error": f"Missing required parameters: {list(missing_required)}"}

        # Check type correctness for present fields
        for key, val in actual_args.items():
            if key in properties:
                prop_type = properties[key].get("type")
                if prop_type == "string" and not isinstance(val, str):
                    return {"valid": False, "error": f"Parameter '{key}' expected string, got {type(val).__name__}"}
                elif prop_type == "integer" and (not isinstance(val, int) or isinstance(val, bool)):
                    return {"valid": False, "error": f"Parameter '{key}' expected integer, got {type(val).__name__}"}
                elif prop_type == "number" and (not isinstance(val, (int, float)) or isinstance(val, bool)):
                    return {"valid": False, "error": f"Parameter '{key}' expected number, got {type(val).__name__}"}
                elif prop_type == "boolean" and not isinstance(val, bool):
                    return {"valid": False, "error": f"Parameter '{key}' expected boolean, got {type(val).__name__}"}

        return {"valid": True, "error": None}

    def evaluate(self, item: Dict[str, Any], response: Any, **kwargs) -> Dict[str, Any]:
        expected_tool = item.get("expected_tool")
        expected_args = item.get("expected_args", {})
        tool_schemas = {t["name"]: t for t in item.get("available_tools", [])}

        extracted_calls = self.extract_tool_calls(response)
        if not extracted_calls:
            return {
                "score": 0.0,
                "passed": False,
                "tool_called": None,
                "error": "NoToolCallGenerated",
                "schema_valid": False,
            }

        first_call = extracted_calls[0]
        called_name = first_call.get("name")
        called_args = first_call.get("arguments", {})

        # Verify tool selection
        tool_match = (called_name == expected_tool) if expected_tool else True

        # Verify against schema
        schema_valid = False
        schema_err = None
        if called_name in tool_schemas:
            schema_res = self.validate_schema(first_call, tool_schemas[called_name])
            schema_valid = schema_res["valid"]
            schema_err = schema_res["error"]
        else:
            schema_err = f"Tool '{called_name}' not defined in tool_schemas"

        # Verify expected arguments
        args_match = True
        for k, v in expected_args.items():
            if called_args.get(k) != v:
                args_match = False
                break

        passed = tool_match and schema_valid and args_match
        return {
            "score": 1.0 if passed else 0.0,
            "passed": passed,
            "called_name": called_name,
            "tool_match": tool_match,
            "schema_valid": schema_valid,
            "schema_error": schema_err,
            "args_match": args_match,
            "total_calls": len(extracted_calls),
        }
