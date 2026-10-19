"""
agent_bench3.py — compiti agentici DIFFICILI (loop lunghi, piu' file, progettazione), stesso motore di agent_bench2.

Ogni compito richiede di leggere una specifica, progettare, scrivere piu' funzioni/file, eseguire i test,
correggere. Il voto lo da' un CHECKER NASCOSTO molto piu' severo dei test visibili.
Uso: python agent_bench3.py <etichetta> <porta> [id ...]
"""
import json, sys, time
from pathlib import Path
import agent_bench2 as ab

T = []

T.append(dict(id="minidb", goal=(
"Implementa in kv.py un piccolo database chiave-valore con TRANSAZIONI ANNIDATE, secondo SPEC.md. "
"Scrivi anche dei test ed eseguili finche' passano."),
seed={"SPEC.md": """# kv.py — specifica
class KV:
  set(key, value), get(key) -> valore o None, delete(key) (nessun errore se manca)
  begin()    apre una transazione (si possono annidare)
  commit()   chiude la transazione PIU' INTERNA rendendone permanenti le modifiche verso il livello sotto;
             se non ci sono transazioni aperte alza RuntimeError
  rollback() annulla le modifiche della transazione piu' interna; RuntimeError se nessuna aperta
  count(value) -> quante chiavi hanno quel valore, considerando le transazioni aperte
  save(path) / KV.load(path) salvano/caricano lo stato COMMITTATO in JSON (save con transazioni aperte -> RuntimeError)
""", "kv.py": "class KV:\n    pass\n"},
checker='''import os, tempfile
from kv import KV
d = KV(); d.set("a", 1); d.set("b", 1)
assert d.get("a") == 1 and d.count(1) == 2 and d.get("x") is None
d.begin(); d.set("a", 2); assert d.get("a") == 2 and d.count(1) == 1
d.begin(); d.delete("b"); assert d.get("b") is None and d.count(1) == 0
d.rollback(); assert d.get("b") == 1
d.commit(); assert d.get("a") == 2
for f in (d.commit, d.rollback):
    try: f()
    except RuntimeError: pass
    else: raise AssertionError("niente RuntimeError")
d.begin(); d.set("c", 3); d.begin(); d.set("c", 4); d.commit(); assert d.get("c") == 4
d.rollback(); assert d.get("c") is None
d.delete("nonce")
p = os.path.join(tempfile.mkdtemp(), "db.json")
d.begin(); d.set("t", 9)
try: d.save(p)
except RuntimeError: pass
else: raise AssertionError("save con transazione aperta")
d.rollback(); d.save(p); e = KV.load(p)
assert e.get("a") == 2 and e.get("b") == 1 and e.get("t") is None and e.count(1) == 1
print("OK")'''))

T.append(dict(id="interprete", goal=(
"Implementa in lang.py la funzione run(source) che esegue il piccolo linguaggio descritto in SPEC.md e "
"ritorna la lista dei valori stampati. Scrivi test ed eseguili."),
seed={"SPEC.md": """# Linguaggio
- istruzioni separate da a-capo; numeri interi; variabili [a-z_]+
- assegnazione:   x = espressione
- stampa:         print espressione
- espressioni: + - * / (divisione intera, verso zero come int(a/b)), parentesi, confronti < > == (danno 1 o 0), meno unario
- blocchi:        if espressione { ... } else { ... }   (else opzionale)
                  while espressione { ... }
- funzioni:       def nome(a, b) { ... return espressione }   chiamate: nome(1, 2)
                  le funzioni vedono solo i loro parametri e le proprie variabili locali; ricorsione permessa
- variabile non definita -> NameError ; divisione per zero -> ZeroDivisionError
""", "lang.py": "def run(source):\n    raise NotImplementedError\n"},
checker='''from lang import run
assert run("x = 2 + 3 * 4\\nprint x") == [14]
assert run("print (2+3)*4\\nprint -3 + 1\\nprint 7 / 2\\nprint -7 / 2") == [20, -2, 3, -3]
assert run("i = 0\\ns = 0\\nwhile i < 5 {\\ns = s + i\\ni = i + 1\\n}\\nprint s") == [10]
assert run("x = 3\\nif x > 2 { print 1 } else { print 0 }\\nif x == 4 { print 9 }") == [1]
src = """def fib(n) {
if n < 2 { return n }
return fib(n - 1) + fib(n - 2)
}
print fib(15)
def add(a, b) { return a + b }
print add(2, add(3, 4))"""
assert run(src) == [610, 9], run(src)
assert run("a = 5\\ndef f(x) { return x * 2 }\\nprint f(a)") == [10]
for bad, exc in (("print y", NameError), ("print 1 / 0", ZeroDivisionError),
                 ("a = 1\\ndef g(x) { return a }\\nprint g(2)", NameError)):
    try: run(bad)
    except exc: pass
    else: raise AssertionError((bad, exc))
print("OK")'''))

