"""
agent_bench2.py — banco AGENTICO piu' difficile, uguale per tutti i modelli.

Stesso loop di autonomy_bench.py (strumenti write_file/read_file/run_python/finish
+ list_files), ma:
  - parla con llama-server (endpoint OpenAI /v1/chat/completions con tool-calling),
    cosi' 27B e Flash-Next girano nello STESSO motore;
  - RAGIONAMENTO ACCESO (impostazioni consigliate da Qwen: temp 0.6, top_p 0.95, top_k 20);
  - compiti su progetti con PIU' FILE gia' presenti: il modello riceve il SINTOMO,
    deve esplorare, trovare il bug, correggere, eseguire i test;
  - verifica finale con un CHECKER NASCOSTO (casi in piu' dei test visibili):
    passa solo se il progetto funziona davvero.

Uso: python agent_bench2.py <etichetta> <porta> [id_compito ...]
"""
from __future__ import annotations
import json, sys, tempfile, time, urllib.request
from pathlib import Path
from sandbox import run_python
from mcp_bench import TOOLS as BASE_TOOLS, Workspace

TOOLS = [t for t in BASE_TOOLS if t["function"]["name"] != "calc"] + [
    {"type": "function", "function": {
        "name": "list_files", "description": "Elenca i file del workspace.",
        "parameters": {"type": "object", "properties": {}}}}]

SYSTEM = ("Sei un agente di programmazione autonomo che lavora in una cartella di progetto. "
          "Strumenti: list_files, read_file, write_file (riscrive il file intero), run_python, finish. "
          "Esplora prima i file, trova la causa, correggi, poi ESEGUI i test per verificarlo. "
          "Non modificare i file di test. Chiama `finish` solo quando i test passano davvero.")
# stile di ragionamento opzionale (vincitore del test stile_ragionamento.py: cinese_toon)
import os as _os
STILI = {"cinese_toon": " Think only in TOON notation (`key: value`, arrays like `edge_cases[3]: a,b,c`, tables like "
                        "`tests[2]{input,expected}:` then one row per line), keys goal, edge_cases, steps, tests, check. "
                        "所有值请用非常简洁的中文书写。",
         # ridotta da Ponytail (MIT, (c) 2026 DietrichGebert, github.com/DietrichGebert/ponytail)
         "ponytail": " Be a lazy senior developer: solve the whole task with the least new code. Before writing, read the "
                     "code the task touches and list every place the change must reach. Take the first option that fully "
                     "works: skip what nobody asked for; reuse what the codebase already has; then the standard library; "
                     "then one obvious line; otherwise the minimum code that works. No abstraction, wrapper, option or "
                     "'for later' code nobody asked for. Bug fix: fix the root cause once. New non-trivial logic gets one "
                     "small check. Never cut validation, error handling that prevents data loss, security, or anything asked."}
SYSTEM += STILI.get(_os.environ.get("STILE", ""), "")

# ---------------------------------------------------------------- compiti
T = []

T.append(dict(id="carrello", goal="I test in test_cart.py falliscono: il totale del carrello con lo sconto e' sbagliato. Trova e correggi il bug (non toccare i test).",
seed={
"pricing.py": '''def apply_discount(price, pct):
    """Prezzo scontato di pct percento, arrotondato a 2 decimali."""
    return round(price * (1 - pct / 100), 2)
''',
"cart.py": '''from pricing import apply_discount

class Cart:
    def __init__(self, discount_pct=0):
        self.items = []
        self.discount_pct = discount_pct

    def add(self, name, price, qty=1):
        self.items.append((name, apply_discount(price, self.discount_pct), qty))

    def total(self):
        subtotal = sum(p * q for _, p, q in self.items)
        return apply_discount(subtotal, self.discount_pct)
''',
"test_cart.py": '''from cart import Cart
c = Cart(discount_pct=10)
c.add("libro", 20.0, 2)
c.add("penna", 5.0)
assert c.total() == 40.5, c.total()
print("OK")
'''},
checker='''from cart import Cart
c = Cart(discount_pct=10); c.add("libro", 20.0, 2); c.add("penna", 5.0)
assert c.total() == 40.5, c.total()
c = Cart(); c.add("a", 9.99, 3); assert round(c.total(), 2) == 29.97, c.total()
c = Cart(50); c.add("x", 10.0); c.add("y", 1.0, 4); assert round(c.total(), 2) == 7.0, c.total()
print("OK")'''))

