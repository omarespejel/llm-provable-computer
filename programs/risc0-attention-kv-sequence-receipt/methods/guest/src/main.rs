use core::cmp::Ordering;

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
struct AttentionSequenceInput {
    initial_kv_cache: Vec<KvEntry>,
    input_steps: Vec<InputStep>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct ScoreRow {
    position: i32,
    score: i64,
    value: [i32; 2],
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct TransitionRow {
    step_index: usize,
    prior_kv_cache: Vec<KvEntry>,
    input_step: InputStep,
    scores: Vec<ScoreRow>,
    selected_position: i32,
    attention_output: [i32; 2],
    next_kv_cache: Vec<KvEntry>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct AttentionSequenceJournal {
    schema: String,
    semantics: String,
    masking_policy: String,
    tie_break: String,
    key_width: usize,
    value_width: usize,
    sequence_length: usize,
    initial_kv_cache: Vec<KvEntry>,
    input_steps: Vec<InputStep>,
    transitions: Vec<TransitionRow>,
    final_kv_cache: Vec<KvEntry>,
}

fn dot(lhs: [i32; 2], rhs: [i32; 2]) -> i64 {
    let score =
        i128::from(lhs[0]) * i128::from(rhs[0]) + i128::from(lhs[1]) * i128::from(rhs[1]);
    i64::try_from(score).expect("attention score outside i64 semantics bound")
}

fn attention_order(lhs: &ScoreRow, rhs: &ScoreRow) -> Ordering {
    match lhs.score.cmp(&rhs.score) {
        Ordering::Equal => rhs.position.cmp(&lhs.position),
        order => order,
    }
}

fn apply_step(step_index: usize, prior_kv_cache: &[KvEntry], input_step: &InputStep) -> TransitionRow {
    let next_item = KvEntry {
        position: input_step.token_position,
        key: input_step.new_key,
        value: input_step.new_value,
    };
    let mut next_kv_cache = prior_kv_cache.to_vec();
    next_kv_cache.push(next_item);

    let mut scores = Vec::with_capacity(next_kv_cache.len());
    for item in &next_kv_cache {
        scores.push(ScoreRow {
            position: item.position,
            score: dot(input_step.query, item.key),
            value: item.value,
        });
    }

    let selected = scores
        .iter()
        .max_by(|left, right| attention_order(left, right))
        .expect("non-empty score trace");
    let selected_position = selected.position;
    let attention_output = selected.value;
    TransitionRow {
        step_index,
        prior_kv_cache: prior_kv_cache.to_vec(),
        input_step: input_step.clone(),
        scores,
        selected_position,
        attention_output,
        next_kv_cache,
    }
}

fn main() {
    let input: AttentionSequenceInput = env::read();
    assert!(
        !input.initial_kv_cache.is_empty(),
        "attention fixture needs at least one initial KV row"
    );
    assert!(
        input.input_steps.len() >= 2,
        "sequence fixture needs at least two carried KV transitions"
    );

    let mut current_kv_cache = input.initial_kv_cache.clone();
    let mut transitions = Vec::with_capacity(input.input_steps.len());
    for (step_index, input_step) in input.input_steps.iter().enumerate() {
        let row = apply_step(step_index, &current_kv_cache, input_step);
        current_kv_cache = row.next_kv_cache.clone();
        transitions.push(row);
    }

    let journal = AttentionSequenceJournal {
        schema: "zkai-attention-kv-risc0-sequence-journal-v1".to_string(),
        semantics: "tiny-single-head-integer-argmax-attention-sequence-v1".to_string(),
        masking_policy: "none".to_string(),
        tie_break: "lowest_position".to_string(),
        key_width: 2,
        value_width: 2,
        sequence_length: input.input_steps.len(),
        initial_kv_cache: input.initial_kv_cache,
        input_steps: input.input_steps,
        transitions,
        final_kv_cache: current_kv_cache,
    };
    env::commit(&journal);
}
