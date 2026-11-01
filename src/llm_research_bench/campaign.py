"""Light orchestration around official benchmark tooling.

The benchmark definitions are not ours: EleutherAI lm-evaluation-harness owns
tasks, prompts, metrics and scoring, and llama.cpp owns inference plus its
standard performance measurement. This module only resolves campaign specs,
records provenance, drives the official CLIs and summarises their JSON output.

Usage (inside the lab container, with lm-eval and llama.cpp on PATH)::

    python -m llm_research_bench.campaign plan    --spec configs/campaigns/smoke.yaml
    python -m llm_research_bench.campaign run     --spec configs/campaigns/smoke.yaml
    python -m llm_research_bench.campaign summary --out results/campaigns
    python -m llm_research_bench.campaign audit   --root results
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "campaign/v1"
BACKENDS = {"gguf", "local-chat-completions"}

# Fields a campaign manifest must carry for a result to be re-analysable later.
MANIFEST_FIELDS = (
    "campaign",
    "hardware_profile",
    "status",
    "started_at_utc",
    "finished_at_utc",
    "environment",
    "runtime",
    "model",
    "server",
    "evaluation",
)

# Provenance that historical suites would have needed but never recorded.
LEGACY_FIELDS = (
    "timestamp",
    "hardware",
    "runtime",
    "model_revision",
    "quantization",
    "seed",
    "temperature",
    "n_repetitions",
    "confidence_interval",
)


class SpecError(ValueError):
    """Campaign specification is invalid or cannot be resolved."""


# --------------------------------------------------------------------------- #
# Spec loading and validation
# --------------------------------------------------------------------------- #


@dataclass
class ModelSpec:
    name: str
    file: str
    quantization: str
    hf_repo: str = ""
    hf_revision: str = ""
    license: str = ""
    alias: str = ""

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class TaskGroup:
    name: str
    backend: str
    tasks: list[str]

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class CampaignSpec:
    campaign: str
    hardware_profile: str
    models: list[ModelSpec]
    task_groups: list[TaskGroup]
    status: str = "measured"
    description: str = ""
    server: dict[str, Any] = field(default_factory=dict)
    bench: dict[str, Any] = field(default_factory=dict)
    evaluation: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "campaign": self.campaign,
            "hardware_profile": self.hardware_profile,
            "status": self.status,
            "description": self.description,
            "server": self.server,
            "bench": self.bench,
            "evaluation": self.evaluation,
            "models": [m.as_dict() for m in self.models],
            "task_groups": [g.as_dict() for g in self.task_groups],
        }


def load_spec(path: str | Path) -> CampaignSpec:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SpecError(f"{path}: expected a YAML mapping at top level")

    try:
        models = [
            ModelSpec(
                name=str(m["name"]),
                file=str(m["file"]),
                quantization=str(m.get("quantization", "unknown")),
                hf_repo=str(m.get("hf_repo", "")),
                hf_revision=str(m.get("hf_revision", "")),
                license=str(m.get("license", "")),
                alias=str(m.get("alias", m["name"])),
            )
            for m in raw.get("models") or []
        ]
        groups = [
            TaskGroup(
                name=str(g["name"]),
                backend=str(g["backend"]),
                tasks=[str(t) for t in g.get("tasks") or []],
            )
            for g in raw.get("task_groups") or []
        ]
    except (KeyError, TypeError) as exc:
        raise SpecError(f"{path}: malformed model/task_group entry ({exc})") from exc

    spec = CampaignSpec(
        campaign=str(raw.get("campaign", "")),
        hardware_profile=str(raw.get("hardware_profile", "")),
        models=models,
        task_groups=groups,
        status=str(raw.get("status", "measured")),
        description=str(raw.get("description", "")),
        server=dict(raw.get("server") or {}),
        bench=dict(raw.get("bench") or {}),
        evaluation=dict(raw.get("evaluation") or {}),
    )
    errors = validate_spec(spec)
    if errors:
        raise SpecError(f"{path}: " + "; ".join(errors))
    return spec


def validate_spec(spec: CampaignSpec) -> list[str]:
    errors: list[str] = []
    if not spec.campaign:
        errors.append("campaign id is required")
    if not spec.hardware_profile:
        errors.append("hardware_profile is required (results must never mix hardware)")
    if spec.status not in {"measured", "estimated", "hypothesis"}:
        errors.append(f"status must be measured|estimated|hypothesis, got {spec.status!r}")
    if not spec.models:
        errors.append("at least one model is required")
    if not spec.task_groups:
        errors.append("at least one task_group is required")

    names = [m.name for m in spec.models]
    for dup in {n for n in names if names.count(n) > 1}:
        errors.append(f"duplicate model name {dup!r}")
    for model in spec.models:
        if not model.file:
            errors.append(f"model {model.name!r} needs a file")
        if not model.quantization or model.quantization == "unknown":
            errors.append(f"model {model.name!r} needs an explicit quantization")

    group_names = [g.name for g in spec.task_groups]
    for dup in {n for n in group_names if group_names.count(n) > 1}:
        errors.append(f"duplicate task_group name {dup!r}")
    for group in spec.task_groups:
        if group.backend not in BACKENDS:
            errors.append(f"group {group.name!r}: backend must be one of {sorted(BACKENDS)}")
        if not group.tasks:
            errors.append(f"group {group.name!r} has no tasks")

    limit = spec.evaluation.get("limit")
    if limit is not None and (not isinstance(limit, int) or limit <= 0):
        errors.append(f"evaluation.limit must be a positive integer, got {limit!r}")
    if not isinstance(spec.evaluation.get("seed", 0), int):
        errors.append("evaluation.seed must be an integer")
    port = spec.server.get("port", 8090)
    if not isinstance(port, int) or not 0 < port < 65536:
        errors.append(f"server.port must be a TCP port, got {port!r}")
    return errors


def resolve_model_path(spec: ModelSpec, models_dir: str | Path) -> Path:
    path = Path(spec.file)
    return path if path.is_absolute() else Path(models_dir) / path


# --------------------------------------------------------------------------- #
# Hashing and provenance
# --------------------------------------------------------------------------- #


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def config_hash(payload: Any) -> str:
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()[:16]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path, cache_file: Path | None = None) -> str:
    """SHA-256 of a model file, cached by (path, size, mtime)."""
    cache: dict[str, Any] = {}
    if cache_file and cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache = {}
    stat = path.stat()
    key = f"{path.resolve()}:{stat.st_size}:{int(stat.st_mtime)}"
    if key in cache:
        return str(cache[key])

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    value = digest.hexdigest()
    if cache_file:
        cache[key] = value
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
    return value


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def collect_environment() -> dict[str, Any]:
    env: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^model name\s*:\s*(.+)$", cpuinfo, re.MULTILINE)
        if match:
            env["cpu_model"] = match.group(1).strip()
    except OSError:
        pass
    try:
        meminfo = Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^MemTotal:\s*(\d+) kB", meminfo, re.MULTILINE)
        if match:
            env["ram_mib"] = round(int(match.group(1)) / 1024)
    except OSError:
        pass
    env["gpu"] = query_gpu()
    return env


_LLAMA_DEVICE_RE = re.compile(
    r"^\s*(CUDA\d+):\s+(.+?)\s+\((\d+) MiB,\s*(\d+) MiB free\)$", re.MULTILINE
)


def _gpus_from_llama() -> list[dict[str, Any]]:
    exe = shutil.which("llama-server")
    if not exe:
        return []
    try:
        proc = subprocess.run(
            [exe, "--list-devices"], capture_output=True, text=True, timeout=120, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return []
    gpus = []
    for ident, name, total, free in _LLAMA_DEVICE_RE.findall(proc.stdout or ""):
        gpus.append(
            {"id": ident, "name": name, "memory_total": f"{total} MiB", "memory_free": f"{free} MiB"}
        )
    return gpus


def query_gpu() -> dict[str, Any]:
    """Best-effort GPU identity; absence is recorded, not hidden.

    nvidia-smi is not present in the sandbox image, so llama.cpp's own device
    listing is the fallback and the manifest says which source was used.
    """
    exe = shutil.which("nvidia-smi")
    if not exe:
        gpus = _gpus_from_llama()
        if gpus:
            return {"available": True, "source": "llama-server --list-devices", "devices": gpus}
        return {"available": False, "reason": "no nvidia-smi and no llama.cpp device listing"}
    query = "name,memory.total,memory.used,driver_version,compute_cap"
    try:
        proc = subprocess.run(
            [exe, f"--query-gpu={query}", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - env specific
        return {"available": False, "reason": str(exc)}
    if proc.returncode != 0:
        return {"available": False, "reason": _first_line(proc.stderr) or "nvidia-smi failed"}
    gpus = []
    for line in proc.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 5:
            gpus.append(
                {
                    "name": parts[0],
                    "memory_total": parts[1],
                    "memory_used": parts[2],
                    "driver": parts[3],
                    "compute_cap": parts[4],
                }
            )
    return {"available": bool(gpus), "source": "nvidia-smi", "devices": gpus}


def binary_version(executable: str, *args: str) -> str:
    exe = shutil.which(executable)
    if not exe:
        return f"{executable}: not found"
    try:
        proc = subprocess.run(
            [exe, *args], capture_output=True, text=True, timeout=120, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - env specific
        return f"{executable}: {exc}"
    text = (proc.stdout or "") + (proc.stderr or "")
    return _first_line(text) or f"{executable}: no version output"


def lm_eval_version() -> str:
    """Version from package metadata: the 0.4.x CLI has no --version flag."""
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "import importlib.metadata as m; print('lm-eval', m.version('lm-eval'))",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - env specific
        return "lm_eval: not installed"
    if proc.returncode != 0:
        return "lm_eval: not installed"
    return _first_line(proc.stdout or "") or "lm_eval: unknown"


# --------------------------------------------------------------------------- #
# Command construction
# --------------------------------------------------------------------------- #


def build_server_cmd(
    binary: str,
    model_path: Path,
    alias: str,
    server: dict[str, Any],
) -> list[str]:
    return [
        binary,
        "-m",
        str(model_path),
        "--host",
        "127.0.0.1",
        "--port",
        str(server.get("port", 8090)),
        "--ctx-size",
        str(server.get("ctx_size", 4096)),
        "--n-gpu-layers",
        str(server.get("gpu_layers", 99)),
        "--threads",
        str(server.get("threads", 2)),
        "--alias",
        alias,
        "--parallel",
        str(server.get("parallel", 1)),
        "--jinja",
        "--no-webui",
    ]


def build_bench_cmd(binary: str, model_path: Path, bench: dict[str, Any]) -> list[str]:
    return [
        binary,
        "-m",
        str(model_path),
        "-p",
        str(bench.get("prompt_tokens", 512)),
        "-n",
        str(bench.get("gen_tokens", 128)),
        "-r",
        str(bench.get("repetitions", 3)),
        "-ngl",
        str(bench.get("gpu_layers", 99)),
        "-o",
        "json",
    ]


def build_lm_eval_cmd(
    task_group: TaskGroup,
    model_alias: str,
    port: int,
    evaluation: dict[str, Any],
    output_path: Path,
) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "lm_eval",
        "--model",
        task_group.backend,
        "--tasks",
        ",".join(task_group.tasks),
        "--limit",
        str(evaluation.get("limit", 20)),
        "--seed",
        str(evaluation.get("seed", 42)),
        "--num_fewshot",
        str(evaluation.get("num_fewshot", 0)),
        "--batch_size",
        str(evaluation.get("batch_size", 1)),
        "--output_path",
        str(output_path),
        "--log_samples",
    ]
    if task_group.backend == "gguf":
        model_args = (
            f"base_url=http://127.0.0.1:{port}"
            f",max_length={evaluation.get('max_length', 2048)}"
            f",max_gen_toks={evaluation.get('max_gen_toks', 256)}"
            ",temperature=0.0"
        )
    else:
        model_args = (
            f"model={model_alias},base_url=http://127.0.0.1:{port}/v1/chat/completions"
        )
    return cmd + ["--model_args", model_args]


# --------------------------------------------------------------------------- #
# llama.cpp server lifecycle
# --------------------------------------------------------------------------- #


class LlamaServer:
    """Context manager around the official llama-server binary."""

    def __init__(self, cmd: list[str], port: int, log_path: Path, timeout_s: int = 300):
        self.cmd = cmd
        self.port = port
        self.log_path = log_path
        self.timeout_s = timeout_s
        self.proc: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> "LlamaServer":
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log = self.log_path.open("wb")
        self.proc = subprocess.Popen(self.cmd, stdout=self._log, stderr=subprocess.STDOUT)
        try:
            self.wait_ready()
        except Exception:
            self.__exit__(*sys.exc_info())
            raise
        return self

    def wait_ready(self) -> None:
        assert self.proc is not None
        deadline = time.monotonic() + self.timeout_s
        url = f"http://127.0.0.1:{self.port}/health"
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    f"llama-server exited with {self.proc.returncode}; see {self.log_path}"
                )
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(2)
        raise RuntimeError(f"llama-server not ready after {self.timeout_s}s; see {self.log_path}")

    def __exit__(self, *exc_info: Any) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=10)
        if getattr(self, "_log", None):
            self._log.close()


# --------------------------------------------------------------------------- #
# Campaign execution
# --------------------------------------------------------------------------- #


def run_key(model: ModelSpec, group: TaskGroup, spec: CampaignSpec, runtime: dict[str, Any]) -> str:
    """Identity of a (model, task group) measurement; a changed key must re-run."""
    return config_hash(
        {
            "schema": SCHEMA_VERSION,
            "model": {"file": model.file, "quantization": model.quantization, "alias": model.alias},
            "group": group.as_dict(),
            "evaluation": spec.evaluation,
            "server": spec.server,
            "runtime": runtime,
        }
    )


def existing_result(group_dir: Path, key: str) -> bool:
    meta = group_dir / "meta.json"
    if not (group_dir / "results.json").exists() or not meta.exists():
        return False
    try:
        recorded = json.loads(meta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return recorded.get("run_key") == key and recorded.get("status") == "measured"


def find_results_json(raw_dir: Path) -> Path:
    if raw_dir.is_file() and raw_dir.suffix == ".json":
        return raw_dir
    candidates = sorted(raw_dir.rglob("results*.json"))
    if not candidates:
        candidates = sorted(raw_dir.rglob("*.json"))
    for candidate in reversed(candidates):
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(payload, dict) and "results" in payload:
            return candidate
    raise FileNotFoundError(f"no lm-eval results JSON under {raw_dir}")


def _tail(path: Path, lines: int = 40) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


def run_command(cmd: list[str], log_path: Path, timeout: int | None = None) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("wb") as log:
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
    return proc.returncode


def parse_llama_bench_output(text: str) -> list[dict[str, Any]]:
    """Extract llama-bench's JSON array from stdout that may include diagnostics."""
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "[":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list) and payload and all(
            isinstance(row, dict)
            and isinstance(row.get("avg_ts"), (int, float))
            and (row.get("n_prompt", 0) or row.get("n_gen", 0))
            for row in payload
        ):
            return payload
    raise ValueError("llama-bench output contains no valid JSON result records")


