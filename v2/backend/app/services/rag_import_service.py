from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from app.db.models import RagChunk, RagDocument
from app.db.session import SessionLocal
from app.schemas.rag import RagSourceItem
from app.services.rag_embedding_service import embed_text


REQUIRED_METADATA = {
    "source_id",
    "scope",
    "ticker",
    "source_type",
    "source_name",
    "published_at",
    "retrieved_at",
    "tags",
    "confidence",
    "license_note",
}

SPY_SOURCE_DIR = Path(__file__).resolve().parents[4] / "TradingAgents" / "rag_sources" / "spy"


@dataclass(frozen=True)
class ImportResult:
    documents_imported: int
    chunks_imported: int


def import_spy_sources(source_dir: Path) -> ImportResult:
    documents_imported = 0
    chunks_imported = 0
    for path in sorted(source_dir.rglob("*")):
        if path.suffix.lower() == ".md":
            imported_chunks = _import_markdown(path)
        elif path.suffix.lower() == ".csv":
            imported_chunks = _import_csv(path)
        else:
            continue
        if imported_chunks > 0:
            documents_imported += 1
            chunks_imported += imported_chunks
    return ImportResult(documents_imported=documents_imported, chunks_imported=chunks_imported)


def import_builtin_spy_sources() -> ImportResult:
    return import_spy_sources(SPY_SOURCE_DIR)


def import_uploaded_source(filename: str, content: bytes) -> ImportResult:
    suffix = Path(filename).suffix.lower()
    text = content.decode("utf-8-sig")
    if suffix == ".md":
        imported_chunks = _import_markdown_text(text, filename)
    elif suffix == ".txt":
        imported_chunks = _import_plain_text(filename, text)
    elif suffix == ".csv":
        imported_chunks = _import_csv_text(filename, text)
    else:
        raise ValueError("Only .md, .txt and .csv RAG sources are supported")
    return ImportResult(
        documents_imported=1 if imported_chunks > 0 else 0,
        chunks_imported=imported_chunks,
    )


def list_rag_sources() -> list[RagSourceItem]:
    with SessionLocal() as db:
        documents = (
            db.query(RagDocument)
            .order_by(RagDocument.ticker.asc(), RagDocument.scope.asc(), RagDocument.source_id.asc())
            .all()
        )
        return [
            RagSourceItem.model_validate(
                {
                    **document.__dict__,
                    "is_deleted": document.deleted_at is not None,
                }
            )
            for document in documents
        ]


def soft_delete_rag_source(source_id: str, deleted_by: str) -> bool:
    with SessionLocal() as db:
        document = db.query(RagDocument).filter_by(source_id=source_id).one_or_none()
        if document is None:
            return False
        if document.deleted_at is None:
            # 中文注释：只标记停用，不删除 chunk，避免破坏历史证据链。
            document.deleted_at = datetime.now(UTC)
            document.deleted_by = deleted_by
            db.commit()
        return True


def restore_rag_source(source_id: str) -> bool:
    with SessionLocal() as db:
        document = db.query(RagDocument).filter_by(source_id=source_id).one_or_none()
        if document is None:
            return False
        if document.deleted_at is not None:
            # 中文注释：恢复只清掉停用标记，chunk 和历史 evidence 本来就保留。
            document.deleted_at = None
            document.deleted_by = None
            db.commit()
        return True


