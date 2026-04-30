"""Shared constants for the bounded Stwo transformer-block gate."""

REQUIRED_TRANSFORMER_BLOCK_OPERATION_IDS = (
    "rmsnorm_scale_lookup",
    "quantized_affine_projection",
    "gated_value_mix",
    "residual_add",
    "bounded_activation_lookup",
)

