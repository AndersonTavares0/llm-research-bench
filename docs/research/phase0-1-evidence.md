# Phase 0/1 evidence log — GPU route and benchmark assets

**Status:** partial verification; model/GPU execution still blocked.
**Date:** 2026-11-13/14 UTC.
**Scope:** read-only checks of the GPU Lab gateway and primary-source benchmark
assets. No lease was acquired, no model inference was requested, and no
production model was modified.

## 1. Gateway route and model mapping (read-only)

- `curl http://192.168.1.23:18081/health` → HTTP 200, body `{"status":"ok"}`.
- `curl http://192.168.1.23:18081/props` → HTTP 200, saved as
  `/tmp/opencode/gpu-props.json`, SHA-256
  `dedb24b7f8eed9703c7a36800c4af5e75306b0632b3349d567c867a917bd5bac`.
  Reported `role=router`, `max_instances=1`, `models_autoload=true`,
  `build_info=b12033-785322d17`. `/version` returns 404; the build string above is
  the available version evidence.
- `curl http://192.168.1.23:18081/v1/models` → HTTP 200, 12,598-byte JSON saved as
  `/tmp/opencode/gpu-models.json`, SHA-256
  `b451a1783d94fe1849880321216cb6df72aa5b9e8e719187bb9e56bf98ac2030`.
- Reported loaded model: `qwen3.5:4B` with
  `/models/Qwen3.5-4B-Q4_K_M-MTP.gguf`.
- Reported lab aliases include `qwen3.5:UNCESORED` with
  `/models/Huihui-Qwen3.5-4B-abliterated.Q4_K_M.gguf` and
  `qwen2.5-coder:UNCESORED` with
  `/models/Qwen2.5-Coder-3B-Instruct-abliterated-Q4_K_M.gguf`.
- The Coder pair is incomplete: `/v1/models` lists no aligned
  `Qwen2.5-Coder-3B-Instruct` GGUF. The Qwen3.5-4B pair is the only verified
  aligned/abliterated pair currently visible through the gateway.

What this establishes: the production gateway route is reachable, the service
reports `ok`, and the reported alias-to-GGUF mapping for the intended pilot
pair exists.

What this does **not** establish: sandbox isolation, lease acquisition,
watchdog/deadline behavior, production cleanup/restoration, model-file SHA-256,
license/provenance of the GGUF artifacts, or that the aliases are served from
the scratch copies rather than production. Those require an authorized lease
and owner-side evidence.

### 1.1 Reported runtime flags (read-only)

The gateway reports these `llama-server` arguments:

| Alias | Context | KV | GPU layers | Parallel | Speculative decoding |
|---|---|---|---|---|---|
| `qwen3.5:4B` | 32768 | q4_0/q4_0 | 99 | 1 | `--spec-type draft-mtp --spec-draft-n-max 2` |
| `qwen3.5:UNCESORED` | 32768 | q4_0/q4_0 | 99 | 1 | `--spec-type ngram-simple --spec-draft-n-max 3` |

Both use `--chat-template-kwargs {"enable_thinking": false}`, batch 512,
ubatch 256, threads 4, `--fit-target 256`, `--cache-ram 0`.

**Confound:** speculative decoding differs between the two aliases. A matched
comparison requires identical speculative-decoding settings (preferably
`--spec-type none` for both) before P1/P2 can be confirmatory. Until then, a
model comparison is a vendor-default artifact comparison and is exploratory.

## 2. Benchmark assets (pinned clones, access date 2026-11-13)

| Asset | Revision / version | License | Count | SHA-256 |
|---|---|---|---|---|
| XSTest prompts | `d7bb5bd738c1fcbc36edd83d5e7d1b71a3e2d84d` | CC BY 4.0 | 450 (250 benign, 200 contrast) | `11783fb294ed017473ee53c207d71f2161c7672c8d0b037501e78387f801cb5a` |
| StrongREJECT full | deprecated `alexandrasouly/strongreject` @ `f7cad6c17e624e21d8df2278e918ae1dddb4cb56`; data path `strongreject_dataset/` | MIT (repository) | **313** prompts, 6 categories | `4dd70357e4ff8b5d0ba5ebafecab5d6dd5633ce8046e3dd1c8bd93e64de44381` |
| StrongREJECT small | same | MIT (repository) | 60 prompts | `3051340e3e89a3598d764dde497d5fcda80e258ac05cc35e6bd87228ac3d467c` |
| BBQ data | `bea11bd97d79217245b5871acd247b9d6eb24598` | CC BY 4.0 | 58,492 rows across 11 files | per-file table below |
| MBBQ English data | `7046cb17bc86292b347a282275d94b78585f3084` | CC BY 4.0 | 12 files (6 categories + controls) | per-file table below |

Correction: the approved plan says StrongREJECT has 346 prompts. The pinned
dataset contains **313** full prompts and **60** small prompts. The earlier
study draft's 313 count is confirmed; 346 is not supported by the retrieved
asset.

StrongREJECT caveat: the current `dsbowen/strong_reject` repository
(`7a551d5b440ec7b75d4f6f5bb7c1719965b76b47`) is the maintained codebase, but
the full/small CSVs are not stored there. `load_datasets.py` downloads them
from the deprecated `alexandrasouly/strongreject` repository. The repository
MIT license does not by itself establish rights for every upstream prompt
source; component-level terms remain unaudited.

