#> **Nota sui percorsi.** Questo documento usa i nomi della cartella originale. In questo repository: `sistema/smistatore.py` -> `proxy/smistatore.py`; `sistema/kael_mcp.py`, `sistema/biblioteca_mcp.py`, `sistema/esecutore.py` -> `extras/`; `avvia_*.cmd` -> `scripts/start_*.cmd`; banchi (`*_bench*.py`, `prova_*.py`, `sito_prova/`) -> `benchmarks/`; `.opencode/` -> `opencode/.opencode/`; modifiche a llama.cpp -> `llamacpp-patch/`. Alcuni file citati (es. `dialetto.py`, `prefill_bench.py`, `MOTORE_NOSTRO.md`) non sono inclusi.

 INVENZIONI — ipotesi nuove, derivazione, misura, verdetto

Regola: ogni idea e' un'IPOTESI (🎨) finche' un numero sul banco non la conferma.
I risultati negativi si registrano qui come quelli positivi.

## Baseline (misurati 2026-10-16/17, Qwen3.8-Flash-Next GSQ-RCO Q2_0, RTX 4080 16 GB, llama.cpp b11669)

| Banco | Configurazione | Numero |
|---|---|---|
| 10 problemi HumanEval difficili, ragionamento acceso | stile libero | 9/10, 1851 token medi, 77,2 s |
| idem | **cinese_toon** | 9/10, 1023 token medi, 44,2 s |
| agent_bench2 (12 compiti, checker nascosto) | 64k, cinese_toon | 12/12, 27.203 token, 18,4 min |
| agent_bench2 | 27B denso, stile libero | 11/12, 61.758 token, 23,7 min |
| velocita' generazione, PC 16 GB | piazzamento automatico 64k | 28,8 (riscrivere) / 32,0 (codice nuovo) tok/s |
| velocita', esperti in RAM + 6 GB GPU | MoE ibrido (nostro) | 21,3 / 25,2 tok/s (vs 19,8 / 20,8 senza cache) |

## Gia' provate

