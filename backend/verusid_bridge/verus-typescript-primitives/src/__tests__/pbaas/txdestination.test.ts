import { IdentityID } from "../../pbaas/IdentityID";
import { KeyID } from "../../pbaas/KeyID";
import { NoDestination } from "../../pbaas/NoDestination";
import { PubKey } from "../../pbaas/PubKey";
import { TxDestination, TxDestinationVariantInterface } from "../../pbaas/TxDestination";
import { fromBase58Check, toIAddress } from "../../utils/address";

describe('Serializes and deserializes TxDestination variants', () => {
  interface AddressInterface {
    new (hash?: Buffer): IdentityID | KeyID | NoDestination;
  }

  function testTxDestinationTypeAddr(TxDestClass: AddressInterface, addr?: string) {
    const hash = addr ? fromBase58Check(addr).hash : undefined;

    const id = new TxDestClass(hash);
    const idFromBuf = new TxDestClass();
    idFromBuf.fromBuffer(id.toBuffer());

    expect(id.toBuffer().toString('hex')).toBe(hash ? hash.toString('hex') : "");
    expect(id.toAddress()).toBe(addr ? addr : null);
    expect(idFromBuf.toAddress()).toBe(id.toAddress());
    expect(idFromBuf.toBuffer().toString('hex')).toBe(id.toBuffer().toString('hex'));
  }

  test('(de)serialize an IdentityID', () => {
    const vrsctest = "VRSCTEST";
    const addr = toIAddress(vrsctest);

    testTxDestinationTypeAddr(IdentityID, addr)
  });

  test('(de)serialize a KeyID', () => {
    testTxDestinationTypeAddr(KeyID, "RQVsJRf98iq8YmRQdehzRcbLGHEx6YfjdH")
  });

  test('(de)serialize a NoDestination', () => {
    testTxDestinationTypeAddr(NoDestination, "")
  });

  test('(de)serialize a compressed PubKey', () => {
    const pub = "024efec1ac0175cbfc54f1461c9670e9c4a6b4e3e0ac8ba85c4b2003e67b1b41d8";

    const key = new PubKey(Buffer.from(pub, 'hex'), true);
    const keyFromBuf = new PubKey();
    keyFromBuf.fromBuffer(key.toBuffer());

    expect(key.toBuffer().toString('hex')).toBe(pub);
    expect(keyFromBuf.toBuffer().toString('hex')).toBe(key.toBuffer().toString('hex'));
  });

  test('(de)serialize a basic TxDestination class with type PKH', () => {
    const addr = "RQVsJRf98iq8YmRQdehzRcbLGHEx6YfjdH";

    const dest = new TxDestination(KeyID.fromAddress(addr));
    const destFromBuf = new TxDestination();
    destFromBuf.fromBuffer(dest.toBuffer());

    expect(destFromBuf.toBuffer().toString('hex')).toBe(dest.toBuffer().toString('hex'));
  });

  test('(de)serialize a basic TxDestination class with type PKH (toChunk)', () => {
    const addr = "RQVsJRf98iq8YmRQdehzRcbLGHEx6YfjdH";

    const dest = new TxDestination(KeyID.fromAddress(addr));
    const destFromChunk = TxDestination.fromChunk(dest.toChunk());

    expect(destFromChunk.toBuffer().toString('hex')).toBe(dest.toBuffer().toString('hex'));
  });

  test('(de)serialize a basic TxDestination class with type Identity (toChunk)', () => {
    const addr = "iQa13cLx5a4bB9nnd8EZPigrqLTsn75VrF";

    const dest = new TxDestination(IdentityID.fromAddress(addr));
    const destFromChunk = TxDestination.fromChunk(dest.toChunk());

    expect(destFromChunk.data instanceof IdentityID).toBe(true);
    expect(destFromChunk.type.toNumber()).toBe(TxDestination.TYPE_ID.toNumber());
    expect(destFromChunk.toBuffer().toString('hex')).toBe(dest.toBuffer().toString('hex'));
  });
});