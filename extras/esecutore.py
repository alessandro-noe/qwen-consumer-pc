"""
esecutore.py — Qwen DIRIGE, Kev ESEGUE nel browser.

  1. Qwen legge l'obiettivo e gli elementi della prima pagina e scrive il piano: una lista di passi
     {"azione": "clicca"|"scrivi"|"scegli", "bersaglio": "...", "valore": "..."}.
  2. A ogni passo il browser elenca gli elementi della pagina; Kev sceglie quale (una passata, ~0,3 s).
  3. Fiducia di Kev sotto SOGLIA -> decide Qwen per quel passo (vede solo gli elementi, non il testo).
  4. Guardiano NEL CODICE: un clic su un elemento irreversibile (invia, paga, elimina...) chiede
     conferma all'utente; senza conferma si ferma. Nessun modello puo' scavalcarlo.
  5. Il testo delle pagine non arriva mai ai modelli: solo etichette degli elementi -> un'istruzione
     scritta nella pagina non puo' diventare un comando.

Modalita' "solo_qwen" (confronto): Qwen sceglie ogni passo da solo, come un agente classico.
"""
import json, re, time, urllib.request

QWEN = "http://127.0.0.1:8090"
KEV = "http://127.0.0.1:9931"
SOGLIA = 0.30
IRREVERSIBILE = re.compile(r"\b(invia|paga|acquista|compra|elimina|cancella account|conferma ordine|iscriviti|"
                           r"send|pay|buy|delete|submit|confirm|subscribe)\b", re.I)

ELEMENTI_JS = """() => {
  const out = []; let i = 0;
  for (const el of document.querySelectorAll('a,button,input,select,textarea,[role=button]')) {
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const id = 'e' + (++i); el.setAttribute('data-ag', id);
    const tag = el.tagName.toLowerCase();
    const ruolo = tag === 'a' ? 'link' : tag === 'input' ? (el.type === 'checkbox' ? 'checkbox' : 'campo') :
                  tag === 'textarea' ? 'campo' : tag === 'select' ? 'menu' : 'pulsante';
    let nome = el.getAttribute('aria-label') || el.innerText || el.placeholder || el.name || '';
    nome = nome.trim().replace(/\\s+/g, ' ').slice(0, 60);
    let extra = '';
    if (tag === 'select') extra = ' opzioni: ' + [...el.options].map(o => o.text).join(', ');
    if (ruolo === 'checkbox') extra = el.checked ? ' (attivo)' : ' (spento)';
    out.push([id, ruolo, nome, extra]);
  }
  return out; }"""


def _post(url, body, timeout=300):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def qwen(prompt, max_tokens=800):
    r = _post(f"{QWEN}/v1/chat/completions", {"messages": [{"role": "user", "content": prompt}], "temperature": 0,
              "max_tokens": max_tokens, "chat_template_kwargs": {"enable_thinking": False}})
    return r["choices"][0]["message"]["content"] or ""


def json_da(testo):
    m = re.search(r"(\[.*\]|\{.*\})", testo, re.S)
    return json.loads(m.group(1)) if m else None


def elementi(pagina):
    return pagina.evaluate(ELEMENTI_JS)


def descrivi(els):
    return "\n".join(f"{i} {r} '{n}'{x}" for i, r, n, x in els)


def pianifica(obiettivo, els, fatto=""):
    p = qwen(f"Sei il pianificatore di un agente che usa un sito web. Obiettivo dell'utente: {obiettivo}\n"
             + (f"Gia' fatto:\n{fatto}" if fatto else "")
             + f"Elementi della pagina ATTUALE:\n{descrivi(els)}\n\n"
             "Scrivi i prossimi passi come lista JSON, solo per elementi di QUESTA pagina; se un passo apre "
             "un'altra pagina fermati li' (dopo vedrai la pagina nuova). Ogni passo: "
             '{"azione": "clicca"|"scrivi"|"scegli", "bersaglio": "nome dell\'elemento com\'e\' scritto nella lista", "valore": "testo o opzione, solo per scrivi/scegli"}.\n'
             "Caselle da attivare o disattivare: clicca. Se l'obiettivo e' gia' raggiunto rispondi []. Rispondi solo con il JSON.")
    piano = json_da(p)
    return piano if isinstance(piano, list) else []