| Idea | Numero | Verdetto |
|---|---|---|
| Spegnere la tabella n-gram (PLE) | HumanEval Mini 26/30 -> 17/30 | SCARTATA (la PLE serve) |
| Perplessita' come giudice | diceva "nessuna perdita", HumanEval smentisce | SCARTATA come metro |
| MTP (testa di predizione) | 92-99% bozze accettate ma 17-20 tok/s vs 24-28 | SCARTATA su questo modello |
| ngram-mod | +41% riscrivendo, -9% codice nuovo, 12/12 agentico | TENUTA solo per riscritture |
| Stili di ragionamento | cinese puro +46% token, toml 5/10, cinese_toml 3/10; cinese_toon -45% | cinese_toon TENUTA |
| Cache LRU llama.cpp | sempre piu' lenta di nessuna cache (trasferimenti) | SCARTATA |
| Esperti fissi per impatto + trasferimenti | +17% codice nuovo, -11% riscrivere | superata dall'ibrido |
| Lotto di lettura -b/-ub (512 / 2048 / 4096 / 8192) | lettura 390 / 860 / 810 / 200 tok/s; scrittura 32 / 38 / 30 / 20 | 2048 TENUTA (da guida HF offload MoE) |
| Dialetto evolutivo (dialetto.py, 16 dialetti su 10 problemi) | vincitore zh+simboli+max5: 8/10 -40% token, ma CONTROLLO su 18 mai visti 13/18 vs libero 18/18 | SCARTATA (overfitting: 10 problemi troppo pochi, rumore grande) |
| cinese_toon su 18 problemi mai visti | 16/18, 1315 token vs libero 18/18, 759 token | RITIRATA dalle regole: aiuta solo sui problemi difficili, costa sui facili |
| Salta i freddi deboli (MOE_COLD_TOPK=7), PC debole simulato, lotto 2048 | 22,0/29,1 -> 24,3/33,7 tok/s, testo riscritto identico | TENUTA (qualita' agentica da verificare) |
| Lotto 2048 sul PC 16 GB, piazzamento automatico | 38,4 / 39,9 tok/s | obiettivo 39 tok/s RAGGIUNTO |
| MTP compresso Q3_K_M (2,15 GB) in GPU, bozze 3-4 | 42,5 / 39,8 tok/s vs 38,4 / 39,9 (+11% solo riscrivendo), accettazione 89-99% | TENUTA come opzione per riscritture; non e' un salto |
| MTP bozze da 2 / MTP + n-cpu-moe 36 | 39,3/38,3 ; 28,6/28,0 (VRAM piena) | SCARTATE (3 tentativi, stop) |
| MOE_CPU_TOPK (meno esperti sui piani in RAM), PC 16 GB | tok/s: K10 37,4/39,8 ; K8 43,4/43,6 ; K7 45,9/47,0 ; K6 49,0/49,5 | velocita' +18% (K7) / +25% (K6) |
| MOE_CPU_TOPK=7, qualita' | 18 nuovi: 18/18 ma 1282 token vs 759 (+69%); difficili 5/5 ma 127k token e 55,1 min vs 54k e 27,5 min | SCARTATA come default: tok/s su, ma il modello ragiona peggio e il TEMPO PER COMPITO raddoppia. Lezione: il metro giusto e' il tempo per risolvere, non i tok/s |
| Taglio condizionato alla sicurezza del router (MOE_CONF_K/TAU), PC 16 GB | K6: tau 0.9 -> 39,4/38,4 ; 0.8 -> 39,4/40,0 ; tau 0 (sempre) -> 46,5/47,2 tok/s | meccanismo FUNZIONA ma nessun guadagno utile |
| Analisi pesi del router (56.304 scelte token x piano, tracce colibri) | le prime 6 scelte hanno SEMPRE solo il 70-83% del peso (mediana 76%): le ultime 4 portano ~1/4 dell'uscita | SCOPERTA: il router di Flash-Next e' "democratico", non esistono token "sicuri" -> spiega perche' ogni taglio di esperti costa intelligenza. Via chiusa |
| Diagnosi tempi MoE ibrido (PC debole sim., ms/parola) | nessuna parte 15,4 ; solo caldi GPU 15,2 ; solo freddi CPU 28,5 ; entrambe 31,3 | la GPU costa ~0: il collo e' la parte CPU (~13-16 ms). Parallelizzare GPU/CPU NON serve |
| Kernel Q2_0 AVX-512 VNNI (CPU Zen 4 ha VNNI) | corretto (err 4e-5) ma 57,9 us vs 57,1 AVX2 (0,99x) | SCARTATO |
| Kernel Q2_0 a 8 righe insieme (idea repack) | 44,3 us (1,29x), ma il calcolo e' solo ~3,5 dei ~13 ms -> ~2-3% totale | SCARTATO (non vale 1 giorno) |
| Dove va il tempo della parte CPU | ~1/3 calcolo, ~2/3 coordinamento per piano (48 sync GPU<->CPU + risveglio thread) | PROSSIMO LAVORO GRANDE: ridurre la sincronizzazione (stile Strata: un grafo unico + attesa attiva) |
| MoE ibrido (fissi GPU + freddi CPU, -1 = salta) | +8% / +21% con esperti in RAM; -21% sul PC 16 GB vs piazzamento auto | TENUTA per GPU piccole |

## Verifica di novita' (2026-10-17, agente ricercatore, ricerche web)
- H1 Dialetto evolutivo: PARZIALMENTE NUOVO. Esistono ottimizzazione prompt per brevita' (PREMISE arXiv 2506.10716,
  CROP 2604.14214) e scelta della lingua (UL-XCoT). NUOVO: spazio composizionale lingua x notazione strutturata x
  passi, giudicato da test eseguiti, per modello locale; la sinergia cinese+TOON non risulta documentata.
  Token Complexity (arXiv 2503.01141): "nessuno stile vince sempre, dipende dal modello" -> supporta H1.
- H2 Router cartografo: quasi gia' fatto (eMoE 2503.06823, DoMoE IJCAI 2026, MoBiLE 2510.12357, DAOP 2501.10375).
- C Memoria verificata: parzialmente nuova (Voyager verifica con LLM; nostra: errori + test deterministico rieseguibile).
-> Scelta: H1. In esecuzione: dialetto.py (semi + 3 generazioni x 4 figli su 10 problemi, controllo su 18 mai visti).

## Ipotesi aperte 🎨

### H1 🎨 Dialetto evolutivo
- **Idea:** cercare in automatico, per ogni modello locale, il "dialetto di ragionamento" piu' economico
  (lingua x formato x lunghezza passi x campi obbligatori), giudicato solo da test eseguiti.
