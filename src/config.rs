use crate::error::{Result, VmError};
use crate::state::MIN_D_MODEL;

#[derive(Debug, Clone, PartialEq)]
pub enum Attention2DMode {
    AverageHard,
    HardSoftmax { temperature: f32 },
    Softmax,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TransformerVmConfig {
    pub d_model: usize,
    pub num_heads: usize,
    pub num_layers: usize,
    pub vocab_size: usize,
    pub max_seq_len: usize,
    pub ff_dim: usize,
    pub attention_mode: Attention2DMode,
}

impl TransformerVmConfig {
    pub fn percepta_reference() -> Self {
        Self {
            d_model: MIN_D_MODEL,
            num_heads: MIN_D_MODEL / 2,
            num_layers: 1,
            vocab_size: 256,
            max_seq_len: 1_000_000,
            ff_dim: 72,
            attention_mode: Attention2DMode::AverageHard,
        }
    }

    pub fn head_dim(&self) -> usize {
        self.d_model / self.num_heads
    }

    pub fn validate(&self) -> Result<()> {
        if self.d_model < MIN_D_MODEL {
            return Err(VmError::InvalidConfig(format!(
                "d_model must be at least {MIN_D_MODEL}, got {}",
                self.d_model
            )));
        }
        if self.num_heads == 0 {
            return Err(VmError::InvalidConfig(
                "num_heads must be greater than zero".to_string(),
            ));
        }
        if !self.d_model.is_multiple_of(self.num_heads) {
            return Err(VmError::InvalidConfig(format!(
                "d_model {} must be divisible by num_heads {}",
                self.d_model, self.num_heads
            )));
        }
        if self.head_dim() != 2 {
            return Err(VmError::InvalidConfig(format!(
                "transformer-vm requires head_dim=2, got {}",
                self.head_dim()
            )));
        }
        if self.ff_dim == 0 {
            return Err(VmError::InvalidConfig(
                "ff_dim must be greater than zero".to_string(),
            ));
        }
        Ok(())
    }
}

impl Default for TransformerVmConfig {
    fn default() -> Self {
        Self::percepta_reference()
    }
}
