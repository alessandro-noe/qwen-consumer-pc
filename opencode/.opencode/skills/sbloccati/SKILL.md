---
name: sbloccati
description: Quando sei bloccato (stesso errore ripetuto, tentativi che non portano a niente, Kael ha detto STOP): fermati, ricapitola e cambia strategia invece di riprovare uguale.
metadata:
  origine: agente-locale, ispirata a ECC skills/agent-introspection-debugging (MIT, (c) 2026 Affaan Mustafa)
---
# Sbloccarsi

1. Fermati. Scrivi in 3 righe: obiettivo, cosa hai provato, l'errore esatto che si ripete.
2. Rileggi l'errore come se fosse la prima volta: cosa dice DAVVERO (file, riga, tipo)?
3. Verifica le ipotesi date per scontate (il file giusto? il comando giusto? l'ambiente giusto?).
4. Cambia approccio: test piu' piccolo, stampa di debug, esploratore su graphify.
5. Se Kael ha detto STOP o dopo 3 tentativi diversi falliti: chiedi all'utente, con il riassunto del punto 1.
