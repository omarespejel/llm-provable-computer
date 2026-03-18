# RFC-D: Python Validation Script

## Status: Draft

## Summary

Provide a Python script that loads the exported ONNX models, executes programs, and produces execution traces — proving the transformer works outside our Rust codebase entirely.

## Motivation

The ultimate proof: someone with Python + ONNX Runtime (and zero Rust) can run the same programs and get the same results. This eliminates any possibility that our Rust code is "faking" the transformer behavior.

## Design

### Script Structure

```
scripts/
  validate_onnx.py        # Main validation script
  requirements.txt        # onnxruntime, numpy
```

### Core Loop

```python
#!/usr/bin/env python3
"""Validate transformer-vm ONNX models against expected outputs."""

import numpy as np
import onnxruntime as ort
import json
import sys

def load_compiled_program(program_dir: str):
    """Load instruction ONNX models and program metadata."""
    with open(f"{program_dir}/metadata.json") as f:
        meta = json.load(f)

    models = {}
    for pc in range(meta["program_length"]):
        path = f"{program_dir}/instr_{pc}.onnx"
        models[pc] = ort.InferenceSession(path)

    return meta, models

def build_input_vector(state, operand):
    """Build the 41-dim input vector from machine state."""
    inp = np.zeros(41, dtype=np.float32)
    inp[0] = 1.0  # constant
    inp[1] = float(state["pc"])
    inp[2] = float(state["pc"] + 1)  # pc_next
    inp[3] = float(state["acc"])
    inp[4] = 1.0 if state["zero_flag"] else 0.0
    inp[5] = 1.0 if state["carry_flag"] else 0.0
    inp[6] = 1.0 if state["halted"] else 0.0
    inp[7] = float(state["sp"])
    inp[8] = float(operand)

    # ACC bits (indices 9-24)
    acc_bits = state["acc"] & 0xFFFF
    for bit in range(16):
        inp[9 + bit] = 1.0 if ((acc_bits >> bit) & 1) else 0.0

    # Operand bits (indices 25-40)
    op_bits = operand & 0xFFFF
    for bit in range(16):
        inp[25 + bit] = 1.0 if ((op_bits >> bit) & 1) else 0.0

    return inp.reshape(1, -1)

def execute_program(meta, models, max_steps=512):
    """Execute the program using ONNX models."""
    state = {
        "pc": 0, "acc": 0, "sp": meta["memory_size"],
        "zero_flag": True, "carry_flag": False, "halted": False,
    }
    memory = list(meta["initial_memory"])
    # Memory write history per address: list of (step, value) pairs
    histories = {addr: [(0, val)] for addr, val in enumerate(memory)}

    trace = [dict(state)]

    for step in range(1, max_steps + 1):
        if state["halted"]:
            break

        pc = state["pc"]
        instr_meta = meta["instructions"][pc]

        # Attention: resolve memory operand
        operand = 0
        if instr_meta.get("memory_read"):
            addr = instr_meta["memory_read_addr"]
            if instr_meta["memory_read_type"] == "direct":
                operand = memory[addr]
            elif instr_meta["memory_read_type"] == "stack_top":
                operand = memory[state["sp"]]

        # Run the ONNX model for this instruction
        input_vec = build_input_vector(state, operand)
        outputs = models[pc].run(None, {"input": input_vec})
        transition = outputs[0][0]

        next_pc = int(round(transition[0]))
        raw_acc = int(round(transition[1]))
        next_sp = int(round(transition[2]))
        mem_write_enable = transition[3] >= 0.5
        mem_write_addr = int(round(transition[4]))
        mem_write_value = int(round(transition[5]))

        # Apply memory write
        if mem_write_enable:
            memory[mem_write_addr] = np.int16(mem_write_value)
            histories.setdefault(mem_write_addr, []).append((step, mem_write_value))

        # Compute flags from the instruction's control logic
        acc = np.int16(raw_acc)
        # (Flag computation depends on instruction type — loaded from metadata)

        state = {
            "pc": next_pc,
            "acc": int(acc),
            "sp": next_sp,
            "zero_flag": instr_meta["zero_flag_rule"](acc, state),
            "carry_flag": instr_meta["carry_flag_rule"](raw_acc, state, operand),
            "halted": instr_meta["halted_rule"](state),
        }
        trace.append(dict(state))

    return state, trace

if __name__ == "__main__":
    program_dir = sys.argv[1] if len(sys.argv) > 1 else "compiled/fibonacci"
    meta, models = load_compiled_program(program_dir)
    final_state, trace = execute_program(meta, models)
    print(f"Steps: {len(trace) - 1}")
    print(f"Halted: {final_state['halted']}")
    print(f"ACC: {final_state['acc']}")
    print(f"PC: {final_state['pc']}")
```

### Metadata File

Each compiled program exports a `metadata.json`:

```json
{
  "program_name": "fibonacci",
  "program_length": 15,
  "memory_size": 5,
  "initial_memory": [0, 1, 0, 0, 7],
  "instructions": [
    {
      "pc": 0,
      "mnemonic": "LOAD 3",
      "memory_read": true,
      "memory_read_type": "direct",
      "memory_read_addr": 3,
      "onnx_file": "instr_0.onnx"
    },
    ...
  ]
}
```

### Test Cases

The Python script validates against known-good outputs:

```python
EXPECTED_OUTPUTS = {
    "addition": {"acc": 8, "halted": True, "steps": 3},
    "counter": {"acc": 5, "halted": True},
    "fibonacci": {"acc": 21, "halted": True},
    "multiply": {"acc": 42, "halted": True},
}
```

### CI Integration

```yaml
# .github/workflows/validate-onnx.yml
- name: Export ONNX models
  run: cargo run --bin tvm -- export-onnx programs/fibonacci.tvm -o compiled/fibonacci/

- name: Validate in Python
  run: python scripts/validate_onnx.py compiled/fibonacci/
```

## Simplification: Flag Logic in Metadata

The flag computation (zero_flag, carry_flag, halted) currently lives in our `TransitionControls` struct. For the Python validator, we export these as metadata rules rather than replicating the full logic:

**Alternative**: Include the flag logic in the ONNX model itself by extending the output to include flag values. This makes the ONNX model fully self-contained.

Extended output: `[next_pc, raw_acc, next_sp, mem_write_enable, mem_addr, mem_value, zero_flag, carry_flag, halted]`

This is cleaner and eliminates the need for instruction-specific flag logic in Python.

## Dependencies

```
# requirements.txt
onnxruntime>=1.18
numpy>=1.24
```

## Open Questions

1. **Flag encoding in ONNX**: Include flags in ONNX output (cleaner, self-contained) or compute externally (simpler ONNX graph)?
2. **Memory history**: Pass as ONNX input (dynamic) or handle externally? External is simpler for the initial version.
3. **Batch execution**: Support batched execution across multiple programs, or one-at-a-time?