### BBQ file hashes

| File | SHA-256 |
|---|---|
| `BBQ/data/Age.jsonl` | `46e805b3fc2d8cbd26eeb8e8430d98cf7b2dc9c83574ff3674e8ce4f0fca2a60` |
| `BBQ/data/Disability_status.jsonl` | `375d40d9b71f056150264445ec189b13934998f3f49a1e311aa7578eb3b45e5f` |
| `BBQ/data/Gender_identity.jsonl` | `8b5adbb368510a97d5775dc43e1c719e0249fe2da33f13c83e3e29edafec7a00` |
| `BBQ/data/Nationality.jsonl` | `a583e74666aec0341ded8aa3983e7cad694eb24de72c254d28b2df3035720090` |
| `BBQ/data/Physical_appearance.jsonl` | `e48d7e13508565f4801574e611043470c25c95a0a62af3699cb5ee7cb02608fb` |
| `BBQ/data/Race_ethnicity.jsonl` | `4a9f1214cfaa115ce7f0bdb40609122e431f5152c71b8ca64d665e483b946ae6` |
| `BBQ/data/Race_x_gender.jsonl` | `e5dbba782f8c4e25b99dd5470b5136e2db73dbf401cf6d4a5a3ed31b02f95696` |
| `BBQ/data/Race_x_SES.jsonl` | `af8e2ae3d0e5be9ebcbfe7149e591d47ff649e263307f4548f7fb12f6a6d83e8` |
| `BBQ/data/Religion.jsonl` | `cb9555f9f3454a52cd2df85956b59bd7fcca5aa922c8527693b1164d08417616` |
| `BBQ/data/SES.jsonl` | `9f92754bb037b0982604b9112705fb81d60a19d9e759c67e4a85e484a070f528` |
| `BBQ/data/Sexual_orientation.jsonl` | `2c71036b9e7584fe589c42aef32c1a42bc01b9a5e9b1b8704342630cdb08cefd` |

### MBBQ English file hashes

| File | SHA-256 |
|---|---|
| `MBBQ/data/Age_en.jsonl` | `15d34d6ba4dc7e8f2fc2362ef9a3a37ce148e04b2edd3e3700eac49e4c10871c` |
| `MBBQ/data/Age_control_en.jsonl` | `3c4f73e2d38c5a8874af5cc6a8816373510a97936111d6c5784b30419c7a88fe` |
| `MBBQ/data/Disability_status_en.jsonl` | `003424ffe5ebf26302c2cae5af9afd37acd1ff55a86b36412e6bc0b59e1fdc88` |
| `MBBQ/data/Disability_status_control_en.jsonl` | `0c7b587acd7a60dee4d8f1d6e507593b045b0091882afa008715a8ef3b72a708` |
| `MBBQ/data/Gender_identity_en.jsonl` | `b6e9be11cb0d6c85bb305867e1b74338ff0ec2dfebc02760778a4364130a3d92` |
| `MBBQ/data/Gender_identity_control_en.jsonl` | `5e868f6d4d777ba42470e62a91eae89e166b7252ebbbb005a4bc8239cf8c5a10` |
| `MBBQ/data/Physical_appearance_en.jsonl` | `cc6fd2e318e7a7058199537bcf3bdb5ee5629ac8480257d72b8130362f374974` |
| `MBBQ/data/Physical_appearance_control_en.jsonl` | `b92450374ccaaac36f035ee1c8b87ccb714306e1c7b59d8a6c0481b61977d76c` |
| `MBBQ/data/SES_en.jsonl` | `6603a4d2ac5293b2718b13d439361a9b8a16e6be8f600b150b8ab9c0d432efb9` |
| `MBBQ/data/SES_control_en.jsonl` | `807778b3f974ed3873e12d3930a64cac2c8eff66ba9b3e35d2c25b7d51fb6535` |
| `MBBQ/data/Sexual_orientation_en.jsonl` | `d61426a4634a8eecc44ca258c3d70b9730dadcefc625bd5890f1207269d7b660` |
| `MBBQ/data/Sexual_orientation_control_en.jsonl` | `c4c5e4c4e7d08f2c3247ea791d73746497cd1c0e1837deb1e0511efbb5a1c0fc` |

## 3. Open gates

- **Lease self-test not run.** `tools/homelab/lease-selftest.sh` must run as
  root on CT108 against `GPU_LAB_BACKEND=fake`; the restricted gateway accepts
  only `job <repo-script>` inside its sandbox, so the controller path and root
  privileges are not available through it. Owner-side execution or an
  authorized maintenance window is required.
- **Isolation, deadline, cleanup and restoration unverified.** These need an
  authorized lease; the read-only `/v1/models` check cannot demonstrate them.
- **GGUF hashes/licenses/provenance unverified.** The gateway reports paths,
  not file digests; the model repositories and license terms still need to be
  recorded.
- **Runtime flags are not matched.** The aligned alias uses `draft-mtp`
  speculative decoding and the abliterated alias uses `ngram-simple`. The pilot
  comparison is confounded until both run with identical speculative-decoding
  settings; otherwise it is exploratory only.
- **No GPU/model run has been performed in this phase.**