def scegli_kev(passo, els):
    istr = f"Prossimo passo: {passo['azione']} {passo['bersaglio']}" + (f" (valore: {passo['valore']})" if passo.get("valore") else "") + ". Quale elemento?"
    r = _post(f"{KEV}/v1/systemone", {"state": "Elementi della pagina:\n" + descrivi(els),
              "questions": {"q": {"type": "choice", "instructions": istr,
                                  "criteria": {i: f"{r_} '{n}'{x}" for i, r_, n, x in els}}}})
    a = r["answers"]["q"]
    return a["choice"], float(a["confidence"])


def scegli_qwen(obiettivo, passo, els, storia=""):
    t = qwen(f"Obiettivo: {obiettivo}\n{storia}Passo da fare: {json.dumps(passo, ensure_ascii=False)}\n"
             f"Elementi della pagina:\n{descrivi(els)}\nRispondi solo con l'id dell'elemento giusto (es. e3).", 20)
    m = re.search(r"\be\d+\b", t)
    return m.group(0) if m else None


def agisci(pagina, eid, passo, els, conferma):
    """Esegue il passo. Ritorna 'ok' o 'fermato' (guardiano)."""
    info = next((e for e in els if e[0] == eid), None)
    if info is None:
        return "id_sconosciuto"
    loc = pagina.locator(f"[data-ag='{eid}']")
    if passo["azione"] == "clicca" or info[1] in ("pulsante", "link", "checkbox"):
        if info[1] != "checkbox" and IRREVERSIBILE.search(info[2]) and not conferma(info[2]):
            return "fermato"
        loc.click()
    elif passo["azione"] == "scegli":
        loc.select_option(label=passo.get("valore", ""))
    else:
        loc.fill(passo.get("valore", ""))
    pagina.wait_for_load_state()
    return "ok"


def esegui(pagina, obiettivo, modo="kev", conferma=lambda nome: False, log=print, max_passi=15, max_piani=8):
    """modo: 'kev' (Qwen pianifica a ogni pagina, Kev esegue i passi) | 'solo_qwen' (Qwen sceglie anche ogni passo)."""
    stat = {"passi": 0, "kev": 0, "qwen_fallback": 0, "qwen_chiamate": 0, "piani": 0, "fermato": None, "esito": "finito"}
    t0 = time.time()
    storia = ""
    while stat["piani"] < max_piani and stat["passi"] < max_passi:
        piano = pianifica(obiettivo, elementi(pagina), storia); stat["piani"] += 1; stat["qwen_chiamate"] += 1
        log(f"  piano {stat['piani']}: {json.dumps(piano, ensure_ascii=False)[:250]}")
        if not piano:
            break
        for passo in piano:
            if stat["passi"] >= max_passi:
                break
            url = pagina.url
            els = elementi(pagina)
            if modo == "kev":
                eid, fid = scegli_kev(passo, els)
                if fid < SOGLIA:
                    eid2 = scegli_qwen(obiettivo, passo, els, storia); stat["qwen_fallback"] += 1; stat["qwen_chiamate"] += 1
                    log(f"  Kev incerto ({fid:.2f} su {eid}) -> Qwen {eid2}")
                    eid = eid2 or eid
                else:
                    stat["kev"] += 1
            else:
                eid = scegli_qwen(obiettivo, passo, els, storia); stat["qwen_chiamate"] += 1
            stat["passi"] += 1
            esito = agisci(pagina, eid, passo, els, conferma)
            nome = next((e[2] for e in els if e[0] == eid), "?")
            log(f"  {passo.get('azione','?'):7s} {str(passo.get('bersaglio',''))[:35]:35s} -> {eid} '{nome}' [{esito}]")
            storia += f"- {passo.get('azione')} '{nome}'" + (f" = {passo['valore']}" if passo.get("valore") else "") + "\n"
            if esito == "fermato":
                stat["fermato"], stat["esito"] = nome, "fermato_per_conferma"
                stat["secondi"] = round(time.time() - t0, 1)
                return stat
            if pagina.url != url:  # pagina nuova: si ripianifica vedendola
                break
    stat["secondi"] = round(time.time() - t0, 1)
    return stat
