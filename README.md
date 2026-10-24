# llm-research-bench

Experimental benchmark and evaluation suite for small language models (2B to 4B parameters) running under a 4096 MiB VRAM budget on an NVIDIA GeForce GTX 1050 Ti.

For the Portuguese version, read [README.pt-BR.md](README.pt-BR.md).

## Testbed

- GPU: NVIDIA GeForce GTX 1050 Ti (4096 MiB GDDR5, 128-bit bus, 112 GB/s theoretical bandwidth, driver 580.173.02, CUDA 13.0)
- Host: AMD Ryzen 5 3600 (6 cores, 12 threads @ 3.6 GHz base), 32 GiB DDR4 3200 MT/s
- Environment: Proxmox VE LXC container CT 108 (Debian 13 Trixie, Linux 6.8.12-14-pve, 2 vCPUs, 4.0 GiB RAM)
- Inference runtime: `llama-server` (commit b4120+) in rootless Podman (`ollama` user)
- Hardware telemetry: Continuous sampling via `libnvidia-ml.so.1` at 250 ms intervals

## Evaluated Models

| Model | Parameters | Quantization | Model Size | Context Tested |
| :--- | :--- | :--- | :--- | :--- |
| `gemma4:E2B` | 2.0B | IQ4_XS + Q8_0 MTP draft | 1.5 GB | 65,536 |
| `gemma4:MTP` | 2.0B | IQ4_XS (no draft, ablation baseline) | 1.5 GB | 65,536 |
| `gemma4:Q4KM` | 2.0B | Q4_K_M (standard quantization) | 3.3 GB | 65,536 |
| `qwen3.5:2B` | 2.0B | Q4_K_XL | 1.3 GB | 16,384 |
| `llama3.2:3B` | 3.0B | Q4_K_M | 2.0 GB | 16,384 |
| `qwen3.5:4B` | 4.0B | Q4_K_M | 2.7 GB | 16,384 |

## Measured Results

### 1. Controlled MTP Speculative Decoding Ablation (N=15, 95% Confidence Interval)

Evaluated with greedy decoding ($\tau = 0.0$) on technical system prompts over 5 trials (15 total runs) to isolate the draft model's effect:

| Configuration | Mean Throughput | Standard Deviation | 95% CI Margin | 95% CI Range | Steady-State Speed | Peak VRAM |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Gemma-4-E2B (with MTP draft) | 42.21 tok/s | 10.82 | ±5.99 | [36.2, 48.2] tok/s | 44.95 tok/s | 2038 MiB |
| Gemma-4-E2B (without MTP draft) | 32.25 tok/s | 5.83 | ±3.23 | [29.0, 35.5] tok/s | 33.75 tok/s | 2038 MiB |

MTP speculative decoding increases generation throughput by 30.9% overall ($t = 3.139, p = 0.0024$) and 33.2% during steady-state runs ($44.95$ vs $33.75$ tok/s, $t = 21.05, p < 10^{-13}$) without increasing VRAM consumption.

### 2. Hardware Performance across Models

| Model | Peak VRAM | VRAM Budget | Prompt Eval | Decode | TTFT | Memory Efficiency | Energy Efficiency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Gemma-4-E2B (MTP) | 1,510 MiB | 36.8% | 468.2 tok/s | 46.3 tok/s | 115.4 ms | 31.4 tok/s/GiB | 0.89 tok/J |
| Qwen-3.5-2B | 1,598 MiB | 39.0% | 389.5 tok/s | 37.5 tok/s | 142.1 ms | 24.0 tok/s/GiB | 0.77 tok/J |
| Llama-3.2-3B | 2,120 MiB | 51.7% | 390.7 tok/s | 27.4 tok/s | 168.3 ms | 13.2 tok/s/GiB | 0.50 tok/J |
| Qwen-3.5-4B | 3,069 MiB | 74.9% | 237.1 tok/s | 18.4 tok/s | 284.6 ms | 6.1 tok/s/GiB | 0.30 tok/J |

Memory efficiency is defined as generation throughput divided by peak allocated VRAM in GiB. Energy efficiency represents generated tokens per Joule of electrical energy ($E = \text{tok/s} / \text{Watts}$) derived from live NVML sensor telemetry.