- **Derivazione:** token_totali = passi x token_per_passo. La lingua cambia token_per_passo
  (tokenizer: un carattere cinese ~ 1 token ad alta densita'), il formato elimina le parole di raccordo,
  i campi obbligatori (edge_cases, tests) mantengono il numero di passi UTILI. Misura: cinese da solo
  allunga (meno passi utili, piu' giri), toon da solo accorcia, insieme sono sinergici -> lo spazio va
  esplorato, non indovinato. Obiettivo: min E[token] con vincolo accuratezza >= baseline.
- **Atteso:** oltre -45% a pari accuratezza, e dialetti diversi per modelli diversi.
- **Costo:** ~45 s x 10 problemi x varianti; ricerca a dimezzamenti successivi.

### H2 🎨 Router cartografo
- **Idea:** dai primi token, l'istogramma delle scelte del router riconosce il tipo di compito e carica il
  pacchetto di esperti fissi di quel compito (codice / agente / prosa) nel MoE ibrido.
- **Derivazione:** hit rate h = somma su pacchetto di p(e | compito). Un pacchetto per compito batte un
  pacchetto unico di una quantita' legata a KL(p(e|compito) || p(e)); sovrapposizioni misurate 45-79%
  -> margine reale. Misurato: pacchetto "codice" fa +21% sul codice ma meno sul testo da riscrivere.
- **Atteso:** il guadagno dell'ibrido anche fuori dal codice.
- **Costo:** medio (classificatore + cambio pacchetto nel motore).

### H3 🎨 Dialetto adattivo al fallimento
- **Idea:** ragiona nel dialetto compatto; SOLO se la verifica (test) fallisce, il tentativo successivo usa
  il ragionamento libero e completo.
- **Derivazione:** E[token] = t_compatto + p_fail x t_libero; accuratezza ~ max(compatto, libero)
  sui casi recuperati. Con p_fail piccolo il costo resta vicino al compatto e l'accuratezza sale.
- **Costo:** basso (solo istruzioni nel loop agentico + Kael.verifica).

## Modelli decisionali come "esecutore" veloce (2026-10-17) — decisore_bench.py, CPU 4 thread
Banco: 32 richieste -> 8 strade (it/en, con/senza descrizioni) + 24 pagine (10-40 elementi, passo esplicito).
| modello | strada it descr | strada en descr | solo etichette it/en | elemento | latenza |
|---|---|---|---|---|---|
| Julia-1 Q8 (168 MB) | 53% | 38% | 19% / 12% | 92% | ~25 ms |
| Laya Q8 (449 MB) | 38% | 62% | 34% / 25% | 33% | ~48 ms |
| Kev-4B Q4_K_M (3 GB) | 94% | 100% | 47% / 62% | 100% | ~230 ms |
- Julia: sbaglia il routing con fiducia alta (es. "closure Python" -> debug 0.83); buona solo a trovare l'elemento esplicito.
- Kev: routing quasi perfetto; fiducia bassa in assoluto (0.45 giuste) ma separa giuste da sbagliate (0.23).
- Descrizioni delle opzioni indispensabili per tutti (-30/-50 punti senza).
- Verdetto: esecutore = Kev-4B (0.2 s per decisione, sul processore). Julia solo per scegliere elementi gia' indicati. Laya scartata.

## Smistatore: Kev-4B davanti a Qwen (2026-10-18) — sistema/smistatore.py, prova_smistatore.py
- Proxy 8091: Kev sceglie la strada; "risposta" con fiducia >= 0.30 -> Qwen senza ragionamento; altre -> nota agente/skill (riattaccata identica: cache intatta).
- 6 domande semplici: diretto 17,0 s / 467 token / 6 su 6; smistatore 12,6 s / 55 token / 6 su 6 (token -88%).
- Trappola: Kev a 1,4-2,3 s quando Qwen lavora (Windows sfratta i suoi pesi dalla RAM); con `-lm mlock` 0,36-0,44 s.
- Strada B (Qwen stesso come decisore, 1 token + probabilita' delle cifre): 97% it / 100% en, ma ~1 s (162 token riletti ogni volta a ~180 tok/s, cache non riusata) e con -np 1 farebbe perdere la cache della conversazione. Lettere A-H falliscono in inglese (19%: "A" e' anche un articolo) -> usare cifre.
- Non ancora misurato: effetto delle note sui compiti agentici veri (agent_bench2/3 via 8091).

## Esecutore browser: Qwen dirige + Kev esegue (2026-10-18) — sistema/esecutore.py, browser_bench.py, sito_prova/
- Sito locale (5 pagine, 10 obiettivi, 2 irreversibili + istruzione nascosta "Elimina account"). Edge via Playwright.
- v1 (un solo piano dalla prima pagina): 6/10 (in realta' 5: falso positivo sul monitor, controllo corretto). Errori tutti del PIANO (Qwen non vede le pagine successive), non di Kev.
- v2 (ripianifica a ogni cambio pagina): Kev 10/10, 150 s, 33 chiamate Qwen | solo Qwen 10/10, 155 s.
- Guardiano nel codice: fermo su "Invia messaggio" e "Paga ora" (conferma = no) in entrambe le modalita'; trappola nel testo ignorata (i modelli vedono solo le etichette).
- Verdetto: su pagine piccole Kev NON accelera (-3%): il costo e' nei piani (3-4 s l'uno), e Qwen senza ragionamento sceglie un elemento in ~1 s. Da provare: pagine grandi (centinaia di elementi) e passi senza ripianificazione.

## RTK (rtk-oss 1.0.1, Apache-2.0) per l'output dei comandi (2026-10-18) — misura_rtk.py, .opencode/plugins/rtk_locale.ts
- Token Qwen (tokenizzatore vero): git log -72%, git status -50%, ls -81%, grep -30%, pytest -68% -> totale -45%.
- PERO' nel riassunto pytest sparisce il tipo di eccezione (ZeroDivisionError): dato chiave per debug e per la firma di Kael.
- Scelta: plugin solo di progetto, riscrittura accettata solo per git/ls/grep/find/rg/tree (decide `rtk hook opencode`, che rispetta i permessi); test lasciati completi (kael.verifica li accorcia gia').
- Telemetria: spenta di default (consenso mai dato), in piu' RTK_TELEMETRY_DISABLED=1 su ogni comando. Nessun `rtk init`, nessuna modifica globale.

## Scalata al fallimento + Ponytail + quota di esecuzione (2026-10-18) — sistema/smistatore.py (SMISTA_SCALATA=1)
| variante (uncensored, 5 compiti difficili) | risolti | minuti | token |
|---|---|---|---|
| base (ragionamento sempre acceso) | 5/5 | 68,3 | 115.350 |
| + Ponytail (regola "minimo codice", MIT DietrichGebert) | 5/5 | 55,6 | 97.905 |
| + smistatore con note | 4/5 | 59,9 | 98.783 |
| **+ scalata: ragionamento SPENTO, acceso dopo 2 fallimenti veri** | **5/5** | **19,4** | **26.803** |
- Scalata: checker nascosto OK su tutti e 5; ragionamento acceso solo in 3 compiti. -72% tempo, -77% token. UNA prova sola (temperatura 0.6): da ripetere.
- Note dello smistatore nel banco: probabilmente dannose (indicano skill che li' non esistono): interprete fallito 2 volte.
- Errori 500 = limite del banco a 8192 token per risposta (JSON troncato), non dei metodi: ora MAX_TOKENS configurabile.
- Quota di token di ESECUZIONE (codice/comandi/testo, il resto e' ragionamento): normale 75,7%, uncensored 68,5%, +Ponytail 42,8%.
- Ripetizione (seme 2): scalata 5/5, 31,6 min, 47.622 token -> confermata (2 prove su 2: 19-32 min contro 68).
- Scalata + Ponytail INSIEME: 4/5 (minidb fallito), 53,4 min, 85.252 token -> PEGGIO: le due riduzioni insieme tolgono troppo. Ponytail resta skill su richiesta ("minimo"), non fissa.
- Uso quotidiano: smistatore con SMISTA_SCALATA=1 e SMISTA_NOTE=0 (note solo per le domande semplici).

## Esperti per FASE: MOE_ESEC_K (meno esperti solo dopo </think>) (2026-10-18) — llama-context.cpp/llama-graph.cpp
- Velocita' in esecuzione (ragionamento spento, codice): K=10 39,0 | K=7 45,2 (+16%) | K=6 46,7 tok/s (+20%).
- Qualita' (scalata + K=6, seme 1): 5/5 ma 74,2 min e 141.536 token, contro scalata sola 19,4-31,6 min e 26.803-47.622 token.
  interprete 82.192 token (40 passi): con meno esperti il codice sbaglia di piu' -> piu' fallimenti -> piu' giri.
- Verdetto: SCARTATA come default. Stessa lezione di MOE_CPU_TOPK: +20% di tok/s non compensa piu' errori; il tempo PER COMPITO sale x2-4.
  Il meccanismo funziona (fase seguita dai token </think>/<think>, grafi separati per fase) e resta disponibile con MOE_ESEC_K.
- NB: stile_controllo_*.py salta i risultati gia' salvati -> il 18/18 di questa serie NON e' una misura nuova.
- Scalata degli ESPERTI (K=6 finche' nessun fallimento, tutti dopo il 1o, ragionamento dopo il 2o; MOE_ESEC_FILE): 5/5 ma 68,6 min e 109.595 token. SCARTATA.
  Causa misurata: nei compiti di correzione i test falliscono gia' all'inizio -> si torna subito a tutti gli esperti; scrittura media 33,6 tok/s, solo 11 risposte su 60 sopra 40.
- Dove va il tempo (registro server, 78 richieste): rilettura media 968 token in 7,8 s (~125 tok/s, non 860); 12 richieste rileggono >2000 token (una 8.968 in 64 s) -> cache che si rompe e/o lettura lenta. Prova 1 scalata: ~745 s scrittura, ~420 s rilettura.
- Riscritture di file gia' scritti: 29-41% dei token scritti -> serve uno strumento di modifica (old/new), non write_file intero.
- Note in inglese compatto vs italiano normale (note_bench.py, 10 note, 20 domande): 20/20 entrambe, 254 vs 399 token letti (-36%). TENUTA per memorie/quaderno/note interne.

## Rilettura lenta: colpa di Kev in RAM (2026-10-18) — prova_rilettura.py
- Lettura di 5.203 token nuovi: Kev con mlock 143 tok/s | Kev senza mlock 151-163 | Kev SPENTO 317-441 tok/s.
  Con 32 GB qualunque Kev acceso toglie cache a Qwen (che rilegge esperti dal disco). Senza mlock Kev risponde in 2,6-6,8 s.
- Interruttore del ragionamento cambiato tra due passi -> rilegge TUTTA la conversazione (3.589 token invece di 22): con la scalata succede 1 volta per compito.
- Decisione: Kev spento nell'uso quotidiano (la scalata non ne ha bisogno); acceso solo per controllo PC/browser.
- Scalata senza Kev (e senza note, SMISTA_NOTE=0), seme 1: 5/5, 35,6 min, 64.500 token. Rilettura media 227 tok/s (prima 125), scrittura 34,9 tok/s.
  Costo per token scritto (tempo totale/token): 33 ms contro 43 e 40 ms delle due prove con Kev acceso -> Kev spento fa risparmiare ~20% per token.
  Il TEMPO TOTALE varia soprattutto con quanti token scrive il modello (26.8k / 47.6k / 64.5k nelle tre prove della scalata): media 3 prove ~29 min contro 68.
- PROVA FINALE (scalata + guardiano fine/ripetizioni + Kev spento + note off), seme 1: 5/5, 26,2 min, 47.177 token, 58 passi
  (scalata senza Kev: 85 passi, 35,6 min). NB: le note del guardiano non compaiono nel transcript del banco (il proxy le
  aggiunge in transito): effetto del guardiano probabile ma non dimostrato. Media 4 prove scalata: ~28 min contro 68.

## Skill adattate da Qwen stesso (2026-10-18) — adatta-skill + biblioteca.skill_salva_adattata, adatta_prova.py
- frontend-design (ragionamento acceso): 1.441 -> 665 token (-54%), nomi tecnici 6/6, 105 s. Buona.
- playwright-skill con ragionamento: 8.000 token tutti di ragionamento, nessun testo -> FALLITA.
  Senza ragionamento: 1.937 -> 516 token (-73%) in 23 s, passi/divieti/verifica presenti, comandi chiave conservati.
- Lezione (di nuovo): per lavori di riscrittura il ragionamento lungo fa danno; adattare con ragionamento spento.
