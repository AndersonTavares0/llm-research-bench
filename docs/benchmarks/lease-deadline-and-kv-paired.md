# Lease deadline enforcement + paired KV-quality check (2026-11-06)

## 1. Per-lease deadline enforcement (fixed and validated)

**Defect:** the supervisor only enforced the 12-hour catastrophe bound
(`GPU_LAB_SAFETY_BOUND_S`), so a 2-minute policy cap had no effect: killing the
SSH client left the supervisor running and the lease held.

**Fix (CT108, backup `/root/gpu-lab-job-supervisor.bak-*`):** the supervisor now
reads an operator policy file and uses it as the deadline when it is a valid
integer ≥10 s and below the catastrophe bound:

```
$STUDY_ROOT/workspace/.gpu-lab-max-seconds
```

It is passed to `controller acquire --deadline` and used by the job wait loop, so
the controller enforces it too. Malformed values are ignored (fall back to the
12-hour bound).

**Validation:** policy 60 s, payload `sleep 600`:

- supervisor log contains `reason=timeout`;
- the lease ended at the policy deadline, not at 600 s;
- `state=production`, `active_requests=0`, real completion `recovered: OK`.

This is the enforcement the earlier session lacked; no controller or drain
safeguard was bypassed.

## 2. KV quantisation accuracy, paired (n=20 per task, ctx 4096)

Both arms used the same first 20 items per task (seed 42, `--limit 20`), each in
an independent lease with a 120 s policy deadline. Per-item correctness comes
from the harness sample logs, so the comparison is paired.

| Task | f16 acc | q8_0 acc | Discordant (f16✗→q8✓ / f16✓→q8✗) | McNemar p | Paired diff (95% bootstrap CI) |
|---|---:|---:|---|---:|---|
| ARC Challenge | 0.350 | 0.400 | 1 / 0 | 1.000 | +0.050 (0.000 to +0.150) |
| HellaSwag | 0.400 | 0.400 | 0 / 0 | 1.000 | 0.000 (0.000 to 0.000) |

**Finding:** across 40 paired items there is exactly **one** discordant case
(ARC, favouring q8_0); no evidence of a quality difference, but also no power to
detect a small one. The bound is “at most a few items out of 40” — not
“q8_0 is lossless”.

Artifacts: `results/campaigns/gpu-lab-kvq-n20-{f16,q8_0}/`.

## Budget and limitations

- Leases this session: 1 × 60 s (deadline validation) + 2 × ~90 s (KV arms) ≈
  4 min of production interruption, within the 30-minute cap; recovery verified
  after every lease.
- n=20 per task, one run per arm, ctx 4096 only.
- The earlier f16 n=40 arm (ARC .450/.475, Hella .425/.450) used a different item
  count and is not part of this paired comparison.
- Long-context capability probes and prompt-length repeats remain pending.
