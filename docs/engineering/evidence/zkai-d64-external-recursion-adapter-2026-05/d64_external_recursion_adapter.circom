pragma circom 2.0.0;

template D64ExternalRecursionAdapter() {
    signal input contract[21];
    signal output digest;
    var acc = 0;
    for (var i = 0; i < 21; i++) {
        contract[i] * 1 === contract[i];
        acc += contract[i];
    }
    digest <== acc;
}

component main { public [contract] } = D64ExternalRecursionAdapter();
