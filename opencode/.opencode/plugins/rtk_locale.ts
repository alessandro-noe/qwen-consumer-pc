// rtk_locale.ts — RTK (rtk-oss 1.0.1, Apache-2.0, github.com/rtk-ai/rtk) solo per questo progetto.
// Ridotto da hooks/opencode/rtk.ts di RTK: la decisione di riscrivere resta a `rtk hook opencode`
// (rispetta i permessi di OpenCode), ma accettiamo la riscrittura SOLO per i comandi in LISTA.
// Misurato (misura_rtk.py): git log -72%, ls -81%, grep -30%; pytest -68% ma perde il tipo di
// eccezione (es. ZeroDivisionError) -> i test restano completi (li accorcia gia' kael.verifica).
// Niente PATH globale, niente `rtk init`, telemetria spenta su ogni comando.
import { execFile } from "node:child_process"
import { existsSync } from "node:fs"

const RTK = process.env.RTK_EXE || "rtk.exe"   // percorso di rtk.exe (rtk-oss): variabile RTK_EXE o nel PATH
const LISTA = new Set(["git", "ls", "grep", "find", "rg", "tree"])

function riscrittura(comando: string, agente?: string): Promise<string | null> {
  const argv = ["hook", "opencode"]
  if (agente) argv.push("--agent", agente)
  argv.push(comando)
  return new Promise((resolve) => {
    execFile(RTK, argv, { encoding: "utf8", timeout: 3000, windowsHide: true,
                          env: { ...process.env, RTK_TELEMETRY_DISABLED: "1" } }, (err, out) => {
      if (err) return resolve(null)
      try {
        const nuovo = String(JSON.parse(String(out ?? "").trim() || "{}").command ?? "").trim()
        const m = nuovo.match(/^rtk\s+(\S+)/)
        if (!m || !LISTA.has(m[1]) || nuovo === comando) return resolve(null)
        resolve(`RTK_TELEMETRY_DISABLED=1 "${RTK}" ` + nuovo.slice(4))
      } catch {
        resolve(null)
      }
    })
  })
}

async function gestisci(tool: unknown, input: any, agente?: string) {
  const t = String(tool ?? "").toLowerCase()
  if ((t !== "bash" && t !== "shell") || !input || typeof input.command !== "string") return
  if (process.env.RTK_DISABLED === "1") return
  const nuovo = await riscrittura(input.command, agente)
  if (nuovo) input.command = nuovo
}

export default {
  id: "rtk_locale",
  async setup(ctx: any) {
    if (!existsSync(RTK)) return console.warn("[rtk_locale] rtk.exe non trovato: plugin spento")
    await ctx?.tool?.hook?.("execute.before", (e: any) =>
      gestisci(e?.tool, e?.input, typeof e?.agent === "string" ? e.agent : undefined))
  },
  async server() {
    if (!existsSync(RTK)) return {}
    return { "tool.execute.before": (input: any, output: any) => gestisci(input?.tool, output?.args) }
  },
}
