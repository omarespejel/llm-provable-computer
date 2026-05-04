use risc0_zkvm::guest::env;

fn main() {
    let journal_bytes: Vec<u8> = env::read();
    env::commit(&journal_bytes);
}
