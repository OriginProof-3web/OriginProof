# Cross Review Prompt

Review the assigned teammate PR from a clean worktree or clone. Read root and applicable `AGENTS.md` before inspecting the diff.

1. Confirm the PR starts from the agreed bootstrap or integration SHA.
2. Run `python scripts/ci/validate_structure.py`, `make env-check`, and `make env-fingerprint`.
3. Compare lockfile, Schema, ABI, and Git hashes with the expected environment fingerprint.
4. Run the owner's narrow tests and the relevant integration or E2E test.
5. Check path ownership, generated-file policy, secret/privacy rules, AI decision boundaries, and undocumented public-contract changes.
6. Do not edit the PR merely to hide a failure. Report a minimal reproducible failure and target owner.

Return: verdict, commands actually run, results, contract changes, security/privacy findings, reproducibility result, and required fixes.