T.append(dict(id="magazzino", goal=(
"Il sistema di magazzino (inventory.py, orders.py, pricing.py, report.py) ha diversi bug segnalati: "
"gli ordini a volte scalano la merce due volte, i prezzi con sconto a quantita' sono sbagliati, "
"e il report mostra totali errati. I test in test_all.py falliscono. Trova e correggi TUTTE le cause, "
"senza modificare i test."),
seed={
"inventory.py": '''class Inventory:
    def __init__(self):
        self.stock = {}
    def add(self, sku, qty):
        self.stock[sku] = self.stock.get(sku, 0) + qty
    def remove(self, sku, qty):
        if self.stock.get(sku, 0) < qty:
            raise ValueError("stock insufficiente per " + sku)
        self.stock[sku] -= qty
''',
"pricing.py": '''PRICES = {"vite": 0.10, "dado": 0.05, "trapano": 89.0}
def unit_price(sku, qty):
    """sconto: 10% da 100 pezzi in su, 20% da 1000 in su"""
    p = PRICES[sku]
    if qty > 1000:
        return p * 0.8
    if qty > 100:
        return p * 0.9
    return p
''',
"orders.py": '''from pricing import unit_price
class Orders:
    def __init__(self, inventory):
        self.inv = inventory
        self.done = []
    def place(self, sku, qty):
        self.inv.remove(sku, qty)
        total = round(unit_price(sku, qty) * qty, 2)
        self.done.append((sku, qty, total))
        self.inv.remove(sku, qty)
        return total
''',
"report.py": '''def summary(orders):
    by_sku = {}
    for sku, qty, total in orders.done:
        by_sku[sku] = by_sku.get(sku, 0) + qty
    grand = sum(t for _, _, t in orders.done[1:])
    return {"pezzi": by_sku, "totale": grand}
''',
"test_all.py": '''from inventory import Inventory
from orders import Orders
from report import summary
inv = Inventory(); inv.add("vite", 5000); inv.add("trapano", 3)
o = Orders(inv)
assert o.place("vite", 100) == 9.0
assert inv.stock["vite"] == 4900, inv.stock
print("OK")
'''},
checker='''from inventory import Inventory
from orders import Orders
from report import summary
from pricing import unit_price
inv = Inventory(); inv.add("vite", 5000); inv.add("dado", 2000); inv.add("trapano", 3)
o = Orders(inv)
assert o.place("vite", 100) == 9.0 and inv.stock["vite"] == 4900
assert o.place("dado", 1000) == 40.0 and inv.stock["dado"] == 1000
assert o.place("vite", 99) == 9.9
assert o.place("trapano", 2) == 178.0
try:
    o.place("trapano", 2)
except ValueError:
    pass
else:
    raise AssertionError("stock insufficiente non segnalato")
assert inv.stock["trapano"] == 1 and len(o.done) == 4
s = summary(o)
assert s["pezzi"] == {"vite": 199, "dado": 1000, "trapano": 2}, s
assert abs(s["totale"] - (9.0 + 40.0 + 9.9 + 178.0)) < 1e-9, s
assert abs(unit_price("vite", 1000) - 0.08) < 1e-9 and abs(unit_price("vite", 100) - 0.09) < 1e-9
print("OK")'''))

