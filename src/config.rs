use std::fmt;
use std::str::FromStr;

use serde::{Deserialize, Serialize};

use crate::error::{Result, VmError};
use crate::state::MIN_D_MODEL;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Attention2DMode {
    AverageHard,
    HardSoftmax { temperature: f32 },
    Softmax,
}

impl fmt::Display for Attention2DMode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::AverageHard => f.write_str("average-hard"),
            Self::HardSoftmax { temperature } => write!(f, "hard-softmax:{temperature}"),
            Self::Softmax => f.write_str("softmax"),
        }
    }
}

impl FromStr for Attention2DMode {
    type Err = String;

    fn from_str(input: &str) -> std::result::Result<Self, Self::Err> {
        let normalized = input.trim().to_ascii_lowercase();
        match normalized.as_str() {
            "average-hard" | "average_hard" | "averagehard" | "hard" => Ok(Self::AverageHard),
            "softmax" => Ok(Self::Softmax),
            "hard-softmax" | "hard_softmax" | "hardsoftmax" => {
                Ok(Self::HardSoftmax { temperature: 1.0 })
            }
            _ => {
                if let Some((prefix, raw_temperature)) = normalized.split_once(':') {
                    if matches!(prefix, "hard-softmax" | "hard_softmax" | "hardsoftmax") {
                        let temperature = raw_temperature.parse::<f32>().map_err(|_| {
                            format!("invalid hard-softmax temperature `{raw_temperature}`")
                        })?;
                        return Ok(Self::HardSoftmax { temperature });
                    }
                }

                Err(format!(
                    "unknown attention mode `{input}`; expected average-hard, softmax, or hard-softmax[:temperature]"
                ))
            }
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
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
        if self.num_layers == 0 {
            return Err(VmError::InvalidConfig(
                "num_layers must be greater than zero".to_string(),
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
                "llm-provable-computer requires head_dim=2, got {}",
                self.head_dim()
            )));
        }
        if self.ff_dim == 0 {
            return Err(VmError::InvalidConfig(
                "ff_dim must be greater than zero".to_string(),
            ));
        }
        if let Attention2DMode::HardSoftmax { temperature } = self.attention_mode {
            if !temperature.is_finite() || temperature <= 0.0 {
                return Err(VmError::InvalidConfig(format!(
                    "hard-softmax temperature must be finite and > 0, got {temperature}"
                )));
            }
        }
        Ok(())
    }
}

