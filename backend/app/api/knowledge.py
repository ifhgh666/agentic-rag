from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from ..dependencies import get_services, require_user
from ..schemas.auth import SessionUser
from ..schemas.documents import DocumentListResponse, UploadResponse

router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.get("/documents", response_model=DocumentListResponse, response_model_exclude={"items": {"__all__": {"source_path", "markdown_path"}}})
def list_documents(_user: SessionUser = Depends(require_user), services=Depends(get_services)):
    return DocumentListResponse(items=services.documents.list_documents())


@router.post("/documents", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _user: SessionUser = Depends(require_user),
    services=Depends(get_services),
):
    content = await file.read()
    try:
        document = services.document_manager.create_upload(file.filename or "upload.pdf", content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    background_tasks.add_task(services.document_manager.process, document.document_id)
    return UploadResponse(document_id=document.document_id, status=document.status, filename=document.filename)


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: UUID, _user: SessionUser = Depends(require_user), services=Depends(get_services)):
    try:
        services.document_manager.delete(document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