T.append(dict(id="durata", goal="parse_duration in durations.py capisce solo ore e minuti. Deve accettare anche giorni (d) e secondi (s), spazi tra le parti (es. '2d 4h'), e alzare ValueError per input non validi (vuoto, unita' sconosciute, numeri mancanti). Ritorna i secondi totali. Aggiorna anche i test.",
seed={
"durations.py": '''import re

def parse_duration(text):
    """'1h30m' -> 5400 secondi."""
    total = 0
    for num, unit in re.findall(r"(\\d+)([hm])", text):
        total += int(num) * (3600 if unit == "h" else 60)
    return total
''',
"test_durations.py": '''from durations import parse_duration
assert parse_duration("1h30m") == 5400
print("OK")
'''},
checker='''from durations import parse_duration
assert parse_duration("1h30m") == 5400
assert parse_duration("45s") == 45
assert parse_duration("2d 4h") == 2*86400 + 4*3600
assert parse_duration("1d2h3m4s") == 86400+7200+180+4
for bad in ["", "abc", "10x", "h", "5h junk", "3"]:
    try:
        parse_duration(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("nessun ValueError per %r" % bad)
print("OK")'''))

T.append(dict(id="lru", goal="Implementa la classe LRUCache in lru.py (oggi e' solo uno scheletro): get(key) ritorna il valore o -1 e rende la chiave 'recente'; put(key, value) inserisce/aggiorna e, se si supera la capacita', elimina la chiave usata meno di recente; len(cache) ritorna il numero di elementi. Scrivi dei test ed eseguili.",
seed={"lru.py": '''class LRUCache:
    def __init__(self, capacity):
        raise NotImplementedError
'''},
checker='''from lru import LRUCache
c = LRUCache(2)
c.put(1, 1); c.put(2, 2)
assert c.get(1) == 1
c.put(3, 3)
assert c.get(2) == -1
c.put(4, 4)
assert c.get(1) == -1 and c.get(3) == 3 and c.get(4) == 4
c.put(3, 30); assert c.get(3) == 30 and len(c) == 2
c.put(5, 5); assert c.get(4) == -1 and len(c) == 2
z = LRUCache(1); z.put("a", 1); z.put("b", 2); assert z.get("a") == -1 and z.get("b") == 2
print("OK")'''))

T.append(dict(id="report", goal="Eseguendo report.py il programma va in errore. Deve leggere sales.csv e scrivere report.json con, per ogni regione, la media delle vendite arrotondata a 2 decimali, ignorando le righe con valore vuoto o non numerico; le regioni senza valori validi non compaiono. Sistemalo ed eseguilo cosi' che report.json sia corretto.",
seed={
"sales.csv": "region,amount\nnord,100\nsud,50\nnord,200\ncentro,\nsud,25.5\nnord,abc\ncentro,n/a\nisole,10\n",
"report.py": '''import csv, json

def build():
    sums, counts = {}, {}
    with open("sales.csv") as f:
        for row in csv.DictReader(f):
            r = row["region"]
            sums[r] = sums.get(r, 0) + float(row["amount"])
            counts[r] = counts.get(r, 0) + 1
    return {r: sums[r] / counts[r] for r in sums}

if __name__ == "__main__":
    json.dump(build(), open("report.json", "w"), indent=1)
'''},
checker='''import json, subprocess, sys
open("sales.csv","w").write("region,amount\\nnord,100\\nsud,50\\nnord,200\\ncentro,\\nsud,25.5\\nnord,abc\\ncentro,n/a\\nisole,10\\n")
subprocess.run([sys.executable, "report.py"], check=True)
d = json.load(open("report.json"))
assert d == {"nord": 150.0, "sud": 37.75, "isole": 10.0}, d
open("sales.csv","w").write("region,amount\\na,1\\na,2\\nb,\\n")
subprocess.run([sys.executable, "report.py"], check=True)
d = json.load(open("report.json")); assert d == {"a": 1.5}, d
print("OK")'''))

