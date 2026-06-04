import io
import logging
import asyncio

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pypdf

from src.app.core.rate_limit import limiter
from src.app.services.vector_store import get_vector_store
from src.shared.schemas import DocumentUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/documents", response_model=DocumentUploadResponse)
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    file: UploadFile,
    tenant_id: str | None = Form(None),
):
    """
    Upload a document (.md or .pdf) to be chunked and indexed into the vector store.
    
    If tenant_id is provided, the document is indexed into the corresponding tenant collection partition.
    """
    filename = file.filename or "unknown"
    if not (filename.endswith(".md") or filename.endswith(".pdf")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only .md and .pdf files are supported.",
        )

    try:
        content_bytes = await file.read()
        
        if filename.endswith(".md"):
            try:
                content = content_bytes.decode("utf-8")
            except UnicodeDecodeError as decode_err:
                logger.error("Failed to decode markdown file as UTF-8", exc_info=True)
                raise HTTPException(
                    status_code=400,
                    detail="Invalid UTF-8 encoding in Markdown file.",
                ) from decode_err
        else:  # .pdf
            try:
                reader = pypdf.PdfReader(io.BytesIO(content_bytes))
                pages_text = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
                content = "\n\n".join(pages_text)
            except Exception as pdf_err:
                logger.error("Failed to parse PDF file", exc_info=True)
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to parse PDF file: {str(pdf_err)}",
                ) from pdf_err

        if not content.strip():
            raise HTTPException(
                status_code=400,
                detail="The uploaded file contains no readable text content.",
            )

        # Wrap text in a LangChain Document
        doc = Document(page_content=content, metadata={"source": filename})

        # Split into chunks using the same settings as CLI ingestion
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n## ", "\n### ", "\n---", "\n\n", "\n", " "],
        )
        splits = text_splitter.split_documents([doc])

        # Add tenant_id metadata to each split for unified tracking/filtering if needed
        if tenant_id:
            for s in splits:
                s.metadata["tenant_id"] = tenant_id

        # Index splits into Chroma DB collection partition asynchronously on a thread pool
        vs = get_vector_store()
        await asyncio.to_thread(vs.add_documents, splits, tenant_id=tenant_id)

        logger.info(
            "Successfully ingested document '%s' with %d chunks [tenant: %s]",
            filename,
            len(splits),
            tenant_id or "default",
        )

        return DocumentUploadResponse(
            filename=filename,
            chunks_count=len(splits),
            tenant_id=tenant_id,
            status="success",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error during document ingestion endpoint execution", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during ingestion: {str(e)}",
        ) from e
