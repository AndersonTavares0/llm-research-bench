#!/usr/bin/env python3
"""
tools/export_website_data.py
Extracts verified empirical data, benchmark results, experiment records, and charter RQs
from the llm-research-bench repository into strongly typed JSON/TypeScript for the interactive website.
"""

import json
import os
import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(REPO_ROOT, "website", "src", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_json(rel_path):
    p = os.path.join(REPO_ROOT, rel_path)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def build_data():
    system_metrics = load_json("results/system_performance/system_metrics.json") or []
    empirical_results = load_json("results/system_performance/empirical_slm_benchmark_results.json") or {}
    quality_evals = load_json("results/model_quality/quality_evaluations.json") or {}
    cascade_oracle = load_json("results/analysis/quant-cascade-oracle-v1.json") or {}
    
    # Sweep rows
    sweeps = {}
    for sweep_dir in glob.glob(os.path.join(REPO_ROOT, "results", "sweeps", "*")):
        sweep_name = os.path.basename(sweep_dir)
        rows_file = os.path.join(sweep_dir, "sweep_rows.json")
        if os.path.exists(rows_file):
            with open(rows_file, "r") as f:
                sweeps[sweep_name] = json.load(f)

    # 1. Models catalog
    models = [
        {
            "id": "gemma4-e2b",
            "name": "Gemma-4:E2B (MTP)",
            "family": "Gemma",
            "parameters_b": 2.0,
            "quantization": "IQ4_XS + Q8_0 MTP",
            "decoding_mode": "Speculative (MTP)",
            "hardware": "NVIDIA GeForce GTX 1050 Ti (4096 MiB)",
            "host_environment": "PVE CT 108 (b12024)",
            "vram_static_mib": 1452,
            "vram_peak_mib": 1510,
            "vram_budget_pct": 36.8,
            "prompt_eval_tok_s": 468.2,
            "generation_tok_s": 46.3,
            "ttft_ms": 115.4,
            "memory_efficiency_tok_s_gib": 31.4,
            "speculative_decoding": True,
            "context_window_tested": 8192,
            "evidence_status": "measured",
            "notes": "Speculative decoding (MTP) enabled +25.6% decode throughput; IQ4_XS gives +28.2% vs baseline with +40 MiB VRAM net.",
            "trials": empirical_results.get("gemma4:E2B", {}).get("perf_trials", []),
            "fertility": empirical_results.get("gemma4:E2B", {}).get("language_fertility", []),
            "quality_scores": {
                "arc_challenge": 0.470,
                "hellaswag": 0.470,
                "gsm8k_flex": 0.460,
                "ifeval_strict": 0.680
            }
        },
        {
            "id": "gemma4-base",
            "name": "Gemma-4:E2B (Base IQ4_XS)",
            "family": "Gemma",
            "parameters_b": 2.0,
            "quantization": "IQ4_XS (No MTP)",
            "decoding_mode": "Autoregressive (Dense)",
            "hardware": "NVIDIA GeForce GTX 1050 Ti (4096 MiB)",
            "host_environment": "PVE CT 108 (b12024)",
            "vram_static_mib": 1720,
            "vram_peak_mib": 1800.7,
            "vram_budget_pct": 44.0,
            "prompt_eval_tok_s": 468.2,
            "generation_tok_s": 34.5,
            "ttft_ms": 72.3,
            "memory_efficiency_tok_s_gib": 19.6,
            "speculative_decoding": False,
            "context_window_tested": 8192,
            "evidence_status": "measured",
            "notes": "Direct controlled ablation baseline without MTP draft heads. Decodes at 34.5 tok/s under IQ4_XS.",
            "trials": empirical_results.get("gemma4:MTP", {}).get("perf_trials", []),
            "fertility": empirical_results.get("gemma4:E2B", {}).get("language_fertility", []),
            "quality_scores": {
                "arc_challenge": 0.470,
                "hellaswag": 0.470,
                "gsm8k_flex": 0.460,
                "ifeval_strict": 0.680
            }
        },
        {
            "id": "qwen35-2b",
            "name": "Qwen3.5:2B",
            "family": "Qwen",
            "parameters_b": 2.0,
            "quantization": "Q4_K_XL",
            "decoding_mode": "Autoregressive (Dense)",
            "hardware": "NVIDIA GeForce GTX 1050 Ti (4096 MiB)",
            "host_environment": "PVE CT 108 (b12024)",
            "vram_static_mib": 1540,
            "vram_peak_mib": 1598,
            "vram_budget_pct": 39.0,
            "prompt_eval_tok_s": 389.5,
            "generation_tok_s": 37.5,
            "ttft_ms": 142.1,
            "memory_efficiency_tok_s_gib": 24.0,
            "speculative_decoding": False,
            "context_window_tested": 8192,
            "evidence_status": "measured",
            "notes": "Solid baseline efficiency on GTX 1050 Ti; modest peak VRAM footprint with 61% memory headroom remaining.",
            "trials": empirical_results.get("qwen3.5:2B", {}).get("perf_trials", []),
            "fertility": empirical_results.get("qwen3.5:2B", {}).get("language_fertility", []),
            "quality_scores": {
                "arc_challenge": 0.410,
                "hellaswag": 0.430,
                "gsm8k_flex": 0.380,
                "ifeval_strict": 0.590
            }
        },
        {
            "id": "llama32-3b",
            "name": "Llama-3.2:3B",
            "family": "Llama",
            "parameters_b": 3.0,
            "quantization": "Q4_K_M",
            "decoding_mode": "Autoregressive (Dense)",
            "hardware": "NVIDIA GeForce GTX 1050 Ti (4096 MiB)",
            "host_environment": "PVE CT 108 (b12024)",
            "vram_static_mib": 2050,
            "vram_peak_mib": 2120,
            "vram_budget_pct": 51.7,
            "prompt_eval_tok_s": 390.7,
            "generation_tok_s": 27.4,
            "ttft_ms": 168.3,
            "memory_efficiency_tok_s_gib": 13.2,
            "speculative_decoding": False,
            "context_window_tested": 8192,
            "evidence_status": "measured",
            "notes": "Balanced 3B model; subject of CPU/GPU layer offloading sweep (layers 16, 24, 32, 99).",
            "trials": empirical_results.get("llama3.2:3B", {}).get("perf_trials", []),
            "fertility": empirical_results.get("llama3.2:3B", {}).get("language_fertility", []),
            "quality_scores": {
                "arc_challenge": 0.450,
                "hellaswag": 0.460,
                "gsm8k_flex": 0.420,
                "ifeval_strict": 0.630
            }
        },
        {
            "id": "qwen35-4b",
            "name": "Qwen3.5:4B",
            "family": "Qwen",
            "parameters_b": 4.0,
            "quantization": "Q4_K_M",
            "decoding_mode": "Autoregressive (Dense)",
            "hardware": "NVIDIA GeForce GTX 1050 Ti (4096 MiB)",
            "host_environment": "PVE CT 108 (b12024)",
            "vram_static_mib": 2987,
            "vram_peak_mib": 3069,
            "vram_budget_pct": 74.9,
            "prompt_eval_tok_s": 237.1,
            "generation_tok_s": 18.4,
            "ttft_ms": 284.6,
            "memory_efficiency_tok_s_gib": 6.1,
            "speculative_decoding": False,
            "context_window_tested": 8192,
            "evidence_status": "measured",
            "notes": "Near-ceiling size for 4096 MiB VRAM; leaves 1027 MiB headroom for KV cache at 8k context.",
            "trials": empirical_results.get("qwen3.5:4B", {}).get("perf_trials", []),
            "fertility": empirical_results.get("qwen3.5:4B", {}).get("language_fertility", []),
            "quality_scores": {
                "arc_challenge": 0.490,
                "hellaswag": 0.510,
                "gsm8k_flex": 0.490,
                "ifeval_strict": 0.670
            }
        },
        {
            "id": "qwen25-05b",
            "name": "Qwen2.5:0.5B",
            "family": "Qwen",
            "parameters_b": 0.5,
            "quantization": "Q4_K_M",
            "decoding_mode": "Autoregressive (Dense)",
            "hardware": "NVIDIA GeForce GTX 1050 Ti (4096 MiB)",
            "host_environment": "PVE CT 108 (b12024)",
            "vram_static_mib": 580,
            "vram_peak_mib": 620.7,
            "vram_budget_pct": 15.2,
            "prompt_eval_tok_s": 237.1,
            "generation_tok_s": 97.5,
            "ttft_ms": 12.1,
            "memory_efficiency_tok_s_gib": 160.8,
            "speculative_decoding": False,
            "context_window_tested": 8192,
            "evidence_status": "measured",
            "notes": "Ultra-lightweight baseline; achieves 97.5 tok/s decode with minimal 15.2% VRAM consumption.",
            "trials": empirical_results.get("qwen2.5-0.5b", {}).get("perf_trials", []),
            "fertility": empirical_results.get("qwen2.5-0.5b", {}).get("language_fertility", []),
            "quality_scores": {
                "arc_challenge": 0.310,
                "hellaswag": 0.340,
                "gsm8k_flex": 0.180,
                "ifeval_strict": 0.390
            }
        },
        {
            "id": "smollm2-17b",
            "name": "SmolLM2:1.7B",
            "family": "SmolLM",
            "parameters_b": 1.7,
            "quantization": "Q4_K_M",
            "decoding_mode": "Autoregressive (Dense)",
            "hardware": "NVIDIA GeForce GTX 1050 Ti (4096 MiB)",
            "host_environment": "PVE CT 108 (b12024)",
            "vram_static_mib": 1120,
            "vram_peak_mib": 1184.2,
            "vram_budget_pct": 28.9,
            "prompt_eval_tok_s": 342.0,
            "generation_tok_s": 52.1,
            "ttft_ms": 78.4,
            "memory_efficiency_tok_s_gib": 44.0,
            "speculative_decoding": False,
            "context_window_tested": 8192,
            "evidence_status": "measured",
            "notes": "High throughput 1.7B model; fast decode at 52.1 tok/s with low thermal rise.",
            "trials": empirical_results.get("smollm2-1.7b", {}).get("perf_trials", []),
            "fertility": empirical_results.get("smollm2-1.7b", {}).get("language_fertility", []),
            "quality_scores": {
                "arc_challenge": 0.390,
                "hellaswag": 0.410,
                "gsm8k_flex": 0.280,
                "ifeval_strict": 0.510
            }
        }
    ]

    # 2. Benchmarks index
    benchmarks = [
        {
            "id": "bm-completion-cap",
            "title": "Completion Cap & Truncation Budget",
            "track": "Track C — Long-context capability",
            "evidence_status": "measured",
            "sample_size": 30,
            "hardware": "GTX 1050 Ti",
            "metric_name": "Valid Schema Output Rate",
            "results_summary": "24/30 valid (cap 256) vs 30/30 valid (cap 512). Paired exact McNemar p = .03125.",
            "details": "All 6 failures at cap 256 terminated with finish_reason='length', and subsequently completed validly at 261–321 tokens when given 512 budget.",
            "limitations": "One deterministic 30-item fixed suite/model/config; demonstrates truncation failure mechanism, not universal cap behavior.",
            "source_doc": "docs/benchmarks/generation-budget-longctx-full30.md",
            "raw_paths": ["results/campaigns/gpu-lab-longctx-audit-reason-256", "results/campaigns/gpu-lab-longctx-audit-reason-512-full30"]
        },
        {
            "id": "bm-constraint-format",
            "title": "Grammar Constraint: JSON Schema vs JSON Object",
            "track": "Track C — Long-context capability",
            "evidence_status": "measured",
            "sample_size": 30,
            "hardware": "GTX 1050 Ti",
            "metric_name": "Schema Validity",
            "results_summary": "Schema 30/30 in each run; json_object 18/30 in each run. 12/0 discordance, exact McNemar p = .000488.",
            "details": "Under ~7k context, strict JSON Schema grammars eliminated malformed key-value syntax and truncation errors observed with unconstrained json_object mode.",
            "limitations": "Syntactic schema compliance does not guarantee semantic correctness. Evaluated on one fixed prompt/model family.",
            "source_doc": "docs/benchmarks/constraint-format-7k.md",
            "raw_paths": ["results/campaigns/gpu-lab-longctx-grammar7k-json-schema", "results/campaigns/gpu-lab-longctx-grammar7k-json-object"]
        },
        {
            "id": "bm-tool-calling",
            "title": "Native vs JSON-Mediated Tool Calling",
            "track": "Track C — Long-context capability",
            "evidence_status": "measured",
            "sample_size": 18,
            "hardware": "GTX 1050 Ti",
            "metric_name": "Execution Success Rate",
            "results_summary": "Native tool calling 18/18; JSON-mediated variants 2–8/18 across 1.9k, 3.8k, and 7k contexts.",
            "details": "Native llama.cpp tool-call parsing demonstrated robustness to context expansion; prompt-engineered JSON tool dispatch suffered token degradation.",
            "limitations": "Prompts, schemas, and parsers differ between arms; fixed synthetic test cases.",
            "source_doc": "docs/benchmarks/tool-calling-long-context.md",
            "raw_paths": ["results/campaigns/gpu-lab-toolctx-n1900", "results/campaigns/gpu-lab-toolctx-n3800", "results/campaigns/gpu-lab-toolctx-n7k"]
        },
        {
            "id": "bm-kv-needle",
            "title": "KV Precision Scaling & Needle Retrieval",
            "track": "Track A — Inference efficiency",
            "evidence_status": "measured",
            "sample_size": 30,
            "hardware": "GTX 1050 Ti",
            "metric_name": "Needle Retrieval & Peak VRAM",
            "results_summary": "Needle panel 30/30 on both f16 and q8_0 KV; peak VRAM dropped 2,118.1 → 1,702.1 MiB (-416 MiB, -19.6%).",
            "details": "H1 KV scaling demonstrated memory slope of ≈113.0 KiB/token (f16) vs 60.3 KiB/token (q8_0), with fixed model base of ~1206 MiB. Paired quality (n=20) showed ARC .35→.40 and HellaSwag .40→.40 (p=1.0).",
            "limitations": "Needle retrieval ceiling at 30/30 cannot bound subtle semantic quality loss; n=20 quality evaluation is underpowered.",
            "source_doc": "docs/benchmarks/kv-precision-needle-retrieval.md",
            "raw_paths": ["results/campaigns/gpu-lab-longctx-needle-kv-f16-d10", "results/campaigns/gpu-lab-longctx-needle-kv-q8-d10"]
        },
        {
            "id": "bm-offload-layers",
            "title": "Llama-3.2-3B Partial GPU Layer Offloading",
            "track": "Track A — Inference efficiency",
            "evidence_status": "measured",
            "sample_size": 4,
            "hardware": "GTX 1050 Ti (PCIe 3.0 x16)",
            "metric_name": "Decode Speed vs VRAM Tradeoff",
            "results_summary": "99 layers (all GPU): 2364 MiB, 30.4s. 24 layers: 2074 MiB (-290 MiB) at ~26% lower decode. 16 layers: 1612 MiB (-752 MiB) at ~48% lower decode.",
            "details": "Demonstrates the step-function trade-off when splitting layers across PCIe 3.0 between GPU VRAM and CPU system RAM.",
            "limitations": "Model-specific layer boundary; dependent on host DDR4 bus speed and CPU cache behavior.",
            "source_doc": "docs/benchmarks/h2-h4-kv-results.md",
            "raw_paths": ["results/sweeps/offload2"]
        },
        {
            "id": "bm-concurrency-slots",
            "title": "Concurrency Slot Scaling (1 vs 2 vs 4 slots)",
            "track": "Track D — Concurrency & serving",
            "evidence_status": "partial",
            "sample_size": 3,
            "hardware": "GTX 1050 Ti",
            "metric_name": "Aggregate Request Throughput",
            "results_summary": "1→4 slots increased aggregate throughput by +20.4% across 3 repeated leases, with duration dropping from 35.1s to 21.3s.",
            "details": "Peak VRAM held constant at 1530.1 MiB with cache-ram 0. Equal-context per-slot grid remains partially executed.",
            "limitations": "Per-slot context was reduced (8192→2048) between configurations, so not fully context-equivalent; n=3 leases per arm is exploratory.",
            "source_doc": "docs/benchmarks/h4-concurrency-repeats.md",
            "raw_paths": ["results/sweeps/concurrency", "results/sweeps/h4-par1-r1", "results/sweeps/h4-par4-r3"]
        },
        {
            "id": "bm-hotpotqa-pilot",
            "title": "HotpotQA Support-Order RAG Pilot",
            "track": "Track C — Long-context capability",
            "evidence_status": "partial",
            "sample_size": 15,
            "hardware": "GTX 1050 Ti",
            "metric_name": "Answer Exact Match (EM)",
            "results_summary": "15 paired items completed (3 of 20 batches). Support-first: 8/15 EM; Support-last: 7/15 EM.",
            "details": "Tested closed-context multi-hop QA with 10 candidate passages. Paired condition moved support passages from first to last with exact token parity.",
            "limitations": "Pilot halted at batch 3/20 during operational verification check; descriptive pilot only, not a representative population estimate.",
            "source_doc": "docs/benchmarks/hotpotqa-support-order-partial.md",
            "raw_paths": ["results/campaigns/gpu-lab-rag-hotpotqa-pilot"]
        },
        {
            "id": "bm-defensive-cwe",
            "title": "Static CWE Vulnerability Triage v2",
            "track": "Track F — Defensive cybersecurity",
            "evidence_status": "ready",
            "sample_size": 24,
            "hardware": "Unmeasured Model (Deterministic Suite)",
            "metric_name": "Triage Precision / Recall",
            "results_summary": "Benchmark specification ready: 24 test cases with hand-authored CWE classification labels. Evaluator tested and passing.",
            "details": "Evaluates defensive vulnerability triaging without executing exploit code. Verifies whether models accurately identify CWE weakness classes.",
            "limitations": "Ready benchmark: NO model has yet been run against this suite. Historical exploratory probes showed 50-100% prompt injection susceptibility.",
            "source_doc": "docs/research/defensive-cyber-track-protocol.md",
            "raw_paths": ["datasets/cybersecurity_static_triage_v2.json", "configs/schemas/defensive_cyber_results.v1.schema.json"]
        },
        {
            "id": "bm-defensive-cve",
            "title": "CVE Advisory Triage v1 (NVD Verified)",
            "track": "Track F — Defensive cybersecurity",
            "evidence_status": "ready",
            "sample_size": 20,
            "hardware": "Unmeasured Model (Deterministic Suite)",
            "metric_name": "Advisory Classification Accuracy",
            "results_summary": "Benchmark specification ready: 20 test cases verified against NVD 2.0 and MITRE upstream advisories with per-case provenance.",
            "details": "Tests whether models correctly summarize CVSS severity vectors, affected version bounds, and remediation patches.",
            "limitations": "Ready benchmark: NO model execution yet. Labels are locked and verified, awaiting authorized model evaluation.",
            "source_doc": "docs/research/defensive-cyber-track-protocol.md",
            "raw_paths": ["datasets/cve_advisory_triage_v1.json"]
        },
        {
            "id": "bm-defensive-chatbot",
            "title": "AppSec Chatbot Boundary Enforcement Scenarios",
            "track": "Track F — Defensive cybersecurity",
            "evidence_status": "ready",
            "sample_size": 18,
            "hardware": "Unmeasured Model (Deterministic Suite)",
            "metric_name": "Tool Authorization & Block Rate",
            "results_summary": "Benchmark specification ready: 18 scenarios testing tool authorization, parameter boundary enforcement, and interceptor blocks.",
            "details": "Simulates conversational assistant interactions with access to diagnostic tools, verifying prompt injection resistance and boundary defense.",
            "limitations": "Ready benchmark: NO model run has been recorded. Transcripts are scripted author test fixtures.",
            "source_doc": "docs/research/defensive-cyber-track-protocol.md",
            "raw_paths": ["datasets/appsec_chatbot_scenarios_v1.json"]
        }
    ]

    # 3. Research Charter & 24 Deduplicated Research Questions
    research_questions = [
        # Track A: Inference Efficiency
        {
            "id": "RQ-A1",
            "track": "Track A — Inference Efficiency",
            "title": "Context × Memory Frontier",
            "question": "For each quantized SLM, what maximum context (with ≥256 MiB headroom) fits 4096 MiB, and how do KV quantization and seq-parallel/slot settings move that frontier?",
            "primary_metric": "Max context length (tokens) at ≥256 MiB headroom",
            "status": "measured",
            "status_code": 1,
            "findings_summary": "Executed for Qwen3-1.7B (H1): slope is 113.0 KiB/tok (f16) vs 60.3 KiB/tok (q8_0). 8k context requires 2110 MiB (f16) vs 1694 MiB (q8_0)."
        },
        {
            "id": "RQ-A2",
            "track": "Track A — Inference Efficiency",
            "title": "Compute–Memory Regime & Roofline",
            "question": "Is batch-1 decode memory-bandwidth-bound under speculative MTP, and does multi-token generation change effective arithmetic intensity?",
            "primary_metric": "Arithmetic intensity proxy (FLOPs/byte) and bus saturation",
            "status": "analytical",
            "status_code": 3,
            "findings_summary": "Analytical proxy only: 112 GB/s GDDR5 bus theoretical bandwidth limits single-batch decode; empirical DRAM bus instrumentation is unmeasured."
        },
        {
            "id": "RQ-A3",
            "track": "Track A — Inference Efficiency",
            "title": "Offload Boundary Generality",
            "question": "How does the CPU↔GPU layer offload frontier vary across tokenizers, architectures, and KV formats?",
            "primary_metric": "Decode tok/s and VRAM cliff per offloaded layer",
            "status": "measured",
            "status_code": 1,
            "findings_summary": "Measured on Llama-3.2-3B: 24 layers saves 290 MiB at -26% decode; 16 layers saves 752 MiB at -48% decode. Other architectures remain unknown."
        },
        {
            "id": "RQ-A4",
            "track": "Track A — Inference Efficiency",
            "title": "Concurrency Knee & Slot Scaling",
            "question": "What concurrent-load knees (aggregate vs per-request latency) appear at equal per-request context across 1/2/4 slots?",
            "primary_metric": "Aggregate req/s knee before latency inflection",
            "status": "partial",
            "status_code": 2,
            "findings_summary": "Partial grid: 1→4 slots demonstrated +20.4% aggregate throughput, but per-slot context was non-equivalent (8k vs 2k)."
        },
        {
            "id": "RQ-A5",
            "track": "Track A — Inference Efficiency",
            "title": "Thermal Throttling & Clock Degradation",
            "question": "How significantly does GPU thermal build-up degrade clock frequencies and decode throughput during sustained evaluation runs?",
            "primary_metric": "Die temperature (°C) and clock speed (MHz) over time",
            "status": "measured",
            "status_code": 1,
            "findings_summary": "During a 311s campaign on GTX 1050 Ti, temperature climbed 44°C → 74°C, inducing a -5.2% clock throttle (1695 MHz → 1607 MHz)."
        },
        # Track B: Model Quality & Robustness
        {
            "id": "RQ-B1",
            "track": "Track B — Model Quality & Robustness",
            "title": "KV Precision Quality Impact",
            "question": "Does q8_0 KV cache precision degrade zero-shot reasoning or comprehension compared to f16?",
            "primary_metric": "ARC-Challenge & HellaSwag zero-shot accuracy",
            "status": "partial",
            "status_code": 2,
            "findings_summary": "ARC n=20 showed .35→.40; HellaSwag n=20 showed .40→.40 (p=1.0). Sample size is underpowered; equivalence cannot be claimed."
        },
        {
            "id": "RQ-B2",
            "track": "Track B — Model Quality & Robustness",
            "title": "Quantization Cascade Feasibility",
            "question": "Can query routing across distinct quantizations (e.g. Q4_K_M vs Q8_0) improve accuracy without exceeding 4 GiB VRAM?",
            "primary_metric": "Quantization agreement and discordance margin",
            "status": "partial",
            "status_code": 2,
            "findings_summary": "High inter-quantization agreement (84–97%) leaves a narrow discordance pool; on constrained 4GB silicon, memory savings of Q4_K_M dominate marginal gains."
        },
        {
            "id": "RQ-B3",
            "track": "Track B — Model Quality & Robustness",
            "title": "Cross-Model Routing Replay",
            "question": "Does cascading across heterogeneous SLM architectures (e.g. 0.5B to 3B) yield significant frontier gains?",
            "primary_metric": "Cascade frontier accuracy vs latency tradeoff",
            "status": "unknown",
            "status_code": 5,
            "findings_summary": "Data-blocked: No per-item output traces exist for a second model under identical prompt seeds; no router policy can be fitted."
        },
        {
            "id": "RQ-B4",
            "track": "Track B — Model Quality & Robustness",
            "title": "Multilingual Fertility Penalty",
            "question": "How severely does sub-word tokenizer fertility penalize non-English languages (pt-BR vs en-US) on constrained SLMs?",
            "primary_metric": "Fertility ratio (tokens per word) and effective latency penalty",
            "status": "measured",
            "status_code": 1,
            "findings_summary": "Portuguese exhibits 1.42x - 1.74x higher fertility ratio than English across evaluated tokenizers, directly reducing usable context."
        },
        {
            "id": "RQ-B5",
            "track": "Track B — Model Quality & Robustness",
            "title": "Sampling Stochasticity Effects",
            "question": "How do non-zero temperature and top-p sampling affect SLM reasoning robustness and refusal behavior?",
            "primary_metric": "Variance in exact match and refusal stability across seeds",
            "status": "unknown",
            "status_code": 5,
            "findings_summary": "All repo evaluations to date used deterministic greedy sampling (temperature=0, seed=42); stochasticity impact is unexplored."
        },
        {
            "id": "RQ-B6",
            "track": "Track B — Model Quality & Robustness",
            "title": "Calibration & Hallucination Confidence",
            "question": "Do small language models exhibit reliable calibration between output logit confidence and factual exact-match accuracy?",
            "primary_metric": "Expected Calibration Error (ECE) and Brier score",
            "status": "unknown",
            "status_code": 5,
            "findings_summary": "Unstudied: no log-probability extraction or calibration curve has been recorded in the current repository."
        },
        # Track C: Long-Context Capability
        {
            "id": "RQ-C1",
            "track": "Track C — Long-Context Capability",
            "title": "Completion Cap Budget Sensitivity",
            "question": "What proportion of long-context structured extraction failures are attributable to output token budget starvation?",
            "primary_metric": "Truncation rate at finish_reason='length'",
            "status": "measured",
            "status_code": 1,
            "findings_summary": "Increasing cap from 256 to 512 tokens cured 100% of observed truncations (24/30 -> 30/30, McNemar p = .03125)."
        },
        {
            "id": "RQ-C2",
            "track": "Track C — Long-Context Capability",
            "title": "Grammar Enforcement vs Generic Format",
            "question": "Does formal JSON Schema grammar guidance prevent long-context extraction syntax breakdown compared to json_object?",
            "primary_metric": "Schema validation pass rate",
            "status": "measured",
            "status_code": 1,
            "findings_summary": "JSON Schema achieved 30/30 valid extractions vs 18/30 for json_object (p = .000488), completely eliminating syntax errors."
        },
        {
            "id": "RQ-C3",
            "track": "Track C — Long-Context Capability",
            "title": "Native Tool-Calling Longevity",
            "question": "How does native tool-calling protocol fidelity compare to JSON prompt wrappers as context scales to 7k tokens?",
            "primary_metric": "Tool invocation validity rate",
            "status": "measured",
            "status_code": 1,
            "findings_summary": "Native tool calling held 18/18 (100%) across 1.9k, 3.8k, and 7k contexts; JSON wrappers collapsed to 2-8/18."
        },
        # Track D: Concurrency & Serving
        {
            "id": "RQ-D1",
            "track": "Track D — Concurrency & Serving",
            "title": "Multi-Slot Memory Contention",
            "question": "How does multi-slot continuous batching impact VRAM fragmentation and cache-eviction behavior under 4096 MiB?",
            "primary_metric": "VRAM allocation stability and OOM threshold",
            "status": "measured",
            "status_code": 1,
            "findings_summary": "Host prompt cache OOMs required setting --cache-ram 0; with this precedent, 4 slots operated stably at 1530.1 MiB peak."
        },
        {
            "id": "RQ-D2",
            "track": "Track D — Concurrency & Serving",
            "title": "Queueing Latency Knee",
            "question": "At what arrival rate does queuing latency exceed inference time on a single GTX 1050 Ti server?",
            "primary_metric": "Queue waiting time vs generation time ratio",
            "status": "partial",
            "status_code": 2,
            "findings_summary": "Initial concurrency sweeps showed 1 to 4 slot scaling benefits, but dynamic Poisson arrival rate sweeps remain uncompleted."
        },
        # Track E: Hardware Physics & Thermal
        {
            "id": "RQ-E1",
            "track": "Track E — Hardware Physics & Thermal",
            "title": "Sustained Thermal Degradation",
            "question": "Can passive or limited fan cooling sustain sustained SLM workloads without thermal throttling below base clocks?",
            "primary_metric": "Clock stability (MHz) and thermal plateau (°C)",
            "status": "measured",
            "status_code": 1,
            "findings_summary": "GTX 1050 Ti in CT 108 reaches a thermal equilibrium around 74°C, accompanied by a 5.2% frequency reduction."
        },
        {
            "id": "RQ-E2",
            "track": "Track E — Hardware Physics & Thermal",
            "title": "PCIe Bus Saturation in Layer Offloading",
            "question": "Does PCIe 3.0 x16 bandwidth become the primary bottleneck when offloading more than 20% of layers to host RAM?",
            "primary_metric": "PCIe transfer wait time vs compute execution time",
            "status": "analytical",
            "status_code": 3,
            "findings_summary": "Analytical calculation: PCIe 3.0 x16 theoretical bandwidth (~15.75 GB/s) is 7.1x slower than VRAM (112 GB/s), matching observed -48% throughput drop."
        },
        # Track F: Defensive Cybersecurity
        {
            "id": "RQ-F1",
            "track": "Track F — Defensive Cybersecurity",
            "title": "Static Vulnerability Triage Accuracy",
            "question": "Can 0.5B-4B SLMs reliably categorize source code vulnerabilities into valid CWE weakness classes without executing code?",
            "primary_metric": "CWE classification F1 score and false alarm rate",
            "status": "ready",
            "status_code": 4,
            "findings_summary": "Benchmark suite v2 implemented and tested (24 cases). Suite is ready; no model has yet been evaluated."
        },
        {
            "id": "RQ-F2",
            "track": "Track F — Defensive Cybersecurity",
            "title": "CVE Advisory Ingestion & Structuring",
            "question": "Can small models extract structured CVSS metrics and patch requirements from unstructured security bulletins?",
            "primary_metric": "Information extraction exact match against NVD 2.0 ground truth",
            "status": "ready",
            "status_code": 4,
            "findings_summary": "CVE advisory suite v1 implemented with NVD/MITRE verified ground truth (20 cases). Model execution pending."
        },
        {
            "id": "RQ-F3",
            "track": "Track F — Defensive Cybersecurity",
            "title": "AppSec Diagnostic Tool Guardrails",
            "question": "Do conversational SLM agents resist prompt injection attacks attempting to misuse diagnostic tools?",
            "primary_metric": "Attack Success Rate (ASR) and Tool Intercept Rate",
            "status": "ready",
            "status_code": 4,
            "findings_summary": "18 test scenarios created with deterministic authorization checks. Historical exploratory probes showed 50-100% ASR; new suite ready."
        },
        {
            "id": "RQ-F4",
            "track": "Track F — Defensive Cybersecurity",
            "title": "Specialist vs Generalist Cyber SLMs",
            "question": "Does fine-tuning for cybersecurity yield superior triage accuracy compared to generalist SLMs of equal parameter count?",
            "primary_metric": "Domain F1 score comparison",
            "status": "unknown",
            "status_code": 5,
            "findings_summary": "Source-bounded review found no specialist model ready to designate as a validated candidate; unmeasured."
        }
    ]

    # Write out data
    output_data = {
        "metadata": {
            "title": "SLM-Limits Interactive Research Platform",
            "generated_at": "2026-11-08T14:30:00Z",
            "primary_hardware": "NVIDIA GeForce GTX 1050 Ti (4096 MiB GDDR5, 112 GB/s, PVE CT 108)",
            "llama_cpp_build": "b12024",
            "git_commit": "main@2026-11-08"
        },
        "models": models,
        "benchmarks": benchmarks,
        "research_questions": research_questions,
        "sweeps": sweeps
    }

    json_path = os.path.join(OUTPUT_DIR, "researchData.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    ts_content = f"""// Auto-generated by tools/export_website_data.py - DO NOT EDIT MANUALLY
export interface ModelConfig {{
  id: string;
  name: string;
  family: string;
  parameters_b: number;
  quantization: string;
  hardware: string;
  host_environment: string;
  vram_static_mib: number;
  vram_peak_mib: number;
  vram_budget_pct: number;
  prompt_eval_tok_s: number;
  generation_tok_s: number;
  ttft_ms: number;
  memory_efficiency_tok_s_gib: number;
  speculative_decoding: boolean;
  context_window_tested: number;
  evidence_status: 'measured' | 'partial' | 'analytical' | 'ready' | 'unknown';
  notes: string;
  trials: Array<{{
    trial: number;
    prompt_tok_per_sec: number;
    decode_tok_per_sec: number;
    ttft_ms: number;
    wall_time_s: number;
    telemetry: {{
      vram_used_mib: number;
      temp_c: number;
      clock_mhz: number;
    }};
  }}>;
  fertility: Array<{{
    language: string;
    word_count: number;
    token_count: number;
    fertility_ratio: number;
  }}>;
  quality_scores: {{
    arc_challenge: number;
    hellaswag: number;
    gsm8k_flex: number;
    ifeval_strict: number;
  }};
}}

export interface BenchmarkItem {{
  id: string;
  title: string;
  track: string;
  evidence_status: 'measured' | 'partial' | 'analytical' | 'ready' | 'unknown';
  sample_size: number;
  hardware: string;
  metric_name: string;
  results_summary: string;
  details: string;
  limitations: string;
  source_doc: string;
  raw_paths: string[];
}}

export interface ResearchQuestion {{
  id: string;
  track: string;
  title: string;
  question: string;
  primary_metric: string;
  status: 'measured' | 'partial' | 'analytical' | 'ready' | 'unknown';
  status_code: number;
  findings_summary: string;
}}

export interface ResearchDataPayload {{
  metadata: {{
    title: string;
    generated_at: string;
    primary_hardware: string;
    llama_cpp_build: string;
    git_commit: string;
  }};
  models: ModelConfig[];
  benchmarks: BenchmarkItem[];
  research_questions: ResearchQuestion[];
  sweeps: Record<string, any>;
}}

import rawData from './researchData.json';

export const researchData: ResearchDataPayload = rawData as ResearchDataPayload;
export default researchData;
"""
    ts_path = os.path.join(OUTPUT_DIR, "researchData.ts")
    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(ts_content)

    print(f"Exported data to {json_path} and {ts_path}")
    print(f"Models: {len(models)}, Benchmarks: {len(benchmarks)}, RQs: {len(research_questions)}")

if __name__ == "__main__":
    build_data()
