---
name: verifica
description: Ciclo di verifica prima di dire che un lavoro e' finito (test, lint, controllo delle modifiche). Usala sempre a fine compito.
metadata:
  origine: agente-locale, ridotta da ECC skills/verification-loop (MIT, (c) 2026 Affaan Mustafa)
---
# Verifica prima di "fatto"

1. **Test**: lancia il comando dei test con `kael.verifica`. Deve rispondere PASSA.
2. **Errori statici** (se il progetto li ha): lint / type-check. Correggi solo cio' che hai toccato.
3. **Modifiche**: rileggi le differenze. Niente file di debug, niente segreti, niente test indeboliti.
4. **Esecuzione reale** quando possibile: lancia il programma o lo script e guarda l'output vero.
5. **Report finale** in 3 righe: cosa e' cambiato, comando che lo prova, esito (PASSA / cosa manca).

Mai "fatto" senza il punto 1 a PASSA.
