from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def create_db_engine():
    """集中创建 SQLAlchemy engine，方便测试替换连接串。"""
    return create_engine(get_settings().database_url, pool_pre_ping=True)


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def reconfigure_session_factory(database_url: str) -> None:
    """中文注释：测试切换独立数据库时，重绑全局 engine 和 SessionLocal。"""
    global engine, SessionLocal
    engine.dispose()
    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal.configure(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
