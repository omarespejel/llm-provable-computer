# Known-Bad Phase 29-37 Corpus

This corpus is manifest-driven. The runner in `tests/known_bad_phase_artifacts.rs`
builds a valid Phase 29 through Phase 37 artifact chain in memory, applies each
mutation listed in `manifest.json`, and checks that the public parser or
source-bound verifier rejects the result.

The important class here is the self-consistent bad artifact: the runner often
recomputes the outer commitment after mutation. That catches verifiers that only
notice a stale root commitment while missing a false inner statement.
