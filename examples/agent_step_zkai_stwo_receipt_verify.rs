use std::env;
use std::fs;
use std::path::Path;

use llm_provable_computer::{
    load_agent_step_receipt_bundle_v1,
    verify_agent_step_receipt_bundle_v1_with_zkai_stwo_model_subreceipt,
};
use serde::Serialize;
use serde_json::Value;

#[derive(Debug, Serialize)]
struct CaseResult {
    case_id: String,
    accepted: bool,
    error: String,
}

#[derive(Debug, Serialize)]
struct Output {
    schema: &'static str,
    results: Vec<CaseResult>,
}

const MAX_JSON_INPUT_BYTES: u64 = 1024 * 1024;

fn load_json(path: &str) -> Result<Value, String> {
    let path_ref = Path::new(path);
    let size = fs::metadata(path_ref)
        .map_err(|err| format!("stat {path}: {err}"))?
        .len();
    if size > MAX_JSON_INPUT_BYTES {
        return Err(format!(
            "read {path}: input is {size} bytes, max is {MAX_JSON_INPUT_BYTES}"
        ));
    }
    let raw = fs::read_to_string(path_ref).map_err(|err| format!("read {path}: {err}"))?;
    serde_json::from_str(&raw).map_err(|err| format!("parse {path}: {err}"))
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 3 {
        eprintln!(
            "usage: agent_step_zkai_stwo_receipt_verify <bundle.json> <zkai_receipt.json> <checked_stwo_evidence.json>"
        );
        std::process::exit(2);
    }

    let result = match (
        load_agent_step_receipt_bundle_v1(Path::new(&args[0])),
        load_json(&args[1]),
        load_json(&args[2]),
    ) {
        (Ok(bundle), Ok(subreceipt), Ok(evidence)) => {
            match verify_agent_step_receipt_bundle_v1_with_zkai_stwo_model_subreceipt(
                &bundle,
                &subreceipt,
                &evidence,
            ) {
                Ok(()) => CaseResult {
                    case_id: "baseline".to_string(),
                    accepted: true,
                    error: String::new(),
                },
                Err(err) => CaseResult {
                    case_id: "baseline".to_string(),
                    accepted: false,
                    error: err.to_string(),
                },
            }
        }
        (bundle, subreceipt, evidence) => {
            let mut errors = Vec::new();
            if let Err(err) = bundle {
                errors.push(err.to_string());
            }
            if let Err(err) = subreceipt {
                errors.push(err);
            }
            if let Err(err) = evidence {
                errors.push(err);
            }
            CaseResult {
                case_id: "baseline".to_string(),
                accepted: false,
                error: errors.join("; "),
            }
        }
    };

    let output = Output {
        schema: "agent-step-zkai-stwo-rust-callback-verifier-v1",
        results: vec![result],
    };
    println!(
        "{}",
        serde_json::to_string_pretty(&output).expect("serialize verifier adapter output")
    );
}
