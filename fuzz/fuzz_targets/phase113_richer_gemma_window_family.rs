#![no_main]

use std::path::{Path, PathBuf};
use std::sync::OnceLock;

use libfuzzer_sys::fuzz_target;
use llm_provable_computer::{
    load_phase107_folded_repeated_multi_interval_gemma_richer_family_artifact,
    load_phase112_transformer_accumulation_semantics_artifact,
    verify_phase113_richer_gemma_window_family_artifact,
    Phase107FoldedRepeatedMultiIntervalGemmaRicherFamilyArtifact,
    Phase112TransformerAccumulationSemanticsArtifact, Phase113RicherGemmaWindowFamilyArtifact,
};

struct Phase113Support {
    leaves: Vec<Phase107FoldedRepeatedMultiIntervalGemmaRicherFamilyArtifact>,
    semantics: Phase112TransformerAccumulationSemanticsArtifact,
}

fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .canonicalize()
        .expect("canonical repo root")
}

fn phase113_support() -> &'static Phase113Support {
    static SUPPORT: OnceLock<Phase113Support> = OnceLock::new();
    SUPPORT.get_or_init(|| {
        let root = repo_root();
        let repeated_window_root =
            root.join("docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22");
        let scaling_root =
            root.join("docs/paper/artifacts/stwo-richer-gemma-window-family-scaling-v1-2026-04-22");
        let leaves = (0..4)
            .map(|index| {
                load_phase107_folded_repeated_multi_interval_gemma_richer_family_artifact(
                    &repeated_window_root.join(format!("phase107-leaf-{index}.stwo.json")),
                )
                .expect("load frozen phase107 leaf")
            })
            .collect::<Vec<_>>();
        let semantics = load_phase112_transformer_accumulation_semantics_artifact(
            &scaling_root.join("phase112-transformer-accumulation-semantics-w8.stwo.json"),
        )
        .expect("load frozen phase112 semantics");
        Phase113Support { leaves, semantics }
    })
}

fuzz_target!(|data: &[u8]| {
    let Ok(artifact) = serde_json::from_slice::<Phase113RicherGemmaWindowFamilyArtifact>(data) else {
        return;
    };
    let support = phase113_support();
    let _ = verify_phase113_richer_gemma_window_family_artifact(
        &artifact,
        &support.leaves,
        &support.semantics,
    );
});
