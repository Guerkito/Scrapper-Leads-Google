"""Estado compartido de los trabajos en segundo plano del panel web."""

from __future__ import annotations

import threading

from engine import decision_maker
from services.campaigns import CampState
from services.search_mission import SearchMission


class BatchJob:
    """Progreso simple para trabajos por lotes (p. ej. enriquecer decisores)."""

    def __init__(self):
        self._lock = threading.RLock()
        self.reset()

    def reset(self):
        with self._lock:
            self.running = False
            self.total = 0
            self.done = 0
            self.saved = 0
            self.message = ""
            self.logs = []

    def snapshot(self):
        with self._lock:
            return {
                "running": self.running,
                "total": self.total,
                "done": self.done,
                "saved": self.saved,
                "message": self.message,
                "logs": list(self.logs[-12:]),
            }


MISSION = SearchMission()
EMAIL_CAMP = CampState()
WA_CAMP = CampState()
DECISION_JOB = BatchJob()


def start_decision_enrichment(limit: int = 20) -> bool:
    if DECISION_JOB.running:
        return False
    DECISION_JOB.reset()
    DECISION_JOB.running = True
    DECISION_JOB.total = decision_maker.pending_count()

    def _work():
        try:
            def _progress(done, total, nombre):
                DECISION_JOB.done = done
                DECISION_JOB.message = f"Analizando {nombre} ({done}/{total})"

            saved = decision_maker.enrich_batch(limit=limit, on_progress=_progress)
            DECISION_JOB.saved = saved
            DECISION_JOB.message = f"{saved} decisor(es) encontrados"
        except Exception as exc:
            DECISION_JOB.message = f"Error: {exc}"
        finally:
            DECISION_JOB.running = False

    threading.Thread(target=_work, daemon=True, name="onyx-decisores").start()
    return True
