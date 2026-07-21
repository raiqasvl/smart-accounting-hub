// Q5/D23-locked: every money field is a decimal STRING over the wire. Never store it as a JS
// `number` for arithmetic — `Number("90.27000000")` drops trailing-zero precision.
//
// M1 has no money-shaped fields yet, so this is just the wire type. `big.js` + the toBig/add/mul
// helpers land here when the first money endpoint ships (M2: accounts.opening_balance).
export type Money = string;