T.append(dict(id="calcolatrice", goal="La calcolatrice in calc.py da' risultati sbagliati: per esempio evaluate('10-3-2') ritorna 9 invece di 5, e non accetta il meno unario come in '-3+5' o '2*-4'. Correggi il parser (precedenza e associativita' corrette per + - * /, parentesi, meno unario).",
seed={
"tokens.py": '''import re

def tokenize(s):
    return re.findall(r"\\d+\\.?\\d*|[-+*/()]", s.replace(" ", ""))
''',
"calc.py": '''from tokens import tokenize

def evaluate(s):
    toks = tokenize(s)
    val, rest = _expr(toks)
    if rest:
        raise ValueError("token in eccesso: %r" % rest)
    return val

def _expr(t):
    left, t = _term(t)
    if t and t[0] in "+-":
        op = t[0]
        right, t = _expr(t[1:])
        left = left + right if op == "+" else left - right
    return left, t

def _term(t):
    left, t = _atom(t)
    if t and t[0] in "*/":
        op = t[0]
        right, t = _term(t[1:])
        left = left * right if op == "*" else left / right
    return left, t

def _atom(t):
    if t[0] == "(":
        v, t = _expr(t[1:])
        return v, t[1:]
    return float(t[0]), t[1:]
''',
"test_calc.py": '''from calc import evaluate
assert evaluate("2+3*4") == 14
assert evaluate("10-3-2") == 5, evaluate("10-3-2")
print("OK")
'''},
checker='''from calc import evaluate
cases = {"2+3*4": 14, "10-3-2": 5, "100/10/5": 2, "2*(3+4)": 14, "-3+5": 2, "2*-4": -8,
         "-(2+3)": -5, "8-2*3-1": 1, "(1+2)*(3-5)/2": -3, "1.5+2.5": 4, "--4": 4}
for e, v in cases.items():
    r = evaluate(e); assert abs(r - v) < 1e-9, (e, r)
print("OK")'''))

T.append(dict(id="banca", goal="In bank.py, se un trasferimento fallisce (conto destinatario inesistente, importo non positivo o fondi insufficienti) i soldi spariscono o i saldi cambiano lo stesso. Rendi transfer atomico: in caso di errore deve alzare l'eccezione giusta (KeyError per conto inesistente, ValueError per importo non positivo, InsufficientFunds per fondi insufficienti) senza cambiare nessun saldo.",
seed={
"bank.py": '''class InsufficientFunds(Exception):
    pass

class Bank:
    def __init__(self):
        self.balances = {}

    def open(self, name, amount=0):
        self.balances[name] = amount

    def withdraw(self, name, amount):
        self.balances[name] -= amount
        if self.balances[name] < 0:
            raise InsufficientFunds(name)

    def deposit(self, name, amount):
        self.balances[name] += amount

    def transfer(self, src, dst, amount):
        self.withdraw(src, amount)
        self.deposit(dst, amount)
'''},
checker='''from bank import Bank, InsufficientFunds
b = Bank(); b.open("a", 100); b.open("b", 10)
b.transfer("a", "b", 30); assert b.balances == {"a": 70, "b": 40}
for args, exc in [(("a", "zzz", 10), KeyError), (("zzz", "a", 10), KeyError),
                  (("a", "b", 0), ValueError), (("a", "b", -5), ValueError),
                  (("b", "a", 41), InsufficientFunds)]:
    before = dict(b.balances)
    try:
        b.transfer(*args)
    except exc:
        pass
    else:
        raise AssertionError("nessuna eccezione %s per %s" % (exc.__name__, args))
    assert b.balances == before, (args, b.balances)
b.transfer("b", "a", 40); assert b.balances == {"a": 110, "b": 0}
print("OK")'''))

