from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.models import RagChunk, RagDocument
from app.db.session import SessionLocal
from app.main import create_app


def clean_db() -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                "TRUNCATE TABLE run_evidence, rag_chunks, rag_documents, "
                "run_reports, run_metrics, run_events, runs, app_settings, users "
                "RESTART IDENTITY CASCADE"
            )
        )
        db.commit()


def make_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("SINGLE_USER_USERNAME", "admin")
    monkeypatch.setenv("SINGLE_USER_PASSWORD", "secret123")
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("RUN_AUTOSTART", "false")
    get_settings.cache_clear()
    clean_db()
    return TestClient(create_app())


def login(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert response.status_code == 200


def test_rag_sources_require_login(monkeypatch):
    client = make_client(monkeypatch)

    response = client.get("/api/rag/sources")

    assert response.status_code == 401


def test_import_spy_sources_and_list_sources(monkeypatch):
    client = make_client(monkeypatch)
    login(client)

    empty = client.get("/api/rag/sources")
    assert empty.status_code == 200
    assert empty.json()["items"] == []

    imported = client.post("/api/rag/import-spy-sources")
    assert imported.status_code == 200
    assert imported.json()["documents_imported"] == 3
    assert imported.json()["chunks_imported"] > 0

    sources = client.get("/api/rag/sources")
    assert sources.status_code == 200
    source_ids = {item["source_id"] for item in sources.json()["items"]}
    assert {"spy_fomc_sample", "spy_holdings_sample", "spy_valuation_sample"} <= source_ids

    repeated = client.post("/api/rag/import-spy-sources")
    assert repeated.status_code == 200
    assert repeated.json()["documents_imported"] == 0


def test_upload_rag_markdown_source(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    content = b"""---
source_id: spy_uploaded_fomc
scope: macro
ticker: SPY
source_type: fomc_statement
source_name: Federal Reserve
published_at: 2026-02-01
retrieved_at: 2026-06-20
url: https://example.test/uploaded-fomc
tags: [fed, rates]
confidence: high
license_note: public_source
---

# Uploaded FOMC Source

## Key Facts

- Policy stayed restrictive.
"""

    response = client.post(
        "/api/rag/upload-source",
        files={"file": ("uploaded.md", content, "text/markdown")},
    )

    assert response.status_code == 200
    assert response.json()["documents_imported"] == 1
    assert response.json()["chunks_imported"] > 0

    sources = client.get("/api/rag/sources")
    source_ids = {item["source_id"] for item in sources.json()["items"]}
    assert "spy_uploaded_fomc" in source_ids


def test_delete_rag_source_soft_deletes_document_and_hides_source(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    content = b"""---
source_id: spy_uploaded_delete_me
scope: macro
ticker: SPY
source_type: fomc_statement
source_name: Federal Reserve
published_at: 2026-02-01
retrieved_at: 2026-06-20
url: https://example.test/delete-me
tags: [fed, rates]
confidence: high
license_note: public_source
---

# Delete Me Source

## Key Facts

- This uploaded source should be disabled without deleting its chunks.
"""

    uploaded = client.post(
        "/api/rag/upload-source",
        files={"file": ("delete-me.md", content, "text/markdown")},
    )
    assert uploaded.status_code == 200

    deleted = client.delete("/api/rag/sources/spy_uploaded_delete_me")

    assert deleted.status_code == 200
    assert deleted.json()["source_id"] == "spy_uploaded_delete_me"
    assert deleted.json()["deleted"] is True

    sources = client.get("/api/rag/sources")
    disabled = next(item for item in sources.json()["items"] if item["source_id"] == "spy_uploaded_delete_me")
    assert disabled["is_deleted"] is True
    assert disabled["deleted_at"] is not None

    with SessionLocal() as db:
        document = db.query(RagDocument).filter_by(source_id="spy_uploaded_delete_me").one()
        assert document.deleted_at is not None
        assert db.query(RagChunk).filter_by(document_id=document.id).count() > 0


def test_deleted_rag_source_stays_listed_with_disabled_status(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    content = b"""---
source_id: spy_uploaded_disabled
scope: macro
ticker: SPY
source_type: fomc_statement
source_name: Federal Reserve
published_at: 2026-02-01
retrieved_at: 2026-06-20
url: https://example.test/disabled
tags: [fed, rates]
confidence: high
license_note: public_source
---

# Disabled Source

## Key Facts

- This uploaded source should stay visible for restore.
"""

    uploaded = client.post(
        "/api/rag/upload-source",
        files={"file": ("disabled.md", content, "text/markdown")},
    )
    assert uploaded.status_code == 200

    deleted = client.delete("/api/rag/sources/spy_uploaded_disabled")
    assert deleted.status_code == 200

    sources = client.get("/api/rag/sources")
    assert sources.status_code == 200
    disabled = next(item for item in sources.json()["items"] if item["source_id"] == "spy_uploaded_disabled")
    assert disabled["is_deleted"] is True
    assert disabled["deleted_at"] is not None


def test_restore_rag_source_clears_soft_delete_and_reappears(monkeypatch):
    client = make_client(monkeypatch)
    login(client)
    content = b"""---
source_id: spy_uploaded_restore_me
scope: macro
ticker: SPY
source_type: fomc_statement
source_name: Federal Reserve
published_at: 2026-02-01
retrieved_at: 2026-06-20
url: https://example.test/restore-me
tags: [fed, rates]
confidence: high
license_note: public_source
---

# Restore Me Source

## Key Facts

- This uploaded source should support restore after disable.
"""

    uploaded = client.post(
        "/api/rag/upload-source",
        files={"file": ("restore-me.md", content, "text/markdown")},
    )
    assert uploaded.status_code == 200

    deleted = client.delete("/api/rag/sources/spy_uploaded_restore_me")
    assert deleted.status_code == 200

    restored = client.post("/api/rag/sources/spy_uploaded_restore_me/restore")

    assert restored.status_code == 200
    assert restored.json()["source_id"] == "spy_uploaded_restore_me"
    assert restored.json()["restored"] is True

    sources = client.get("/api/rag/sources")
    assert sources.status_code == 200
    restored_item = next(item for item in sources.json()["items"] if item["source_id"] == "spy_uploaded_restore_me")
    assert restored_item["is_deleted"] is False
    assert restored_item["deleted_at"] is None

    with SessionLocal() as db:
        document = db.query(RagDocument).filter_by(source_id="spy_uploaded_restore_me").one()
        assert document.deleted_at is None
        assert document.deleted_by is None


def test_delete_missing_rag_source_returns_404(monkeypatch):
    client = make_client(monkeypatch)
    login(client)

    response = client.delete("/api/rag/sources/missing_source")

    assert response.status_code == 404


def test_restore_missing_rag_source_returns_404(monkeypatch):
    client = make_client(monkeypatch)
    login(client)

    response = client.post("/api/rag/sources/missing_source/restore")

    assert response.status_code == 404
