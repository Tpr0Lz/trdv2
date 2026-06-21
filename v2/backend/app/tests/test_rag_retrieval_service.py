from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import text

from app.db.models import RagDocument, Run, RunEvidence, User
from app.db.session import SessionLocal
from app.schemas.rag import RetrievedEvidence
from app.services.rag_import_service import import_spy_sources
from app.services.rag_retrieval_service import (
    build_spy_rag_contexts,
    format_evidence_context,
    retrieve_spy_evidence,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
SPY_SOURCES = REPO_ROOT / "TradingAgents" / "rag_sources" / "spy"


def clean_tables() -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                "TRUNCATE TABLE run_evidence, rag_chunks, rag_documents, "
                "run_reports, run_metrics, run_events, runs, app_settings, users "
                "RESTART IDENTITY CASCADE"
            )
        )
        db.commit()


def create_run(ticker: str = "SPY") -> str:
    with SessionLocal() as db:
        user = User(username=f"user-{ticker}", password_hash="hash")
        db.add(user)
        db.flush()
        run = Run(
            user_id=user.id,
            ticker=ticker,
            analysis_date=date(2026, 1, 31),
            asset_type="stock",
            status="running",
            config_snapshot={},
            selected_analysts=["news"],
            checkpoint_thread_id=f"thread-{ticker}",
        )
        db.add(run)
        db.commit()
        return run.id


def test_retrieve_news_evidence_returns_macro_sample():
    clean_tables()
    run_id = create_run("SPY")
    import_spy_sources(SPY_SOURCES)

    with SessionLocal() as db:
        results = retrieve_spy_evidence(
            db,
            run_id=run_id,
            ticker="SPY",
            agent_name="News Analyst",
            query="SPY macro policy inflation labor market latest evidence",
            top_k=3,
        )
        db.commit()

        assert results
        assert any(item.source_type == "fomc_statement" for item in results)
        assert db.query(RunEvidence).filter_by(run_id=run_id).count() == len(results)


def test_retrieve_evidence_assigns_stable_citation_keys():
    clean_tables()
    run_id = create_run("SPY")
    import_spy_sources(SPY_SOURCES)

    with SessionLocal() as db:
        first = retrieve_spy_evidence(
            db,
            run_id=run_id,
            ticker="SPY",
            agent_name="News Analyst",
            query="SPY macro policy inflation labor market latest evidence",
            top_k=3,
        )
        db.commit()
        second = retrieve_spy_evidence(
            db,
            run_id=run_id,
            ticker="SPY",
            agent_name="News Analyst",
            query="SPY macro policy inflation labor market latest evidence",
            top_k=3,
        )
        db.commit()

    assert [item.citation_key for item in first] == ["E1", "E2", "E3"]
    assert [item.citation_key for item in second] == ["E1", "E2", "E3"]


def test_non_spy_does_not_retrieve_evidence():
    clean_tables()
    run_id = create_run("NVDA")
    import_spy_sources(SPY_SOURCES)

    with SessionLocal() as db:
        results = retrieve_spy_evidence(
            db,
            run_id=run_id,
            ticker="NVDA",
            agent_name="News Analyst",
            query="NVDA macro policy",
            top_k=3,
        )

        assert results == []
        assert db.query(RunEvidence).filter_by(run_id=run_id).count() == 0


def test_retrieve_evidence_ignores_soft_deleted_sources():
    clean_tables()
    run_id = create_run("SPY")
    import_spy_sources(SPY_SOURCES)

    with SessionLocal() as db:
        document = db.query(RagDocument).filter_by(source_id="spy_fomc_sample").one()
        # 中文注释：停用资料不应进入未来 agent 的 RAG context。
        document.deleted_at = datetime.now(UTC)
        document.deleted_by = "admin"
        db.commit()

        results = retrieve_spy_evidence(
            db,
            run_id=run_id,
            ticker="SPY",
            agent_name="News Analyst",
            query="SPY macro policy inflation labor market latest evidence",
            top_k=5,
        )

    assert all(item.source_id != "spy_fomc_sample" for item in results)


def test_format_evidence_context_includes_sources():
    clean_tables()
    run_id = create_run("SPY")
    import_spy_sources(SPY_SOURCES)

    with SessionLocal() as db:
        results = retrieve_spy_evidence(
            db,
            run_id=run_id,
            ticker="SPY",
            agent_name="Fundamentals Analyst",
            query="SPY holdings sector weights valuation earnings concentration",
            top_k=3,
        )

    context = format_evidence_context(results)

    assert "Retrieved SPY Evidence" in context
    assert "Source:" in context


def test_format_evidence_context_includes_citation_keys():
    item = RetrievedEvidence(
        chunk_id="chunk-1",
        citation_key="E1",
        agent_name="News Analyst",
        query="SPY macro",
        score=0.9,
        excerpt="Rates stayed restrictive.",
        source_id="spy_fomc_sample",
        source_title="FOMC Statement Sample",
        source_type="fomc_statement",
        source_name="Federal Reserve",
        published_at=date(2026, 1, 28),
        url="https://example.test",
    )

    context = format_evidence_context([item])

    assert "[E1] FOMC Statement Sample" in context
    assert "When referencing this evidence in your report, cite it as [E1]." in context


def test_build_spy_rag_contexts_does_not_duplicate_run_evidence():
    clean_tables()
    run_id = create_run("SPY")
    import_spy_sources(SPY_SOURCES)

    with SessionLocal() as db:
        first = build_spy_rag_contexts(db, run_id, "SPY")
        db.commit()
        first_count = db.query(RunEvidence).filter_by(run_id=run_id).count()

        second = build_spy_rag_contexts(db, run_id, "SPY")
        db.commit()
        second_count = db.query(RunEvidence).filter_by(run_id=run_id).count()

    assert first
    assert second == first
    assert second_count == first_count


def test_build_spy_rag_contexts_imports_sample_sources_when_empty():
    clean_tables()
    run_id = create_run("SPY")

    with SessionLocal() as db:
        contexts = build_spy_rag_contexts(db, run_id, "SPY")
        db.commit()

        assert contexts
        assert db.query(RunEvidence).filter_by(run_id=run_id).count() > 0
