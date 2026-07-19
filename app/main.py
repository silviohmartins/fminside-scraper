from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from fminside.config import OUTPUT_DIR
from fminside.leagues import carregar_ligas, carregar_nacoes
from fminside.pipeline import ScrapeFilters, run_scrape

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    error = "error"


@dataclass
class Job:
    id: str
    mode: str
    query: str
    nationality: str = ""
    status: JobStatus = JobStatus.queued
    message: str = ""
    stage: str = ""
    done: int = 0
    total: int = 0
    urls: int = 0
    batch: int = 0
    files: list[str] = field(default_factory=list)
    output_dir: str = ""
    error: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    logs: list[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_jobs: dict[str, Job] = {}
_lock = threading.Lock()
_active = False


class JobCreate(BaseModel):
    mode: str = Field(..., pattern="^(club|league)$")
    query: str = Field(..., min_length=1)
    nationality: str = ""
    max_pages: Optional[int] = None
    max_players: Optional[int] = None


app = FastAPI(title="fminside-scraper", version="1.0.0")


def _append_log(job: Job, line: str) -> None:
    job.logs.append(line)
    if len(job.logs) > 200:
        job.logs = job.logs[-200:]


def _run_job(job_id: str, body: JobCreate) -> None:
    global _active
    with _lock:
        job = _jobs[job_id]
        job.status = JobStatus.running
        job.message = "Iniciando…"
        _active = True

    def on_progress(stage: str, payload: dict[str, Any]) -> None:
        with _lock:
            j = _jobs[job_id]
            j.stage = stage
            j.updated_at = _now_iso()
            if "urls" in payload:
                j.urls = int(payload["urls"])  # type: ignore[arg-type]
            if "total" in payload:
                j.total = int(payload["total"])  # type: ignore[arg-type]
            if "done" in payload:
                j.done = int(payload["done"])  # type: ignore[arg-type]
            if "batch" in payload:
                j.batch = int(payload["batch"])  # type: ignore[arg-type]
            if stage == "clubs_start":
                j.message = f"Listando clubes da liga {payload.get('league') or '…'}…"
                _append_log(j, j.message)
            elif stage == "clubs_page":
                added = int(payload.get("added") or 0)
                j.message = (
                    f"Clubes: {payload.get('clubs', 0)}"
                    f" (página {payload.get('batch', 0)}, +{added})"
                )
                if added > 0 or int(payload.get("batch") or 0) == 0:
                    _append_log(j, j.message)
            elif stage == "clubs_done":
                j.message = f"Clubes listados: {payload.get('clubs', 0)}"
                _append_log(j, j.message)
            elif stage == "clubs_filtered":
                titles = payload.get("titles") or []
                j.message = (
                    f"Após filtro de nação: {payload.get('clubs', 0)} clubes"
                    + (f" ({', '.join(titles)})" if titles else "")
                )
                _append_log(j, j.message)
            elif stage == "warn_mixed_leagues":
                titles = payload.get("titles") or []
                j.message = (
                    "Atenção: títulos de liga mistos sem nação — "
                    + ", ".join(str(t) for t in titles)
                )
                _append_log(j, j.message)
            elif stage == "club_crawl":
                j.message = f"Elenco: {payload.get('club')} ({payload.get('league_title')})"
                _append_log(j, j.message)
            elif stage == "crawl_page":
                added = int(payload.get("added") or 0)
                batch = int(payload.get("batch") or 0)
                j.message = f"Coletando URLs… {j.urls} (página {batch}, +{added})"
                if added > 0 or batch == 0:
                    _append_log(j, j.message)
            elif stage == "crawl_done":
                j.message = f"URLs coletadas: {j.urls} — iniciando perfis…"
                _append_log(j, j.message)
            elif stage == "scrape_start":
                j.message = f"Baixando {payload.get('total', 0)} perfis…"
                _append_log(j, j.message)
            elif stage == "scrape_player":
                nome = payload.get("nome", "?")
                j.message = f"[{j.done}/{j.total}] {nome}"
                _append_log(j, j.message)
            elif stage == "scrape_skip":
                j.message = f"[{j.done}/{j.total}] pulado"
            elif stage == "scrape_error":
                j.message = f"[{j.done}/{j.total}] erro em perfil"
                _append_log(j, f"{j.message}: {payload.get('url')}")
            elif stage == "done":
                j.files = list(payload.get("files") or [])  # type: ignore[arg-type]
                j.output_dir = str(payload.get("output_dir") or "")
                j.message = f"Concluído: {payload.get('players', 0)} jogadores"
                _append_log(j, j.message)

    try:
        filters = ScrapeFilters(
            club=body.query if body.mode == "club" else "",
            league=body.query if body.mode == "league" else "",
            nationality=(body.nationality or "").strip(),
            max_load_more=body.max_pages,
            max_profiles=body.max_players,
            output_dir=OUTPUT_DIR,
        )
        result = run_scrape(filters, on_progress=on_progress)
        with _lock:
            job = _jobs[job_id]
            job.status = JobStatus.done
            job.files = [str(p) for p in result.files]
            job.output_dir = str(result.output_dir)
            job.done = len(result.jogadores)
            job.total = max(job.total, job.done)
            job.updated_at = _now_iso()
            job.message = f"Concluído: {len(result.jogadores)} jogadores, {len(result.files)} arquivo(s)"
    except Exception as exc:  # noqa: BLE001
        with _lock:
            job = _jobs[job_id]
            job.status = JobStatus.error
            job.error = str(exc)
            job.updated_at = _now_iso()
            job.message = f"Erro: {exc}"
            _append_log(job, job.message)
    finally:
        with _lock:
            _active = False


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/leagues")
def api_leagues(refresh: bool = False) -> dict:
    ligas = carregar_ligas(force_refresh=refresh)
    return {"leagues": ligas, "count": len(ligas)}


@app.get("/api/nations")
def api_nations(refresh: bool = False) -> dict:
    nacoes = carregar_nacoes(force_refresh=refresh)
    return {"nations": nacoes, "count": len(nacoes)}


@app.post("/api/jobs")
def create_job(body: JobCreate, background: BackgroundTasks) -> dict:
    global _active
    with _lock:
        if _active:
            raise HTTPException(
                status_code=409,
                detail="Já existe um scraping em andamento. Aguarde terminar.",
            )
        job_id = uuid.uuid4().hex[:12]
        job = Job(
            id=job_id,
            mode=body.mode,
            query=body.query.strip(),
            nationality=(body.nationality or "").strip(),
        )
        _jobs[job_id] = job
        _active = True  # reserva imediatamente

    background.add_task(_run_job, job_id, body)
    return {"id": job_id, "status": JobStatus.queued}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job não encontrado")
        return {
            "id": job.id,
            "mode": job.mode,
            "query": job.query,
            "nationality": job.nationality,
            "status": job.status,
            "message": job.message,
            "stage": job.stage,
            "done": job.done,
            "total": job.total,
            "urls": job.urls,
            "batch": job.batch,
            "files": job.files,
            "output_dir": job.output_dir,
            "error": job.error,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "logs": job.logs[-40:],
        }


@app.get("/api/files/{path:path}")
def download_file(path: str) -> FileResponse:
    root = OUTPUT_DIR.resolve()
    target = (OUTPUT_DIR / path).resolve()
    if not str(target).startswith(str(root)) or not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(target, filename=target.name, media_type="application/json")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