def valid_llama_bench_json(path: Path) -> bool:
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(
        isinstance(records, list)
        and records
        and all(
            isinstance(row, dict)
            and isinstance(row.get("avg_ts"), (int, float))
            and (row.get("n_prompt", 0) or row.get("n_gen", 0))
            for row in records
        )
    )


def check_tasks_available(groups: list[TaskGroup]) -> None:
    """Fail before touching the GPU if a task id is wrong for this harness version."""
    wanted = sorted({task for group in groups for task in group.tasks})
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "lm_eval", "ls", "tasks"],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - env specific
        raise SpecError(f"cannot list lm-eval tasks: {exc}") from exc
    listing = (proc.stdout or "") + (proc.stderr or "")
    # `ls tasks` prints a padded markdown table: rows look like "|name   |path|type|".
    missing = [task for task in wanted if not re.search(rf"(?m)^\|\s*{re.escape(task)}\s*\|", listing)]
    if missing:
        raise SpecError(
            f"tasks not found in this lm-eval version: {', '.join(missing)} "
            "(check `lm_eval ls tasks`)"
        )


def run_campaign(
    spec: CampaignSpec,
    *,
    out_dir: Path,
    models_dir: Path,
    llama_server: str = "llama-server",
    llama_bench: str = "llama-bench",
    force: bool = False,
    bench: bool = True,
    evaluate: bool = True,
) -> dict[str, Any]:
    campaign_dir = out_dir / spec.campaign / spec.hardware_profile
    campaign_dir.mkdir(parents=True, exist_ok=True)
    lock_file = campaign_dir / ".models.lock.json"

    runtime = {
        "llama_cpp": binary_version(llama_server, "--version"),
        "llama_bench": binary_version(llama_bench, "--help"),
        "lm_eval": lm_eval_version(),
        "schema": SCHEMA_VERSION,
    }
    environment = collect_environment()
    manifest_base = {
        "campaign": spec.campaign,
        "hardware_profile": spec.hardware_profile,
        "status": spec.status,
        "environment": environment,
        "runtime": runtime,
        "server": spec.server,
        "evaluation": spec.evaluation,
    }

    summary: dict[str, Any] = {
        "campaign": spec.campaign,
        "hardware_profile": spec.hardware_profile,
        "status": spec.status,
        "manifest": manifest_base,
        "model_files": {},
        "bench": [],
        "groups": [],
    }

    for model in spec.models:
        model_path = resolve_model_path(model, models_dir)
        if not model_path.exists():
            raise SpecError(f"model file not found: {model_path}")
        sha = sha256_file(model_path, cache_file=lock_file)
        summary["model_files"][model.name] = {
            "path": str(model_path),
            "size_bytes": model_path.stat().st_size,
            "sha256": sha,
            **model.as_dict(),
        }

        model_dir = campaign_dir / model.name
        model_dir.mkdir(parents=True, exist_ok=True)

        if bench:
            bench_dir = model_dir / "llama-bench"
            bench_json = bench_dir / "results.json"
            bench_meta = bench_dir / "meta.json"
            try:
                prior_bench_meta = json.loads(bench_meta.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                prior_bench_meta = {}
            if (
                force
                or prior_bench_meta.get("status") != "measured"
                or not valid_llama_bench_json(bench_json)
            ):
                bench_dir.mkdir(parents=True, exist_ok=True)
                cmd = build_bench_cmd(llama_bench, model_path, spec.bench)
                started = utc_now()
                code = run_command(cmd, bench_dir / "run.log")
                manifest = {
                    **manifest_base,
                    "model": summary["model_files"][model.name],
                    "bench": spec.bench,
                    "command": cmd,
                    "started_at_utc": started,
                    "finished_at_utc": utc_now(),
                    "exit_code": code,
                    "status": "measured" if code == 0 else "failed",
                }
                if code == 0:
                    try:
                        records = parse_llama_bench_output(
                            (bench_dir / "run.log").read_text(encoding="utf-8", errors="replace")
                        )
                        bench_json.write_text(json.dumps(records, indent=2), encoding="utf-8")
                    except (OSError, ValueError) as exc:
                        manifest["status"] = "failed"
                        manifest["error"] = str(exc)
                if manifest["status"] != "measured":
                    manifest["stderr_tail"] = _tail(bench_dir / "run.log")
                    bench_meta.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                    summary["bench"].append(
                        {"model": model.name, "error": manifest.get("error", manifest["stderr_tail"])}
                    )
                else:
                    bench_meta.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                    summary["bench"].append({"model": model.name, "raw": str(bench_json)})
            else:
                summary["bench"].append({"model": model.name, "raw": str(bench_json)})
        if not evaluate:
            continue

        pending = []
        for group in spec.task_groups:
            key = run_key(model, group, spec, runtime)
            group_dir = model_dir / group.name
            if not force and existing_result(group_dir, key):
                summary["groups"].append(
                    {"model": model.name, "group": group.name, "status": "skipped", "run_key": key}
                )
                continue
            pending.append((group, group_dir, key))

        if not pending:
            continue

        cmd = build_server_cmd(
            llama_server, model_path, model.alias or model.name, spec.server
        )
        port = int(spec.server.get("port", 8090))
        timeout_s = int(spec.server.get("startup_timeout_s", 300))
        with LlamaServer(cmd, port, model_dir / "llama-server.log", timeout_s) as server:
            for group, group_dir, key in pending:
                group_dir.mkdir(parents=True, exist_ok=True)
                raw_dir = group_dir / "raw"
                raw_dir.mkdir(parents=True, exist_ok=True)
                eval_cmd = build_lm_eval_cmd(
                    group, model.alias or model.name, port, spec.evaluation, raw_dir
                )
                started = utc_now()
                try:
                    code = run_command(eval_cmd, group_dir / "run.log")
                except subprocess.TimeoutExpired:
                    code = -1
                finished = utc_now()
                manifest = {
                    **manifest_base,
                    "model": summary["model_files"][model.name],
                    "task_group": group.as_dict(),
                    "server_command": cmd,
                    "command": eval_cmd,
                    "run_key": key,
                    "started_at_utc": started,
                    "finished_at_utc": finished,
                    "exit_code": code,
                    "status": "measured" if code == 0 else "failed",
                }
                if code == 0:
                    try:
                        found = find_results_json(raw_dir)
                        shutil.copyfile(found, group_dir / "results.json")
                    except FileNotFoundError as exc:
                        manifest["status"] = "failed"
                        manifest["error"] = str(exc)
                else:
                    manifest["stderr_tail"] = _tail(group_dir / "run.log")
                (group_dir / "meta.json").write_text(
                    json.dumps(manifest, indent=2), encoding="utf-8"
                )
                summary["groups"].append(
                    {
                        "model": model.name,
                        "group": group.name,
                        "status": manifest["status"],
                        "run_key": key,
                        "dir": str(group_dir),
                    }
                )
        summary["groups"].append({"model": model.name, "group": "_server", "port": port})

    (campaign_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


# --------------------------------------------------------------------------- #
# Analysis of official outputs
# --------------------------------------------------------------------------- #

PRIMARY_METRICS = (
    "acc,none",
    "acc_norm,none",
    "exact_match,strict-match",
    "exact_match,flexible-extract",
    "inst_level_strict_acc,none",
    "prompt_level_strict_acc,none",
)


def wilson_interval(value: float, n: int, z: float = 1.96) -> list[float] | None:
    """95% Wilson score interval; deterministic, valid for small samples."""
    if n <= 0 or not 0.0 <= value <= 1.0:
        return None
    denominator = 1 + z * z / n
    centre = (value + z * z / (2 * n)) / denominator
    half = z * math.sqrt(value * (1 - value) / n + z * z / (4 * n * n)) / denominator
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def _sample_count(task_result: dict[str, Any], fallback: int | None) -> int:
    counts = task_result.get("n-samples") or {}
    if isinstance(counts, dict) and isinstance(counts.get("effective"), int):
        return counts["effective"]
    alias = task_result.get("alias")
    if isinstance(alias, str) and alias.isdigit():
        return int(alias)
    return fallback or 0


def summarize(out_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    bench_rows: list[dict[str, Any]] = []
    campaigns: set[str] = set()

    for results_path in sorted(out_dir.rglob("results.json")):
        group_dir = results_path.parent
        meta_path = group_dir / "meta.json"
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = {}
        if meta.get("status") not in (None, "measured"):
            continue
        try:
            payload = json.loads(results_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, dict):
            continue
        results = payload.get("results") or {}
        limit = (meta.get("evaluation") or {}).get("limit")
        model = (meta.get("model") or {}).get("name") or group_dir.parent.name
        hardware = meta.get("hardware_profile") or group_dir.parent.parent.name
        campaign = meta.get("campaign") or group_dir.parent.parent.parent.name
        campaigns.add(campaign)
        for task, task_result in results.items():
            if not isinstance(task_result, dict):
                continue
            n = _sample_count(task_result, limit)
            metrics = [k for k in PRIMARY_METRICS if isinstance(task_result.get(k), (int, float))]
            if not metrics:
                metrics = [
                    k
                    for k, v in sorted(task_result.items())
                    if k.endswith(",none") and isinstance(v, (int, float)) and "stderr" not in k
                ]
            for metric in metrics:
                value = float(task_result[metric])
                rows.append(
                    {
                        "campaign": campaign,
                        "hardware_profile": hardware,
                        "model": model,
                        "task": task,
                        "metric": metric,
                        "value": round(value, 4),
                        "n": n,
                        "ci95": wilson_interval(value, n),
                        "status": meta.get("status", "measured"),
                    }
                )

    for bench_path in sorted(out_dir.rglob("llama-bench/results.json")):
        try:
            payload = json.loads(bench_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        records = payload.get("results") if isinstance(payload, dict) else payload
        if not isinstance(records, list):
            continue
        try:
            meta = json.loads((bench_path.parent / "meta.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
        if meta.get("status") != "measured":
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            bench_rows.append(
                {
                    "campaign": meta.get("campaign", bench_path.parents[3].name),
                    "hardware_profile": meta.get("hardware_profile", bench_path.parents[2].name),
                    "model": bench_path.parent.parent.name,
                    "n_prompt": record.get("n_prompt"),
                    "n_gen": record.get("n_gen"),
                    "avg_ts": record.get("avg_ts"),
                    "stddev_ts": record.get("stddev_ts"),
                    "build": record.get("build_commit") or record.get("build_number"),
                    "gpu": record.get("gpu_info"),
                    "backends": record.get("backends"),
                }
            )

    return {
        "generated_at_utc": utc_now(),
        "campaigns": sorted(c for c in campaigns if c),
        "note": (
            "Zeros-CI colunas usam Wilson 95%. Amostras pequenas (limit por tarefa) "
            "descrevem esta campanha e não autorizam ranking entre modelos."
        ),
        "quality": rows,
        "performance": bench_rows,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Resultados de campanha (gerado automaticamente)",
        "",
        f"Gerado em {summary['generated_at_utc']} a partir de saídas oficiais do "
        "lm-evaluation-harness e do llama-bench.",
        "",
        f"> {summary['note']}",
        "",
    ]
    quality = summary.get("quality") or []
    if quality:
        lines += ["## Qualidade (lm-evaluation-harness)", ""]
        lines += [
            "| campanha | hardware | modelo | tarefa | métrica | valor | n | IC95% |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for row in quality:
            ci = row.get("ci95")
            ci_text = f"[{ci[0]:.3f}, {ci[1]:.3f}]" if ci else "—"
            lines.append(
                f"| {row['campaign']} | {row['hardware_profile']} | {row['model']} | "
                f"{row['task']} | {row['metric']} | {row['value']:.3f} | {row['n']} | {ci_text} |"
            )
        lines.append("")
    performance = summary.get("performance") or []
    if performance:
        lines += ["## Desempenho (llama-bench)", ""]
        lines += [
            "| modelo | prompt | geração | tok/s médio | desvio | build | GPU | backends |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for row in performance:
            avg = row.get("avg_ts")
            std = row.get("stddev_ts")
            lines.append(
                f"| {row['model']} | {row['n_prompt']} | {row['n_gen']} | "
                f"{avg:.2f} | {std:.2f} | {row['build']} | {row['gpu']} | {row['backends']} |"
                if isinstance(avg, (int, float)) and isinstance(std, (int, float))
                else f"| {row['model']} | {row['n_prompt']} | {row['n_gen']} | — | — | "
                f"{row['build']} | {row['gpu']} | {row['backends']} |"
            )
        lines.append("")
    if not quality and not performance:
        lines.append("_Nenhum resultado encontrado._")
    return "\n".join(lines) + "\n"


def audit_results(root: Path) -> list[dict[str, Any]]:
    """Report missing provenance instead of rewriting historical numbers."""
    findings: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.json")):
        if ".models.lock" in path.name or "raw" in path.parts:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, dict):
            continue
        if "manifest" in payload or ("campaign" in payload and "model_files" in payload):
            present = payload.get("manifest") or payload
            missing = [f for f in MANIFEST_FIELDS if not present.get(f)]
            findings.append({"file": str(path), "format": "campaign/v1", "missing": missing})
        elif "models_evaluated" in payload or "results" in payload:
            top_keys = set(payload)
            missing = [f for f in LEGACY_FIELDS if f not in top_keys]
            findings.append({"file": str(path), "format": "legacy", "missing": missing})
    return findings


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _cmd_plan(args: argparse.Namespace) -> int:
    spec = load_spec(args.spec)
    models_dir = Path(args.models_dir)
    payload = {
        "spec": spec.as_dict(),
        "models": [
            {
                "name": model.name,
                "path": str(resolve_model_path(model, models_dir)),
                "exists": resolve_model_path(model, models_dir).exists(),
                "server_cmd": build_server_cmd(
                    args.llama_server,
                    resolve_model_path(model, models_dir),
                    model.alias or model.name,
                    spec.server,
                ),
                "bench_cmd": build_bench_cmd(
                    args.llama_bench, resolve_model_path(model, models_dir), spec.bench
                ),
            }
            for model in spec.models
        ],
        "lm_eval": [
            {
                "group": group.name,
                "task_group": group.as_dict(),
                "cmd": build_lm_eval_cmd(
                    group,
                    spec.models[0].alias or spec.models[0].name,
                    int(spec.server.get("port", 8090)),
                    spec.evaluation,
                    Path("<out>") / spec.campaign / spec.hardware_profile / spec.models[0].name / group.name / "raw",
                ),
            }
            for group in spec.task_groups
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    spec = load_spec(args.spec)
    if not args.skip_task_check:
        check_tasks_available(spec.task_groups)
    summary = run_campaign(
        spec=spec,
        out_dir=Path(args.out),
        models_dir=Path(args.models_dir),
        llama_server=args.llama_server,
        llama_bench=args.llama_bench,
        force=args.force,
        bench=not args.no_bench,
        evaluate=not args.no_eval,
    )
    failed = [g for g in summary["groups"] if g.get("status") == "failed"]
    failed_bench = [b for b in summary["bench"] if b.get("error")]
    print(
        json.dumps(
            {"campaign": spec.campaign, "failed": failed, "failed_bench": failed_bench},
            indent=2,
        )
    )
    return 1 if failed or failed_bench else 0


def _cmd_summary(args: argparse.Namespace) -> int:
    out = Path(args.out)
    summary = summarize(out)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
    print(render_markdown(summary))
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    findings = audit_results(Path(args.root))
    print(f"{'arquivo':60} {'formato':12} campos ausentes")
    for item in findings:
        print(f"{item['file'][-60:]:60} {item['format']:12} {', '.join(item['missing']) or '-'}")
    print(f"\n{len(findings)} arquivo(s) analisado(s).")
    if args.strict and any(item["missing"] for item in findings):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="llm_research_bench.campaign",
        description="Orchestrate official benchmarks (llama.cpp + lm-evaluation-harness).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="validate a spec and print resolved commands")
    plan.add_argument("--spec", required=True)
    plan.add_argument("--models-dir", default="/models")
    plan.add_argument("--llama-server", default="llama-server")
    plan.add_argument("--llama-bench", default="llama-bench")
    plan.set_defaults(func=_cmd_plan)

    run = sub.add_parser("run", help="execute a campaign, resuming finished work")
    run.add_argument("--spec", required=True)
    run.add_argument("--out", default="results/campaigns")
    run.add_argument("--models-dir", default="/models")
    run.add_argument("--llama-server", default="llama-server")
    run.add_argument("--llama-bench", default="llama-bench")
    run.add_argument("--force", action="store_true")
    run.add_argument("--no-bench", action="store_true")
    run.add_argument("--no-eval", action="store_true")
    run.add_argument("--skip-task-check", action="store_true")
    run.set_defaults(func=_cmd_run)

    summary = sub.add_parser("summary", help="aggregate official outputs into tables")
    summary.add_argument("--out", default="results/campaigns")
    summary.set_defaults(func=_cmd_summary)

    audit = sub.add_parser("audit", help="report provenance gaps in stored results")
    audit.add_argument("--root", default="results")
    audit.add_argument("--strict", action="store_true", help="exit 1 when fields are missing")
    audit.set_defaults(func=_cmd_audit)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
