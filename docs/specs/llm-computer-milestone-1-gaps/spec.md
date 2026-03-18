# Specification: Closing Milestone 1 Gaps — Real Transformer Execution

## Version: 0.1.0-draft | March 2026

Status: implemented in the repository. Burn execution, ONNX export, Tract/ONNX execution, Python validation, multi-engine verification, CLI integration, and CI enforcement are all present.

---

## 1. Problem Statement

transformer-vm-rs implements the correct math of a compiled transformer VM (2D attention, gated FF, hull-backed memory), but it cannot prove to external observers that the model IS a standard transformer. The weights live in custom Rust structs. No ML framework can load them. No ONNX file exists. No one outside our codebase can reproduce the execution.

This spec defines the work to close that gap.

## 2. Goals

1. **Burn model**: Implement the TransformerVm as a Burn 0.20.1 `Module` with the forward pass running through Burn's tensor operations
2. **ONNX export**: Generate standard ONNX model files from compiled program weights
3. **Cross-framework verification**: Prove equivalence by running the same programs through Burn, ONNX/Tract, and the existing native VM — all producing identical traces
4. **Python validation**: A standalone Python script that loads the ONNX models and executes programs using only `onnxruntime` — zero Rust required

## 3. Non-Goals

- WASM compiler frontend (separate future milestone)
- GPU acceleration
- Training/fine-tuning integration
- Performance optimization of the Burn/ONNX path (correctness first)
- Differentiable attention (average-hard only for now)

## 4. Architecture

### 4.1 Execution Engine Hierarchy

```
                    ┌─────────────────────┐
                    │   Program Compiler    │
                    │   (ISA → weights)     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
   ┌──────────────┐  ┌───────────────┐  ┌──────────────┐
   │  Native VM    │  │  Burn Model   │  │  ONNX Export  │
   │  (fast path)  │  │  (framework)  │  │  (portable)   │
   │  Matrix/f64   │  │  Tensor/f32   │  │  Standard ops │
   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
          │                  │                  │
          │                  ▼                  ▼
          │           Burn NdArray BE     Tract / ONNX RT
          │                  │                  │
          └──────────┬───────┴──────────┬───────┘
                     ▼                  ▼
              Differential Verifier
              (all traces must match)
                     │
                     ▼
              NativeInterpreter
              (semantic oracle)
```

### 4.2 Weight Flow

```
InstructionCompiler
    │
    ├─→ FeedForwardWeights (current: Matrix/f64)
    │       │
    │       ├─→ BurnGatedFeedForward (Burn nn::Linear, Param<Tensor<f32>>)
    │       │
    │       └─→ ONNX GraphProto (MatMul + Add + Mul nodes, float32 initializers)
    │
    └─→ TransitionControls (flag logic)
            │
            ├─→ Burn: separate boolean computation post-FF
            │
            └─→ ONNX: extended output or metadata
```

### 4.3 File Layout (New)

```
src/
  burn_model.rs          # Burn Module definitions
  burn_runtime.rs        # Burn-based execution runtime
  onnx_export.rs         # ONNX file generation
  engine.rs              # ExecutionEngine trait, engine dispatch
tests/
  burn_model.rs          # Burn model tests
  onnx_export.rs         # ONNX round-trip tests
  cross_engine.rs        # Multi-engine differential tests
scripts/
  validate_onnx.py       # Python ONNX validation
  requirements.txt       # Python deps
compiled/                # Output directory for ONNX models (gitignored)
```

## 5. Component Specifications

### 5.1 Burn Model (RFC-A)

See [RFC-A: Burn Model Integration](rfc-a-burn-model.md).

Key decisions:
- Backend: `burn-ndarray` (pure Rust, deterministic)
- Precision: `f32` (standard ML, verified equivalent to f64 for our value range)
- Attention: Backend Extension for HullKvCache OR standard tensor decomposition
- Serialization: Burn Records (MessagePack)

### 5.2 ONNX Export (RFC-B)

See [RFC-B: ONNX Export and Standard-Op Attention](rfc-b-onnx-export.md).

Key decisions:
- One ONNX file per compiled instruction (simplest, most inspectable)
- Standard ONNX ops only (MatMul, Add, Mul, ArgMax, Gather)
- Opset 19, IR version 9, float32
- Generation via `onnx-protobuf` crate in Rust

### 5.3 Differential Verification (RFC-C)

See [RFC-C: Three-Way Differential Verification](rfc-c-differential-verification.md).

Key decisions:
- `ExecutionEngine` trait unifies all engines
- Lockstep comparison (fail on first divergence)
- Exact match required (no floating-point tolerance — compiled weights produce exact integers)

### 5.4 Python Validation (RFC-D)

See [RFC-D: Python Validation Script](rfc-d-python-validation.md).

Key decisions:
- Uses `onnxruntime` only (no custom code)
- Validates against known-good outputs for all shipped programs
- CI-runnable

## 6. Dependency Changes

### New Dependencies

```toml
[dependencies]
burn = { version = "=0.20.1", features = ["ndarray"] }

[dependencies.onnx-export]  # Optional feature
onnx-protobuf = "0.3"

[dev-dependencies]
tract-onnx = "0.21"  # For ONNX validation in tests
```

### Feature Flags

```toml
[features]
default = []
burn = ["dep:burn"]
onnx = ["dep:onnx-protobuf"]
full = ["burn", "onnx"]
```

The existing fast-path VM has zero new dependencies. Burn and ONNX are opt-in features.

## 7. Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Burn model produces identical traces | `verify_engines([native_vm, burn_model, native_interp])` passes for all shipped programs |
| ONNX models load in Tract | `tract-onnx` loads and executes all exported instruction models |
| ONNX models load in ONNX Runtime | Python `validate_onnx.py` passes for all shipped programs |
| ONNX models load in PyTorch | `torch.onnx.load` + `ort.InferenceSession` produces correct results |
| 10K+ step execution matches across all engines | Long-run stress test with 3-way verification |
| Property tests pass with Burn engine | Random program generation + Burn execution matches native |

## 8. Open Questions

1. **Burn version pinning**: Pin to `=0.20.1` or allow `0.20.x`? Recommend exact pin for reproducibility.
2. **ONNX opset version**: 19 (latest stable) or lower for wider compatibility?
3. **Flag computation in ONNX**: Self-contained (9 outputs) or external (6 outputs + metadata)?
4. **CI for Python validation**: Run in GitHub Actions? Requires Python + ONNX Runtime.
5. **Burn CubeCL backend**: Use in addition to NdArray for performance comparison?

## 9. References

- [RFC-A: Burn Model Integration](rfc-a-burn-model.md)
- [RFC-B: ONNX Export](rfc-b-onnx-export.md)
- [RFC-C: Differential Verification](rfc-c-differential-verification.md)
- [RFC-D: Python Validation](rfc-d-python-validation.md)
- [Research Document](research.md)
- [Burn 0.20.1 Documentation](https://burn.dev)
- [ONNX Specification](https://onnx.ai/onnx/)
- [Tract Documentation](https://github.com/sonos/tract)
