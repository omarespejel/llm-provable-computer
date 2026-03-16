# RFC-004: Execution Runtime

## Summary

Implement the autoregressive execution loop that runs compiled programs step-by-step through the transformer's forward pass. Each step: encode current state → forward pass → decode next state → repeat.

## Interface

```rust
pub struct ExecutionRuntime<B: Backend> {
    model: TransformerVm<B>,
    state: MachineState,
    trace: Vec<MachineState>,
    step_count: usize,
    max_steps: usize,
}

impl<B: Backend> ExecutionRuntime<B> {
    pub fn new(model: TransformerVm<B>, initial_state: MachineState, max_steps: usize) -> Self;

    /// Execute one step. Returns the new state.
    pub fn step(&mut self) -> &MachineState;

    /// Execute until HALT or max_steps.
    pub fn run(&mut self) -> ExecutionResult;

    /// Get the full execution trace.
    pub fn trace(&self) -> &[MachineState];

    /// Get throughput (steps/sec).
    pub fn throughput(&self) -> f64;
}

pub struct ExecutionResult {
    pub final_state: MachineState,
    pub steps: usize,
    pub halted: bool,
    pub elapsed: Duration,
    pub tokens_per_sec: f64,
}
```

## Execution Loop

```rust
pub fn run(&mut self) -> ExecutionResult {
    let start = Instant::now();
    while self.step_count < self.max_steps && !self.state.halted {
        let token = encode_state(&self.state, self.model.config.d_model);
        let input = Tensor::from_data(&token);
        let output = self.model.forward_step(input);
        self.state = decode_state(&output.to_data());
        self.trace.push(self.state.clone());
        self.step_count += 1;
    }
    let elapsed = start.elapsed();
    ExecutionResult {
        final_state: self.state.clone(),
        steps: self.step_count,
        halted: self.state.halted,
        elapsed,
        tokens_per_sec: self.step_count as f64 / elapsed.as_secs_f64(),
    }
}
```

## Testing

1. Counter program: ACC increments from 0 to N, then halts
2. Addition program: computes A + B correctly for random inputs
3. Memory test: STORE then LOAD returns correct value
4. Conditional: JZ skips/takes branch correctly
5. Performance: measure tokens/sec on CPU, compare against Percepta's 33K/sec claim

---

# RFC-005: Hybrid Architecture Scaffold

## Summary

Design the architecture for mixing compiled (deterministic) layers with trained (probabilistic) layers in a single transformer. This is the long-term vision: a model that can switch between "compute mode" (compiled, 100% accurate arithmetic/logic) and "generate mode" (trained, probabilistic language).

## Architecture Concept

```
Layer 0-2: Trained (standard attention + learned FF) — language understanding
Layer 3-4: Compiled (2D attention + compiled FF) — deterministic computation
Layer 5-6: Trained (standard attention + learned FF) — output generation
```

## Interface

```rust
pub enum LayerType {
    /// Trained via gradient descent. Standard attention.
    Trained { config: TrainedLayerConfig },
    /// Compiled from program. 2D attention + HullKVCache.
    Compiled { weights: CompiledBlock },
    /// Frozen: was trained, now frozen. Standard attention, no gradients.
    Frozen { config: TrainedLayerConfig },
}

pub struct HybridTransformerConfig {
    pub layers: Vec<LayerType>,
    pub d_model: usize,
    pub vocab_size: usize,
}
```

## Key Challenge: Interface Between Layer Types

Compiled layers expect binary-encoded state vectors. Trained layers expect learned embedding representations. The interface layers must translate between these representations:

```rust
/// Adapter layer between trained and compiled representations.
pub struct RepresentationAdapter<B: Backend> {
    /// Projection from trained embedding space → binary state space
    to_binary: Linear<B>,
    /// Projection from binary state space → trained embedding space
    from_binary: Linear<B>,
}
```

## Testing

- Hybrid model forward pass completes without error
- Compiled layers produce deterministic outputs regardless of surrounding trained layers
- Adapter layers preserve information in round-trip (to_binary → from_binary ≈ identity)

## Status

This RFC is Phase 2. Phase 1 focuses on pure compiled execution (RFCs 001-004).
