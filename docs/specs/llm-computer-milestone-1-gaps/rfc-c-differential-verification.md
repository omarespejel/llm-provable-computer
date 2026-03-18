# RFC-C: Three-Way Differential Verification

## Status: Draft

## Summary

Extend the existing differential verifier to support three-way comparison: (1) Native VM (fast path), (2) Burn model (framework path), and (3) ONNX model (portable path). All three must produce identical execution traces for every program.

## Motivation

Currently we verify that `TransformerVm` matches `NativeInterpreter` — two Rust implementations that could share the same bugs. Adding Burn and ONNX paths creates independent implementations that cross-validate:

- **NativeInterpreter**: Direct ISA semantics (reference oracle)
- **TransformerVm**: Compiled FF weights, hull attention (fast path)
- **BurnTransformerVm**: Same weights through Burn's tensor ops (framework proof)
- **ONNX model via Tract**: Same weights through standard ONNX ops (portability proof)

If all four agree, the claim is airtight.

## Design

### Verification Trait

```rust
pub trait ExecutionEngine {
    fn step(&mut self) -> Result<&MachineState>;
    fn run(&mut self) -> Result<ExecutionResult>;
    fn state(&self) -> &MachineState;
    fn step_count(&self) -> usize;
    fn is_halted(&self) -> bool;
}
```

All four engines implement this trait. The verifier is engine-agnostic:

```rust
pub fn verify_engines(
    engines: &mut [&mut dyn ExecutionEngine],
    max_steps: usize,
) -> Result<VerificationResult> {
    // Step all engines in lockstep
    // Compare state after each step
    // Report first divergence
}
```

### Comparison Semantics

For f32 vs f64 differences (Burn/ONNX use f32, native VM uses f64):

```rust
fn states_equivalent(a: &MachineState, b: &MachineState) -> bool {
    // PC, SP, flags, halted: exact match (these are discrete)
    // ACC: exact match (compiled weights produce exact integer results
    //       even in f32, because the values are designed to round cleanly)
    // Memory: exact match (same reasoning)
    a == b
}
```

The compiled weights are designed such that:
- All intermediate values are exact integers or simple fractions
- The `round()` at the output produces exact integer results
- f32 has enough precision for our value range (i16 = ±32767)

If any f32 rounding issues arise, they indicate a bug in the weight compilation, not an acceptable tolerance.

### Test Matrix

| Engine A | Engine B | What it proves |
|----------|----------|----------------|
| NativeInterpreter | TransformerVm | Compiled weights match ISA semantics |
| TransformerVm | BurnTransformerVm | Burn framework produces same results |
| BurnTransformerVm | ONNX/Tract | Standard ONNX ops produce same results |
| NativeInterpreter | ONNX/Tract | Full chain: ISA semantics = ONNX model |

### Property Test Extension

Extend the existing proptest to verify all engines:

```rust
proptest! {
    #[test]
    fn all_engines_match_on_random_programs(
        specs in random_program_specs(),
    ) {
        let program = build_random_program(&specs);
        let vm = compile_to_vm(program.clone());
        let burn = compile_to_burn(program.clone());
        let onnx = compile_to_onnx(program.clone());
        let native = NativeInterpreter::new(program, ...);

        verify_engines(&mut [&mut vm, &mut burn, &mut onnx, &mut native], 64)?;
    }
}
```

### CLI Extension

```bash
# Verify all engines agree
tvm run programs/fibonacci.tvm --verify-all

# Verify specific engine pair
tvm run programs/fibonacci.tvm --verify-burn
tvm run programs/fibonacci.tvm --verify-onnx
```

## Incremental Rollout

1. **Phase 1**: Burn model + differential verification (RFC-A)
2. **Phase 2**: ONNX export + Tract verification (RFC-B)
3. **Phase 3**: Full four-way verification + property tests

Each phase adds one engine and extends the verifier.

## Dependencies

No additional dependencies beyond RFC-A and RFC-B.
