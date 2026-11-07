# Schema-specific vs generic JSON constraints at ~6.8k context

## Question and controlled comparison

Does llama.cpp's generic JSON-object constraint provide the same structured-data
reliability as a schema-specific constraint? Four leases compared `json_schema`
and `json_object` twice, reversing order on the second pair. Each run used the
same fixed 30-case structured-output suite, Qwen3-1.7B Q4_K_M (SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
b12024, ctx 8192, q8_0 K/V, 6,800 filler setting, strict prompt, temperature 0,
seed 42, one client, and a 512-token generation cap. Per paired run, only
`response_format` changed. Captured requests were checked: prompts and all other
payload fields matched; the format was exactly `json_schema` or `json_object`.

## Results

| Order | Constraint | Schema-valid | Failure type | Empty | Finish reason | p50 / p95 (ms) | Peak VRAM |
|---|---|---:|---|---:|---|---:|---:|
| 1 | `json_schema` | **30/30** | none | 0 | stop 30 | 6,089 / 9,926 | 1,702.1 MiB |
| 1 | `json_object` | **18/30** | schema echo 12 | 0 | stop 30 | 7,048 / 9,935 | 1,702.1 MiB |
| 2 (reversed) | `json_object` | **18/30** | schema echo 12 | 0 | stop 30 | 7,064 / 9,985 | 1,702.1 MiB |
| 2 (reversed) | `json_schema` | **30/30** | none | 0 | stop 30 | 6,099 / 9,982 | 1,702.1 MiB |

Every generic-mode failure was syntactically valid JSON that copied the schema
instead of answering the requested case (example: output contained `"required":
["city", "unit"]` and the property definitions). These are schema/semantic
failures, not invalid JSON, empties, or generation-cap hits. The same 12 cases
failed in both JSON-object executions; all outputs and validity classifications
were identical within each repeated mode.

Per paired execution, exact two-sided McNemar gives 12 schema-only successes,
zero JSON-object-only successes (**p = 0.000488**). This p-value is descriptive
for these 30 fixed benchmark items; prompt-template dependence and the exact
repeat outputs mean the two executions are reproducibility checks, not 60
independent items or a sample of arbitrary applications.

Peak sampled VRAM was unchanged. The median latency was about 0.96 s higher for
generic JSON mode in both pairs; p95 was similar. With one execution per arm per
order and deterministic decoding, latency differences are descriptive only.

## Interpretation

Generic JSON mode constrains syntax but does not encode the requested object
schema. In this prompt setup, the model frequently emitted the schema itself.
For applications requiring specific fields and types, use schema-specific
constraints and still validate semantic correctness. This result does not show
that generic JSON mode is generally inferior for tasks that only require valid
JSON, nor that schema constraints ensure the values are correct in other tasks.

Together with `generation-budget-longctx-full30.md`, this separates two failure
classes: earlier 256-token cap failures ended with `finish_reason=length` and
were rescued by 512 tokens; the generic-JSON failures here ended normally but
returned the wrong JSON object. Raising the token cap would not address these
schema-echo failures.

## Reproduction and safety

Raw requests/responses, usage, finish reasons, metadata, server logs, and VRAM
samples are archived under:

- `results/campaigns/gpu-lab-longctx-grammar7k-json-schema/`
- `results/campaigns/gpu-lab-longctx-grammar7k-json-object/`
- `results/campaigns/gpu-lab-longctx-grammar7k-json-object-r2/`
- `results/campaigns/gpu-lab-longctx-grammar7k-json-schema-r2/`

All four manifests report `status=measured`, `exit_code=0`, the same model hash,
runtime, context, KV types, seed, and case count. Controller generations 271–274
each ended `supervisor_stopped` / `restored`; after each lease, production
returned to `active_requests=0` and passed both health and a real completion
check. The original remote `longctx-config-next.env` was restored unchanged.

Repeated boundary refusals were reviewed without changing controller code or
loosening the boundary. The backend permits container descendants, conmon,
runtime processes, and recognized infrastructure within the generation cgroup;
other processes are rejected. Refusals at generations 266, 269, and 270 named
transient `bash` PIDs. Those processes were gone afterward, and successful
leases at 267–268 and 271–274 show no persistent contamination. Historical
parent/command-line data for the rejected PIDs was not retained, so the cause
cannot be determined more precisely than a transient process-placement/race
hypothesis. The refusal path remains intact.

Experimental-design and claim-calibration methods were informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065
