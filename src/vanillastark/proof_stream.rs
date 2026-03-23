/// Proof stream with Fiat-Shamir transform.
/// Ported from the stark-anatomy Python reference implementation.
use sha3::{
    digest::{ExtendableOutput, Update, XofReader},
    Shake256,
};

use super::field::FieldElement;

/// Objects that can be pushed/pulled from the proof stream.
#[derive(Clone, Debug)]
pub enum ProofObject {
    /// Raw bytes (Merkle root, etc.)
    Bytes(Vec<u8>),
    /// A codeword (list of field elements)
    Codeword(Vec<FieldElement>),
    /// A triple of field elements (FRI query leaf)
    Triple(FieldElement, FieldElement, FieldElement),
    /// A Merkle authentication path
    Path(Vec<Vec<u8>>),
    /// A single field element
    Element(FieldElement),
}

impl ProofObject {
    /// Serialize a single proof object to bytes (deterministic).
    fn serialize(&self) -> Vec<u8> {
        let mut out = Vec::new();
        match self {
            ProofObject::Bytes(data) => {
                out.push(0);
                out.extend_from_slice(&(data.len() as u32).to_le_bytes());
                out.extend_from_slice(data);
            }
            ProofObject::Codeword(elements) => {
                out.push(1);
                out.extend_from_slice(&(elements.len() as u32).to_le_bytes());
                for e in elements {
                    out.extend_from_slice(&e.value().to_le_bytes());
                }
            }
            ProofObject::Triple(a, b, c) => {
                out.push(2);
                out.extend_from_slice(&a.value().to_le_bytes());
                out.extend_from_slice(&b.value().to_le_bytes());
                out.extend_from_slice(&c.value().to_le_bytes());
            }
            ProofObject::Path(path) => {
                out.push(3);
                out.extend_from_slice(&(path.len() as u32).to_le_bytes());
                for segment in path {
                    out.extend_from_slice(&(segment.len() as u32).to_le_bytes());
                    out.extend_from_slice(segment);
                }
            }
            ProofObject::Element(e) => {
                out.push(4);
                out.extend_from_slice(&e.value().to_le_bytes());
            }
        }
        out
    }

    /// Deserialize a single proof object from bytes. Returns (object, bytes_consumed).
    fn deserialize(data: &[u8]) -> (Self, usize) {
        let tag = data[0];
        let mut offset = 1;
        match tag {
            0 => {
                let len = u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap()) as usize;
                offset += 4;
                let bytes = data[offset..offset + len].to_vec();
                offset += len;
                (ProofObject::Bytes(bytes), offset)
            }
            1 => {
                let count =
                    u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap()) as usize;
                offset += 4;
                let mut elements = Vec::with_capacity(count);
                for _ in 0..count {
                    let val = u128::from_le_bytes(data[offset..offset + 16].try_into().unwrap());
                    offset += 16;
                    elements.push(FieldElement::new(val));
                }
                (ProofObject::Codeword(elements), offset)
            }
            2 => {
                let a = u128::from_le_bytes(data[offset..offset + 16].try_into().unwrap());
                offset += 16;
                let b = u128::from_le_bytes(data[offset..offset + 16].try_into().unwrap());
                offset += 16;
                let c = u128::from_le_bytes(data[offset..offset + 16].try_into().unwrap());
                offset += 16;
                (
                    ProofObject::Triple(
                        FieldElement::new(a),
                        FieldElement::new(b),
                        FieldElement::new(c),
                    ),
                    offset,
                )
            }
            3 => {
                let count =
                    u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap()) as usize;
                offset += 4;
                let mut path = Vec::with_capacity(count);
                for _ in 0..count {
                    let len =
                        u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap()) as usize;
                    offset += 4;
                    let segment = data[offset..offset + len].to_vec();
                    offset += len;
                    path.push(segment);
                }
                (ProofObject::Path(path), offset)
            }
            4 => {
                let val = u128::from_le_bytes(data[offset..offset + 16].try_into().unwrap());
                offset += 16;
                (ProofObject::Element(FieldElement::new(val)), offset)
            }
            _ => panic!("unknown proof object tag: {}", tag),
        }
    }
}

#[derive(Clone, Debug)]
pub struct ProofStream {
    pub objects: Vec<ProofObject>,
    pub read_index: usize,
}

