# RFC-A: Burn 0.20.1 Model Integration

## Status: Draft

## Summary

Implement the TransformerVm as a proper Burn `Module`, using Burn's tensor operations for the forward pass instead of hand-rolled matrix-vector multiplications. This proves the model is a real transformer running through a standard ML framework.

## Motivation

Our current `model.rs` implements the transformer forward pass as direct Rust code. While mathematically correct, this doesn't demonstrate that the model IS a standard transformer — it could be any program organized to look like one.

By implementing the model in Burn, we get:
1. The forward pass runs through Burn's tensor computation graph
2. Weights are stored in Burn's `Param<Tensor>` format
3. The model can be serialized via Burn's Record system
4. Anyone with Burn can load and run the model
5. We can differentially verify against our existing fast-path implementation

## Design

### Module Structure

```rust
use burn::prelude::*;
use burn::nn;

#[derive(Module, Debug)]
pub struct BurnTransformerVm<B: Backend> {
    config: TransformerVmConfig,
    blocks: Vec<BurnTransformerVmBlock<B>>,
    /// Maps PC → layer index for instruction dispatch
    layer_for_pc: Vec<usize>,
}

#[derive(Module, Debug)]
pub struct BurnTransformerVmBlock<B: Backend> {
    attention: BurnMultiHead2DAttention<B>,
    ff: BurnGatedFeedForward<B>,
}

#[derive(Module, Debug)]
pub struct BurnMultiHead2DAttention<B: Backend> {
    num_heads: usize,
    mode: Attention2DMode,
    // No learned projections — keys are geometric (step, value),
    // queries are fixed directions like [1, 0]
}

#[derive(Module, Debug)]
pub struct BurnGatedFeedForward<B: Backend> {
    gate: nn::Linear<B>,    // W_gate: ff_dim × input_dim
    value: nn::Linear<B>,   // W_value: ff_dim × input_dim
    output: nn::Linear<B>,  // W_out: output_dim × ff_dim
}
```

### Weight Transfer

The critical operation: take our existing compiled `FeedForwardWeights` (from `model.rs`) and load them into Burn's `nn::Linear` layers.

```rust
impl<B: Backend> BurnGatedFeedForward<B> {
    /// Load weights from the compiled instruction's FF matrices.
    pub fn from_compiled(
        compiled: &FeedForwardWeights,
        device: &B::Device,
    ) -> Self {
        let gate = nn::LinearConfig::new(INPUT_DIM, ff_dim)
            .with_bias(true)
            .init(device);
        // Copy gate.weight from compiled.gate.data
        // Copy gate.bias from compiled.gate_bias
        // ... (same for value and output)
        Self { gate, value, output }
    }
}
```

### Forward Pass

```rust
impl<B: Backend> BurnGatedFeedForward<B> {
    pub fn forward(&self, input: Tensor<B, 1>) -> Tensor<B, 1> {
        let gate_out = self.gate.forward(input.clone());
        let value_out = self.value.forward(input);
        let hidden = gate_out * value_out;  // element-wise gating
        self.output.forward(hidden)
    }
}
```

This is identical math to our current `FeedForwardWeights::evaluate()`, but running through Burn's tensor ops.

### Attention Handling

The 2D attention with HullKvCache is our custom operation. Two approaches:

**Option 1: Backend Extension (recommended for correctness)**

Implement a custom Burn Backend Extension trait:

```rust
pub trait HullAttentionOps<B: Backend> {
    fn hull_attention_2d(
        query: Tensor<B, 1>,    // [2]
        cache: &HullKvCache,
    ) -> Tensor<B, 1>;          // [value_dim]
}
```

This keeps the hull optimization while running within Burn's framework.

**Option 2: Standard tensor ops (recommended for portability)**

Decompose the attention into standard ops:
```rust
fn standard_attention_2d<B: Backend>(
    query: Tensor<B, 1>,    // [2]
    keys: Tensor<B, 2>,     // [n, 2]
    values: Tensor<B, 2>,   // [n, value_dim]
) -> Tensor<B, 1> {
    let scores = keys.matmul(query.unsqueeze());  // [n, 1]
    let max_idx = scores.argmax(0);
    values.select(0, max_idx)
}
```

This is O(n) but uses only standard tensor ops. For the correctness demonstration, this suffices.

### Memory as Tensors

Currently, `AddressedMemory` stores per-address `HullKvCache` instances. For the Burn model, we represent memory history as tensors:

```rust
#[derive(Debug, Clone)]
pub struct BurnMemory<B: Backend> {
    /// Per-address key history: [num_addresses, max_writes, 2]
    keys: Vec<Tensor<B, 2>>,
    /// Per-address value history: [num_addresses, max_writes, 1]
    values: Vec<Tensor<B, 2>>,
    /// Number of writes per address
    write_counts: Vec<usize>,
}
```

### Serialization

Burn's Record system serializes the model to MessagePack (default), bincode, or JSON:

```rust
use burn::record::{NamedMpkFileRecorder, FullPrecisionSettings};

let recorder = NamedMpkFileRecorder::<FullPrecisionSettings>::new();
model.save_file("model.mpk", &recorder).expect("save");
```

This produces a Burn-specific format. For ONNX interop, see RFC-B.

## Backend Selection

Use `burn-ndarray` for deterministic, pure-Rust CPU inference:

```toml
[dependencies]
burn = { version = "=0.20.1", features = ["ndarray"] }
```

This is the simplest backend with no external dependencies, perfect for our use case (small model, CPU-only, determinism required).

## Integration with Existing Code

The Burn model runs alongside the existing fast-path implementation:

```rust
pub enum ExecutionEngine {
    /// Current hand-rolled implementation (fast, ~500K tok/sec)
    Native,
    /// Burn framework implementation (proves it's a real transformer)
    Burn,
}
```

Both engines must produce identical execution traces. The differential verifier (`verification.rs`) is extended to support three-way comparison: Native VM, Burn model, and NativeInterpreter.

## Open Questions

1. **Burn's `nn::Linear` bias handling**: Does `nn::Linear` apply bias as `Wx + b` matching our `W @ input + bias`? (Yes — standard convention.)
2. **Tensor dtype**: Use `f64` to match our current `Scalar = f64`, or `f32`? Recommendation: `f32` for the Burn model (standard ML practice), verify equivalence within tolerance.
3. **Dynamic memory**: Burn tensors are fixed-size. Memory histories grow dynamically. Use `Vec<Tensor>` with dynamic concatenation, or pre-allocate max size?

## Dependencies

```toml
burn = { version = "=0.20.1", features = ["ndarray"] }
```

No other new dependencies needed.
