use risc0_zkvm::guest::env;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct KvEntry {
    position: i32,
    key: [i32; 2],
    value: [i32; 2],
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct InputStep {
    token_position: i32,
    query: [i32; 2],
    new_key: [i32; 2],
    new_value: [i32; 2],
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct AttentionInput {
    prior_kv_cache: Vec<KvEntry>,
    input_step: InputStep,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct ScoreRow {
    position: i32,
    score: i32,
    value: [i32; 2],
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct AttentionJournal {
    schema: String,
    semantics: String,
    prior_kv_cache: Vec<KvEntry>,
    input_step: InputStep,
    scores: Vec<ScoreRow>,
    selected_position: i32,
    attention_output: [i32; 2],
    next_kv_cache: Vec<KvEntry>,
}

fn dot(lhs: [i32; 2], rhs: [i32; 2]) -> i32 {
    lhs[0] * rhs[0] + lhs[1] * rhs[1]
}

fn main() {
    let input: AttentionInput = env::read();
    assert!(
        !input.prior_kv_cache.is_empty(),
        "attention fixture needs at least one prior KV row"
    );

    let next_item = KvEntry {
        position: input.input_step.token_position,
        key: input.input_step.new_key,
        value: input.input_step.new_value,
    };
    let mut next_kv_cache = input.prior_kv_cache.clone();
    next_kv_cache.push(next_item);

    let mut scores = Vec::with_capacity(next_kv_cache.len());
    for item in &next_kv_cache {
        scores.push(ScoreRow {
            position: item.position,
            score: dot(input.input_step.query, item.key),
            value: item.value,
        });
    }

    let selected = scores
        .iter()
        .max_by_key(|row| (row.score, -row.position))
        .expect("non-empty score trace");
    let selected_position = selected.position;
    let attention_output = selected.value;

    let journal = AttentionJournal {
        schema: "zkai-attention-kv-risc0-semantics-journal-v1".to_string(),
        semantics: "tiny-single-head-integer-argmax-attention-v1".to_string(),
        prior_kv_cache: input.prior_kv_cache,
        input_step: input.input_step,
        scores,
        selected_position,
        attention_output,
        next_kv_cache,
    };
    env::commit(&journal);
}