T.append(dict(id="pianificatore", goal=(
"Implementa in plan.py la funzione schedule(tasks, workers) secondo SPEC.md. Scrivi test ed eseguili."),
seed={"SPEC.md": """# schedule(tasks, workers) -> lista di (tempo_inizio, nome) ordinata per (tempo_inizio, nome)
tasks: dict nome -> {"durata": int>0, "dopo": [nomi], "priorita": int (piu' alto = prima)}
- un compito parte solo quando TUTTI quelli in "dopo" sono finiti
- al massimo `workers` compiti contemporaneamente
- quando si libera un worker (o all'inizio), tra i compiti pronti si sceglie la priorita' piu' alta;
  a parita', il nome in ordine alfabetico
- dipendenza verso un compito inesistente -> KeyError ; ciclo -> ValueError
""", "plan.py": "def schedule(tasks, workers):\n    raise NotImplementedError\n"},
checker='''from plan import schedule
t = {"a": {"durata": 3, "dopo": [], "priorita": 1},
     "b": {"durata": 2, "dopo": [], "priorita": 5},
     "c": {"durata": 1, "dopo": ["a", "b"], "priorita": 0},
     "d": {"durata": 4, "dopo": ["b"], "priorita": 2}}
assert schedule(t, 1) == [(0, "b"), (2, "d"), (6, "a"), (9, "c")], schedule(t, 1)
assert schedule(t, 2) == [(0, "a"), (0, "b"), (2, "d"), (3, "c")], schedule(t, 2)
assert schedule(t, 9) == [(0, "a"), (0, "b"), (2, "d"), (3, "c")]
assert schedule({}, 3) == []
for bad, exc in (({"x": {"durata": 1, "dopo": ["y"], "priorita": 0}}, KeyError),
                 ({"x": {"durata": 1, "dopo": ["y"], "priorita": 0}, "y": {"durata": 1, "dopo": ["x"], "priorita": 0}}, ValueError)):
    try: schedule(bad, 1)
    except exc: pass
    else: raise AssertionError(exc)
u = {n: {"durata": 1, "dopo": [], "priorita": 0} for n in "zyx"}
assert schedule(u, 2) == [(0, "x"), (0, "y"), (1, "z")]
print("OK")'''))

T.append(dict(id="jsonpatch", goal=(
"Implementa in jdiff.py le funzioni diff(a, b) e patch(doc, ops) secondo SPEC.md, cosi' che "
"patch(a, diff(a, b)) == b per ogni coppia di documenti JSON. Scrivi test ed eseguili."),
seed={"SPEC.md": """# diff/patch per documenti JSON (dict, list, str, int, float, bool, None annidati)
diff(a, b) -> lista di operazioni {"op": "add"|"remove"|"replace", "path": "/a/0/b", "value": ...}
  - path in stile JSON Pointer: "/" separa; "~" si scrive "~0" e "/" si scrive "~1"; "" e' la radice
  - dict: chiavi nuove -> add, chiavi sparite -> remove, valori diversi -> ricorsione (o replace se tipi diversi)
  - list: se lunghezze uguali confronta per indice; altrimenti replace dell'intera lista
patch(doc, ops) -> NUOVO documento (doc non va modificato); path inesistente per remove/replace -> KeyError
""", "jdiff.py": "def diff(a, b):\n    raise NotImplementedError\n\ndef patch(doc, ops):\n    raise NotImplementedError\n"},
checker='''import copy
from jdiff import diff, patch
cases = [({"a": 1}, {"a": 2}), ({"a": 1, "b": {"c": [1, 2]}}, {"b": {"c": [1, 3]}, "d": None}),
         ([1, 2, 3], [1, 2]), ({"x/y": 1, "t~": 2}, {"x/y": 5}), (1, "uno"), ({}, {"n": {"m": {"o": [True]}}}),
         ({"l": [{"a": 1}, {"b": 2}]}, {"l": [{"a": 1}, {"b": 3}]})]
for a, b in cases:
    a0 = copy.deepcopy(a); ops = diff(a, b); r = patch(a, ops)
    assert r == b, (a, b, ops, r)
    assert a == a0, "patch ha modificato l'originale"
ops = diff({"x/y": 1}, {"x/y": 2})
assert ops == [{"op": "replace", "path": "/x~1y", "value": 2}], ops
assert diff({"a": 1}, {"a": 1}) == []
try: patch({"a": 1}, [{"op": "remove", "path": "/zz"}])
except KeyError: pass
else: raise AssertionError("KeyError mancante")
print("OK")'''))

TASKS = {t["id"]: t for t in T}

if __name__ == "__main__":
    label, port = sys.argv[1], sys.argv[2]
    ids = sys.argv[3:] or list(TASKS)
    out = Path(__file__).resolve().parent / "runs" / "agent_bench3.json"
    out.parent.mkdir(exist_ok=True)
    res = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    for tid in ids:
        key = f"{label}|{tid}"
        if key in res:
            continue
        r = ab.run_one(TASKS[tid], port, max_steps=40)
        res[key] = r
        out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{key}: {'RISOLTO' if r['solved'] else 'FALLITO'} | passi {r['steps']} | token {r['tokens']} | "
              f"{r['sec']}s | finish={r['finished']}" + (f" | ERR {r['error']}" if r['error'] else ""), flush=True)
    rows = [v for k, v in res.items() if k.startswith(label + "|")]
    print(f"\n=== {label}: {sum(v['solved'] for v in rows)}/{len(rows)} compiti difficili risolti, "
          f"{sum(v['sec'] for v in rows)/60:.1f} min, {sum(v['tokens'] for v in rows)} token ===", flush=True)
