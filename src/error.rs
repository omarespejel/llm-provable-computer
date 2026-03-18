use thiserror::Error;

pub type Result<T> = std::result::Result<T, VmError>;

#[derive(Debug, Error)]
pub enum VmError {
    #[error("i/o error: {0}")]
    Io(#[from] std::io::Error),
    #[error("invalid config: {0}")]
    InvalidConfig(String),
    #[error("parse error on line {line}: {message}")]
    Parse { line: usize, message: String },
    #[error("unknown label `{label}` referenced on line {line}")]
    UnknownLabel { line: usize, label: String },
    #[error("program counter {pc} is out of bounds for program length {len}")]
    ProgramCounterOutOfBounds { pc: usize, len: usize },
    #[error("memory address {addr} is out of bounds for memory size {size}")]
    MemoryOutOfBounds { addr: usize, size: usize },
    #[error("stack underflow: sp {sp} is invalid for memory size {size}")]
    StackUnderflow { sp: usize, size: usize },
    #[error("stack overflow: sp {sp} cannot grow downward within memory size {size}")]
    StackOverflow { sp: usize, size: usize },
    #[error("stack pointer {sp} is out of bounds for memory size {size}")]
    InvalidStackPointer { sp: usize, size: usize },
    #[error("compiled transition produced invalid {field} value {value}")]
    InvalidTransitionField { field: &'static str, value: i64 },
    #[error("execution mismatch at step {step}: {message}")]
    ExecutionMismatch { step: usize, message: String },
    #[error("serialization error: {0}")]
    Serialization(String),
    #[error("unsupported proof construction: {0}")]
    UnsupportedProof(String),
    #[error("onnx error: {0}")]
    Onnx(String),
    #[error("hull cache is empty")]
    EmptyHull,
}
