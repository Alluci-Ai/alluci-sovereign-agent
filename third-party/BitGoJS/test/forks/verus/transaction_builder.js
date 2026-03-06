/* global describe, it */

var assert = require('assert')

const {
  Transaction,
  TransactionBuilder,
  OptCCParams,
  TxDestination,
  networks,
  ECPair,
  script,
  crypto
} = require('../../../src')
var ops = require('bitcoin-ops')
const { fromBase58Check } = require('../../../src/address')

describe('TransactionBuilder (verustest)', function () {
  var network = networks['verustest']
  it('Build and sign p2pkh', function () {
    var value = 50 * 1e8
    var txid = '40c8a218923f23df3692530fa8e475251c50c7d630dccbdfbd92ba8092f4aa13'
    var vout = 0

    var wif = 'Uqrcm4XqZWZCh7Y4WHKi6zSN3FG5LxBtPmfRJizYsnoKn6KsWMjx'
    var keyPair = ECPair.fromWIF(wif, network)

    var pk = crypto.hash160(keyPair.getPublicKeyBuffer())
    var spk = script.pubKeyHash.output.encode(pk)

    var txb = new TransactionBuilder(network)

    txb.addInput(txid, vout, Transaction.DEFAULT_SEQUENCE, spk)
    txb.addOutput('RRw1H4iQnhM7SGSunxQznoRZTNNa13xniG', value)
    txb.setVersion(4)

    var hashType = Transaction.SIGHASH_ALL | Transaction.SIGHASH_BITCOINCASHBIP143

    txb.sign(0, keyPair, null, hashType, value)

    var tx = txb.build()
    var hex = tx.toHex()
    assert.equal(
      '04000080000000000113aaf49280ba92bddfcbdc30d6c7501c2575e4a80f539236df233f9218a2c840000000006b483045022100c78749f2d5e112026' +
      '66e0b36a5a7b06b043982ed1cceb0781aead43e00d7827002204889e13e876261a927d5b9c78f7cee9a0d102975dc8fa620ac06bc50f95eeff7412103' +
      '75e81cfc7591aa04c6a6156738ab4d42af4dd9ae8156adbcf406d881ae060fb3ffffffff0100f2052a010000001976a914b6a8cd8f23c1159e1948555' +
      'c9033621dced917f588ac00000000000000000000000000000000000000', hex)
  })

  it('Parse and re-build from txHex', function () {
    var value = 50 * 1e8

    var txHex = '04000080000000000113aaf49280ba92bddfcbdc30d6c7501c2575e4a80f539236df233f9218a2c840000000006b483045022100c78749f2d5e112026' +
    '66e0b36a5a7b06b043982ed1cceb0781aead43e00d7827002204889e13e876261a927d5b9c78f7cee9a0d102975dc8fa620ac06bc50f95eeff7412103' +
    '75e81cfc7591aa04c6a6156738ab4d42af4dd9ae8156adbcf406d881ae060fb3ffffffff0100f2052a010000001976a914b6a8cd8f23c1159e1948555' +
    'c9033621dced917f588ac00000000000000000000000000000000000000'

    var tx = Transaction.fromHex(txHex, network)
    tx.ins[0].value = value

    var txb = TransactionBuilder.fromTransaction(tx, network)

    assert.equal(
      txb.inputs[0].signatures[0].toString('hex'),
      '3045022100c78749f2d5e11202666e0b36a5a7b06b043982ed1cceb0781aead43e00d7827002204889e13e876261a' +
      '927d5b9c78f7cee9a0d102975dc8fa620ac06bc50f95eeff741'
    )
    assert.equal(undefined, txb.inputs[0].signatures[1])

    var hex = txb.build().toHex()
    assert.equal(txHex, hex)
  })

  it('Parse and re-build VerusID spend from txHex', function () {
    var txHex = '0400008085202f8901b7c260c77c9570d2867b92a2e18d1821744e462e419e651b3ab56d8babd8a29c00000000694c670101010121030e723d1692129e2adc075250ba18b88c8efdfd841f3b4d47bc1d0c7f5ce4f5fc408a5163ac9ab7829db1e577c532d72effce7e5c14c4e9cdaa6151bc43bad20086453d8da3e61ebb49d56a16811f87275ffba1c4b04c9ec7ff6ef786f17918f6f0ffffffff0200f902950000000024050403000000cc1b04030001011504e763c569b60cfc702488e1ff5d8764acd9a56e4475f0d102950000000024050403000000cc1b0403000101150439a34181d4d91a55d7bd8100580e5eca59265ca475000000006b9a00000000000000000000000000'

    var tx = Transaction.fromHex(txHex, network)

    var txb = TransactionBuilder.fromTransaction(tx, network)

    assert.equal(
      txb.inputs[0].signatures[0].toString('hex'),
      '0101010121030e723d1692129e2adc075250ba18b88c8efdfd841f3b4d47bc1d0c7f5ce4f5fc408a5163ac9ab7829db1e577c532d72effce7e5c14c4e9cdaa6151bc43bad20086453d8da3e61ebb49d56a16811f87275ffba1c4b04c9ec7ff6ef786f17918f6f0'
    )
    assert.equal(undefined, txb.inputs[0].signatures[1])

    var hex = txb.build().toHex()

    assert.equal(hex, txHex)
  })

  it('Build and sign VerusID spend to VerusID', function () {
    var value = 10 * 1e8
    var outputValue = 9.999 * 1e8
    var txid = 'aad50ddc043983582345d6e39ca1eb58351be7dc53e81af5e5932ea078da9312'
    var vout = 0
    var dest = 'i8jHXEEYEQ7KEoYe6eKXBib8cUBZ6vjWSd'
    var prevOutDest = 'iQa13cLx5a4bB9nnd8EZPigrqLTsn75VrF'

    var wif = 'UphVXWCjV3F435Ecg4tyH6TqWSTH3E45bHrHVsSsFxfANvHEkZKW'
    var keyPair = ECPair.fromWIF(wif, network)

    const prevOutMaster = new OptCCParams(3, 0, 0, 0)
    const prevOutParams = new OptCCParams(3, 0, 1, 1, [
      new TxDestination(4, fromBase58Check(prevOutDest).hash)
    ])

    const prevOutputScript = script.compile([
      prevOutMaster.toChunk(),
      ops.OP_CHECKCRYPTOCONDITION,
      prevOutParams.toChunk(),
      ops.OP_DROP
    ])

    var txb = new TransactionBuilder(network)

    txb.setVersion(4)
    txb.setExpiryHeight(52000)
    txb.setVersionGroupId(0x892f2085)

    txb.addInput(txid, vout, Transaction.DEFAULT_SEQUENCE, prevOutputScript)

    const outMaster = new OptCCParams(3, 0, 0, 0)
    const outParams = new OptCCParams(3, 0, 1, 1, [new TxDestination(4, fromBase58Check(dest).hash)])

    const outputScript = script.compile([
      outMaster.toChunk(),
      ops.OP_CHECKCRYPTOCONDITION,
      outParams.toChunk(),
      ops.OP_DROP
    ])

    txb.addOutput(outputScript, outputValue)

    var hashType = Transaction.SIGHASH_ALL

    txb.sign(0, keyPair, null, hashType, value)

    var tx = txb.build()

    var hex = tx.toHex()

    assert.equal(
      hex,
      '0400008085202f89011293da78a02e93e5f51ae853dce71b3558eba19ce3d6452358833904dc0dd5aa00000000694c670101010121037284666add9d34b52bbbcf151979f84b5f4dbc93e7f525c3c0a6629b88b79f3140e5b2365f4d1557d3600263650582537ae97dbdcbe70998ba45cf8897cb7dd4564f1e49285af2197ec8c67dc192eaf793d0e40b7f85a20b708d89757c90cb5f0bffffffff016043993b0000000024050403000000cc1b0403000101150439a34181d4d91a55d7bd8100580e5eca59265ca4750000000020cb00000000000000000000000000'
    )
  })
})