impl Default for ProofStream {
    fn default() -> Self {
        Self::new()
    }
}

fn shake256(data: &[u8], num_bytes: usize) -> Vec<u8> {
    let mut hasher = Shake256::default();
    hasher.update(data);
    let mut reader = hasher.finalize_xof();
    let mut output = vec![0u8; num_bytes];
    reader.read(&mut output);
    output
}

fn serialize_objects(objects: &[ProofObject]) -> Vec<u8> {
    let mut out = Vec::new();
    for obj in objects {
        out.extend_from_slice(&obj.serialize());
    }
    out
}

impl ProofStream {
    pub fn new() -> Self {
        Self {
            objects: Vec::new(),
            read_index: 0,
        }
    }

    pub fn push(&mut self, obj: ProofObject) {
        self.objects.push(obj);
    }

    pub fn pull(&mut self) -> ProofObject {
        assert!(
            self.read_index < self.objects.len(),
            "ProofStream: cannot pull object; queue empty."
        );
        let obj = self.objects[self.read_index].clone();
        self.read_index += 1;
        obj
    }

    /// Serialize the entire proof stream to bytes.
    pub fn serialize(&self) -> Vec<u8> {
        let mut out = Vec::new();
        out.extend_from_slice(&(self.objects.len() as u32).to_le_bytes());
        for obj in &self.objects {
            let serialized = obj.serialize();
            out.extend_from_slice(&(serialized.len() as u32).to_le_bytes());
            out.extend_from_slice(&serialized);
        }
        out
    }

    /// Prover Fiat-Shamir: hash ALL objects.
    pub fn prover_fiat_shamir(&self) -> Vec<u8> {
        let data = serialize_objects(&self.objects);
        shake256(&data, 32)
    }

    /// Verifier Fiat-Shamir: hash objects up to read_index.
    pub fn verifier_fiat_shamir(&self) -> Vec<u8> {
        let data = serialize_objects(&self.objects[..self.read_index]);
        shake256(&data, 32)
    }

    /// Deserialize a proof stream from bytes.
    pub fn deserialize(data: &[u8]) -> Self {
        let count = u32::from_le_bytes(data[0..4].try_into().unwrap()) as usize;
        let mut offset = 4;
        let mut objects = Vec::with_capacity(count);
        for _ in 0..count {
            let obj_len = u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap()) as usize;
            offset += 4;
            let (obj, _) = ProofObject::deserialize(&data[offset..offset + obj_len]);
            offset += obj_len;
            objects.push(obj);
        }
        Self {
            objects,
            read_index: 0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_proof_stream_push_pull() {
        let mut ps = ProofStream::new();
        ps.push(ProofObject::Bytes(vec![1, 2, 3]));
        ps.push(ProofObject::Element(FieldElement::new(42)));

        if let ProofObject::Bytes(data) = ps.pull() {
            assert_eq!(data, vec![1, 2, 3]);
        } else {
            panic!("expected Bytes");
        }
        if let ProofObject::Element(e) = ps.pull() {
            assert_eq!(e, FieldElement::new(42));
        } else {
            panic!("expected Element");
        }
    }

    #[test]
    fn test_proof_stream_serialize_deserialize() {
        let mut ps = ProofStream::new();
        ps.push(ProofObject::Bytes(vec![1, 2, 3]));
        ps.push(ProofObject::Element(FieldElement::new(42)));
        ps.push(ProofObject::Triple(
            FieldElement::new(1),
            FieldElement::new(2),
            FieldElement::new(3),
        ));

        let serialized = ps.serialize();
        let ps2 = ProofStream::deserialize(&serialized);
        assert_eq!(ps2.objects.len(), 3);
    }

    #[test]
    fn test_fiat_shamir_consistency() {
        let mut ps = ProofStream::new();
        ps.push(ProofObject::Bytes(vec![1, 2, 3]));

        let prover_hash = ps.prover_fiat_shamir();

        // Simulate verifier: pull the object, then verifier_fiat_shamir should match
        let mut ps2 = ps.clone();
        let _ = ps2.pull();
        let verifier_hash = ps2.verifier_fiat_shamir();

        assert_eq!(prover_hash, verifier_hash);
    }
}
