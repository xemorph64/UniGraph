import asyncio
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.neo4j_service import neo4j_service

router = APIRouter()


_DATASET_SQL_FILES = {
    "100": "dataset_100_interconnected_txns.sql",
    "200": "dataset_200_interconnected_txns.sql",
}

_DATASET_SWITCH_LOCK = asyncio.Lock()


class DatasetStreamRequest(BaseModel):
    dataset: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _tail_lines(text: str, line_limit: int = 20, char_limit: int = 2500) -> str:
    lines = text.splitlines()
    joined = "\n".join(lines[-line_limit:])
    if len(joined) <= char_limit:
        return joined
    return joined[-char_limit:]


@router.get("/options")
async def get_dataset_options():
    return {
        "datasets": [
            {"dataset": dataset, "sql_file": sql_file}
            for dataset, sql_file in _DATASET_SQL_FILES.items()
        ],
        "switch_in_progress": _DATASET_SWITCH_LOCK.locked(),
    }


@router.post("/stream")
async def stream_dataset(request: DatasetStreamRequest):
    dataset = request.dataset.strip()
    if dataset not in _DATASET_SQL_FILES:
        raise HTTPException(
            status_code=400,
            detail="Invalid dataset. Use '100' or '200'.",
        )

    if _DATASET_SWITCH_LOCK.locked():
        raise HTTPException(
            status_code=409,
            detail="Dataset switch already in progress. Try again shortly.",
        )

    async with _DATASET_SWITCH_LOCK:
        started = time.perf_counter()
        root = _repo_root()
        script_path = root / "scripts" / "ingest_transactions_input_sql.py"
        sql_file = root / _DATASET_SQL_FILES[dataset]

        if not script_path.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Ingestion script not found: {script_path}",
            )

        if not sql_file.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Dataset SQL file not found: {sql_file}",
            )

        try:
            purge_stats = await neo4j_service.clear_all_data()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to clear existing graph data: {exc}",
            ) from exc

        tmp_report = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix=f"dataset_switch_{dataset}_",
            dir=str(root),
            delete=False,
        )
        report_path = Path(tmp_report.name)
        tmp_report.close()

        command = [
            sys.executable,
            str(script_path),
            "--sql-file",
            str(sql_file),
            "--api-url",
            "http://localhost:8000/api/v1/transactions/ingest",
            "--report-file",
            str(report_path),
            "--delay-ms",
            "0",
        ]

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
            )

            stdout_tail = _tail_lines(result.stdout or "")
            stderr_tail = _tail_lines(result.stderr or "")

            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Dataset ingestion failed. "
                        f"exit_code={result.returncode}; "
                        f"stdout_tail={stdout_tail or '<empty>'}; "
                        f"stderr_tail={stderr_tail or '<empty>'}"
                    ),
                )

            if not report_path.exists():
                raise HTTPException(
                    status_code=500,
                    detail="Ingestion completed but report file was not produced.",
                )

            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                totals = report.get("totals") or {}
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Failed to parse ingestion report. "
                        f"stdout_tail={stdout_tail or '<empty>'}; "
                        f"stderr_tail={stderr_tail or '<empty>'}; "
                        f"error={exc}"
                    ),
                ) from exc
        finally:
            try:
                report_path.unlink(missing_ok=True)
            except Exception:
                pass

        duration_seconds = round(time.perf_counter() - started, 3)

        return {
            "dataset": dataset,
            "sql_file": sql_file.name,
            "removed_previous_data": True,
            "purge": purge_stats,
            "totals": {
                "transactions_parsed": int(totals.get("transactions_parsed", 0) or 0),
                "ingest_success": int(totals.get("ingest_success", 0) or 0),
                "ingest_errors": int(totals.get("ingest_errors", 0) or 0),
                "flagged": int(totals.get("flagged", 0) or 0),
            },
            "duration_seconds": duration_seconds,
            "message": (
                f"Switched to dataset {dataset}. "
                f"Previous graph data removed and {sql_file.name} streamed."
            ),
        }
