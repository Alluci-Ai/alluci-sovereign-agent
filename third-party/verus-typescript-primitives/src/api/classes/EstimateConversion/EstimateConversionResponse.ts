import { ApiResponse } from "../../ApiResponse";

export class EstimateConversionResponse extends ApiResponse {
  result: {
    estimatedcurrencyout: number,
    inputcurrencyid: string,
    netinputamount: number,
    outputcurrencyid: string,
    estimatedcurrencystate: {
      currencies: {
          [currencyid: string]: {
              conversionfees: number,
              fees: number,
              lastconversionprice: number,
              primarycurrencyin: number,
              priorweights: number,
              reservein: number,
              reserveout: number,
              viaconversionprice: number
          }
      },
      currencyid: string,
      emitted: number,
      flags: number,
      initialsupply: number,
      preconvertedout: number,
      primarycurrencyconversionfees: number,
      primarycurrencyfees: number,
      primarycurrencyout: number,
      reservecurrencies: Array<{
        currencyid: string,
        priceinreserve: number,
        reserves: number,
        weight: number
      }>,
      supply: number,
      version: number
  },
  }
}
