import { site } from "@/lib/site";

export const agentGuidance = [
  "## Para agentes",
  "",
  "Valide com `tiss_validate`, aplique correções com `tiss_apply_fixes` e revalide até zerar os erros, em no máximo três rodadas. Use `tiss_build` para montar o XML e `tiss_hash` para calcular o hash do epílogo.",
  `- [Instalar a skill](https://github.com/Voa-Health/tiss/tree/main/skills/voa-tiss): \`npx skills add Voa-Health/tiss\``,
  `- [Orientações para agentes](https://github.com/Voa-Health/tiss/blob/main/AGENTS.md)`,
  `- [MCP remoto](${site.url}/mcp)`,
].join("\n");
