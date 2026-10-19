---
name: minimo
description: Prima di scrivere codice: la soluzione piu' piccola che risolve TUTTO il compito, senza extra. Usala sempre quando devi scrivere o modificare codice.
metadata:
  origine: agente-locale, ridotta da Ponytail (MIT, (c) 2026 DietrichGebert, github.com/DietrichGebert/ponytail). Misurata sui 5 compiti difficili: -15% token, -19% tempo, 5/5.
---
# Il minimo codice che funziona

Prima leggi il codice che il compito tocca ed elenca ogni punto che la modifica deve raggiungere (chiamanti, test, configurazione).

Poi prendi la PRIMA opzione che funziona davvero:
1. Serve davvero? Salta funzioni e opzioni che nessuno ha chiesto (dillo in una riga).
2. Esiste gia' nel progetto (funzione, modulo, schema)? Usala come la usa il codice vicino.
3. Libreria standard o dipendenza gia' installata? Usala. Mai una dipendenza nuova per poche righe.
4. Basta una riga chiara? Una riga.
5. Altrimenti: il minimo codice che funziona.

- Niente astrazioni, wrapper, opzioni o codice "per dopo" non richiesto. Togliere batte aggiungere.
- Bug: trova tutti i chiamanti, correggi la causa una volta sola.
- Logica nuova non banale: un piccolo test o assert.
- MAI tagliare: validazione dei dati in ingresso, gestione degli errori che evita perdite di dati, sicurezza, cio' che l'utente ha chiesto.

Alla fine, una riga: cosa hai saltato o non verificato.
