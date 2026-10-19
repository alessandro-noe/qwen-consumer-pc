#> **Nota sui percorsi.** Questo documento usa i nomi della cartella originale. In questo repository: `sistema/smistatore.py` -> `proxy/smistatore.py`; `sistema/kael_mcp.py`, `sistema/biblioteca_mcp.py`, `sistema/esecutore.py` -> `extras/`; `avvia_*.cmd` -> `scripts/start_*.cmd`; banchi (`*_bench*.py`, `prova_*.py`, `sito_prova/`) -> `benchmarks/`; `.opencode/` -> `opencode/.opencode/`; modifiche a llama.cpp -> `llamacpp-patch/`. Alcuni file citati (es. `dialetto.py`, `prefill_bench.py`, `MOTORE_NOSTRO.md`) non sono inclusi.

 Un modello quasi di frontiera, intero, su un PC consumer — rapporto misurato

> Bozza del 2026-10-17, aggiornata il 2026-10-18. Ogni numero e' misurato su questo PC; dove un dato viene da altri e' indicata la fonte.
> I risultati negativi sono riportati come quelli positivi.

## In breve

- **Modello:** Qwen3.8-Flash-Next (MoE: 125B parametri totali, ~6B attivi per token, 48 piani x 512 esperti, top-10),
  **intero** (nessun esperto tagliato), compressione GSQ-RCO Q2_0 di ISTA-DASLab (37,6 GB + tabella n-gram 28,8 GB).
- **PC:** RTX 4080 SUPER 16 GB (PCIe 4.0), Ryzen 7 7800X3D (8 core), 32 GB DDR5-5600, Windows 11.
- **Velocita':** ~40 token/s in scrittura, ~860 token/s in lettura del prompt.
- **Lavoro da agente, compiti difficili:** **5/5 in 27,5 minuti**, contro **3/5 in 34,9 minuti** di Qwen3.8-27B denso
  sullo stesso PC, stesso motore, stesse impostazioni.
- **Scalata al fallimento (nostra):** il modello lavora senza ragionamento e lo accende solo dopo 2 fallimenti veri
  dei test: **5/5 in 19,4 e 31,6 minuti** (due prove) invece di 68,3 con il ragionamento sempre acceso (versione uncensored).
- Attorno al modello: un'infrastruttura agentica personale (OpenCode + smistatore con modello decisionale Kev-4B +
  Kael + graphify + RTK), tutta in locale.

## 1. La ricetta (riproducibile)

| Pezzo | Scelta | Perche' (misurato) |
|---|---|---|
| Pesi | GSQ-RCO Q2_0 (ISTA-DASLab, Hugging Face) | modello intero in 37,6 GB residenti |
| Motore | llama.cpp b11669 (commit 620d2225c) | |
| Tabella n-gram 28,8 GB | `-lm mmap -lzm on` (resta su disco, letta su richiesta) | senza: non entra in memoria; spenta: qualita' crolla (26/30 -> 17/30) |
| Lotto di lettura | `-b 2048 -ub 2048` | lettura 390 -> 860 tok/s, scrittura ~32 -> ~40 |
| Contesto | `-c 65536` | 262k + KV 8 bit e' ~2x piu' lento nel lavoro agentico |
| Thread | 8 (predefinito) | 6-7 thread piu' lenti |
| Ragionamento | acceso, stile libero | decisivo per la qualita' (vedi 3) |

Comando: `avvia_modello.cmd`.

## 2. Velocita' (PC 16 GB)

| Configurazione | Riscrivere un file | Codice nuovo |
|---|---|---|
| llama.cpp, lotto 512 (predefinito) | ~31-34 | ~32 |
| **lotto 2048 (scelta)** | **38,4-40,5** | **39,5-39,9** |
| lotto 2048 + bozza n-gram (`--spec-type ngram-mod`) | +41% riscrivendo (misurato con lotto 512) | -9% |
| lotto 2048 + MTP compresso Q3_K_M in GPU | 42,5 | 39,8 |

Lettura del prompt (11.015 token di codice, server caldo): 390 tok/s (lotto 512) -> 860 tok/s (2048);
4096: 810; 8192: ~200 (ruba memoria video agli esperti).

**PC piu' debole simulato** (esperti in RAM, ~7-13 GB di memoria video):

| Configurazione | Riscrivere | Codice nuovo |
|---|---|---|
| esperti in RAM, solo il nucleo in GPU (~7 GB) | 19,8 | 20,8 |
| + MoE ibrido nostro (6 GB di esperti fissi per impatto) | 22,0 | 29,1 |
| + salta i freddi deboli (`MOE_COLD_TOPK=7`) | 24,3 | 33,7 |

## 3. Qualita'

**HumanEval** (164 problemi, test ufficiali; estrazione del codice corretta):