T.append(dict(id="config", goal="merge_config in config.py deve unire due configurazioni in modo PROFONDO: i dizionari annidati si uniscono ricorsivamente, le liste si concatenano (prima base poi override), gli altri valori dell'override vincono. Non deve modificare i dizionari in ingresso. Oggi fa un merge superficiale. Correggilo e scrivi test.",
seed={"config.py": '''def merge_config(base, override):
    out = base
    out.update(override)
    return out
'''},
checker='''import copy
from config import merge_config
base = {"db": {"host": "x", "port": 1, "opts": {"a": 1}}, "tags": ["a"], "debug": False}
over = {"db": {"port": 2, "opts": {"b": 2}}, "tags": ["b"], "debug": True, "new": 1}
b0, o0 = copy.deepcopy(base), copy.deepcopy(over)
r = merge_config(base, over)
assert r == {"db": {"host": "x", "port": 2, "opts": {"a": 1, "b": 2}}, "tags": ["a", "b"], "debug": True, "new": 1}, r
assert base == b0 and over == o0, "input modificati"
r["db"]["opts"]["a"] = 99; assert base["db"]["opts"]["a"] == 1, "condivide oggetti con base"
assert merge_config({"a": {"x": 1}}, {"a": 5}) == {"a": 5}
assert merge_config({}, {}) == {}
print("OK")'''))

T.append(dict(id="limitatore", goal="Il TokenBucket in ratelimit.py (rate = gettoni al secondo, capacity = massimo) si comporta male: dopo una lunga pausa concede piu' richieste della capacita', e con rate frazionari non ricarica mai. Correggi la ricarica. L'orologio e' iniettabile (parametro clock) per i test.",
seed={
"ratelimit.py": '''import time

class TokenBucket:
    def __init__(self, rate, capacity, clock=time.monotonic):
        self.rate, self.capacity, self.clock = rate, capacity, clock
        self.tokens = capacity
        self.last = clock()

    def allow(self, cost=1):
        now = self.clock()
        self.tokens += int((now - self.last) * self.rate)
        self.last = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False
''',
"test_ratelimit.py": '''from ratelimit import TokenBucket
t = [0.0]
b = TokenBucket(rate=1, capacity=2, clock=lambda: t[0])
assert b.allow() and b.allow() and not b.allow()
t[0] = 100
assert b.allow() and b.allow() and not b.allow(), "supera la capacita'"
print("OK")
'''},
checker='''from ratelimit import TokenBucket
t = [0.0]; clk = lambda: t[0]
b = TokenBucket(rate=1, capacity=2, clock=clk)
assert b.allow() and b.allow() and not b.allow()
t[0] = 100; assert b.allow() and b.allow() and not b.allow()
t = [0.0]; b = TokenBucket(rate=0.5, capacity=1, clock=lambda: t[0])
assert b.allow() and not b.allow()
t[0] = 1.0; assert not b.allow()
t[0] = 2.0; assert b.allow(), "rate frazionario non ricarica"
t[0] = 2.5; assert not b.allow()
t = [0.0]; b = TokenBucket(rate=10, capacity=5, clock=lambda: t[0])
assert b.allow(5) and not b.allow(1)
t[0] = 0.3; assert b.allow(3) and not b.allow(1)
print("OK")'''))

T.append(dict(id="eventi", goal="EventBus in events.py ha due problemi: gli handler devono essere chiamati in ordine di priorita' (numero piu' alto prima; a parita', in ordine di iscrizione), e se un handler si disiscrive durante emit un altro handler viene saltato. Correggi entrambi.",
seed={"events.py": '''class EventBus:
    def __init__(self):
        self.handlers = {}

    def subscribe(self, event, fn, priority=0):
        self.handlers.setdefault(event, []).append((priority, fn))

    def unsubscribe(self, event, fn):
        lst = self.handlers.get(event, [])
        for i, (p, f) in enumerate(lst):
            if f is fn:
                del lst[i]
                return

    def emit(self, event, *args):
        for p, fn in self.handlers.get(event, []):
            fn(*args)
'''},
checker='''from events import EventBus
log = []
bus = EventBus()
bus.subscribe("e", lambda: log.append("low"), priority=0)
bus.subscribe("e", lambda: log.append("high"), priority=5)
bus.subscribe("e", lambda: log.append("low2"), priority=0)
bus.emit("e"); assert log == ["high", "low", "low2"], log
log.clear(); bus2 = EventBus()
def once():
    log.append("once"); bus2.unsubscribe("x", once)
bus2.subscribe("x", once); bus2.subscribe("x", lambda: log.append("after"))
bus2.emit("x"); assert log == ["once", "after"], log
log.clear(); bus2.emit("x"); assert log == ["after"], log
bus2.emit("nessuno")
print("OK")'''))

