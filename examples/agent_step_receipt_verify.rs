use std::env;
use std::path::Path;

use llm_provable_computer::load_agent_step_receipt_bundle_v1;
use serde::Serialize;

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

fn split_case_arg(index: usize, arg: String) -> (String, String) {
    if let Some((case_id, path)) = arg.split_once('=') {
        (case_id.to_string(), path.to_string())
    } else {
        (format!("case_{index}"), arg)
    }
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage: agent_step_receipt_verify <case_id=path> [...]");
        std::process::exit(2);
    }

    let mut results = Vec::with_capacity(args.len());
    for (index, arg) in args.into_iter().enumerate() {
        let (case_id, path) = split_case_arg(index, arg);
        match load_agent_step_receipt_bundle_v1(Path::new(&path)) {
            Ok(_) => results.push(CaseResult {
                case_id,
                accepted: true,
                error: String::new(),
            }),
            Err(err) => results.push(CaseResult {
                case_id,
                accepted: false,
                error: err.to_string(),
            }),
        }
    }

    let output = Output {
        schema: "agent-step-receipt-rust-verifier-adapter-v1",
        results,
    };
    println!(
        "{}",
        serde_json::to_string_pretty(&output).expect("serialize verifier adapter output")
    );
}
