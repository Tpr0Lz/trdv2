from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import require_current_username
from app.schemas.rag import RagDeleteResponse, RagImportResponse, RagRestoreResponse, RagSourcesResponse
from app.services.rag_import_service import (
    import_builtin_spy_sources,
    import_uploaded_source,
    list_rag_sources,
    restore_rag_source,
    soft_delete_rag_source,
)

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/sources", response_model=RagSourcesResponse)
def get_rag_sources(username: str = Depends(require_current_username)) -> RagSourcesResponse:
    return RagSourcesResponse(items=list_rag_sources())


@router.post("/import-spy-sources", response_model=RagImportResponse)
def import_spy_sources(username: str = Depends(require_current_username)) -> RagImportResponse:
    # 中文注释：显式导入项目内置 SPY RAG 资料，便于演示 RAG 数据准备流程。
    result = import_builtin_spy_sources()
    return RagImportResponse(
        documents_imported=result.documents_imported,
        chunks_imported=result.chunks_imported,
    )


@router.delete("/sources/{source_id}", response_model=RagDeleteResponse)
def delete_rag_source(
    source_id: str,
    username: str = Depends(require_current_username),
) -> RagDeleteResponse:
    deleted = soft_delete_rag_source(source_id, username)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG source not found")
    return RagDeleteResponse(source_id=source_id, deleted=True)


@router.post("/sources/{source_id}/restore", response_model=RagRestoreResponse)
def restore_deleted_rag_source(
    source_id: str,
    username: str = Depends(require_current_username),
) -> RagRestoreResponse:
    restored = restore_rag_source(source_id)
    if not restored:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG source not found")
    return RagRestoreResponse(source_id=source_id, restored=True)


@router.post("/upload-source", response_model=RagImportResponse)
async def upload_rag_source(
    file: UploadFile = File(...),
    username: str = Depends(require_current_username),
) -> RagImportResponse:
    # 中文注释：上传内容直接写入 PostgreSQL，不在本机磁盘保留原始文件。
    content = await file.read()
    try:
        result = import_uploaded_source(file.filename or "uploaded.md", content)
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RAG source must be UTF-8 text",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return RagImportResponse(
        documents_imported=result.documents_imported,
        chunks_imported=result.chunks_imported,
    )