T.append(dict(id="negozio", goal="Il piccolo sito del negozio (app.py usa pages.py e text.py) ha due bug segnalati dagli utenti: la pagina 1 del catalogo mostra i prodotti della pagina 2, e gli URL dei prodotti con accenti (es. 'Caffe' Espresso Forte' o 'Cioccolato Fondente 70%') sono sbagliati. Trova le cause e correggi. Esegui test_app.py.",
seed={
"text.py": '''def slugify(name):
    return name.lower().replace(" ", "-")
''',
"pages.py": '''def paginate(items, page, per_page=3):
    """page parte da 1. Ritorna la lista di quella pagina (vuota se fuori range)."""
    start = page * per_page
    return items[start:start + per_page]
''',
"app.py": '''from pages import paginate
from text import slugify

PRODUCTS = ["Pane", "Latte", "Caff\\u00e8 Espresso Forte", "Cioccolato Fondente 70%", "Mele", "Pere", "Uva"]

def catalog(page):
    return [{"name": n, "url": "/p/" + slugify(n)} for n in paginate(PRODUCTS, page)]
''',
"test_app.py": '''from app import catalog
p1 = catalog(1)
assert [x["name"] for x in p1] == ["Pane", "Latte", "Caff\\u00e8 Espresso Forte"], p1
assert p1[2]["url"] == "/p/caffe-espresso-forte", p1[2]["url"]
print("OK")
'''},
checker='''from app import catalog
from text import slugify
from pages import paginate
assert [x["name"] for x in catalog(1)] == ["Pane", "Latte", "Caff\\u00e8 Espresso Forte"]
assert [x["name"] for x in catalog(3)] == ["Uva"] and catalog(4) == [] and catalog(0) == []
assert slugify("Caff\\u00e8 Espresso Forte") == "caffe-espresso-forte"
assert slugify("Cioccolato Fondente 70%") == "cioccolato-fondente-70", slugify("Cioccolato Fondente 70%")
assert slugify("  Pi\\u00f9   Spazi -- qui ") == "piu-spazi-qui", slugify("  Pi\\u00f9   Spazi -- qui ")
assert paginate(list(range(10)), 2, 4) == [4, 5, 6, 7]
print("OK")'''))

T.append(dict(id="percorso", goal="shortest_path in graph.py deve ritornare la lista dei nodi del percorso piu' corto (numero di archi) da start a goal in un grafo non orientato dato come lista di archi, oppure None se non esiste. Oggi a volte ritorna percorsi non minimi, e va in errore se goal non e' raggiungibile. Correggilo.",
seed={"graph.py": '''def shortest_path(edges, start, goal):
    adj = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    stack, seen, parent = [start], {start}, {}
    while stack:
        node = stack.pop()
        if node == goal:
            break
        for n in adj[node]:
            if n not in seen:
                seen.add(n); parent[n] = node; stack.append(n)
    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    return path[::-1]
'''},
checker='''from graph import shortest_path
E = [(1,2),(2,3),(3,4),(4,5),(1,6),(6,5),(5,7)]
assert shortest_path(E, 1, 5) == [1, 6, 5], shortest_path(E, 1, 5)
assert shortest_path(E, 1, 7) == [1, 6, 5, 7]
assert shortest_path(E, 3, 3) == [3]
assert shortest_path(E + [(8, 9)], 1, 9) is None
assert shortest_path(E, 1, 99) is None
assert shortest_path([], "a", "a") == ["a"]
print("OK")'''))

