# Public Comparison Notes

This bundle keeps the public-paper comparison honest.

- `zkLLM` matters here because it explicitly specializes non-arithmetic tensor operations and attention rather than pretending transformer proving is only dense arithmetic.
- `Jolt Atlas` matters because it supports direct ONNX/tensor relations instead of generic CPU or VM emulation.
- `NANOZK` matters because it makes layerwise transformer proving a serious public route rather than a fallback.

These are comparison-shape notes, not matched wall-clock benchmark rows.
