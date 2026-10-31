# K11122 Boolean-SAT checkpoint provenance

These merged checkpoints come from the completed GitHub Actions run
[`41164233786`](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41164233786)
at commit `bf2e497771e56119c21465db880a385fd108eeed`.

Each branch began from the same deterministic prior union: 1,221 residuals for
target 0 and 1,027 for target 3. The new files are sorted set unions of the two
final branch checkpoint mask lists for each target. Only unconditional
residual obligations are merged; branch assertions, policies, ranks, auxiliary
variables, and solver conclusions are not merged.

| Target | Branch | Artifact ID | Artifact ZIP SHA-256 |
|---:|---:|---:|---|
| 0 | 0 | 13028882993 | `05bf9d806a94f75e2b6095fc633fe1177880a74b5bc84fda5ca03a635449a31a` |
| 0 | 1 | 13029232369 | `6e766bdeacf63daa29af8ceff93c5ec8f332eaefcbcc380c7a1d3e5e7d63cd39` |
| 3 | 0 | 13028497215 | `461d833cbf15e2303ecb7282ba4d53e6c6ebbe8a7da69910032166b265bb8b46` |
| 3 | 1 | 13028823204 | `f4824a6127bfa5aa34c1a595a11d238d655624dd6da6d9072702cd0e782fd557` |

All four GitHub digests, ZIP CRCs, internal `SHA256.json` manifests, checkpoint
source hashes, and final candidate replays were checked independently before
forming these unions. Both orbits remain `UNKNOWN`; this is reusable search
evidence, not a positive policy or negative certificate.
