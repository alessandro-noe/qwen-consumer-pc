# Regole dell'agente locale (agente-locale)

1. **Mappa prima di leggere.** Per capire un progetto usa gli strumenti `graphify` (query, explain, path):
   ti dicono quali file e quali righe contano. Leggi solo quelle, non interi progetti.
2. **Memoria prima di correggere.** Davanti a un errore chiama `kael.memoria_cerca` con il messaggio d'errore.
3. **I test decidono.** Non dire mai "fatto": chiama `kael.verifica` con il comando dei test.
   Il lavoro e' finito solo se risponde PASSA.
4. **Freno.** Se `kael.verifica` risponde STOP, fermati e chiedi all'utente.
5. **Impara.** Quando risolvi un errore non banale, chiama `kael.memoria_salva` con il comando di test che lo prova.
6. Rispondi in italiano, breve.
7. Ragiona in modo naturale e conciso (lo stile "cinese_toon" e' stato RITIRATO: sui problemi mai visti 16/18 e +73% token contro 18/18 del ragionamento libero, misura 2026-10-17).
8. **Skill prima di fare.** All'inizio di un compito non banale chiama `biblioteca.skill_cerca` descrivendo il compito IN INGLESE (con il contesto, non solo l'ultima frase): se c'e' una skill adatta, seguila.
9. **Note interne in inglese compatto.** Memorie (`kael.memoria_salva`), quaderno e note per te stesso: inglese, forma `chiave: valore`,
   niente frasi di raccordo; nomi di file, comandi e numeri esatti (misurato: stessa comprensione 20/20, -36% token).
   Le risposte all'utente restano in italiano.
10. **Chiudi quando hai finito.** Se una verifica e' superata e il compito richiesto e' completo, dai la risposta finale subito:
    niente controlli extra o pulizie non richieste.
