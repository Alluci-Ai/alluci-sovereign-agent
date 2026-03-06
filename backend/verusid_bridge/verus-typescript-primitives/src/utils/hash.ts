import createHash = require("create-hash");

export const hash = (...params: Array<Buffer>): Buffer => {
  const _hash = createHash("sha256");

  params.forEach((value) => {
    _hash.update(value)
  })

  return createHash("sha256").update(_hash.digest()).digest();
}

export const hash160 = (data: Buffer): Buffer => {
  const sha256 = createHash("sha256");
  const ripemd160 = createHash("ripemd160");

  return ripemd160.update(sha256.update(data).digest()).digest();
}