def _import_markdown(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return _import_markdown_text(text, str(path))


def _import_markdown_text(text: str, source_label: str) -> int:
    metadata, body = _parse_frontmatter(text)
    _validate_metadata(metadata, source_label)
    title = _first_heading(body) or metadata["source_id"]
    return _upsert_document_with_chunks(metadata, title, body)


def _import_csv(path: Path) -> int:
    return _import_csv_text(path.name, path.read_text(encoding="utf-8"))


def _import_csv_text(filename: str, text: str) -> int:
    rows = list(csv.DictReader(text.splitlines()))
    if not rows:
        return 0
    source_id = rows[0].get("source_id") or Path(filename).stem
    as_of_date = rows[0].get("as_of_date") or date.today().isoformat()
    metadata = {
        "source_id": source_id,
        "scope": "spy_structure",
        "ticker": "SPY",
        "source_type": "holdings",
        "source_name": "State Street",
        "published_at": as_of_date,
        "retrieved_at": date.today().isoformat(),
        "url": "",
        "tags": ["spy", "holdings", "sector"],
        "confidence": "high",
        "license_note": "public_source",
    }
    body = _render_holdings_csv(rows)
    return _upsert_document_with_chunks(metadata, f"SPY Holdings {as_of_date}", body)


def _import_plain_text(filename: str, text: str) -> int:
    body = text.strip()
    if not body:
        return 0
    source_id = f"uploaded_{Path(filename).stem}"
    metadata = {
        "source_id": source_id,
        "scope": "macro",
        "ticker": "SPY",
        "source_type": "uploaded_text",
        "source_name": "User Upload",
        "published_at": None,
        "retrieved_at": date.today().isoformat(),
        "url": "",
        "tags": ["uploaded", "spy"],
        "confidence": "medium",
        "license_note": "user_provided",
    }
    title = _first_heading(body) or Path(filename).stem
    return _upsert_document_with_chunks(metadata, title, body)


def _upsert_document_with_chunks(metadata: dict[str, Any], title: str, body: str) -> int:
    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    with SessionLocal() as db:
        existing = db.query(RagDocument).filter_by(source_id=metadata["source_id"]).one_or_none()
        if existing is not None and existing.content_hash == content_hash:
            return 0
        if existing is not None:
            # source_id 作为证据引用的稳定身份，内容变更必须使用新的 source_id。
            raise ValueError(
                f"source_id {metadata['source_id']} already exists with different content; use a new source_id"
            )
        document = RagDocument(source_id=metadata["source_id"])
        db.add(document)
        document.ticker = metadata["ticker"].upper()
        document.scope = metadata["scope"]
        document.source_type = metadata["source_type"]
        document.source_name = metadata["source_name"]
        document.title = title
        document.published_at = _parse_date(metadata.get("published_at"))
        document.retrieved_at = _parse_date(metadata.get("retrieved_at"))
        document.url = metadata.get("url") or None
        document.tags = metadata.get("tags", [])
        document.confidence = metadata["confidence"]
        document.license_note = metadata["license_note"]
        document.document_metadata = metadata
        document.content_hash = content_hash
        db.flush()
        chunks = _split_chunks(body)
        for index, chunk_text in enumerate(chunks):
            db.add(
                RagChunk(
                    document_id=document.id,
                    chunk_index=index,
                    chunk_text=chunk_text,
                    embedding=embed_text(chunk_text),
                    token_estimate=max(1, len(chunk_text.split())),
                    chunk_metadata={"source_id": document.source_id},
                )
            )
        db.commit()
        return len(chunks)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise ValueError("Markdown source is missing YAML metadata")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("Markdown source is missing closing YAML metadata")
    raw_metadata = text[4:end]
    body = text[end + 5 :].strip()
    return _parse_simple_yaml(raw_metadata), body


def _parse_simple_yaml(raw: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for line in raw.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()]
            metadata[key.strip()] = items
        else:
            metadata[key.strip()] = value.strip("'\"")
    return metadata


def _validate_metadata(metadata: dict[str, Any], source_label: object) -> None:
    missing = sorted(REQUIRED_METADATA - set(metadata))
    if missing:
        raise ValueError(f"{source_label} metadata missing required fields: {', '.join(missing)}")
    if str(metadata["ticker"]).upper() != "SPY":
        raise ValueError(f"{source_label} metadata ticker must be SPY")


def _first_heading(body: str) -> str | None:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _split_chunks(body: str) -> list[str]:
    chunks = [part.strip() for part in body.split("\n## ") if part.strip()]
    return [chunks[0]] + [f"## {chunk}" for chunk in chunks[1:]] if chunks else []


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    return date.fromisoformat(str(value))


def _render_holdings_csv(rows: list[dict[str, str]]) -> str:
    lines = ["# SPY Holdings", "", "## Key Facts"]
    for row in rows:
        lines.append(
            f"- {row.get('ticker')} {row.get('name')} weight {row.get('weight')}% in {row.get('sector')}."
        )
    lines.extend(
        [
            "",
            "## Why It Matters For SPY",
            "SPY is market-cap weighted, so large holdings and sector concentration can drive index behavior.",
        ]
    )
    return "\n".join(lines)
