# Project instructions

- Keep this repository focused on reproducible small-model research under constrained hardware; cybersecurity is a secondary exploratory track.
- Preserve raw results and provenance. Never overwrite historical artifacts to update interpretation; label measured, published, theoretical, and unknown evidence separately.
- Treat repeated queries within one hardware run as descriptive observations, not independent hardware replicates. Do not report hardware-level inference from them.
- Do not run model/GPU or production experiments until the current route, isolation, cleanup, and recovery controls are verified. Never execute generated code outside a verified OS-enforced sandbox.
- Run `python -m pytest tests/` for code changes. Compile both reports with `tectonic reports/pt-BR/report_pt-BR.tex --outdir reports/pt-BR` and `tectonic reports/en-US/report_en-US.tex --outdir reports/en-US`; inspect rendered pages when report layout changes.
- Keep Portuguese and English documentation/report conclusions aligned, and distinguish exploratory results from confirmatory evidence.