| Modello | Senza ragionamento | Con ragionamento (sui problemi sbagliati) |
|---|---|---|
| Flash-Next Q2_0 | 154/164 (93,9%) | ~163/164 |
| Qwen3.8-27B denso (IQ2_M) | 157/164 (95,7%) | ~162/164 |
| Mini tagliato a 128 esperti/piano | 118/164 (72,0%) | - |
| Qwen3.8-4B | 112/164 (68,3%) | - |

Problemi mai visti (18 di controllo, ragionamento acceso): Flash-Next 18/18.

**Compiti da agente** (`agent_bench2.py`, `agent_bench3.py`): progetti con piu' file, il modello riceve solo il sintomo,
usa strumenti (leggi/scrivi/esegui), voto da un checker nascosto piu' severo dei test visibili.

| Banco | Flash-Next Q2_0 | 27B |
|---|---|---|
| 12 compiti normali | 12/12 | 11/12 |
| **5 compiti difficili** (database con transazioni, interprete di un linguaggio, bug intrecciati in 4 file, pianificatore con dipendenze, diff/patch JSON) | **5/5, 27,5 min, 54k token** | **3/5, 34,9 min, 70k token** |

Il 27B genera piu' token al secondo (~45) ma sui compiti lunghi sbaglia di piu' e scrive di piu':
il **tempo per finire il lavoro** e' il metro giusto, non i token al secondo.

