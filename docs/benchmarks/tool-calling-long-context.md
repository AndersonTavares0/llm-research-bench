# Tool calling at 1.9k and 3.8k context (GTX 1050 Ti)

> **Audit correction:** The historical interpretation below overstates these
> exploratory results. Nominal fill settings were not verified token counts;
> native and JSON arms differ in interface, prompt, and schema, not just decoding
> constraint. Empty or invalid content does not establish EOS or grammar behavior,
> and missing tool selections must not be counted as wrong tool choices. A perfect
> score on 18 fixed cases does not establish robustness or no degradation.

18 deterministic cases across three tools (`get_weather`, `convert_currency`,
`search_notes`), each with an expected tool and expected argument semantics.
Scoring separates **tool selection**, **argument-schema validity**, and
**semantic correctness**; empty outputs are counted separately.

## Native tool calling (OpenAI `tools` channel)

| Context | Valid | Selection | Args schema | Semantic | Empty | p50 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1.9k | **18/18** | 1.00 | 1.00 | 1.00 | 0 | 3,206 ms | 4,579 ms |
| 3.8k | **18/18** | 1.00 | 1.00 | 1.00 | 0 | 3,579 ms | 5,945 ms |

**Finding:** native tool calling is robust to a 2× prompt increase on this stack —
no selection, schema or semantic errors, and latency rises only with prefill.

## JSON-constrained "tool call" (response_format json_schema)

The model returns `{"tool": ..., "arguments": {...}}` as JSON text under a grammar.

| Variant | 1.9k | 3.8k | Dominant failures |
|---|---:|---:|---|
| v1: `arguments` as bare object | 2/18 | 3/18 | grammar forced `arguments = {}` → 16 schema failures |
| v2: union properties, no `required` | 6/18 | 8/18 | truncated JSON (early EOS), omitted required args, wrong tool |

**Interpretation:** JSON-mediated tool calling is not a substitute for the native
tool channel on llama.cpp b12024. Two mechanisms are visible:
1. `additionalProperties`-free object schemas collapse `arguments` to `{}`;
2. the grammar still permits EOS mid-object, so truncated JSON appears — the same
   early-stop behaviour seen in the structured-output mechanism probe.

Selection is also weaker (9/18 wrong tool): asking the model to name a tool inside
JSON text is a different task from emitting a tool call.

## Practical conclusion

Use the native `tools` channel for function calling. Grammar-constrained JSON is a
good fit for **data extraction** (structured output: 27/30 at 3.8k), not for
tool invocation.

## Limitations

- One run per cell, one model/quantisation, ctx 8192, q8_0 KV.
- The JSON arm's schema design is a deliberate tradeoff (union of argument keys,
  no `required`) to allow per-tool subsets; a per-tool `anyOf` schema might do
  better but llama.cpp's grammar coverage for it is untested here.
- 18 cases → Wilson half-width ≈ ±0.11 even for a perfect score.

Artifacts: `results/campaigns/gpu-lab-toolctx-{n1900,n3800,j1900,j3800,j2-1900,j2-3800}/`.

## Near the context limit (~7k tokens)

| Suite | Condition | Result | p50 | p95 | VRAM |
|---|---|---|---:|---:|---:|
| Tool calling (native) | ~6.8k fill | **18/18** selection, schema and semantics | 5,115 ms | 8,992 ms | 1,702 MiB |
| Structured output (constrained) | ~6.8k fill | 24/30 (0.80) | 6,088 ms | 8,178 ms | 1,702 MiB |

Native tool calling shows **no degradation at ~7k tokens**, well past the 3.8k
point where JSON-mediated calls already struggled. Structured output under
constrained decoding falls from 27/30 (3.8k) to 24/30 (7k), but the paired test
gives 3 improved / 6 worsened, McNemar **p = 0.508** — no evidence of a real drop
at this sample size.

Latency continues to scale with prompt length (tool p50 3.58 s → 5.12 s; p95
5.95 s → 8.99 s), and VRAM stays flat because the KV budget is preallocated.

Artifacts: `results/campaigns/gpu-lab-toolctx-n7k/`, `…-longctx-s7k/`.
