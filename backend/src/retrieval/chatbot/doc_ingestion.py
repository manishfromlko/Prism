"""Ingestion pipeline for Word documents in data/platform_documents/."""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List

from ..config import RetrievalConfig
from ..embeddings import EmbeddingService
from .doc_store import DocumentChunkStore

logger = logging.getLogger(__name__)

DOCS_DIR = Path(
    os.getenv(
        "PLATFORM_DOCS_DIR",
        str(Path(__file__).parents[4] / "data" / "platform_documents"),
    )
)
CHUNK_SIZE = 800   # characters
CHUNK_OVERLAP = 150


def _read_docx(path: Path) -> str:
    """Extract plain text from a .docx file."""
    try:
        import docx  # python-docx
        doc = docx.Document(str(path))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except ImportError:
        raise RuntimeError(
            "python-docx is required for Word document ingestion. "
            "Install with: pip install python-docx"
        )


def _split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping character chunks, respecting paragraph boundaries."""
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if not current:
            current = para
        elif len(current) + len(para) + 2 <= chunk_size:
            current = current + "\n\n" + para
        else:
            chunks.append(current)
            # Start next chunk with overlap from the end of current
            overlap_text = current[-overlap:] if len(current) > overlap else current
            current = overlap_text + "\n\n" + para

    if current:
        chunks.append(current)

    return chunks


def _doc_id_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r"[^a-z0-9_]", "_", stem.lower())


def ingest_platform_docs(docs_dir: Path = DOCS_DIR, drop_existing: bool = False) -> Dict:
    """
    Read all .docx files from docs_dir, chunk them, embed, and store in platform_docs.

    Returns summary dict: {inserted, files_processed, errors}
    """
    config = RetrievalConfig.from_env()
    embedding_service = EmbeddingService(config)
    store = DocumentChunkStore(config)
    store.create_collection(drop_if_exists=drop_existing)

    doc_files = list(docs_dir.glob("*.docx"))
    if not doc_files:
        logger.warning(f"No .docx files found in {docs_dir}")
        return {"inserted": 0, "files_processed": 0, "errors": []}

    all_chunks: List[Dict] = []
    errors: List[str] = []

    for doc_path in doc_files:
        try:
            logger.info(f"Processing: {doc_path.name}")
            text = _read_docx(doc_path)
            if not text.strip():
                logger.warning(f"Empty document: {doc_path.name}")
                continue

            raw_chunks = _split_into_chunks(text)
            doc_id = _doc_id_from_filename(doc_path.name)

            for idx, chunk_text in enumerate(raw_chunks):
                all_chunks.append({
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_chunk_{idx:04d}",
                    "chunk_text": chunk_text,
                    "source_file": doc_path.name,
                    "vector": None,  # filled below
                })

            logger.info(f"  → {len(raw_chunks)} chunks from {doc_path.name}")
        except Exception as e:
            logger.error(f"Failed to process {doc_path.name}: {e}")
            errors.append(f"{doc_path.name}: {e}")

    if not all_chunks:
        return {"inserted": 0, "files_processed": len(doc_files) - len(errors), "errors": errors}

    logger.info(f"Embedding {len(all_chunks)} chunks…")
    texts = [c["chunk_text"] for c in all_chunks]
    vectors = embedding_service.generate_embeddings(texts)
    for chunk, vec in zip(all_chunks, vectors):
        chunk["vector"] = vec

    inserted = store.upsert_chunks(all_chunks)
    logger.info(f"Ingestion complete: {inserted} chunks stored in platform_docs")

    return {
        "inserted": inserted,
        "files_processed": len(doc_files) - len(errors),
        "errors": errors,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = ingest_platform_docs()
    print(result)
