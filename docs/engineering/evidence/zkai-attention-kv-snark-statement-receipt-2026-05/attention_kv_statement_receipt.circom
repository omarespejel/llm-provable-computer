pragma circom 2.0.0;

template AttentionKvStatementReceipt() {
    signal input contract[17];
    signal output digest;
    var acc = 0;
    for (var i = 0; i < 17; i++) {
        contract[i] * 1 === contract[i];
        acc += contract[i];
    }
    digest <== acc;
}

component main { public [contract] } = AttentionKvStatementReceipt();
