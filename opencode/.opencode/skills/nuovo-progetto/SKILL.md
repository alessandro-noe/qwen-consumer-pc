---
name: nuovo-progetto
description: Capire in fretta un progetto sconosciuto (struttura, punti d'ingresso, come si lancia e come si testa) usando la mappa di graphify.
metadata:
  origine: agente-locale, ispirata a ECC skills/codebase-onboarding (MIT, (c) 2026 Affaan Mustafa)
---
# Capire un progetto nuovo

1. Se manca la mappa: `graphify update .` (solo codice, nessun modello serve).
2. Leggi `graphify-out/GRAPH_REPORT.md`: comunita' principali e nodi piu' collegati.
3. Trova i punti d'ingresso (main, server, CLI) e il comando dei test (README, pyproject, package.json).
4. Riassumi in 10 righe: cosa fa, moduli principali, come si lancia, come si testa, dove sono i rischi.
