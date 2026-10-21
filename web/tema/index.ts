import type { ThemeConfig } from "antd";
import { FONT_FAMILY, FONT_FAMILY_CODE } from "./fonts";
import { light } from "./light";

const fontFamily = `var(--font-plex-sans), ${FONT_FAMILY}`;
const fontFamilyCode = `var(--font-plex-mono), ${FONT_FAMILY_CODE}`;
const components: ThemeConfig["components"] = {};

if (light.components) {
  for (const [name, overrides] of Object.entries(light.components)) {
    const patched = { ...(overrides as Record<string, unknown>) };
    if ("fontFamily" in patched) patched.fontFamily = fontFamily;
    if ("fontFamilyCode" in patched) patched.fontFamilyCode = fontFamilyCode;
    (components as Record<string, unknown>)[name] = patched;
  }
}

export const theme: ThemeConfig = {
  ...light,
  cssVar: {},
  token: {
    ...light.token,
    fontFamily,
    fontFamilyCode,
  },
  components,
};