**Versione senza censure** (abliterated di SC117, stessa compressione): 5/5 difficili e 18/18 di controllo, ma
68,3 min e 115k token sui difficili (circa il doppio dei token per passo); ~36 tok/s a caldo (i pezzi modificati
dall'abliterazione sono salvati a 8 bit: +398 MB).

**Come si riduce il tempo per compito** (versione senza censure, 5 compiti difficili, limite 32k token per risposta):

| Variante | Risolti | Minuti | Token |
|---|---|---|---|
| ragionamento sempre acceso | 5/5 | 68,3 | 115.350 |
| + regola "minimo codice" (Ponytail, MIT) | 5/5 | 55,6 | 97.905 |
| + smistatore con note su agenti/skill | 4/5 | 59,9 | 98.783 |
| **+ scalata al fallimento** (prova 1 / prova 2, semi diversi) | **5/5 / 5/5** | **19,4 / 31,6** | **26.803 / 47.622** |
| scalata + Ponytail insieme | 4/5 | 53,4 | 85.252 |
| scalata + 6 esperti su 10 dopo `</think>` (`MOE_ESEC_K=6`) | 5/5 | 74,2 | 141.536 |

Quota di token di esecuzione (codice/comandi, il resto e' ragionamento): 76% modello normale, 68% senza censure.

## 4. Cosa e' nostro

1. **Kael** (`sistema/kael_mcp.py`, server MCP): memoria di errori ammessi **solo se un comando di test lo dimostra**,
   verifica obbligatoria prima di dire "fatto", STOP dopo 3 errori uguali.
2. **MoE ibrido in llama.cpp** (modifiche marcate `agente-locale`): esperti caldi fissi in GPU scelti per
   **impatto misurato** (non frequenza), freddi calcolati dalla CPU (`id = -1` = salta), salta-i-freddi-deboli.
3. **Misura d'impatto per esperto** (dentro colibri): ha mostrato che un taglio basato su sonde brevi copriva
   solo il 64% dell'impatto reale.
4. **Banchi agentici** con checker nascosti e i confronti di questo rapporto.
5. **Scoperte misurate sul modello** (sezione 5).
6. **Smistatore** (`sistema/smistatore.py`, proxy tra OpenCode e il modello): un modello DECISIONALE (Kev-4B, sul
   processore, ~0,4 s) sceglie la strada di ogni richiesta; le domande semplici vanno senza ragionamento
   (6 domande: 467 -> 55 token, 6/6 giuste); **scalata al fallimento**: nei compiti il ragionamento si accende solo
   dopo 2 risultati falliti di test/esecuzione (il segnale viene dai fatti, non dal modello).
7. **Esperti per fase** (`MOE_ESEC_K` nel motore): tutti gli esperti durante prompt e ragionamento, K dopo `</think>`.
   +20% tok/s in esecuzione, ma tempo per compito peggiore (sezione 3): spento di serie.
8. **Esecutore browser** (`sistema/esecutore.py`): Qwen pianifica a ogni pagina, Kev sceglie l'elemento, guardiano
   NEL CODICE sulle azioni irreversibili (invia/paga/elimina chiedono conferma), i modelli vedono solo le etichette
   degli elementi (un'istruzione nascosta nella pagina e' stata ignorata). 10/10 su un sito locale, ma nessun
   guadagno di tempo su pagine piccole (150 s contro 155 s di Qwen da solo).

Preso da altri e dichiarato: modello (Qwen), compressione (ISTA-DASLab GSQ-RCO), motore (llama.cpp, MIT),
tabella su disco (llama.cpp lazy mode), lotto 2048 (guida Hugging Face sull'offload dei MoE), modello decisionale
Kev-4B, RTK (rtk-oss, Apache-2.0: output dei comandi -45% token; escluso pytest perche' toglie il tipo di eccezione),
regola Ponytail (MIT), profilo agenti/skill ridotto da ECC (MIT).
Strata (github.com/Niko1221/Strata) e' un motore dedicato a questo modello con idee simili all'ibrido;
lo abbiamo letto, non eseguito.

## 5. Scoperte e risultati negativi

| Prova | Risultato | Lezione |
|---|---|---|
| Tagliare il modello a 128 esperti/piano (Mini) | HumanEval 72% vs 94% | non tagliare: comprimere |
| Spegnere la tabella n-gram | 26/30 -> 17/30 | serve |
| Perplessita' come giudice | diceva "nessuna perdita" | giudicare solo con test di generazione |
| Ragionamento spento | sembrava peggio del 27B | con ragionamento recupera 9 errori su 10 |
| Stile di ragionamento "cinese + TOON" | 9/10 su 10 problemi, ma 16/18 e +73% token su 18 nuovi | su pochi problemi si trovano falsi vincitori |
| Ricerca evolutiva del dialetto (16 dialetti) | vincitore 13/18 sui problemi nuovi (libero 18/18) | overfitting: servono set di controllo |
| Meno esperti sui piani in RAM (top-7/top-6) | 47-50 tok/s ma compiti difficili in 55 min invece di 27,5 | piu' veloce per token, piu' lento per compito |
| **Pesi del router** (56.304 scelte) | le prime 6 su 10 hanno solo il 70-83% del peso (mediana 76%) | il router e' "democratico": ogni taglio di esperti costa intelligenza |
| MTP (testa di bozza del modello) | 89-99% accettata, ma +11% solo riscrivendo | la verifica di piu' token moltiplica gli esperti da calcolare |
| Cache LRU di llama.cpp | sempre piu' lenta di nessuna cache | i trasferimenti su PCIe costano piu' del guadagno |
| Kernel Q2_0 AVX-512 VNNI / 8 righe | 0,99x / 1,29x sul kernel, ~2-3% in totale | il calcolo e' 1/3 del tempo CPU |
| **Dove va il tempo** (ms per parola, PC debole) | GPU ~0; CPU ~13-16, di cui ~2/3 sincronizzazione per piano | il prossimo salto e' ridurre la sincronizzazione GPU<->CPU |
| Modelli decisionali come smistatori (32 richieste, 8 strade) | Julia-1 38-53%, Laya 38-62%, Kev-4B 94-100% | le descrizioni delle opzioni valgono 30-50 punti |
| Qwen stesso come decisore (1 token, probabilita' delle cifre) | 97-100%, ma ~1 s e rompe la cache della conversazione | lettere A-H falliscono in inglese (19%): usare cifre |
| Kev mentre Qwen lavora | 1,4-2,3 s invece di 0,25 s | Windows sfratta i suoi pesi: `-lm mlock` -> 0,4 s |
| Errori 500 nei banchi | JSON della chiamata troncato a 8.192 token | era il limite del banco, non del metodo |
| **Togliere ragionamento vs togliere esperti** | scalata -55/-72% tempo; meno esperti +8% a +280% tempo | si guadagna togliendo il ragionamento inutile, non la capacita' |
| Strata (motore dedicato) secondo i suoi dati | Q2_0 a 60-94 tok/s con 47-64 GB di RAM; con 32 GB consiglia solo il Coder | sul nostro PC il limite e' la RAM |
| WSL2 | non misurato; disco 9P lento e RAM limitata dalla VM | per un modello letto dal disco aggiunge i costi che fanno male |

## 6. Limiti

- Un solo PC; i banchi sono piccoli (12 + 5 compiti agentici, 18 problemi di controllo); quasi ogni variante ha
  UNA prova (la scalata due): le differenze piccole possono essere caso.
- I punteggi "con ragionamento" su HumanEval sono stimati rifacendo solo i problemi sbagliati.
- Le velocita' variano di qualche token/s tra un avvio e l'altro (server caldo vs freddo).
- Licenza del modello: qwen-community-1.0; i pesi non vengono ridistribuiti.

## 7. File

`avvia_modello.cmd`, `opencode.json`, `sistema/` (Kael, regole), `agent_bench2.py`, `agent_bench3.py`,
`spec_bench.py`, `prefill_bench.py`, `stile_ragionamento.py`, `dialetto.py`, `decisore_bench.py`, `decisore_qwen.py`,
`browser_bench.py`, `misura_rtk.py`, `velocita_fase.py`, `sistema/smistatore.py`, `sistema/esecutore.py`,
`avvia_smistatore.cmd`, `.opencode/` (agenti, skill, plugin RTK), `INVENZIONI.md` (registro completo),
`MOTORE_NOSTRO.md` (piano e origine di ogni idea), modifiche a llama.cpp in `studio/llamacpp_src` (marcate `agente-locale`).
