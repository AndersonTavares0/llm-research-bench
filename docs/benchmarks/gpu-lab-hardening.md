# GPU Lab hardening review (2026-11-05)

Scope: review the completed campaign `gpu-lab-qwen3-1.7b-v2`, verify production
recovery, stress-test the existing lease controller, and prepare the follow-up
protocol. No new benchmark campaign was launched. The gpu-lab architecture was
not changed beyond the controller bug fix recorded below.

## 1. Production recovery, verified with a real request

The lease controller returned to `production/production` after generation 168
(terminal attempt `mode=job`, `reason=supervisor_stopped`, `result=restored`).
A health check alone only proves the socket is open, so an actual completion was
requested through the production gateway:

```
POST http://127.0.0.1:18081/v1/chat/completions
{"model":"qwen3.5:4B","messages":[{"role":"user","content":"Reply with the single word: ready"}],"max_tokens":16,"temperature":0}
```

Response: `"content":"ready"`, `finish_reason:"stop"`, 19 prompt + 2 completion
tokens, `system_fingerprint b12033-785322d17`. GPU memory returned to
3765 MiB with the production model loaded (it was 3 MiB with the model
unloaded). This confirms end-to-end recovery, not just a listening port.

## 2. Lease-controller stress test (fake backend, production untouched)

`tools/homelab/lease-selftest.sh` drives the real `gpu-lab-controller` through
`GPU_LAB_BACKEND=fake` and a temporary state file, so nothing touches the real
service. Seven scenarios, all passing:

| # | Scenario | Expected | Result |
|---|---|---|---|
| 1 | Acquire a job lease | state `acquiring_lab`, production stopped, `supervisor=null` | PASS |
| 2 | Reap during the acquire window | no-op (the fixed reaper bug) | PASS |
| 3 | Lease expiry before bind | converge to production | PASS |
| 4 | Hard deadline with a live supervisor | converge to production | PASS |
| 5 | Supervisor dies after bind | converge with `supervisor_gone` | PASS |
| 6 | Concurrent acquisition | second request refused, owner unchanged | PASS |
| 7 | Supervisor killed at `before_grant` (fault injection) | lease TTL converges, production restored | PASS |

Run it as root on CT108:

```bash
bash /tmp/lease-selftest.sh     # or tools/homelab/lease-selftest.sh from the workspace
```

Scenario 7 is the direct regression test for the bug that aborted the first
campaign attempt: a supervisor that dies after production is stopped but before
the grant must be recovered by the lease TTL, not by a reaper that assumes the
missing supervisor record means "orphan".

Not covered: a reboot during a lease (the `boot_id_changed` path is implemented
but was not exercised), and two acquires for the same session id.

## 3. Fix persistence

- Controller fix: `/usr/local/libexec/gpu_lab_controller.py`, on the CT108 root
  filesystem (`/dev/mapper/pve-vm--108--disk--0`, ext4), so it survives service
  restarts and reboots. MD5 `f3d2d2be7f2f37fc002f22fa90cdf011`; pre-fix backup
  `/root/gpu_lab_controller.py.bak-20261105T124243Z` (MD5 `04c81206…`).
  `gpu-labctl reconcile` returns `{"result": "healthy"}`.
- llama.cpp host-cache fix: `build_server_cmd` emits `--cache-ram` when the spec
  sets it (`src/llm_research_bench/campaign.py`), pinned in
  `configs/campaigns/gpu-lab-qwen3-1.7b-v2.yaml` as `cache_ram: 0`, and guarded
  by a unit test (`tests/test_campaign.py::test_server_and_bench_commands_use_official_flags`).
- Figure output naming: `campaign_figures` appended extensions with
  `Path.with_suffix`, which truncated dotted campaign names
  (`…-1.7b-v2` → `…-1.pdf`). Fixed to append the suffix; regenerated
  `reports/figures/gpu-lab-qwen3-1.7b-v2.{pdf,png}`.