impl Default for TransformerVmConfig {
    fn default() -> Self {
        Self::percepta_reference()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn percepta_reference_has_head_dim_2() {
        let config = TransformerVmConfig::percepta_reference();
        assert_eq!(config.head_dim(), 2);
        assert_eq!(config.d_model, MIN_D_MODEL);
        assert_eq!(config.num_heads, MIN_D_MODEL / 2);
    }

    #[test]
    fn default_equals_percepta_reference() {
        assert_eq!(
            TransformerVmConfig::default(),
            TransformerVmConfig::percepta_reference()
        );
    }

    #[test]
    fn validate_accepts_percepta_reference() {
        TransformerVmConfig::percepta_reference()
            .validate()
            .unwrap();
    }

    #[test]
    fn validate_rejects_d_model_too_small() {
        let config = TransformerVmConfig {
            d_model: 4,
            num_heads: 2,
            ..TransformerVmConfig::default()
        };
        let err = config.validate().unwrap_err();
        assert!(err.to_string().contains("d_model must be at least"));
    }

    #[test]
    fn validate_rejects_zero_num_heads() {
        let config = TransformerVmConfig {
            num_heads: 0,
            ..TransformerVmConfig::default()
        };
        let err = config.validate().unwrap_err();
        assert!(err
            .to_string()
            .contains("num_heads must be greater than zero"));
    }

    #[test]
    fn validate_rejects_zero_num_layers() {
        let config = TransformerVmConfig {
            num_layers: 0,
            ..TransformerVmConfig::default()
        };
        let err = config.validate().unwrap_err();
        assert!(err
            .to_string()
            .contains("num_layers must be greater than zero"));
    }

    #[test]
    fn validate_rejects_non_divisible_d_model() {
        let config = TransformerVmConfig {
            d_model: 37,
            num_heads: 18,
            ..TransformerVmConfig::default()
        };
        let err = config.validate().unwrap_err();
        assert!(err.to_string().contains("must be divisible by"));
    }

    #[test]
    fn validate_rejects_head_dim_not_2() {
        let config = TransformerVmConfig {
            d_model: 36,
            num_heads: 9, // head_dim = 4
            ..TransformerVmConfig::default()
        };
        let err = config.validate().unwrap_err();
        assert!(err.to_string().contains("head_dim=2"));
    }

    #[test]
    fn validate_rejects_zero_ff_dim() {
        let config = TransformerVmConfig {
            ff_dim: 0,
            ..TransformerVmConfig::default()
        };
        let err = config.validate().unwrap_err();
        assert!(err.to_string().contains("ff_dim must be greater than zero"));
    }

    #[test]
    fn validate_rejects_zero_temperature() {
        let config = TransformerVmConfig {
            attention_mode: Attention2DMode::HardSoftmax { temperature: 0.0 },
            ..TransformerVmConfig::default()
        };
        let err = config.validate().unwrap_err();
        assert!(err.to_string().contains("temperature"));
    }

    #[test]
    fn validate_rejects_negative_temperature() {
        let config = TransformerVmConfig {
            attention_mode: Attention2DMode::HardSoftmax { temperature: -1.0 },
            ..TransformerVmConfig::default()
        };
        assert!(config.validate().is_err());
    }

    #[test]
    fn validate_rejects_nan_temperature() {
        let config = TransformerVmConfig {
            attention_mode: Attention2DMode::HardSoftmax {
                temperature: f32::NAN,
            },
            ..TransformerVmConfig::default()
        };
        assert!(config.validate().is_err());
    }

    #[test]
    fn validate_rejects_infinite_temperature() {
        let config = TransformerVmConfig {
            attention_mode: Attention2DMode::HardSoftmax {
                temperature: f32::INFINITY,
            },
            ..TransformerVmConfig::default()
        };
        assert!(config.validate().is_err());
    }

    #[test]
    fn from_str_parses_average_hard_variants() {
        for input in ["average-hard", "average_hard", "averagehard", "hard"] {
            assert_eq!(
                Attention2DMode::from_str(input).unwrap(),
                Attention2DMode::AverageHard,
                "failed for `{input}`"
            );
        }
    }

    #[test]
    fn from_str_parses_softmax() {
        assert_eq!(
            Attention2DMode::from_str("softmax").unwrap(),
            Attention2DMode::Softmax
        );
    }

    #[test]
    fn from_str_parses_hard_softmax_default_temperature() {
        for input in ["hard-softmax", "hard_softmax", "hardsoftmax"] {
            assert_eq!(
                Attention2DMode::from_str(input).unwrap(),
                Attention2DMode::HardSoftmax { temperature: 1.0 },
                "failed for `{input}`"
            );
        }
    }

    #[test]
    fn from_str_parses_hard_softmax_with_temperature() {
        assert_eq!(
            Attention2DMode::from_str("hard-softmax:0.5").unwrap(),
            Attention2DMode::HardSoftmax { temperature: 0.5 }
        );
        assert_eq!(
            Attention2DMode::from_str("hard_softmax:10").unwrap(),
            Attention2DMode::HardSoftmax { temperature: 10.0 }
        );
    }

    #[test]
    fn from_str_is_case_insensitive() {
        assert_eq!(
            Attention2DMode::from_str("AVERAGE-HARD").unwrap(),
            Attention2DMode::AverageHard
        );
        assert_eq!(
            Attention2DMode::from_str("SOFTMAX").unwrap(),
            Attention2DMode::Softmax
        );
    }

    #[test]
    fn from_str_rejects_unknown_mode() {
        let err = Attention2DMode::from_str("unknown").unwrap_err();
        assert!(err.contains("unknown attention mode"));
    }

    #[test]
    fn from_str_rejects_invalid_temperature() {
        let err = Attention2DMode::from_str("hard-softmax:abc").unwrap_err();
        assert!(err.contains("invalid hard-softmax temperature"));
    }

    #[test]
    fn display_round_trips_through_from_str() {
        let modes = [
            Attention2DMode::AverageHard,
            Attention2DMode::Softmax,
            Attention2DMode::HardSoftmax { temperature: 0.5 },
        ];
        for mode in &modes {
            let displayed = mode.to_string();
            let parsed = Attention2DMode::from_str(&displayed).unwrap();
            assert_eq!(&parsed, mode, "round-trip failed for {displayed}");
        }
    }
}
