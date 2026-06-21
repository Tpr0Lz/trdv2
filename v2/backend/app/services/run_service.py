from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.run_states import RunStatus
from app.db.models import Run, User
from app.schemas.runs import RunCreateRequest
from app.services.run_event_service import append_run_event


def normalize_selected_analysts(asset_type: str, selected_analysts: list[str]) -> list[str]:
    """宏观模式只运行新闻分析员，避免误触股票行情和基本面数据源。"""
    if asset_type == "macro":
        return ["news"]
    return selected_analysts


def ensure_single_user(db: Session, username: str) -> User:
    """第一阶段认证来自 .env，这里只确保数据库里有稳定 user_id。"""
    user = db.get(User, "single-user")
    if user is None:
        user = User(id="single-user", username=username, password_hash="env-managed")
        db.add(user)
        db.flush()
    elif user.username != username:
        user.username = username
        db.flush()
    return user


def create_run(db: Session, username: str, payload: RunCreateRequest) -> Run:
    user = ensure_single_user(db, username)
    run_id = str(uuid4())
    selected_analysts = normalize_selected_analysts(payload.asset_type, payload.selected_analysts)
    config_snapshot = {
        "llm_provider": payload.llm_provider,
        "deep_think_llm": payload.deep_think_llm,
        "quick_think_llm": payload.quick_think_llm,
        "output_language": payload.output_language,
        "research_depth": payload.research_depth,
    }
    run = Run(
        id=run_id,
        user_id=user.id,
        ticker=payload.ticker.upper(),
        analysis_date=payload.analysis_date,
        asset_type=payload.asset_type,
        status=RunStatus.QUEUED.value,
        status_reason=None,
        config_snapshot=config_snapshot,
        selected_analysts=selected_analysts,
        checkpoint_thread_id=run_id,
    )
    db.add(run)
    db.flush()
    append_run_event(
        db,
        run.id,
        "run_created",
        {
            "ticker": run.ticker,
            "analysis_date": run.analysis_date.isoformat(),
            "asset_type": run.asset_type,
        },
    )
    db.commit()
    db.refresh(run)
    return run


def list_runs(db: Session, username: str) -> list[Run]:
    user = ensure_single_user(db, username)
    stmt = select(Run).where(Run.user_id == user.id).order_by(Run.created_at.desc())
    return list(db.scalars(stmt))


def get_run(db: Session, username: str, run_id: str) -> Run | None:
    user = ensure_single_user(db, username)
    stmt = select(Run).where(Run.id == run_id, Run.user_id == user.id)
    return db.scalar(stmt)
