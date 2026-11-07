# HotpotQA subset attribution

`hotpotqa-validation-100.jsonl` is a deterministic subset of the
`hotpotqa/hotpot_qa` dataset, configuration `distractor`, validation split,
downloaded at Hub revision
`1908d6afbbead072334abe2965f91bd2709910ab`.

HotpotQA was created by Yang et al. (2018), “HotpotQA: A Dataset for Diverse,
Explainable Multi-hop Question Answering,” and is distributed under
CC-BY-SA-4.0. This repository retains the dataset's question, answer, candidate
Wikipedia passages, and supporting-fact annotations. The subset selection is
described in `hotpotqa-validation-100.manifest.json` and can be regenerated with
`python tools/rag/prepare_hotpotqa.py` in an environment with `datasets==5.1.0`.

This is a balanced bridge/comparison sample, not a population-representative
estimate. It is a closed-context QA set with supplied candidate passages, not a
retrieval benchmark over a live corpus and not a version-history conflict set.
