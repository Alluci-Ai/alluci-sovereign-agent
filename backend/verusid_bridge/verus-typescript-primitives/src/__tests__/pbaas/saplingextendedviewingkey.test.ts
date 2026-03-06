import { SaplingExtendedViewingKey } from '../../pbaas/SaplingExtendedViewingKey';

describe('SaplingExtendedViewingKey', () => {
  const mainnetKey = 'zxviews1q0njl87fqqqqpq8vghkp6nz9wx48mwelukvhx3yfwg7msatglv4xy8rrh87k9z472edvlrt950qyy6r766dxnpqktxug7t2wy80s4ug325dwp9hf4vw9a6ethf2mwc9wan28p88dq8q2e8sdlw2mhffg6hy92tjyuquz7a8reqdz905x6xt6kqdx5wn7jvas0733hends8q6s8k87emn6m060xdnhgmvn4zmx0ssrwve84lzxkqu2dnfq5qsjwrtlject0an0k282rsnx0kq4';

  it('should decode and encode a mainnet extended viewing key', () => {
    const key = SaplingExtendedViewingKey.fromKeyString(mainnetKey);

    expect(key.depth).toBeGreaterThanOrEqual(0);
    expect(key.parentFVKTag.length).toBe(4);
    expect(key.childIndex.length).toBe(4);
    expect(key.chainCode.length).toBe(32);
    expect(key.ak.length).toBe(32);
    expect(key.nk.length).toBe(32);
    expect(key.ovk.length).toBe(32);
    expect(key.dk.length).toBe(32);

    const encoded = key.toKeyString(false);
    expect(encoded).toBe(mainnetKey);
  });

  it('should round-trip through buffer serialization', () => {
    const key = SaplingExtendedViewingKey.fromKeyString(mainnetKey);
    
    const buffer = key.toBuffer();
    expect(buffer.length).toBe(169);

    const key2 = new SaplingExtendedViewingKey();
    key2.fromBuffer(buffer);

    expect(key2.depth).toBe(key.depth);
    expect(key2.parentFVKTag.equals(key.parentFVKTag)).toBe(true);
    expect(key2.childIndex.equals(key.childIndex)).toBe(true);
    expect(key2.chainCode.equals(key.chainCode)).toBe(true);
    expect(key2.ak.equals(key.ak)).toBe(true);
    expect(key2.nk.equals(key.nk)).toBe(true);
    expect(key2.ovk.equals(key.ovk)).toBe(true);
    expect(key2.dk.equals(key.dk)).toBe(true);

    const encoded = key2.toKeyString(false);
    expect(encoded).toBe(mainnetKey);
  });
});
