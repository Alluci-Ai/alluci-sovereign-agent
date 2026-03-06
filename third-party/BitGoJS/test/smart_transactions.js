// /* global describe, it */

// var assert = require('assert')
// var bcrypto = require('../src/crypto')
// var bscript = require('../src/script')
// var btemplates = require('../src/templates')
// var ops = require('bitcoin-ops')

// var fixtures = {valid: [{
//   "type": "smarttransaction",
//   "pubKeys": [
//     "02359c6e3f04cefbf089cf1d6670dc47c3fb4df68e2bad1fa5a369f9ce4b42bbd1",
//     "0395a9d84d47d524548f79f435758c01faec5da2b7e551d3b8c995b7e06326ae4a"
//   ],
//   "signatures": [
//     "304402207515cf147d201f411092e6be5a64a6006f9308fad7b2a8fdaab22cd86ce764c202200974b8aca7bf51dbf54150d3884e1ae04f675637b926ec33bf75939446f6ca2801",
//     "3045022100ef253c1faa39e65115872519e5f0a33bbecf430c0f35cf562beabbad4da24d8d02201742be8ee49812a73adea3007c9641ce6725c32cd44ddb8e3a3af460015d140501"
//   ],
//   "output": "04030001012102e3154f8122ff442fbca3ff8ff4d4fb2d9285fd9f4d841d58fb8d6b7acefed60f OP_CHECKCRYPTOCONDITION 04030601012102e3154f8122ff442fbca3ff8ff4d4fb2d9285fd9f4d841d58fb8d6b7acefed60f48018167460c2f56774ed27eeb8685f29f6cec0b090b00610ed496b32d298194ce70655f7b7267739bba2cb35f9171f6b7fc55ba6d3895010000000200000000010000000100000000 OP_DROP",
//   "input": "0101010121022ea799926b7aa5601d56d5b033ab92e7e658806a1a990041af1ab897997310f040594a24df4cf6ecbbbd06f4690dfdcbebdacdc5a94b6f56a10beb876a3b812e805d60079fd2e5302e131b60aeb94c59474eb4a6378f6042f2212b3adad68dd594",
//   "inputHex": "0047304402207515cf147d201f411092e6be5a64a6006f9308fad7b2a8fdaab22cd86ce764c202200974b8aca7bf51dbf54150d3884e1ae04f675637b926ec33bf75939446f6ca2801483045022100ef253c1faa39e65115872519e5f0a33bbecf430c0f35cf562beabbad4da24d8d02201742be8ee49812a73adea3007c9641ce6725c32cd44ddb8e3a3af460015d140501",
//   "outputHex": "522102359c6e3f04cefbf089cf1d6670dc47c3fb4df68e2bad1fa5a369f9ce4b42bbd1210395a9d84d47d524548f79f435758c01faec5da2b7e551d3b8c995b7e06326ae4a52ae",
//   "inputStack": [
//     "",
//     "304402207515cf147d201f411092e6be5a64a6006f9308fad7b2a8fdaab22cd86ce764c202200974b8aca7bf51dbf54150d3884e1ae04f675637b926ec33bf75939446f6ca2801",
//     "3045022100ef253c1faa39e65115872519e5f0a33bbecf430c0f35cf562beabbad4da24d8d02201742be8ee49812a73adea3007c9641ce6725c32cd44ddb8e3a3af460015d140501"
//   ]
// }]}//require('./fixtures/templates.json')

// describe.only("smart-transactions", function () {
//   describe("classifyOutput", function () {
//     fixtures.valid.forEach(function (f) {
//       if (!f.output) return;

//       it("classifies " + f.output + " as " + f.type, function () {
//         var output = bscript.fromASM(f.output);
//         var type = btemplates.classifyOutput(output);

//         assert.strictEqual(type, f.type);
//       });
//     });
//   });

//   describe("classifyInput", function () {
//     fixtures.valid.forEach(function (f) {
//       if (!f.input) return;

//       it("classifies " + f.input + " as " + f.type, function () {
//         var input = bscript.fromASM(f.input);
//         var type = btemplates.classifyInput(input);

//         assert.strictEqual(type, f.type);
//       });
//     });
//   });
// });
