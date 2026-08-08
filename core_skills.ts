// core_skills.ts - aggregates built‑in skill manifests
// This file imports each JSON skill definition from the core_skills directory
// and exports them as a typed array for use by the runtime.

// eslint-disable-next-line @typescript-eslint/no-var-requires
const auth01 = require('./core_skills/auth_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const bmc01 = require('./core_skills/bmc_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const c2c01 = require('./core_skills/c2c_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const cdg01 = require('./core_skills/cdg_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const cht01 = require('./core_skills/cht_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const hcd01 = require('./core_skills/hcd_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const fnd01 = require('./core_skills/fnd_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const fnd02 = require('./core_skills/fnd_02.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const ikigai01 = require('./core_skills/ikigai_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const msg01 = require('./core_skills/msg_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const ptc01 = require('./core_skills/ptc_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const vbp01 = require('./core_skills/vbp_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const vrs01 = require('./core_skills/vrs_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const ws01 = require('./core_skills/ws_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const spe01 = require('./core_skills/spe_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const ir01 = require('./core_skills/ir_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const ldl01 = require('./core_skills/ldl_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const ocs01 = require('./core_skills/ocs_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const suf01 = require('./core_skills/suf_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const swd01 = require('./core_skills/swd_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const okd01 = require('./core_skills/okd_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const cmp01 = require('./core_skills/cmp_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const fde01 = require('./core_skills/fde_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const ftl01 = require('./core_skills/ftl_01.json');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const hro01 = require('./core_skills/hro_01.json');

export const CORE_SKILLS = [
  auth01,
  bmc01,
  c2c01,
  cdg01,
  cht01,
  cmp01,
  fde01,
  fnd01,
  fnd02,
  ftl01,
  hcd01,
  hro01,
  ikigai01,
  ir01,
  ldl01,
  msg01,
  ocs01,
  okd01,
  ptc01,
  spe01,
  suf01,
  swd01,
  vbp01,
  vrs01,
  ws01,
];
