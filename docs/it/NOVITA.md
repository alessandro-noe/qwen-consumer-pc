# Cosa è nuovo e cosa no (confronto onesto con il lavoro di altri)

Ricerca fatta il 2026-10-18. "Nostro" vuol dire "non abbiamo trovato niente di uguale", non "sicuramente mai fatto".
Tutti i nostri numeri vengono da **pochi compiti** (5 difficili, 12 normali, 18 di controllo): sono risultati **preliminari**.

## 1. Scalata al fallimento (ragionamento acceso solo dopo errori veri) — in parte nota
- Già noto: passare a una modalità "lenta" quando l'agente si blocca o fallisce — **SwiftSage** (Lin et al., NeurIPS 2023,
  https://arxiv.org/abs/2305.17390), con due modelli diversi e in ambienti testuali.
- Proposta per agenti che programmano in *Prompt-Induced Waste in Coding Agents* (arXiv 2608.01347, 2026,
  https://arxiv.org/html/2608.01347): la "scalata guidata dalle prove" vi risulta **non misurabile** perché il loro baseline non falliva mai.
- Interruttori del ragionamento esistono (es. `enable_thinking` di Qwen) ma si usano a mano.
- **Qui di nuovo:** un solo modello, l'interruttore lo gira un proxy contando i fallimenti **reali** nei risultati degli strumenti
  (test, codici d'uscita, errori di PowerShell/Python), e un **risultato positivo misurato**: 5/5 compiti difficili in
  ~28 minuti di media (4 prove) contro 68 con il ragionamento sempre acceso.

## 2. Router "democratico" e "token più veloci, lavoro più lento" — in parte nota
- Già noto: ridurre gli esperti attivi peggiora la qualità — *Training-Free Halving of Activated Experts* (arXiv 2609.04575),
  *Harder Tasks Need More Experts* (https://arxiv.org/abs/2403.07652), *Not All Experts are Equal* (https://arxiv.org/abs/2402.14800).
- **Qui di nuovo:** su un MoE da 512 esperti / top-10, i primi 6 esperti portano solo il ~76% del peso (mediana su 56.304 scelte);
  e la misura end-to-end che 6-7 esperti invece di 10 danno +16-25% di token/s ma **2-4 volte più tempo per finire un compito**.

## 3. 125B MoE su 16 GB di scheda video + 32 GB di RAM — metodo noto, numeri nuovi
- Il metodo (esperti in RAM, tabella per strato letta dal disco con mmap) è documentato da altri utenti di llama.cpp
  (es. 24 GB VRAM + 32 GB RAM: 25-27 token/s; 32 GB VRAM + 96 GB RAM: 52 token/s).
- **Qui:** ~39 token/s con 16 GB + 32 GB, senza tagliare il modello. Non abbiamo trovato numeri pubblicati per questa combinazione.

## 4. Un secondo modello acceso rallenta il primo — meccanismo noto, misura pratica
- Noto: la pressione sulla RAM svuota la cache del disco (https://justine.lol/mmap/).
- **Qui:** un modello decisionale da 4B tenuto in RAM fa leggere il modello grande 2-3 volte più piano (143 contro 317-441 token/s).

## 5. Kael: memoria che accetta solo correzioni dimostrate da un test — in gran parte nota
- *What Should Coding Agents Remember? Selective Retrieval of Validated Repair Experience* (NeurIPS 2026) e lavori sull'astensione
  della memoria. La nostra differenza (il test viene eseguito al momento del salvataggio) è piccola.

## Idee prese da altri (con licenza) e adattate
Guardiano (ripetizioni, "chiudi quando i test passano", ricerche a raffica): ispirato a **Hermes Agent** (MIT).
Regola "minimo codice": **Ponytail** (MIT). Profilo minimo agenti/skill: **ECC** (MIT). Filtro dell'output dei comandi: **RTK** (rtk-oss, Apache-2.0).
