# Resultados de campanha (gerado automaticamente)

Gerado em 2026-11-05T13:22:01Z a partir de saídas oficiais do lm-evaluation-harness e do llama-bench.

> Zeros-CI colunas usam Wilson 95%. O --limit do lm-eval seleciona as primeiras N amostras (não uma amostra aleatória); portanto estes números descrevem esta campanha e não autorizam ranking entre modelos.

## Qualidade (lm-evaluation-harness)

| campanha | hardware | modelo | tarefa | métrica | valor | n | IC95% |
|---|---|---|---|---|---|---|---|
| gpu-lab-qwen3-1.7b-v2 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | gsm8k | exact_match,strict-match | 0.000 | 100 | [0.000, 0.037] |
| gpu-lab-qwen3-1.7b-v2 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | gsm8k | exact_match,flexible-extract | 0.460 | 100 | [0.366, 0.557] |
| gpu-lab-qwen3-1.7b-v2 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | ifeval | inst_level_strict_acc,none | 0.755 | 100 | [0.662, 0.829] |
| gpu-lab-qwen3-1.7b-v2 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | ifeval | prompt_level_strict_acc,none | 0.680 | 100 | [0.583, 0.763] |
| gpu-lab-qwen3-1.7b-v2 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | arc_challenge | acc,none | 0.470 | 100 | [0.375, 0.567] |
| gpu-lab-qwen3-1.7b-v2 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | arc_challenge | acc_norm,none | 0.470 | 100 | [0.375, 0.567] |
| gpu-lab-qwen3-1.7b-v2 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | hellaswag | acc,none | 0.440 | 100 | [0.347, 0.538] |
| gpu-lab-qwen3-1.7b-v2 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | hellaswag | acc_norm,none | 0.470 | 100 | [0.375, 0.567] |
| local-rtx3060ti-qwen3-1.7b-v1 | local-rtx3060ti-8gib | qwen3-1.7b-q4km | gsm8k | exact_match,strict-match | 0.000 | 100 | [0.000, 0.037] |
| local-rtx3060ti-qwen3-1.7b-v1 | local-rtx3060ti-8gib | qwen3-1.7b-q4km | gsm8k | exact_match,flexible-extract | 0.410 | 100 | [0.319, 0.508] |
| local-rtx3060ti-qwen3-1.7b-v1 | local-rtx3060ti-8gib | qwen3-1.7b-q4km | ifeval | inst_level_strict_acc,none | 0.755 | 100 | [0.662, 0.829] |
| local-rtx3060ti-qwen3-1.7b-v1 | local-rtx3060ti-8gib | qwen3-1.7b-q4km | ifeval | prompt_level_strict_acc,none | 0.660 | 100 | [0.563, 0.745] |
| local-rtx3060ti-qwen3-1.7b-v1 | local-rtx3060ti-8gib | qwen3-1.7b-q4km | arc_challenge | acc,none | 0.460 | 100 | [0.366, 0.557] |
| local-rtx3060ti-qwen3-1.7b-v1 | local-rtx3060ti-8gib | qwen3-1.7b-q4km | arc_challenge | acc_norm,none | 0.480 | 100 | [0.385, 0.577] |
| local-rtx3060ti-qwen3-1.7b-v1 | local-rtx3060ti-8gib | qwen3-1.7b-q4km | hellaswag | acc,none | 0.440 | 100 | [0.347, 0.538] |
| local-rtx3060ti-qwen3-1.7b-v1 | local-rtx3060ti-8gib | qwen3-1.7b-q4km | hellaswag | acc_norm,none | 0.480 | 100 | [0.385, 0.577] |
| local-rtx3060ti-qwen3-1.7b-v1 | local-rtx3060ti-8gib | qwen3-1.7b-q8 | arc_challenge | acc,none | 0.500 | 100 | [0.404, 0.596] |
| local-rtx3060ti-qwen3-1.7b-v1 | local-rtx3060ti-8gib | qwen3-1.7b-q8 | arc_challenge | acc_norm,none | 0.440 | 100 | [0.347, 0.538] |
| local-rtx3060ti-qwen3-1.7b-v1 | local-rtx3060ti-8gib | qwen3-1.7b-q8 | hellaswag | acc,none | 0.430 | 100 | [0.337, 0.528] |
| local-rtx3060ti-qwen3-1.7b-v1 | local-rtx3060ti-8gib | qwen3-1.7b-q8 | hellaswag | acc_norm,none | 0.470 | 100 | [0.375, 0.567] |
| smoke-qwen3-1.7b-v1 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | gsm8k | exact_match,strict-match | 0.000 | 20 | [0.000, 0.161] |
| smoke-qwen3-1.7b-v1 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | gsm8k | exact_match,flexible-extract | 0.000 | 20 | [0.000, 0.161] |
| smoke-qwen3-1.7b-v1 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | ifeval | inst_level_strict_acc,none | 0.667 | 20 | [0.449, 0.831] |
| smoke-qwen3-1.7b-v1 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | ifeval | prompt_level_strict_acc,none | 0.600 | 20 | [0.387, 0.781] |
| smoke-qwen3-1.7b-v1 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | arc_challenge | acc,none | 0.350 | 20 | [0.181, 0.567] |
| smoke-qwen3-1.7b-v1 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | arc_challenge | acc_norm,none | 0.400 | 20 | [0.219, 0.613] |
| smoke-qwen3-1.7b-v1 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | hellaswag | acc,none | 0.400 | 20 | [0.219, 0.613] |
| smoke-qwen3-1.7b-v1 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | hellaswag | acc_norm,none | 0.400 | 20 | [0.219, 0.613] |
| smoke-qwen3-1.7b-v1 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | belebele_por_Latn | acc,none | 0.750 | 20 | [0.531, 0.888] |
| smoke-qwen3-1.7b-v1 | gpu-lab-ct108-gtx1050ti-4gib | qwen3-1.7b-q4km | belebele_por_Latn | acc_norm,none | 0.750 | 20 | [0.531, 0.888] |

## Desempenho (llama-bench)

| modelo | prompt | geração | tok/s médio | desvio | build | GPU | backends |
|---|---|---|---|---|---|---|---|
| qwen3-1.7b-q4km | 512 | 0 | 848.84 | 1.89 | ddf48f85c | NVIDIA GeForce GTX 1050 Ti | CUDA |
| qwen3-1.7b-q4km | 0 | 128 | 48.03 | 0.01 | ddf48f85c | NVIDIA GeForce GTX 1050 Ti | CUDA |
| qwen3-1.7b-q4km | 512 | 0 | 10135.44 | 164.64 | ddf48f85c | NVIDIA GeForce RTX 3060 Ti | CUDA |
| qwen3-1.7b-q4km | 0 | 128 | 255.80 | 0.52 | ddf48f85c | NVIDIA GeForce RTX 3060 Ti | CUDA |
| qwen3-1.7b-q8 | 512 | 0 | 10925.78 | 155.77 | ddf48f85c | NVIDIA GeForce RTX 3060 Ti | CUDA |
| qwen3-1.7b-q8 | 0 | 128 | 179.99 | 0.16 | ddf48f85c | NVIDIA GeForce RTX 3060 Ti | CUDA |
| qwen3-1.7b-q4km | 512 | 0 | 850.30 | 1.12 | ddf48f85c | NVIDIA GeForce GTX 1050 Ti | CUDA |
| qwen3-1.7b-q4km | 0 | 128 | 48.15 | 0.02 | ddf48f85c | NVIDIA GeForce GTX 1050 Ti | CUDA |

