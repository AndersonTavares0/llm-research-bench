"""Sequential sweep runner for constrained-GPU experiments.

One approved lease, several campaign cells: each cell rewrites the server
context/KV settings, measures throughput with llama-bench, and samples GPU
memory at 1 Hz into its own CSV. Everything runs through ``campaign.run_campaign``
so provenance, resume keys and manifests stay identical to a single campaign.

Usage (inside a gpu-lab job)::

    python -m llm_research_bench.sweep generate --base configs/campaigns/...yaml \
        --grid ctx=2048,4096 --kv f16,q8_0 --out /workspace/results/sweep
    python -m llm_research_bench.sweep analyze --root /workspace/results/sweep
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable

import yaml

KV_CACHE_TYPES = {"f16": "f16", "q8_0": "q8_0"}


def expand_grid(
    base: dict[str, Any],
    contexts: list[int],
    kv_types: list[str],
    layers: list[int] | None = None,
    parallels: list[int] | None = None,
    suffix: str = "",
) -> list[dict[str, Any]]:
    """One spec per cell; the campaign name carries every swept setting."""
    specs: list[dict[str, Any]] = []
    for ctx in contexts:
      for kv in kv_types:
        for n_layers in layers or [None]:
          for n_parallel in parallels or [None]:
            if kv not in KV_CACHE_TYPES:
                raise ValueError(f"unsupported KV type {kv!r}")
            spec = json.loads(json.dumps(base))  # deep copy
            cell = f"-ctx{ctx}-kv{kv}"
            if n_layers is not None:
                cell += f"-layers{n_layers}"
            if n_parallel is not None:
                cell += f"-par{n_parallel}"
            spec["campaign"] = f"{base['campaign']}{suffix}{cell}"
            spec.setdefault("server", {})
            spec["server"]["ctx_size"] = ctx
            spec["server"]["cache_type_k"] = KV_CACHE_TYPES[kv]
            spec["server"]["cache_type_v"] = KV_CACHE_TYPES[kv]
            spec["server"]["cache_ram"] = spec["server"].get("cache_ram", 0)
            if n_layers is not None:
                spec["server"]["gpu_layers"] = n_layers
                # llama-bench takes its own -ngl; without this the sweep would
                # measure full offload in every cell.
                spec.setdefault("bench", {})["gpu_layers"] = n_layers
            if n_parallel is not None:
                spec["server"]["parallel"] = n_parallel
            spec["description"] = (
                f"{base.get('description', '')} [ctx={ctx}, kv={kv}"
                f"{f', layers={n_layers}' if n_layers is not None else ''}"
                f"{f', parallel={n_parallel}' if n_parallel is not None else ''}]"
            )
            specs.append(spec)
    return specs


def _vram_used_mib() -> float | None:
    exe = shutil.which("nvidia-smi")
    if exe:
        try:
            out = subprocess.run(
                [exe, "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5, check=True,
            ).stdout.strip()
            return float(out.splitlines()[0])
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    try:  # the lab image ships torch but not always nvidia-smi
        import torch

        free, total = torch.cuda.mem_get_info()
        return round((total - free) / 1024**2, 1)
    except Exception:
        return None


def sample_memory(path: Path, stop: threading.Event, interval: float = 1.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["utc", "vram_used_mib"])
        while not stop.is_set():
            value = _vram_used_mib()
            if value is not None:
                writer.writerow([time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), value])
                handle.flush()
            stop.wait(interval)


def peak_vram(csv_path: Path) -> float | None:
    try:
        with csv_path.open(encoding="utf-8") as handle:
            values = [float(row["vram_used_mib"]) for row in csv.DictReader(handle)]
    except (OSError, KeyError, ValueError):
        return None
    return max(values) if values else None


def run_cells(
    specs: list[dict[str, Any]],
    *,
    out_dir: Path,
    runner: Callable[..., dict[str, Any]],
    **runner_kwargs: Any,
) -> list[dict[str, Any]]:
    """Run each spec with 1 Hz memory sampling; return one row per cell."""
    rows = []
    for spec in specs:
        ctx = spec.server["ctx_size"]
        kv = spec.server["cache_type_k"]
        csv_path = out_dir / f"{spec.campaign}-vram.csv"
        stop = threading.Event()
        sampler = threading.Thread(target=sample_memory, args=(csv_path, stop), daemon=True)
        sampler.start()
        started = time.time()
        try:
            runner(spec=spec, out_dir=out_dir / "campaigns", **runner_kwargs)
            status, error = "measured", None
        except Exception as exc:  # one failed cell must not abort the sweep
            status, error = "failed", str(exc)
        finally:
            stop.set()
            sampler.join(timeout=5)
        rows.append(
            {
                "campaign": spec.campaign,
                "ctx": ctx,
                "kv": kv,
                "status": status,
                "error": error,
                "duration_s": round(time.time() - started, 1),
                "peak_vram_mib": peak_vram(csv_path),
                "telemetry_csv": str(csv_path),
            }
        )
        (out_dir / "sweep_rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


def analyze(root: Path) -> list[dict[str, Any]]:
    """Join sweep rows with llama-bench throughput; missing cells stay null."""
    rows = json.loads((root / "sweep_rows.json").read_text(encoding="utf-8"))
    out = []
    for row in rows:
        prefill = decode = None
        for bench in sorted((root / "campaigns").glob(f"{row['campaign']}/*/*/llama-bench/results.json")):
            try:
                records = json.loads(bench.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for record in records:
                if record.get("n_gen") == 0 and record.get("n_prompt"):
                    prefill = round(float(record["avg_ts"]), 3)
                elif record.get("n_prompt") == 0 and record.get("n_gen"):
                    decode = round(float(record["avg_ts"]), 3)
        latencies: dict[str, dict[str, Any]] = {}
        for res in sorted((root / "campaigns").glob(f"{row['campaign']}/*/*/*/results.json")):
            try:
                payload = json.loads(res.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            for suite, metrics in (payload.get("results") or {}).items():
                if isinstance(metrics, dict) and "latency_p50_ms" in metrics:
                    latencies[suite] = {
                        "p50_ms": metrics.get("latency_p50_ms"),
                        "p95_ms": metrics.get("latency_p95_ms"),
                        "n": metrics.get("latency_n"),
                    }
        out.append({**row, "prefill_tok_s": prefill, "decode_tok_s": decode, "latencies": latencies})
    (root / "sweep_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--base", required=True)
    gen.add_argument("--grid", required=True, help="ctx=2048,4096")
    gen.add_argument("--kv", default="f16,q8_0")
    gen.add_argument("--layers", help="csv of gpu layer counts, e.g. 99,32,16")
    gen.add_argument("--parallel", help="csv of server parallel slots, e.g. 1,2,4")
    gen.add_argument("--out", required=True)
    run = sub.add_parser("run")
    run.add_argument("--base", required=True)
    run.add_argument("--grid", required=True)
    run.add_argument("--kv", default="f16,q8_0")
    run.add_argument("--layers")
    run.add_argument("--parallel")
    run.add_argument("--campaign-suffix", default="",
                     help="appended before the cell suffix (one per lease repeat)")
    run.add_argument("--out", required=True)
    run.add_argument("--models-dir", default="/models")
    run.add_argument("--llama-server", default="llama-server")
    run.add_argument("--llama-bench", default="llama-bench")
    run.add_argument("--no-bench", action="store_true",
                     help="skip llama-bench per cell (server-only memory sampling)")
    run.add_argument("--bench-only", action="store_true",
                     help="skip evaluation per cell (memory/throughput sweeps)")
    sub.add_parser("analyze").add_argument("--root", required=True)
    args = parser.parse_args(argv)

    if args.cmd == "analyze":
        print(json.dumps(analyze(Path(args.root)), indent=2))
        return 0

    base = yaml.safe_load(Path(args.base).read_text(encoding="utf-8"))
    ctxs = [int(x) for x in args.grid.split("=", 1)[1].split(",")]
    layers = [int(x) for x in args.layers.split(",")] if args.layers else None
    parallels = [int(x) for x in args.parallel.split(",")] if args.parallel else None
    specs = expand_grid(base, ctxs, args.kv.split(","), layers=layers,
                        parallels=parallels, suffix=args.campaign_suffix)
    out = Path(args.out)
    (out / "specs").mkdir(parents=True, exist_ok=True)
    for spec in specs:
        (out / "specs" / f"{spec['campaign']}.yaml").write_text(
            yaml.safe_dump(spec, sort_keys=False), encoding="utf-8"
        )
    if args.cmd == "generate":
        print(json.dumps([s["campaign"] for s in specs], indent=2))
        return 0

    from llm_research_bench import campaign

    loaded = [campaign.load_spec(out / "specs" / f"{s['campaign']}.yaml") for s in specs]
    rows = run_cells(
        loaded,
        out_dir=out,
        runner=campaign.run_campaign,
        models_dir=Path(args.models_dir),
        llama_server=args.llama_server,
        llama_bench=args.llama_bench,
        **({"evaluate": False} if args.bench_only else {}),
        **({"bench": False} if args.no_bench else {}),
    )
    print(json.dumps(rows, indent=2))
    return 0 if all(r["status"] == "measured" for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
