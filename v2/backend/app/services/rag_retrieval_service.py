from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import RagChunk, RagDocument, RunEvidence
from app.schemas.rag import RetrievedEvidence
from app.services.rag_embedding_service import cosine_similarity, embed_text
from app.services.rag_import_service import SPY_SOURCE_DIR, import_spy_sources


AGENT_SCOPE_FILTERS = {
    "News Analyst": {"macro", "risk"},
    "Fundamentals Analyst": {"spy_structure", "valuation", "top_holding"},
    "Portfolio Manager": {"macro", "valuation", "risk", "spy_structure"},
}


def retrieve_spy_evidence(
    db: Session,
    run_id: str,
    ticker: str,
    agent_name: str,
    query: str,
    top_k: int = 5,
) -> list[RetrievedEvidence]:
    """中文注释：第一版 RAG 只服务 SPY，避免误把 SPY 资料注入其它 ticker。"""
    if ticker.upper() != "SPY":
        return []

    allowed_scopes = AGENT_SCOPE_FILTERS.get(agent_name)
    if not allowed_scopes:
        return []

    query_embedding = embed_text(query)
    rows = (
        db.query(RagChunk, RagDocument)
        .join(RagDocument, RagChunk.document_id == RagDocument.id)
        .filter(RagDocument.ticker == "SPY")
        .filter(RagDocument.scope.in_(allowed_scopes))
        .filter(RagDocument.deleted_at.is_(None))
        .all()
    )
    ranked = sorted(
        rows,
        key=lambda pair: (
            cosine_similarity(query_embedding, pair[0].embedding),
            pair[1].published_at.isoformat() if pair[1].published_at else "",
        ),
        reverse=True,
    )[:top_k]

    results: list[RetrievedEvidence] = []
    for chunk, document in ranked:
        score = cosine_similarity(query_embedding, chunk.embedding)
        evidence = (
            db.query(RunEvidence)
            .filter_by(run_id=run_id, chunk_id=chunk.id, agent_name=agent_name, query=query)
            .one_or_none()
        )
        if evidence is None:
            # 中文注释：resume 会重新构建 context，已记录过的证据不能重复写入。
            evidence = RunEvidence(
                run_id=run_id,
                chunk_id=chunk.id,
                agent_name=agent_name,
                query=query,
                citation_key=_next_citation_key(db, run_id),
                score=score,
                excerpt=_excerpt(chunk.chunk_text),
            )
            db.add(evidence)
            db.flush()
        results.append(
            RetrievedEvidence(
                chunk_id=chunk.id,
                citation_key=evidence.citation_key,
                agent_name=agent_name,
                query=query,
                score=score,
                excerpt=evidence.excerpt,
                source_id=document.source_id,
                source_title=document.title,
                source_type=document.source_type,
                source_name=document.source_name,
                published_at=document.published_at,
                url=document.url,
            )
        )
    return results


def _next_citation_key(db: Session, run_id: str) -> str:
    # 中文注释：引用号按 run 维度稳定增长，避免 resume 后已有证据换编号。
    count = db.query(RunEvidence).filter_by(run_id=run_id).count()
    return f"E{count + 1}"


def build_spy_rag_contexts(db: Session, run_id: str, ticker: str) -> dict[str, str]:
    _ensure_spy_sources_imported(db, ticker)
    contexts: dict[str, str] = {}
    queries = {
        "News Analyst": "SPY macro policy inflation labor market latest evidence",
        "Fundamentals Analyst": "SPY holdings sector weights valuation earnings concentration",
        "Portfolio Manager": "SPY final decision risk valuation macro evidence",
    }
    for agent_name, query in queries.items():
        evidence = retrieve_spy_evidence(db, run_id, ticker, agent_name, query, top_k=5)
        context = format_evidence_context(evidence)
        if context:
            contexts[agent_name] = context
    return contexts


def format_evidence_context(items: list[RetrievedEvidence]) -> str:
    if not items:
        return ""
    lines = [
        "## Retrieved SPY Evidence",
        "",
        "Use the following retrieved evidence as factual grounding. Do not treat it as the final investment decision.",
        "When referencing evidence in your report, cite it with the provided key such as [E1].",
        "",
    ]
    for index, item in enumerate(items, start=1):
        # 中文注释：优先使用数据库里的稳定引用号，历史空值才回退到本次序号。
        key = item.citation_key or f"E{index}"
        published = item.published_at.isoformat() if item.published_at else "unknown"
        lines.extend(
            [
                f"[{key}] {item.source_title}",
                f"- Source: {item.source_name}",
                f"- Published: {published}",
                f"- Type: {item.source_type}",
                f"- Citation: cite this evidence as [{key}]",
                f"- When referencing this evidence in your report, cite it as [{key}].",
                f"- Evidence: {item.excerpt}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _excerpt(text: str, limit: int = 420) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 3] + "..."


def _ensure_spy_sources_imported(db: Session, ticker: str) -> None:
    if ticker.upper() != "SPY":
        return
    has_spy_sources = db.query(RagDocument.id).filter_by(ticker="SPY").first() is not None
    if has_spy_sources:
        return
    # 中文注释：首次 SPY 运行时导入项目内置样例资料，避免空库导致 RAG 永远不生效。
    if SPY_SOURCE_DIR.exists():
        import_spy_sources(SPY_SOURCE_DIR)