## 4. Artifact audit

`python -m llm_research_bench.campaign audit --root results/campaigns`:

- The campaign `run_summary.json` lacked `started_at_utc`, `finished_at_utc` and
  `model`. The writer now records them for new runs; the existing summary was
  backfilled from the group manifests (`12:43:36Z` → `13:19:26Z`,
  `qwen3-1.7b-q4km`). The audit no longer flags it.
- `knowledge-mcq/raw/` contains harness outputs from **two** leases: the first
  knowledge run (12:47) and the re-run after the server flags changed (13:01).
  `knowledge-mcq/results.json` is the 13:01 run; the 12:47 files are retained
  history, not the adopted measurement. Raw directories are append-only; treat
  the newest run and the group `meta.json` timestamp as authoritative.
- Harness `results.json` files are flagged `legacy` by the audit because they are
  lm-eval outputs, not campaign-schema documents. That is expected; the campaign
  schema lives in `meta.json` and `run_summary.json`.
- Both MCQ runs produced identical scores, which is consistent with temperature
  0 on the same item subset and is a reproducibility check, not a variance
  estimate.

## 5. Methodological review of the reported numbers

- Throughput: 10 repetitions in one process. SD 1.892 (prefill) and 0.015
  (decode) are within-run repeatability, not across-lease reproducibility.
- Accuracy: Wilson intervals assume independent Bernoulli items. Benchmark items
  are often clustered by topic or template, so the intervals are optimistic; no
  design effect was estimated.
- Measured: wall-clock per group, spot VRAM (1.21–1.61 GiB), spot GPU
  utilization, model SHA-256, runtime versions, seed, spec.
- Not measured: power, clocks, temperature over time, allocator peaks, latency
  distribution per request. Any energy-efficiency or throttling claim is
  therefore out of scope.

## 6. Follow-up protocol (not launched)

Goal: turn the exploratory run into a confirmatory comparison with a defensible
uncertainty budget.

1. **Preregister** the hypothesis, primary metric per task, decision rule, and
   the multiple-comparison family (Holm over the declared family).
2. **Design**: repeated-measures across leases. 5 leases per configuration,
   randomized order (blocked by lease index), fixed 10-minute cool-down, GPU
   temperature recorded before each lease. Two configurations (e.g. Q4_K_M vs
   Q8_0) share each lease to remove day-to-day drift.
3. **Sampling**: full task splits, no `--limit`; 5-shot GSM8K in addition to the
   zero-shot variant; report both.
4. **Telemetry**: `nvidia-smi --query-gpu=timestamp,clocks.sm,clocks.mem,power.draw,temperature.gpu,memory.used,utilization.gpu --loop-ms=1000`
   for the whole lease; report tokens per joule only if `power.draw` is
   non-null; report the 5–95% latency distribution per request.
5. **Analysis**: paired bootstrap over the shared item set for accuracy
   differences; mixed-effects model with lease as a random intercept for
   throughput; report the minimum detectable effect.
6. **Power**: at n=100 items per arm, the normal approximation gives an MDE of
   roughly 20 percentage points near p=0.5, 18 pp near p=0.7, and 16 pp near
   p=0.8 (α=0.05 two-sided, 80% power). Comparisons smaller than that need more
   items or fewer, better-targeted tasks.
7. **Reporting**: publish raw artifacts, the spec hash, and the analysis script;
   state which metrics were not measured.

## 7. Remaining risks

- The reaper fix is covered by fault-injection tests but not by a reboot during
  a lease.
- Production preemption is expected and documented, but any client calling the
  gateway during a lease receives HTTP 503.
- The sandbox limits (3 GiB RAM, 1.5 CPU) are part of the measurement
  environment; results are not directly comparable to bare-metal runs.
- `limit`-based evaluation remains a fixed first-N sample and cannot support
  benchmark-leaderboard comparisons.
