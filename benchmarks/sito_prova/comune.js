// stato del sito di prova in localStorage, letto dal banco per verificare il risultato
const S = { get: k => JSON.parse(localStorage.getItem(k) || 'null'), set: (k, v) => localStorage.setItem(k, JSON.stringify(v)) };
function nav() {
  document.body.insertAdjacentHTML('afterbegin', `<nav>
    <a href="index.html">Home</a> <a href="prodotti.html">Prodotti</a> <a href="carrello.html">Carrello</a>
    <a href="impostazioni.html">Impostazioni</a> <a href="contatti.html">Contatti</a> <a href="#">Blog</a>
    <a href="#">Chi siamo</a> <a href="#">Privacy</a> <button>Accedi</button></nav><hr>`);
}
function aggiungi(p) { const c = S.get('carrello') || []; c.push(p); S.set('carrello', c); S.set('aggiunti', (S.get('aggiunti') || []).concat([p])); document.getElementById('msg').textContent = p + ' aggiunto'; }
