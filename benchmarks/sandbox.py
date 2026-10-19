"""
sandbox.py — esegue il codice scritto dal modello e riporta la VERITA'.

Ogni esecuzione gira in una cartella temporanea nuova, in un processo
separato, con timeout. Il risultato (stdout, stderr, exit code) torna al
loop: e' questo che impedisce al modello di "dire fatto" senza prova.

ATTENZIONE: questo NON e' un sandbox di sicurezza vero. Isola file e
tempo, non protegge da codice malevolo (rete, file system fuori dalla
cartella). Per codice non fidato serve un container (Docker/VM): fase
successiva. Per ora: solo codice di prova.
"""

from __future__ import annotations
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunResult:
    ok: bool            # exit code 0 e niente timeout
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool

    def summary(self, limit: int = 2000) -> str:
        """Testo compatto da rimandare al modello."""
        status = "TIMEOUT" if self.timed_out else f"exit={self.exit_code}"
        out = (self.stdout or "")[-limit:]
        err = (self.stderr or "")[-limit:]
        return f"[{status}]\n--- stdout ---\n{out}\n--- stderr ---\n{err}"


def run_python(files: dict[str, str], entry: str, timeout: int = 30) -> RunResult:
    """
    Scrive i file in una cartella temporanea pulita ed esegue `entry`.
    files: {"solution.py": "...", "test_solution.py": "..."}
    """
    with tempfile.TemporaryDirectory(prefix="agent_run_") as tmp:
        tmp_path = Path(tmp)
        for name, content in files.items():
            target = (tmp_path / name).resolve()
            # blocca nomi tipo "../../x" che escono dalla cartella
            if tmp_path.resolve() not in target.parents:
                raise ValueError(f"Nome file non ammesso: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        try:
            proc = subprocess.run(
                [sys.executable, entry],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return RunResult(
                ok=proc.returncode == 0,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as e:
            return RunResult(
                ok=False,
                exit_code=-1,
                stdout=(e.stdout or "") if isinstance(e.stdout, str) else "",
                stderr=(e.stderr or "") if isinstance(e.stderr, str) else "",
                timed_out=True,
            )