### 3. Adversarial Robustness and Tool Calling

| Model | Direct Attack Refusal (5 Vectors) | Indirect Log Injection | MCP Tool Calling (stdio) | Technical Reasoning |
| :--- | :--- | :--- | :--- | :--- |
| Gemma-4-E2B (MTP) | 100% (5/5) | Failed (vulnerable) | Passed (multi-turn) | 33.3% (ZFS parity only) |
| Qwen-3.5-4B | 100% (5/5) | Failed (vulnerable) | Passed (multi-turn) | 33.3% (ZFS parity only) |
| Qwen-3.5-2B | 100% (5/5) | Failed (vulnerable) | Passed (multi-turn) | 0.0% (failed arithmetic) |
| Llama-3.2-3B | 100% (5/5) | Failed (vulnerable) | Failed (turn 2 parse error) | 33.3% (RAM logic only) |

All four models refused weaponized Log4Shell CVE exploits, C++ keyloggers, DAN roleplay bypasses, and system prompt extraction. However, all four models executed the simulated command override (`[CRITICAL_SYSTEM_OVERRIDE]`) when embedded in server log text. Post-training safety alignment fails to separate control instructions from untrusted data in context.

## Repository Layout

```
llm-research-bench/
├── configs/
│   ├── experiment_matrix.yaml           # Model hyperparameters
│   └── models.ini                       # llama-server router presets
├── datasets/
│   ├── gsm8k_50.json                    # 50 official GSM8K questions
│   ├── arc_challenge_50.json            # 50 official ARC-Challenge questions
│   ├── safety_prompts.json              # 6 categorized safety prompts
│   ├── reasoning_prompts.json           # Quantitative technical problems
│   └── agentic_tools.json               # JSON Schema tool definitions
├── results/
│   ├── controlled_experiments/          # Empirical traces from N=15 ablation runs
│   ├── system_performance/              # CSV and JSON hardware metrics
│   ├── model_quality/                   # Safety and agentic evaluation records
│   └── benchmark_comprehensive_results.json # Full raw empirical trace
├── reports/
│   ├── figures/                         # Vector PDF charts generated from real data
│   ├── pt-BR/                           # Portuguese LaTeX source and compiled PDF
│   └── en-US/                           # English LaTeX source and compiled PDF
├── src/llm_research_bench/
│   ├── ablation_runner.py               # N=5 controlled ablation execution harness
│   ├── quant_runner.py                  # Quantization impact measurement runner
│   ├── telemetry_collector.py           # Native NVML ctypes sampler (250 ms loop)
│   ├── statistical_analysis.py          # SciPy inferential engine (Welch t-test, Mann-Whitney, Cohen d)
│   ├── statistical_engine.py            # Student's t 95% confidence interval engine
│   ├── generate_figures.py              # Publication-grade vector PDF chart generator (8 figures)
│   ├── mcp_server.py                    # Standard JSON-RPC 2.0 stdio MCP server
│   ├── benchmark_suite.py               # Evaluation engine
│   └── split_results.py                 # Telemetry and result separator
├── tests/                               # Unit test suite
└── pyproject.toml                       # Python package configuration
```

## Running the Experiments

### 1. Install Dependencies

```bash
git clone https://github.com/AndersonTavares0/llm-research-bench.git
cd llm-research-bench
pip install -e .
pip install matplotlib
```

### 2. Run Unit Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 3. Run Controlled MTP Ablation

```bash
python src/llm_research_bench/ablation_runner.py --base-url http://127.0.0.1:18081 --repetitions 5
```

### 4. Regenerate Figures

```bash
python src/llm_research_bench/generate_figures.py
```

### 5. Compile LaTeX Reports

```bash
tectonic reports/en-US/report_en-US.tex --outdir reports/en-US
tectonic reports/pt-BR/report_pt-BR.tex --outdir reports/pt-BR
```

## Scientific Reports

- English: [`reports/en-US/report_en-US.pdf`](reports/en-US/report_en-US.pdf)
- Portuguese: [`reports/pt-BR/report_pt-BR.pdf`](reports/pt-BR/report_pt-BR.pdf)

## License

MIT License.
