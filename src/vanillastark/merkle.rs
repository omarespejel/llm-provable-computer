/// Merkle tree using blake2b.
/// Ported from the stark-anatomy Python reference implementation.
use blake2::{Blake2b512, Digest};

pub struct Merkle;

fn hash(data: &[u8]) -> Vec<u8> {
    let mut hasher = Blake2b512::new();
    hasher.update(data);
    hasher.finalize().to_vec()
}

impl Merkle {
    /// Commit to pre-hashed leaves (each leaf is already a hash digest).
    pub fn commit_(leafs: &[Vec<u8>]) -> Vec<u8> {
        assert!(leafs.len().is_power_of_two(), "length must be power of two");
        if leafs.len() == 1 {
            return leafs[0].clone();
        }
        let half = leafs.len() / 2;
        let left = Self::commit_(&leafs[..half]);
        let right = Self::commit_(&leafs[half..]);
        let mut combined = left;
        combined.extend_from_slice(&right);
        hash(&combined)
    }

    /// Commit to raw data (hash each element first, then build tree).
    pub fn commit(data_array: &[Vec<u8>]) -> Vec<u8> {
        let hashed: Vec<Vec<u8>> = data_array.iter().map(|da| hash(da)).collect();
        Self::commit_(&hashed)
    }

    /// Open a leaf in the pre-hashed tree (return authentication path).
    pub fn open_(index: usize, leafs: &[Vec<u8>]) -> Vec<Vec<u8>> {
        assert!(leafs.len().is_power_of_two(), "length must be power of two");
        assert!(index < leafs.len(), "cannot open invalid index");
        if leafs.len() == 2 {
            return vec![leafs[1 - index].clone()];
        }
        let half = leafs.len() / 2;
        if index < half {
            let mut path = Self::open_(index, &leafs[..half]);
            path.push(Self::commit_(&leafs[half..]));
            path
        } else {
            let mut path = Self::open_(index - half, &leafs[half..]);
            path.push(Self::commit_(&leafs[..half]));
            path
        }
    }

    /// Open a data element (hash each element first, then open in tree).
    pub fn open(index: usize, data_array: &[Vec<u8>]) -> Vec<Vec<u8>> {
        let hashed: Vec<Vec<u8>> = data_array.iter().map(|da| hash(da)).collect();
        Self::open_(index, &hashed)
    }

    /// Verify a pre-hashed leaf against a root and authentication path.
    pub fn verify_(root: &[u8], index: usize, path: &[Vec<u8>], leaf: &[u8]) -> bool {
        assert!(index < (1 << path.len()), "cannot verify invalid index");
        if path.len() == 1 {
            if index == 0 {
                let mut combined = leaf.to_vec();
                combined.extend_from_slice(&path[0]);
                return root == hash(&combined).as_slice();
            } else {
                let mut combined = path[0].clone();
                combined.extend_from_slice(leaf);
                return root == hash(&combined).as_slice();
            }
        }
        if index.is_multiple_of(2) {
            let mut combined = leaf.to_vec();
            combined.extend_from_slice(&path[0]);
            Self::verify_(root, index >> 1, &path[1..], &hash(&combined))
        } else {
            let mut combined = path[0].clone();
            combined.extend_from_slice(leaf);
            Self::verify_(root, index >> 1, &path[1..], &hash(&combined))
        }
    }

    /// Verify a data element against a root and authentication path.
    pub fn verify(root: &[u8], index: usize, path: &[Vec<u8>], data_element: &[u8]) -> bool {
        Self::verify_(root, index, path, &hash(data_element))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_merkle_commit_open_verify() {
        let n = 16;
        let leafs: Vec<Vec<u8>> = (0..n).map(|i| vec![i as u8; 32]).collect();
        let root = Merkle::commit_(&leafs);

        for i in 0..n {
            let path = Merkle::open_(i, &leafs);
            assert!(Merkle::verify_(&root, i, &path, &leafs[i]));
        }
    }

    #[test]
    fn test_merkle_wrong_leaf_fails() {
        let n = 16;
        let leafs: Vec<Vec<u8>> = (0..n).map(|i| vec![i as u8; 32]).collect();
        let root = Merkle::commit_(&leafs);

        let path = Merkle::open_(0, &leafs);
        assert!(!Merkle::verify_(&root, 0, &path, &[255u8; 32]));
    }

    #[test]
    fn test_merkle_wrong_index_fails() {
        let n = 16;
        let leafs: Vec<Vec<u8>> = (0..n).map(|i| vec![i as u8; 32]).collect();
        let root = Merkle::commit_(&leafs);

        let path = Merkle::open_(0, &leafs);
        assert!(!Merkle::verify_(&root, 1, &path, &leafs[0]));
    }
}
