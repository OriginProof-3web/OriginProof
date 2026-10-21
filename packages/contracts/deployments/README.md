# Deployment manifests

Current API manifests are produced by `make deploy-local` via `script/deploy_local.py`.
Use `31337.local.json` with `source_commit_sha`, deployment ID/block/hash, genesis
hash, per-contract ABI hashes and distinct roles. Local manifests are generated
and ignored; never invent a commit SHA or copy a sample into active configuration.
Only verified non-local manifests may be committed, with actual immutable identity
and no private keys or RPC tokens. This is not permission for public deployment.

`legacy/31337.example.json` and `legacy/31337.sample.json` preserve the historical
1.0.0 shape and old sample exactly. They are not valid inputs to the current loader.
`make deploy-local-legacy` writes `<chain-id>.legacy.local.json`, never a current
manifest. It requires a disposable local environment and a user-provided legacy
deployer key. The wallet v5 live test creates its own disposable node and separate
evidence; it does not reuse any of these legacy manifests.
