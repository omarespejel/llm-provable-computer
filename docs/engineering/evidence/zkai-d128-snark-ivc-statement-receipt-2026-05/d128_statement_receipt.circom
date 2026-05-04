pragma circom 2.0.0;

template D128StatementReceipt() {
    signal input contract[16];
    signal output digest;
    var acc = 0;
    for (var i = 0; i < 16; i++) {
        contract[i] * 1 === contract[i];
        acc += contract[i];
    }
    digest <== acc;
}

component main { public [contract] } = D128StatementReceipt();
