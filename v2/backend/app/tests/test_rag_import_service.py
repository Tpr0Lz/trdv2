import pytest
from sqlalchemy import text
from pathlib import Path
import shutil

from app.db.models import RagChunk, RagDocument
from app.db.session import SessionLocal
from app.services.rag_import_service import import_spy_sources

TMP_SOURCE_DIR = Path("app/tests/.rag_import_tmp")


@pytest.fixture(autouse=True)
def cleanup_source_dir():
    if TMP_SOURCE_DIR.exists():
        shutil.rmtree(TMP_SOURCE_DIR)
    yield
    if TMP_SOURCE_DIR.exists():
        shutil.rmtree(TMP_SOURCE_DIR)


def clean_rag_tables() -> None:
    with SessionLocal() as db:
        db.execute(text("TRUNCATE TABLE run_evidence, rag_chunks, rag_documents RESTART IDENTITY CASCADE"))
        db.commit()


def write_source_file(name: str, content: str) -> Path:
    TMP_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    for existing in TMP_SOURCE_DIR.glob("*"):
        if existing.is_file():
            existing.unlink()
    source = TMP_SOURCE_DIR / name
    source.write_text(content, encoding="utf-8")
    return source


def test_import_spy_markdown_source():
    clean_rag_tables()
    source = write_source_file(
        "spy_fomc.md",
        """---
source_id: spy_fomc_test
scope: macro
ticker: SPY
related_tickers: []
source_type: fomc_statement
source_name: Federal Reserve
published_at: 2026-01-28
retrieved_at: 2026-06-20
url: https://example.test/fomc
tags: [fed, rates]
confidence: high
license_note: public_source
---

# FOMC Test

## Key Facts

- Rates remained restrictive.

## Why It Matters For SPY

Rate pressure can lower valuation multiples.
""",
    )

    result = import_spy_sources(source.parent)

    assert result.documents_imported == 1
    with SessionLocal() as db:
        document = db.query(RagDocument).filter_by(source_id="spy_fomc_test").one()
        chunks = db.query(RagChunk).filter_by(document_id=document.id).all()
        assert document.ticker == "SPY"
        assert document.scope == "macro"
        assert chunks
        assert chunks[0].embedding


def test_import_rejects_missing_metadata():
    clean_rag_tables()
    source = write_source_file("bad.md", "# Missing metadata")

    with pytest.raises(ValueError, match="metadata"):
        import_spy_sources(source.parent)


def test_import_is_idempotent_for_same_content():
    clean_rag_tables()
    source = write_source_file(
        "spy_valuation.md",
        """---
source_id: spy_valuation_test
scope: valuation
ticker: SPY
related_tickers: []
source_type: valuation_summary
source_name: Manual
published_at: 2026-01-31
retrieved_at: 2026-06-20
url: https://example.test/valuation
tags: [valuation]
confidence: medium
license_note: manual_summary
---

# Valuation Test

## Key Facts

- Valuation is elevated.
""",
    )

    first = import_spy_sources(source.parent)
    second = import_spy_sources(source.parent)

    assert first.documents_imported == 1
    assert second.documents_imported == 0
    with SessionLocal() as db:
        assert db.query(RagDocument).count() == 1


def test_import_rejects_same_source_id_with_different_content():
    clean_rag_tables()
    source = write_source_file(
        "spy_valuation.md",
        """---
source_id: spy_valuation_test
scope: valuation
ticker: SPY
related_tickers: []
source_type: valuation_summary
source_name: Manual
published_at: 2026-01-31
retrieved_at: 2026-06-20
url: https://example.test/valuation
tags: [valuation]
confidence: medium
license_note: manual_summary
---

# Valuation Test

## Key Facts

- Valuation is elevated.
""",
    )
    import_spy_sources(source.parent)
    source.write_text(
        source.read_text(encoding="utf-8").replace("Valuation is elevated.", "Valuation is cheap."),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="source_id"):
        import_spy_sources(source.parent)
