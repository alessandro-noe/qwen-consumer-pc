> Versione italiana della guida. Riferimento principale (inglese): [INSTALL.md](../../INSTALL.md).

# Guida d'installazione (Windows)

Tempo: ~30 minuti + il download dei modelli (~66 GB). Tutto gira in locale: niente abbonamenti, niente dati inviati fuori.

## 0. Cosa serve

| | Minimo provato |
|---|---|
| Scheda video | NVIDIA 16 GB (provato: RTX 4080 SUPER), driver aggiornato |
| RAM | 32 GB (con 64 GB va più veloce) |
| Disco | ~110 GB liberi su SSD (il modello legge una tabella dal disco mentre lavora: meglio NVMe) |
| Programmi | Python 3.11+, Node.js (per OpenCode), Git |

## 1. Scarica questo repository

```
git clone https://github.com/alessandro-noe/qwen-consumer-pc
cd qwen-consumer-pc
pip install -r requirements.txt
```

## 2. llama.cpp (il motore)

Dalle release ufficiali di llama.cpp scarica la versione **Windows x64 con CUDA** (provata: build **11669**, commit `620d2225c`)
e, se la release la fornisce a parte, anche l'archivio con le librerie **cudart**. Estrai tutto nella cartella `llama\`
del repository, in modo che esista `llama\llama-server.exe`.

> Versioni più nuove dovrebbero funzionare; servono le opzioni `-lm mmap` e `-lzm on` (lettura "pigra" della tabella dal disco).

## 3. Il modello (scegli una o entrambe)

| Versione | Repository Hugging Face | Cartella dove metterla |
|---|---|---|
| Normale (~39 tok/s) | `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`, sottocartella `Q2_0` | `models\flashnext_q2_0\Q2_0\` |
| Senza censure (~35 tok/s) | `SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF`, sottocartella `Q2_0` | `models\flashnext_q2_0_abl\Q2_0\` |

Ogni versione sono **due file** (`...-00001-of-00002.gguf` ~38 GB e `...-00002-of-00002.gguf` 28,8 GB).
Il secondo (la tabella) è **identico** nelle due versioni: se le vuoi entrambe, scaricalo una volta e crea un collegamento
(`mklink /H nuovo esistente`) invece di occupare altri 28,8 GB.

Opzionali:
- **Kev-4B** (modello decisionale per la biblioteca di skill e il browser): `ggml-org/Kev-4B-GGUF`, file `Kev-4B-Q4_K_M.gguf` → `models\decisionali\`.
  Con 32 GB di RAM tienilo **spento** nell'uso normale: acceso rallenta la lettura del modello grande di 2-3 volte (misurato).
- **Vista** (il modello legge le immagini): `mmproj-Qwen3.8-Flash-Next-BF16.gguf` dal repository di ISTA-DASLab → `models\flashnext_vista\`.

Controlla le impronte SHA-256 pubblicate sulle pagine dei file.

## 4. OpenCode (l'agente)

```
npm i -g @opencode/cli
```
(provato con la versione 2.0.32)

## 5. Installazione

```
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```
Lo script:
1. controlla che ci siano `llama\llama-server.exe` e almeno un modello;
2. crea `opencode.json` con i percorsi giusti per il tuo PC (modelli, Kael, biblioteca di skill, regole);
3. **ti chiede** se avviare lo smistatore insieme a Windows (consigliato: non usa la scheda video finché non chiedi qualcosa).

## 6. Uso

1. Avvia lo smistatore: `scripts\start_proxy.cmd` (se non hai scelto l'avvio automatico).
2. Apri un terminale nella cartella del repository e scrivi `opencode`.
3. Nella lista dei modelli cerca **"flash"**: "Flash-Next 125B uncensored" (senza censure) o "normal".
4. Scrivi. La prima volta il modello si accende da solo (~40 s); la prima risposta di una conversazione nuova legge il
   prompt iniziale (~30-90 s), poi è veloce.
5. Dopo 30 minuti senza uso il modello si spegne e libera scheda video e RAM.

Qualsiasi altro agente o programma compatibile OpenAI può usare `http://127.0.0.1:8091/v1` (modelli `flashnext-uncensored`, `flashnext-normale`).

## 7. Opzioni

| Variabile | Cosa fa | Predefinito |
|---|---|---|
| `SMISTA_SCALATA=1` | ragionamento spento, acceso dopo 2 errori veri | acceso dallo script di avvio |
| `SMISTA_SCALA_DOPO` | dopo quanti errori accendere il ragionamento | 2 |
| `SMISTA_GUARDIA=0` | spegne il guardiano (ripetizioni, ricerche a raffica, "chiudi") | acceso |
| `SMISTA_SPEGNI_MIN` | minuti senza uso prima di spegnere il modello (0 = mai) | 30 |
| `BIBLIOTECA_RADICI` | altre cartelle di skill da indicizzare, separate da `;` | — |
| `LLAMA_SERVER` | percorso di `llama-server.exe` | `llama\llama-server.exe` |
| `RTK_EXE` | percorso di `rtk.exe` (rtk-oss) per accorciare l'output di git/ls/grep | nel PATH |

## 8. Rifare le misure sul tuo PC

```
python benchmarks\velocita_fase.py prova            # token/s
python benchmarks\agent_bench3.py mio_pc 8091       # 5 compiti difficili, con controllo nascosto
```
Risultati in `benchmarks\runs\`. Se li condividi (issue o discussione), aiuti a capire come va su altre schede e altra RAM.

## Problemi comuni

- **Il primo messaggio è lentissimo**: è la lettura del prompt iniziale di OpenCode a freddo. Nelle conversazioni successive
  resta in memoria. Non tenere acceso Kev o altri modelli: rubano RAM alla cache del disco.
- **Errore di memoria della scheda video**: chiudi giochi/programmi che usano la GPU, oppure riduci il contesto (`-c 32768`).
- **Il modello non compare in OpenCode**: apri OpenCode *dentro* la cartella del repository (lì c'è `opencode.json`).
