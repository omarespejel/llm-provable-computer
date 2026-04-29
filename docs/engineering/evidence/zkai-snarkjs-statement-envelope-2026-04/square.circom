pragma circom 2.0.0;

template Square() {
    signal input x;
    signal output y;
    y <== x * x;
}

component main { public [x] } = Square();
