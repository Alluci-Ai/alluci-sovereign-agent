import { toLowerCaseCLocale } from "../../utils/tolower";

describe('Address tests', () => {
  test('toIAddress tests', async () => {
    expect(toLowerCaseCLocale("VRSCTEST")).toBe("vrsctest");
    expect(toLowerCaseCLocale("!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`{|}~")).toBe("!\"#$%&'()*+,-./0123456789:;<=>?@abcdefghijklmnopqrstuvwxyz[\\]^_`{|}~");
    expect(toLowerCaseCLocale("Ⓐ.VRSC")).toBe("Ⓐ.vrsc");
  });
});