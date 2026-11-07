# Cybersecurity model evidence and evaluation plan

**Status:** evidence review only; no model selected, downloaded, or run. Sources
were checked on 2026-11-07. Hub metadata and model-owner claims are not
independent validation or legal advice.

## Decision summary

The evidence reviewed so far does not justify adding a specialist model to the
benchmark catalog as a validated security model. `SecGPT-1.5B` is the most
plausible same-scale specialist candidate found, but its capability evidence is
owner-reported, its card and checkpoint metadata disagree on parameter count,
and its full-precision weights leave little practical margin on a 4-GiB GPU.
`Qwen2.5-1.5B-Instruct` is a reasonable general-purpose comparison candidate,
not a control whose performance can be inferred from published numbers. Neither
has been run in this environment.

## Candidate and evidence review

| Candidate/source | What the source supports | Limitations for this project |
|---|---|---|
| [SecGPT-1.5B model card](https://huggingface.co/clouditera/SecGPT-1.5B/tree/74755b86b0b2380d6a16f313339e018d892a0121) and [project repository](https://github.com/Clouditera/SecGPT) | Owner describes a Chinese security-focused Qwen-family model and reports security and general-task scores. Card labels the license Apache-2.0. | The model card labels it 2B, while the Hub API snapshot at revision [`74755b86b0b2380d6a16f313339e018d892a0121`](https://huggingface.co/clouditera/SecGPT-1.5B/tree/74755b86b0b2380d6a16f313339e018d892a0121) reports `Qwen2ForCausalLM` with 1,543,714,304 F16 parameters. These are owner/Hub claims and need reconciliation. The project README says SecGPT outperforms Qwen2.5 across its evaluation table, but its own 1.5B table has lower SecGPT scores on C-Eval (54.02 vs 59.91), GSM8K (55.95 vs 61.03), and BBH (34.90 vs 43.44). Its better CS-Eval number is not an independent reproduction. Chinese orientation limits direct English-task applicability. At roughly 3.09 GB decimal for F16 weights alone, full-precision inference is not a practical 4-GiB fit once runtime memory is included; no verified compatible quantized artifact was assessed. |
| [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/989aa7980e4cf806f80c7fef2b1adb7bc71aa306) | Official card reports Apache-2.0, 1.54B parameters, multilingual support including English, and 32,768-token context. It is a plausible same-scale general baseline for a controlled comparison. | Card claims/context are not an evaluation result for this repository. The linked revision is a metadata snapshot; verify the exact runtime/quantization before any comparison. |
| [Qwensploit CyberSecurity GGUF](https://huggingface.co/xtools-at/Qwen3.5-4B-Qwensploit-CyberSecurity-GGUF/tree/ea2af9ae5cef4016223dbfcdcd8e3075efeafeec) | Hub metadata advertises a Q4_K_M GGUF of about 2.07 GB for the text weights. | This community repository derives from an unofficial three-way merged “uncensored/heretic” base, not the official Qwen checkpoint. Hub tags and the Apache-2.0 label do not establish the complete license chain. A 2.07-GB weight file does not prove 4-GiB runtime fit; context/KV, activations, multimodal projector, and runtime support still matter. No independent security evaluation was found. Not selected. |
| [Vectrayx-Nano](https://huggingface.co/jsantillana/vectrayx-nano/tree/f0adf8060110bb15577e6a6229a886472698d422) | Author presents a 42M-parameter Spanish cybersecurity model with a 1K context and GGUF variants; the linked paper reports small repeated experiments. | Language, context, author-controlled benchmark, and lack of independent replication make it a poor primary candidate for this project’s English practical tasks. Not selected. |

Hub license fields above are metadata snapshots, not a legal audit of base-model,
training-data, or merge rights. Before a model enters a reproducible run, record
its immutable revision, weight-file hash/quantization, provenance, license
chain, tokenizer/template, and tested runtime support.

## What existing cybersecurity evaluations establish

[CyberSecEval 3](https://arxiv.org/abs/2408.01605) spans risks to third parties
and application developers: insecure code suggestions, prompt injection,
malicious code execution requests, offensive capability and other safety
questions. It is useful as a taxonomy, but the paper evaluates a dated model
cohort, and some outcomes use LLM judgments or human studies. Its offensive
sections include phishing and cyber operations; do not copy those tasks into
this repository without a separately approved, isolated protocol.

The current [Meta PurpleLlama CybersecurityBenchmarks README](https://github.com/meta-llama/PurpleLlama/tree/main/CybersecurityBenchmarks)
describes a broader CyberSecEval 4 suite, including code, scanner/SOC-related,
tool and offensive-operation tasks. The suite’s own setup expects a cyber range
and some components have substantial compute/storage demands. The upstream
software is marked [MIT licensed](https://github.com/meta-llama/PurpleLlama/blob/main/CybersecurityBenchmarks/LICENSE),
but that does not automatically license every benchmark dataset or third-party
artifact. We should borrow task distinctions, not execute the suite wholesale.

[CS-Eval](https://arxiv.org/abs/2411.16239) reports 4,369 cybersecurity
questions over 42 subcategories and multiple knowledge/ability/application
levels. It uses static questions and, for open-ended answers, an LLM judge; its
paper discusses data quality/contamination risks and identifies executable
vulnerability environments and agents as future work. It therefore measures
knowledge/reasoning under its protocol, not successful operation in a live or
disposable pentest environment. SecGPT’s published CS-Eval score is
owner-reported; the cited benchmark paper is not an independent SecGPT
replication.

## Safe, staged evaluation if deployment controls are verified

Do not run a candidate until the current inference route, GPU-lab isolation,
watchdog, lease cleanup, and recovery procedure are confirmed from authoritative
operator configuration. Then use a pre-registered, staged study:

1. **Static vulnerability analysis:** versioned, locally stored code snippets
   with independently established vulnerable/non-vulnerable labels; ask for
   location, weakness, evidence and a bounded remediation. Score TP/FP/FN,
   localization, evidence quality and whether proposed fixes pass tests.
2. **Scanner-output interpretation:** canned scanner findings with known true,
   false-positive and duplicate cases. Measure triage accuracy and explanation
   calibration; do not scan external targets.
3. **Mock tool selection and authorization:** simulated tool schemas and
   harmless responses only. Score correct selection/arguments and separately
   record refusals, unsafe or out-of-scope actions, and malformed calls.
4. **Optional execution stage:** only in a disposable local target with
   outbound networking disabled, no secrets, resettable snapshots and verified
   containment/recovery. This stage is not currently authorized by verified
   infrastructure evidence and is not a prerequisite for the first two stages.

For a confirmatory comparison, lock a separate held-out case set before prompt
development; freeze dataset/checkpoint hashes, quantization, template, prompt,
decoding, runtime and scoring rubric; compare SecGPT-1.5B with Qwen2.5-1.5B-
Instruct under the same harness and hardware. Have two blinded reviewers
adjudicate ambiguous code/evidence outcomes and resolve disagreements without
seeing model identity. Keep exploratory pilot cases out of tuning and the final
holdout. Report quality, false positives, false negatives, valid-fix test rate,
tool-call correctness, unsafe behavior and refusals as distinct outcomes; also
record latency, throughput, peak VRAM and practical context. Do not use lower
refusal rate as a proxy for capability.

## Sources and retrieval limits

- Meta, *CyberSecEval 3*, arXiv:2408.01605v2 (2024-09-06); official paper and
  benchmark repository linked above.
- Meta, *CyberSecEval 4* repository README and MIT license, current upstream
  content checked 2026-11-07.
- SecGPT project README and Hugging Face card/API metadata, checked 2026-11-07;
  claims are from the model owner, not independent evaluations.
- Qwen2.5-1.5B-Instruct official model card, checked 2026-11-07.
- Vectrayx-Nano and Qwensploit Hub cards/API metadata, checked 2026-11-07;
  community/author claims, not independently reproduced.

Web-search integration returned no usable results during this review, so this
is a bounded primary-source scan rather than a systematic literature review.
No specialist candidate was selected, downloaded, or executed; no live
deployment configuration or recovery procedure was available in the repository.
