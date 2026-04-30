"""Shared constants for the bounded Stwo transformer-block gate."""

TRANSFORMER_BLOCK_PROFILE_VERSION = "rmsnorm-gated-affine-residual-block-v1"
TRANSFORMER_BLOCK_MODEL_ID = "urn:zkai:ptvm:rmsnorm-gated-affine-residual-block-v1"

REQUIRED_TRANSFORMER_BLOCK_OPERATION_IDS = (
    "rmsnorm_scale_lookup",
    "quantized_affine_projection",
    "gated_value_mix",
    "residual_add",
    "bounded_activation_lookup",
)
