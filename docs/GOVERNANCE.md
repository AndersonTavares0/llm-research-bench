# Repository Governance & Branch Protection Architecture

**Repository:** `AndersonTavares0/llm-research-bench`  
**Model:** Single-Maintainer Open Scientific Research Repository  
**Lead Maintainer:** Anderson Tavares (@AndersonTavares0)

---

## 1. Single-Maintainer Operating Model

Because this repository is maintained by an individual principal researcher, classic enterprise pull request rules requiring approvals from *other* team members can create operational deadlock (where the sole owner is blocked from merging authorized code).

To balance **rigorous automated quality gates** with **maintainer autonomy**, the repository adopts the following policy:

1. **Automation Over Bureaucracy:** Quality gates are enforced through automated GitHub Actions CI (`test` and `compile-reports`) rather than mandatory manual peer review counters.
2. **Branching Strategy:**
   - `main`: Production-ready release branch representing published monographs, verified benchmarks, and reproducible code. Never push directly to `main`.
   - `feat/*`: Feature branches for new evaluators, datasets, profilers, or tooling.
   - `fix/*`: Bugfix branches for CI, calculation corrections, or code errors.
   - `docs/*`: Monograph and documentation updates.
3. **Traceability:** Every change enters `main` via a Pull Request with a clear description, commit history, and automated check passes.

---

## 2. GitHub Branch Protection Configuration Guide

To configure branch protection for `main` on GitHub without blocking the solo maintainer:

Navigate to: **Settings $\to$ Branches $\to$ Branch protection rules $\to$ Add rule** (or **Rulesets $\to$ New ruleset**) for branch pattern `main`:

### Recommended Configuration:
1. **Require status checks to pass before merging:** `ENABLED`
   - Select status check: `test` (Unit and integration tests)
   - Select status check: `compile-reports` (Tectonic LaTeX monograph compilation)
2. **Require branches to be up to date before merging:** `ENABLED`
3. **Do not allow bypassing the above settings:** `ENABLED` (or disabled for repo owner if emergency hotfix bypass is needed)
4. **Require a pull request before merging:** `ENABLED`
   - **Required approvals:** Set to `0` (or leave unchecked if solo maintainer merges own PRs).
   - *Note:* If GitHub requires at least 1 approval, uncheck "Require approvals" while keeping "Require a pull request before merging" enabled, so the maintainer can merge their own PR after CI passes.
5. **Do not allow force pushes:** `ENABLED` (Prevents accidental history rewriting)
6. **Do not allow deletions:** `ENABLED` (Prevents accidental branch deletion)

---

## 3. Administrative Actions Required by Repository Owner

The following actions require repository owner privileges and must be executed in the GitHub web interface:

- [ ] Apply branch protection rule to `main` as outlined in Section 2 above.
- [ ] Confirm GitHub Actions permissions under **Settings $\to$ Actions $\to$ General $\to$ Workflow permissions**: Select **Read repository contents and packages permissions** (default secure).
- [ ] Enable Dependabot alerts and security updates under **Settings $\to$ Code security and analysis**.