T.append(dict(id="romani", goal="roman.py converte numeri romani ma from_roman sbaglia le forme sottrattive (IV, IX, XL, CM...) e accetta stringhe non valide. Correggi: to_roman(n) per 1..3999 (ValueError fuori range), from_roman(s) che rifiuta con ValueError le forme non canoniche (es. 'IIII', 'VX', 'IC', 'MMMM', ''), cosi' che from_roman(to_roman(n)) == n per ogni n.",
seed={"roman.py": '''VALS = [(1000,"M"),(900,"CM"),(500,"D"),(400,"CD"),(100,"C"),(90,"XC"),(50,"L"),(40,"XL"),(10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")]
ONE = {"I":1,"V":5,"X":10,"L":50,"C":100,"D":500,"M":1000}

def to_roman(n):
    out = ""
    for v, s in VALS:
        while n >= v:
            out += s; n -= v
    return out

def from_roman(s):
    return sum(ONE[c] for c in s)
'''},
checker='''from roman import to_roman, from_roman
for n in range(1, 4000):
    assert from_roman(to_roman(n)) == n, n
assert to_roman(1994) == "MCMXCIV" and from_roman("MCMXCIV") == 1994
for bad in ["IIII", "VX", "IC", "MMMM", "", "ABC", "XM", "VV", "IIV"]:
    try:
        from_roman(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("accettato %r" % bad)
for bad in [0, 4000, -1]:
    try:
        to_roman(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("to_roman(%r) senza errore" % bad)
print("OK")'''))

TASKS = {t["id"]: t for t in T}


# ---------------------------------------------------------------- loop
class LS(Workspace):
    def call(self, name, args):
        if name == "list_files":
            self.used.append(name)
            return "\n".join(sorted(p.name for p in self.tmp.iterdir() if p.is_file()))
        return super().call(name, args)


def chat(port, messages):
    body = {"messages": messages, "tools": TOOLS, "temperature": 0.6, "top_p": 0.95, "top_k": 20,
            "seed": int(_os.environ.get("SEED", "1")), "max_tokens": int(_os.environ.get("MAX_TOKENS", "8192"))}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        return json.loads(r.read().decode())


def run_one(task, port, max_steps=30):
    with tempfile.TemporaryDirectory(prefix="ab2_") as d:
        ws = LS(Path(d))
        for name, content in task["seed"].items():
            (Path(d) / name).write_text(content, encoding="utf-8")
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task["goal"]}]
        steps, toks, t0, err = 0, 0, time.time(), None
        try:
            for _ in range(max_steps):
                steps += 1
                body = chat(port, messages)
                toks += (body.get("usage") or {}).get("completion_tokens", 0)
                msg = body["choices"][0]["message"]
                calls = msg.get("tool_calls") or []
                messages.append({"role": "assistant", "content": msg.get("content") or "",
                                 **({"tool_calls": calls} if calls else {})})
                if not calls:
                    break
                for c in calls:
                    fn = c["function"]["name"]
                    raw = c["function"].get("arguments") or "{}"
                    try:
                        args = raw if isinstance(raw, dict) else json.loads(raw)
                    except json.JSONDecodeError:
                        obs = "ERRORE: argomenti JSON non validi"
                    else:
                        obs = ws.call(fn, args)
                    messages.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": obs[:4000]})
                if ws.final is not None:
                    break
        except Exception as e:   # contesto pieno, timeout, ecc.: il compito conta come non risolto
            err = f"{type(e).__name__}: {e}"[:300]
        files = {p.name: p.read_text(encoding="utf-8") for p in Path(d).iterdir() if p.is_file()}
        files["__checker__.py"] = task["checker"]
        res = run_python(files, "__checker__.py", timeout=60)
        return {"solved": res.ok, "steps": steps, "tokens": toks, "sec": round(time.time() - t0),
                "used": ws.used, "finished": ws.final is not None, "error": err,
                "checker": res.summary(400), "transcript": messages}


if __name__ == "__main__":
    label, port = sys.argv[1], sys.argv[2]
    ids = sys.argv[3:] or list(TASKS)
    out = Path(__file__).resolve().parent / "runs" / "agent_bench2.json"
    out.parent.mkdir(exist_ok=True)
    res = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    for tid in ids:
        key = f"{label}|{tid}"
        if key in res:
            continue
        r = run_one(TASKS[tid], port)
        res[key] = r
        out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{key}: {'RISOLTO' if r['solved'] else 'FALLITO'} | passi {r['steps']} | token {r['tokens']} | "
              f"{r['sec']}s | finish={r['finished']}" + (f" | ERR {r['error']}" if r['error'] else ""), flush=True)
    rows = [v for k, v in res.items() if k.startswith(label + "|")]
    print(f"\n=== {label}: {sum(v['solved'] for v in rows)}/{len(rows)} compiti risolti ===")
