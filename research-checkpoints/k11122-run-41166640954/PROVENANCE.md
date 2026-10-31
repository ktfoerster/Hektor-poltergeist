# K11122 persistent-worker checkpoint provenance

These merged checkpoints come from completed GitHub Actions run
[`41166640954`](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41166640954)
at commit `60120ba34710c0316110ece1739fa1f10d2994d8`.

Each branch began from the same deterministic previous union: 1,541 residuals
for target 0 and 1,325 for target 3. The new files are sorted set unions of the
two final branch mask lists for each target. Only unconditional residual
obligations are merged; branch assertions, policies, ranks, auxiliary
variables, and solver conclusions are excluded.

| Target | Branch | Artifact ID | Artifact ZIP SHA-256 | Checkpoint SHA-256 |
|---:|---:|---:|---|---|
| 0 | 0 | 13030390269 | `757f46a851aeb4ba8564be8401e54de8ed397aa1317f5e5485161dd43b936419` | `7b700c97ad5e6369399e724e237734a8174b9de25e7d1084c7e0e66096521a23` |
| 0 | 1 | 13029782198 | `b219002323e7f8e96d80474a9add475e8d6a1ee36eab93e51a440bd3f29a585a` | `ef0d0b4dd3f21db00c42e912fa1e98293b1ece10ad23caec2a79cc2ccc2f04dc` |
| 3 | 0 | 13029547838 | `e56220073b0cb4bffecca5087eb48db257024258f467f397f223aafde894085a` | `d708d619c425403b1907577b31d29139077ca63b8127a97273aba6dd9f04ba29` |
| 3 | 1 | 13029552874 | `05a4e235433ddc3f833ca19a0f9049f2166e6a3af9a74dd26dafb48e8da3c841` | `7d1bdc3e9a51d5bb20d004f73229b09645a45dca4a8f2b7e9e4b07b8be221973` |

All four GitHub digests, ZIP CRCs, internal `SHA256.json` manifests, checkpoint
source hashes, and final candidate replays were checked independently before
forming these unions. Both orbits remain `UNKNOWN`; this is reusable search
evidence, not a positive policy or negative certificate.
