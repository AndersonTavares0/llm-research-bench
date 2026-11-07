# KV-quantisation accuracy at ctx 4096 — blocked by the lease budget

Goal: compare q8_0 vs f16 KV cache on 100-item MCQ at equal context. The 2-minute
per-lease interruption cap makes this infeasible at n=100, so a reduced n=40 arm
was attempted.

## What was measured

f16 arm completed at limit 40 (ctx 4096, q8-free KV, no llama-bench):

| Task | acc | acc_norm | n |
|---|---:|---:|---:|
| ARC Challenge | 0.450 | 0.475 | 40 |
| HellaSwag | 0.425 | 0.450 | 40 |

Artifact: `results/campaigns/gpu-lab-kvq-ctx4096-f16/`.

The q8_0 arm did **not** complete: the job was still running at ~3 minutes (the
80-request MCQ load at ctx 4096 with model start-up), so the supervisor was
terminated to stop the interruption. No q8_0 numbers exist from this run; the
existing q8_0 data at ctx 4096 (n=100, from `gpu-lab-kv-quality`) used a longer
lease window and is not comparable to this n=40 f16 arm.

## Why this is a hard boundary, not a bug

The host-side timing is dominated by per-request prefill at ctx 4096 plus model
load (~15 s); even 40 items per task exceed 120 s. Therefore:

- a *like-for-like* n=100 (or n=40) comparison cannot run under the 2-minute cap;
- shrinking n until it fits (≈15–20 items per task) would produce Wilson
  intervals of ±20–25 pp, which cannot detect the effect the comparison is
  looking for;
- the q8_0 arm must use the same n and context as f16, so the cap must accommodate
  both.

## Operational lesson

Killing the SSH client does not stop the job: the supervisor keeps running and
the lease stays held. A timeout must be enforced by terminating the supervisor
(`kill -TERM <pid>` from the controller state), then verifying
`state=production` with a real completion. The aborted q8_0 lease ran ~3 minutes,
which exceeds the stated 2-minute cap; it was stopped as soon as it was detected
and production recovered (`recovered: OK`, `active_requests=0`).

## Options (need authorisation)

1. Raise the per-lease cap to ~5 minutes for this one experiment (n=100, ±5 pp).
2. Keep the 2-minute cap and run the comparison at ctx 2048 with limit 20
   (~±20 pp), explicitly labelled as a coarse check.
3. Drop the accuracy comparison and rely on the existing latency/memory evidence,
   stating that KV quantisation quality is unmeasured.

No further GPU work was started after this boundary was reached.
