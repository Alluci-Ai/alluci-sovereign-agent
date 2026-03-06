import { SaplingExtendedSpendingKey } from '../../pbaas/SaplingExtendedSpendingKey';

describe('SaplingExtendedSpendingKey', () => {
  const mainnetKey = 'secret-extended-key-main1q0njl87fqqqqpq8vghkp6nz9wx48mwelukvhx3yfwg7msatglv4xy8rrh87k9z472el95h53ym2tku2dazny0j2vfukgmp6fu3k7edzcx9n8egesc32sdy3xr4s2ep4skgc7t5j5zds4ws7hf2nuszf7ltfn2nc5rk3k77gyeqdz905x6xt6kqdx5wn7jvas0733hends8q6s8k87emn6m060xdnhgmvn4zmx0ssrwve84lzxkqu2dnfq5qsjwrtlject0an0k282rs0gws78';

  it('should decode and encode a mainnet extended spending key', () => {
    const key = SaplingExtendedSpendingKey.fromKeyString(mainnetKey);

    expect(key.depth).toBeGreaterThanOrEqual(0);
    expect(key.parentFVKTag.length).toBe(4);
    expect(key.childIndex.length).toBe(4);
    expect(key.chainCode.length).toBe(32);
    expect(key.ask.length).toBe(32);
    expect(key.nsk.length).toBe(32);
    expect(key.ovk.length).toBe(32);
    expect(key.dk.length).toBe(32);

    const encoded = key.toKeyString(false);
    expect(encoded).toBe(mainnetKey);
  });

  it('should round-trip through buffer serialization', () => {
    const key = SaplingExtendedSpendingKey.fromKeyString(mainnetKey);
    
    const buffer = key.toBuffer();
    expect(buffer.length).toBe(169);

    const key2 = new SaplingExtendedSpendingKey();
    key2.fromBuffer(buffer);

    expect(key2.depth).toBe(key.depth);
    expect(key2.parentFVKTag.equals(key.parentFVKTag)).toBe(true);
    expect(key2.childIndex.equals(key.childIndex)).toBe(true);
    expect(key2.chainCode.equals(key.chainCode)).toBe(true);
    expect(key2.ask.equals(key.ask)).toBe(true);
    expect(key2.nsk.equals(key.nsk)).toBe(true);
    expect(key2.ovk.equals(key.ovk)).toBe(true);
    expect(key2.dk.equals(key.dk)).toBe(true);

    const encoded = key2.toKeyString(false);
    expect(encoded).toBe(mainnetKey);
  });
});
