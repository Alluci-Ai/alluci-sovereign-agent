import { SaplingPaymentAddress } from "../../pbaas/SaplingPaymentAddress";

describe('(de)serializes SaplingPaymentAddress', () => {
  test('(de)serializes SaplingPaymentAddress from address string', () => {
    const addrString = "zs1vs80kux83va28g9f0h6zpmd69vwaykmtd2j3lf5hgzw9tuesdspjx5h6fmy63jevqh8fwuh7cxz";
    const paymentAddrFromAddr = SaplingPaymentAddress.fromAddressString(addrString);

    expect(paymentAddrFromAddr.toAddressString()).toBe(addrString);
  });

  test('(de)serializes SaplingPaymentAddress from address string', () => {
    const addrString = "zs1dr4s62vj6w72v33kx407q00t75lxjfla5734mpf55qy25xjmeq23zagn5r0pmuwzmpl2ks9vlwh";
    const paymentAddrFromAddr = SaplingPaymentAddress.fromAddressString(addrString);

    expect(paymentAddrFromAddr.toAddressString()).toBe(addrString);
  });

  test('(de)serializes SaplingPaymentAddress from address string', () => {
    const addrString = "zs1wczplx4kegw32h8g0f7xwl57p5tvnprwdmnzmdnsw50chcl26f7tws92wk2ap03ykaq6jyyztfa";
    const paymentAddrFromAddr = SaplingPaymentAddress.fromAddressString(addrString);

    expect(paymentAddrFromAddr.toAddressString()).toBe(addrString);
  });
});