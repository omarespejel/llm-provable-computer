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
        let idx = address as usize;
        let history = self.histories.get(idx).ok_or(VmError::MemoryOutOfBounds {
            addr: idx,
            size: self.cells.len(),
        })?;

        if history.total_size() == 0 {
            return Ok(self.cells[idx]);
        }

        let (_, value) = history.query_argmax([1.0, 0.0])?;
        Ok(value[0].round() as i16)
    }

    pub fn store(&mut self, address: u8, value: i16, step: usize) -> Result<()> {
        let idx = address as usize;
        let history = self
            .histories
            .get_mut(idx)
            .ok_or(VmError::MemoryOutOfBounds {
                addr: idx,
                size: self.cells.len(),
            })?;

        self.cells[idx] = value;
        history.insert([step as f32, value as f32], &[value as f32]);
        Ok(())
    }

    pub fn snapshot(&self) -> Vec<i16> {
        self.cells.clone()
    }

    pub fn history_len(&self, address: u8) -> Result<usize> {
        let idx = address as usize;
        self.histories
            .get(idx)
            .map(HullKvCache::total_size)
            .ok_or(VmError::MemoryOutOfBounds {
                addr: idx,
                size: self.cells.len(),
            })
    }
}
