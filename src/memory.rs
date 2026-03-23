use crate::config::Attention2DMode;
use crate::error::{Result, VmError};
use crate::geometry::HullKvCache;

#[derive(Debug, Clone)]
pub struct AddressedMemory {
    cells: Vec<i16>,
    histories: Vec<HullKvCache>,
}

impl AddressedMemory {
    pub fn from_initial(initial: &[i16]) -> Self {
        let mut histories = vec![HullKvCache::new(); initial.len()];
        for (addr, value) in initial.iter().enumerate() {
            histories[addr].insert([0.0, *value as f32], &[*value as f32]);
        }
        Self {
            cells: initial.to_vec(),
            histories,
        }
    }

    pub fn len(&self) -> usize {
        self.cells.len()
    }

    pub fn is_empty(&self) -> bool {
        self.cells.is_empty()
    }

    pub fn load(&self, address: u8) -> Result<i16> {
        self.load_with_mode(address, &Attention2DMode::AverageHard)
    }

    pub fn load_with_mode(&self, address: u8, mode: &Attention2DMode) -> Result<i16> {
        let idx = self.checked_index(address)?;
        let history = &self.histories[idx];

        if history.total_size() == 0 {
            return Ok(self.cells[idx]);
        }

        let value = history.query_value([1.0, 0.0], mode)?;
        Ok(value
            .first()
            .copied()
            .unwrap_or(self.cells[idx] as f32)
            .round() as i16)
    }

    pub fn store(&mut self, address: u8, value: i16, step: usize) -> Result<()> {
        let idx = self.checked_index(address)?;
        let history = &mut self.histories[idx];

        self.cells[idx] = value;
        history.insert([step as f32, value as f32], &[value as f32]);
        Ok(())
    }

    pub fn snapshot(&self) -> Vec<i16> {
        self.cells.clone()
    }

    pub fn history_len(&self, address: u8) -> Result<usize> {
        let idx = self.checked_index(address)?;
        Ok(self.histories[idx].total_size())
    }

    fn checked_index(&self, address: u8) -> Result<usize> {
        let idx = usize::from(address);
        if idx < self.cells.len() {
            Ok(idx)
        } else {
            Err(VmError::MemoryOutOfBounds {
                addr: idx,
                size: self.cells.len(),
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn from_initial_preserves_values() {
        let mem = AddressedMemory::from_initial(&[10, 20, 30]);
        assert_eq!(mem.len(), 3);
        assert!(!mem.is_empty());
        assert_eq!(mem.snapshot(), vec![10, 20, 30]);
    }

    #[test]
    fn empty_memory() {
        let mem = AddressedMemory::from_initial(&[]);
        assert!(mem.is_empty());
        assert_eq!(mem.len(), 0);
    }

    #[test]
    fn load_returns_initial_value() {
        let mem = AddressedMemory::from_initial(&[42, 99]);
        assert_eq!(mem.load(0).unwrap(), 42);
        assert_eq!(mem.load(1).unwrap(), 99);
    }

    #[test]
    fn load_out_of_bounds_returns_error() {
        let mem = AddressedMemory::from_initial(&[1, 2]);
        let err = mem.load(2).unwrap_err();
        assert!(err.to_string().contains("out of bounds"));
    }

    #[test]
    fn store_updates_cell_and_snapshot() {
        let mut mem = AddressedMemory::from_initial(&[0, 0]);
        mem.store(0, 42, 1).unwrap();
        assert_eq!(mem.load(0).unwrap(), 42);
        assert_eq!(mem.snapshot(), vec![42, 0]);
    }

    #[test]
    fn store_out_of_bounds_returns_error() {
        let mut mem = AddressedMemory::from_initial(&[0]);
        let err = mem.store(1, 42, 1).unwrap_err();
        assert!(err.to_string().contains("out of bounds"));
    }

    #[test]
    fn multiple_stores_returns_latest() {
        let mut mem = AddressedMemory::from_initial(&[0]);
        mem.store(0, 10, 1).unwrap();
        mem.store(0, 20, 2).unwrap();
        mem.store(0, 30, 3).unwrap();
        assert_eq!(mem.load(0).unwrap(), 30);
    }

    #[test]
    fn history_len_tracks_insertions() {
        let mut mem = AddressedMemory::from_initial(&[0]);
        assert_eq!(mem.history_len(0).unwrap(), 1); // initial value
        mem.store(0, 10, 1).unwrap();
        assert_eq!(mem.history_len(0).unwrap(), 2);
        mem.store(0, 20, 2).unwrap();
        assert_eq!(mem.history_len(0).unwrap(), 3);
    }

    #[test]
    fn history_len_out_of_bounds() {
        let mem = AddressedMemory::from_initial(&[0]);
        assert!(mem.history_len(1).is_err());
    }

    #[test]
    fn load_with_softmax_mode_blends_values() {
        let mut mem = AddressedMemory::from_initial(&[0]);
        mem.store(0, 10, 2).unwrap();
        // Softmax blends across all history entries
        let value = mem.load_with_mode(0, &Attention2DMode::Softmax).unwrap();
        // Should be between 0 and 10 (blended)
        assert!((0..=10).contains(&value), "softmax value={value}");
    }
}
