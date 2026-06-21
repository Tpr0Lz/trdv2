import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_current_username
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.events import RunEventResponse, RunEventsResponse
from app.schemas.quality import RunQualityResponse
from app.schemas.rag import RunEvidenceResponse
from app.schemas.reports import RunMetricResponse, RunReportsResponse
from app.schemas.runs import RunCreateRequest, RunListResponse, RunResponse
from app.schemas.trace import RunTraceResponse
from app.services.run_artifact_service import get_run_metrics, list_run_evidence, list_run_reports
from app.services.run_event_service import list_run_events
from app.services.run_quality_service import build_run_quality
from app.services.run_trace_service import build_run_trace
from app.services import run_service
from app.services.sse_broker import broker

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    request: Request,
    payload: RunCreateRequest,
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> RunResponse:
    run = run_service.create_run(db, username, payload)
    if get_settings().run_autostart:
        request.app.state.run_manager.start_run(run.id)
    return run


@router.get("", response_model=RunListResponse)
def list_runs(
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> RunListResponse:
    return RunListResponse(items=run_service.list_runs(db, username))


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> RunResponse:
    run = run_service.get_run(db, username, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.post("/{run_id}/resume", response_model=RunResponse)
def resume_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> RunResponse:
    run = run_service.get_run(db, username, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    try:
        request.app.state.run_manager.resume_run(run.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.refresh(run)
    return run


@router.post("/{run_id}/pause", response_model=RunResponse)
def pause_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> RunResponse:
    run = run_service.get_run(db, username, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    try:
        request.app.state.run_manager.pause_run(run.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.refresh(run)
    return run


@router.post("/{run_id}/cancel", response_model=RunResponse)
def cancel_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> RunResponse:
    run = run_service.get_run(db, username, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    try:
        request.app.state.run_manager.cancel_run(run.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.refresh(run)
    return run


@router.get("/{run_id}/events", response_model=RunEventsResponse)
def get_run_events(
    run_id: str,
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> RunEventsResponse:
    run = run_service.get_run(db, username, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return RunEventsResponse(items=list_run_events(db, run_id))


@router.get("/{run_id}/trace", response_model=RunTraceResponse)
def get_run_trace(
    run_id: str,
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> RunTraceResponse:
    run = run_service.get_run(db, username, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return RunTraceResponse(items=build_run_trace(db, run_id))


@router.get("/{run_id}/quality", response_model=RunQualityResponse)
def get_run_quality(
    run_id: str,
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> RunQualityResponse:
    run = run_service.get_run(db, username, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return build_run_quality(db, run_id)


@router.get("/{run_id}/reports", response_model=RunReportsResponse)
def get_run_reports(
    run_id: str,
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> RunReportsResponse:
    run = run_service.get_run(db, username, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return RunReportsResponse(items=list_run_reports(db, run_id))


@router.get("/{run_id}/metrics", response_model=RunMetricResponse)
def get_run_metric_snapshot(
    run_id: str,
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> RunMetricResponse:
    run = run_service.get_run(db, username, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return get_run_metrics(db, run_id)


@router.get("/{run_id}/evidence", response_model=RunEvidenceResponse)
def get_run_evidence(
    run_id: str,
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> RunEvidenceResponse:
    run = run_service.get_run(db, username, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return RunEvidenceResponse(items=list_run_evidence(db, run_id))


@router.get("/{run_id}/stream")
def stream_run_events(
    run_id: str,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    after_event_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    username: str = Depends(require_current_username),
) -> StreamingResponse:
    run = run_service.get_run(db, username, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    header_event_id = int(last_event_id) if last_event_id and last_event_id.isdigit() else None
    resume_after_event_id = after_event_id if after_event_id is not None else header_event_id
    history = [
        RunEventResponse.model_validate(event)
        for event in list_run_events(db, run_id, resume_after_event_id)
    ]

    async def event_generator() -> AsyncGenerator[str, None]:
        # 中文注释：先补历史事件，再订阅进程内新事件，刷新页面不会丢进度。
        for event in history:
            yield _format_sse(event)
        async for event in broker.subscribe(run_id):
            yield _format_sse(event)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _format_sse(event: RunEventResponse) -> str:
    data = event.model_dump(mode="json")
    return f"id: {event.id}\nevent: {event.event_type}\ndata: {json.dumps(data)}\n\n"
