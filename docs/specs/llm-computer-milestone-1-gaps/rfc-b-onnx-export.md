# RFC-B: ONNX Export and Standard-Op Attention

## Status: Draft

## Summary

Generate ONNX model files from our compiled transformer weights, enabling the model to be loaded and executed in any ONNX-compatible runtime (ONNX Runtime, PyTorch, Tract, etc.). This is the definitive proof that our system IS a standard transformer.

## Motivation

The single most compelling demonstration we can make:

1. Compile a program (e.g., Fibonacci) into transformer weights
2. Export those weights as a standard ONNX model file
3. Load the ONNX model in PyTorch or ONNX Runtime
4. Feed it the initial state token
5. Get the correct execution trace out

If someone can do this with stock PyTorch and zero custom code, the claim "this is a real transformer" is proven.

## Design

### ONNX Graph Structure

One execution step of our transformer maps to this ONNX graph:

```
Input: state_token [1, d_model=36]    (encoded machine state)
       memory_value [1]                (attention-retrieved memory operand)

  ┌──────────────┐
  │ Build Input   │  Concatenate state bits + operand bits + constants
  │ Vector        │  → input [1, INPUT_DIM=41]
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ Gate Linear   │  W_gate @ input + b_gate → gate [1, ff_dim]
  └──────┬───────┘
         │
  ┌──────────────┐
  │ Value Linear  │  W_value @ input + b_value → value [1, ff_dim]
  └──────┬───────┘
         │
  ┌──────────────┐
  │ Element Mul   │  gate * value → hidden [1, ff_dim]
  └──────┬───────┘
         │
  ┌──────────────┐
  │ Output Linear │  W_out @ hidden + b_out → output [1, OUTPUT_DIM=6]
  └──────┬───────┘
         ▼
Output: transition [1, 6]  (next_pc, raw_acc, next_sp, mem_write_enable, mem_addr, mem_value)
```

This uses only standard ONNX operators: `MatMul`, `Add`, `Mul`, `Concat`.

### Attention as Standard Ops

For ONNX portability, we decompose the 2D hull attention into standard ops:

```
Input: query [1, 2]          (e.g., [1, 0] for latest-write)
       all_keys [n, 2]       (history of (step, value) pairs)
       all_values [n, v_dim]  (stored values)

  ┌──────────────┐
  │ MatMul        │  scores = all_keys @ query^T → [n, 1]
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ ArgMax        │  idx = argmax(scores, dim=0) → scalar
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ Gather        │  value = all_values[idx] → [1, v_dim]
  └──────┬───────┘
         ▼
Output: memory_value [1, v_dim]
```

This is O(n) per query but uses only standard ONNX ops (`MatMul`, `ArgMax`, `Gather`). The results are identical to our HullKvCache for average-hard attention with unique maxima.

### ONNX Generation in Rust

Use the `onnx-protobuf` crate to construct ONNX model files:

```rust
use onnx_protobuf::onnx_ml_proto3::*;

fn build_onnx_model(compiled: &TransformerVm) -> ModelProto {
    let mut graph = GraphProto::default();
    graph.name = "transformer_vm".to_string();

    // Input: state token
    graph.input.push(make_tensor_input("state", &[1, 36]));
    graph.input.push(make_tensor_input("memory_operand", &[1]));

    // Add gate linear: MatMul + Add
    let gate_weights = tensor_from_matrix(&compiled.gate);
    graph.initializer.push(gate_weights);
    graph.node.push(make_matmul("gate_matmul", "input_vec", "gate_W", "gate_pre"));
    graph.node.push(make_add("gate_add", "gate_pre", "gate_b", "gate_out"));

    // Add value linear: MatMul + Add
    // ... (same pattern)

    // Element-wise multiply: gate * value
    graph.node.push(make_mul("gating", "gate_out", "value_out", "hidden"));

    // Output linear: MatMul + Add
    // ...

    // Output
    graph.output.push(make_tensor_output("transition", &[1, 6]));

    ModelProto {
        ir_version: 9,
        opset_import: vec![OperatorSetIdProto {
            domain: String::new(),
            version: 19,
        }],
        graph: Some(graph),
        ..Default::default()
    }
}
```

### Per-Instruction ONNX Models

Each compiled instruction produces its own ONNX subgraph (since different instructions have different weights). The full model has one subgraph per PC value, with a dispatch mechanism.

Two approaches for the dispatch:

**Option A: Separate ONNX file per instruction**
- Simple, each file is a standard model
- External dispatch logic selects which model to run
- Best for initial demonstration

**Option B: Single ONNX file with conditional dispatch**
- Uses ONNX `If` or `Switch` node to select subgraph by PC
- More complex but self-contained
- Requires ONNX opset ≥ 16 for `If` node

**Recommendation**: Start with Option A. Each instruction is a separate, inspectable ONNX model. The execution loop is external.

### Validation Pipeline

```
1. Compile program → TransformerVm (existing code)
2. Export each instruction's FF weights → ONNX files
3. Load ONNX files in Tract (Rust) or ONNX Runtime (Python)
4. Run the same program through the ONNX models
5. Compare execution trace against native VM
6. If traces match → proven that the ONNX model IS the same transformer
```

### Python Validation Script

For maximum credibility, provide a Python script that:

```python
import onnxruntime as ort
import numpy as np

# Load the compiled instruction models
models = {}
for pc in range(program_length):
    models[pc] = ort.InferenceSession(f"compiled/instr_{pc}.onnx")

# Execute the program
state = initial_state()
for step in range(max_steps):
    input_vec = build_input_vector(state, memory_operand)
    output = models[state.pc].run(None, {"input": input_vec})
    state = apply_transition(state, output)
    if state.halted:
        break

print(f"Result: acc={state.acc}")
```

If this Python script produces the same result as our Rust VM, the proof is complete.

## File Format

Each ONNX file follows the standard format:
- ONNX IR version 9
- Opset 19 (latest stable)
- Float32 weights (standard ML precision)
- Named inputs/outputs for clarity

## Alternatives Considered

### Custom ONNX Domain

Register `"com.transformer_vm"` with a `HullAttention2D` custom op. Rejected because:
- Requires custom runtime support in every tool
- Defeats the purpose of proving this is a "standard" transformer
- The O(n) decomposition is fine for correctness proof (optimization is separate)

### Burn ONNX Export

Burn cannot export to ONNX (issue #918). Using Burn for the model definition is orthogonal — we generate ONNX directly from compiled weights.

### NNEF via Tract

Tract serializes to NNEF/OPL, not ONNX. NNEF is less widely supported. Stick with ONNX for maximum compatibility.

## Dependencies

```toml
onnx-protobuf = "0.3"  # or latest
prost = "0.13"          # protobuf serialization (dep of onnx-protobuf)
```

## Open Questions

1. **Float precision**: Our current VM uses `f64`. ONNX models typically use `f32`. Do the compiled weights produce correct results in `f32`? Need to verify with tolerance testing.
2. **Dynamic memory history**: ONNX models have fixed input shapes. The memory history grows over time. Options: (a) pre-allocate max history size, (b) use ONNX dynamic axes, (c) handle memory externally.
3. **Multi-layer dispatch**: For multi-layer configs, how to encode the PC → layer mapping in ONNX? Option A (separate files) handles this naturally.
