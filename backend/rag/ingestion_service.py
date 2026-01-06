"""
Document ingestion service for RAG.

Handles the complete pipeline:
1. File validation and reading
2. Text chunking
3. Embedding generation
4. Vector store persistence
5. Document metadata storage
"""

import logging
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from .models import Document, Chunk
from .chunking import OverlappingChunker
from .embeddings import IEmbeddingService
from .vector_store import IVectorStore
from .config import IngestionConfig

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Service for ingesting documents into the RAG system.

    Pipeline: file → chunks → embeddings → vector store
    """

    def __init__(
        self,
        chunker: OverlappingChunker,
        embedding_service: IEmbeddingService,
        vector_store: IVectorStore,
        config: Optional[IngestionConfig] = None
    ):
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.config = config or IngestionConfig()

        logger.info("Initialized ingestion service")

    async def ingest_file(
        self,
        file_path: Path,
        user_id: str,
        filename: str
    ) -> Document:
        """
        Ingest a document file into the RAG system.

        Args:
            file_path: Path to the file to ingest
            user_id: User identifier
            filename: Original filename

        Returns:
            Document object with metadata

        Raises:
            ValueError: If file type not supported or file too large
            IOError: If file cannot be read
        """
        # Validate file
        self._validate_file(file_path, filename)

        # Read file content
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try with latin-1 as fallback
            content = file_path.read_text(encoding='latin-1')
            logger.warning(f"File {filename} decoded with latin-1 encoding")

        # Create document object
        document = Document(
            user_id=user_id,
            filename=filename,
            content=content,
            size_chars=len(content)
        )

        logger.info(f"Starting ingestion for {filename} ({document.size_chars} chars)")

        # Chunk the text
        chunks = self.chunker.chunk_text(
            text=content,
            doc_id=document.doc_id,
            user_id=user_id,
            filename=filename
        )

        document.chunk_count = len(chunks)

        if not chunks:
            logger.warning(f"No chunks created for {filename}")
            return document

        # Generate embeddings
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = await self.embedding_service.embed_texts(chunk_texts)

        # Store in vector database
        await self.vector_store.add_chunks(chunks, embeddings)

        # Save document metadata if configured
        if self.config.store_document_metadata:
            await self._save_document_metadata(document, user_id)

        # Save raw document if configured
        if self.config.store_raw_documents:
            await self._save_raw_document(document, file_path, user_id)

        logger.info(
            f"Successfully ingested {filename}: "
            f"{len(chunks)} chunks, {document.size_chars} chars"
        )

        return document

    async def delete_document(self, doc_id: str, user_id: str) -> int:
        """
        Delete a document and all its chunks.

        Args:
            doc_id: Document identifier
            user_id: User identifier

        Returns:
            Number of chunks deleted
        """
        # Delete from vector store
        deleted_count = await self.vector_store.delete_document(doc_id, user_id)

        # Delete metadata file if exists
        user_dir = self.config.get_user_upload_dir(user_id)
        metadata_file = user_dir / f"{doc_id}.json"
        if metadata_file.exists():
            metadata_file.unlink()
            logger.info(f"Deleted metadata file: {metadata_file}")

        # Delete raw document file if exists
        # Find file with doc_id prefix
        for file_path in user_dir.glob(f"{doc_id}__*"):
            file_path.unlink()
            logger.info(f"Deleted raw document: {file_path}")

        logger.info(f"Deleted document {doc_id}: {deleted_count} chunks removed")
        return deleted_count

    async def get_document_metadata(self, doc_id: str, user_id: str) -> Optional[Document]:
        """
        Retrieve document metadata.

        Args:
            doc_id: Document identifier
            user_id: User identifier

        Returns:
            Document object or None if not found
        """
        user_dir = self.config.get_user_upload_dir(user_id)
        metadata_file = user_dir / f"{doc_id}.json"

        if not metadata_file.exists():
            return None

        try:
            metadata_dict = json.loads(metadata_file.read_text())
            return Document(**metadata_dict)
        except Exception as e:
            logger.error(f"Error loading document metadata: {e}")
            return None

    def _validate_file(self, file_path: Path, filename: str) -> None:
        """Validate file type and size."""
        # Check file extension
        if not any(filename.lower().endswith(ext) for ext in self.config.supported_extensions):
            raise ValueError(
                f"Unsupported file type. Supported: {', '.join(self.config.supported_extensions)}"
            )

        # Check file size
        if not file_path.exists():
            raise IOError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size
        if file_size > self.config.max_file_size_bytes:
            raise ValueError(
                f"File too large: {file_size} bytes "
                f"(max: {self.config.max_file_size_bytes} bytes)"
            )

    async def _save_document_metadata(self, document: Document, user_id: str) -> None:
        """Save document metadata to JSON file."""
        user_dir = self.config.get_user_upload_dir(user_id)
        metadata_file = user_dir / f"{document.doc_id}.json"

        try:
            # Don't store full content in metadata (too large)
            metadata_dict = document.dict(exclude={'content'})
            metadata_file.write_text(json.dumps(metadata_dict, indent=2, default=str))
            logger.debug(f"Saved document metadata: {metadata_file}")
        except Exception as e:
            logger.error(f"Error saving document metadata: {e}")

    async def _save_raw_document(
        self,
        document: Document,
        source_path: Path,
        user_id: str
    ) -> None:
        """Save raw document file to uploads directory."""
        user_dir = self.config.get_user_upload_dir(user_id)
        # Use doc_id prefix to make it easy to find and delete later
        dest_path = user_dir / f"{document.doc_id}__{document.filename}"

        try:
            # Copy file if source is different from destination
            if source_path.resolve() != dest_path.resolve():
                dest_path.write_text(document.content, encoding='utf-8')
                logger.debug(f"Saved raw document: {dest_path}")
        except Exception as e:
            logger.error(f"Error saving raw document: {e}")
