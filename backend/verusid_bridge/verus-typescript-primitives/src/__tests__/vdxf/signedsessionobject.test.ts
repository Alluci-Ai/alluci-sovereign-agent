import { SignedSessionObject, SignedSessionObjectData } from "../../vdxf/classes";

describe('Serializes and deserializes signed session object properly', () => {
  test('signed session object', async () => {
    const req = new SignedSessionObject({
      system_id: "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV",
      signing_id: "iB5PRXMHLYcNtM8dfLB6KwfJrHU2mKDYuU",
      signature: {
        signature:
          "AYG2IQABQSAN1fp6A9NIVbxvKuOVLLU+0I+G3oQGbRtS6u4Eampfb217Cdf5FCMScQhV9kMxtjI9GWzpchmjuiTB2tctk6qT",
      },
      data: new SignedSessionObjectData({
        session_id: "iKNufKJdLX3Xg8qFru9AuLBvivAEJ88PW4",
        timestamp_micro: 2038523,
        body: "request body"
      })
    })

    const reqbuf = req.toBuffer()
    const _req = new SignedSessionObject()
    _req.fromBuffer(reqbuf)

    expect(_req.toBuffer().toString('hex')).toBe(reqbuf.toString('hex'));

    expect(_req.getDataHash(10000, 1).toString('hex')).toBe(req.getDataHash(10000, 1).toString('hex'))
    expect(_req.getDataHash(10000, 2).toString('hex')).toBe(req.getDataHash(10000, 2).toString('hex'))

    const headers = _req.getHeaders()

    expect(headers["VDXF-Key"]).toBe("iQFqjYQnaiCPENEShSb8Jy3qD6En43juVr");
    expect(headers["VDXF-Version"]).toBe("1");
    expect(headers["VerusID-Session-ID"]).toBe("iKNufKJdLX3Xg8qFru9AuLBvivAEJ88PW4");
    expect(headers["VerusID-Signature"]).toBe("AYG2IQABQSAN1fp6A9NIVbxvKuOVLLU+0I+G3oQGbRtS6u4Eampfb217Cdf5FCMScQhV9kMxtjI9GWzpchmjuiTB2tctk6qT");
    expect(headers["VerusID-Timestamp-Micro"]).toBe("2038523")
  });
});
