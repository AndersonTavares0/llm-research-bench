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

## 2026-11-05: gateway accounting leak blocks lease drain

After the in-service probe and several completion checks, every subsequent
`gpu-lab job` aborted during acquisition with `production requests did not
drain` (`wait_for_drain(timeout=30)`), even though the service was idle
(0% GPU utilization, `/health` 200).

Evidence from `/var/lib/gpu-lab-controller/state.json` while idle:

```
state=production generation=180
active_requests=1
active_request_owners={'09adfb31…': {'pid': 344, 'starttime': '15532'}}
```

PID 344 inside CT108 is `ollama_priority_gateway.py`. The owner key changes with
each new completion, so the gateway appears to retain one stale request-owner
entry after local requests, and the lab drain check treats the service as busy
forever. Two consecutive lease attempts (generations 179, 180) were refused with
`acquire_abort_before_stop reason=drain_failed`, and the launcher reported the
misleading `job startup timed out` because it waits only 20 s for `.ready`
while the drain timeout is 30 s.

Impact: GPU campaigns cannot start until the stale owner is cleared. Production
itself is healthy; no lease is held and no data was lost.

Remediation options (need operator approval):
1. restart `ollama-priority-gateway.service` between campaigns, or
2. clear the stale `active_request_owners` entry through a supported gateway
   endpoint if one exists, or
3. fix the gateway to release the owner in a `finally` block on client
   disconnect/timeout.

Do not edit `state.json` by hand: the controller treats it as authoritative and
a wrong edit can mask real activity.

### Fix (2026-11-05, applied to CT108)

Root cause of the stuck owner: `LeaseStore.production_request()` keyed owners by
the **gateway's own PID**, so a persisted owner whose request had ended could
never be distinguished from a live one — `recover_orphaned_requests()` sees a
live process and keeps it, and drain waits forever. The launcher compounded it by
waiting only 20 s for `.ready` while `wait_for_drain` allows 30 s.

Changes (backups `*.bak-20261105T164717Z` on CT108):

- `gpu_lease.py`: `production_request(token=None)`; new `prune_requests(live)`
  that drops owners absent from the gateway's in-memory live set, and **only in
  `production` state** (a lab lease is never touched).
- `gpu_coordinator.py`: `lease(priority, token=None)`; `prune_requests()`.
- `ollama_priority_gateway.py`: one token per request, held in
  `server.active_tokens`; pruned at admission; discarded in `finally`.
- `gpu-lab-job`: ready wait 20 s → 90 s.

Validation before the restart (isolated, temp state): a live token and a stale
token coexist, `prune_requests({"live-token"})` removes exactly the stale one,
normal context exit still leaves zero owners. After one controlled restart:
sequential and two concurrent completions each leave `active_requests=0`, and
`/health` is 200.

### H4 repeat leases: root cause and fix (2026-11-05)

The six approved leases (generations 181–186) acquired and released correctly and
production answered a real completion after each, but every payload exited with
`status=2/INVALIDARGUMENT` in ~2.8 s and wrote no rows.

Root cause: the wrapper passed `--campaign-suffix -r1`. argparse treats a
token starting with `-` as an option, so it stopped with exit code 2 before any
work — reproduced locally with the identical arguments:

```
sweep.py run: error: argument --campaign-suffix: expected one argument
```

Fix: suffixes lose their leading dash and the entrypoint always uses the
`--campaign-suffix=<value>` form; `expand_grid` strips a leading dash defensively
and prefixes the repeat with `-`. Two regression tests now cover the CLI parse
(cell named `…-r2-ctx8192-kvq8_0-par4`) and document that the dashed spaced form
is rejected by argparse.

This class of failure is invisible to `bash -n`; only executing the CLI with the
real argument vector catches it.
