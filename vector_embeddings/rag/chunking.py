"""
Text chunking with overlap.

This module implements overlapping text chunking for RAG pipelines.
"""

from typing import List
import hashlib
from rag.models import Chunk, Document
from rag.config import ChunkingConfig


class OverlappingChunker:
    """
    Chunks text into overlapping segments for better context preservation.
    
    Overlap helps ensure that information split across chunk boundaries
    is still captured in at least one chunk completely.
    """
    
    def __init__(self, config: ChunkingConfig = None):
        """
        Initialize the chunker.
        
        Args:
            config: Chunking configuration (size and overlap).
        """
        self.config = config or ChunkingConfig()
    
    def chunk_text(
        self,
        text: str,
        doc_id: str,
        tenant_id: str,
        metadata: dict = None
    ) -> List[Chunk]:
        """
        Chunk text with overlap.
        
        Args:
            text: The text to chunk.
            doc_id: Document ID.
            tenant_id: Tenant ID for multi-tenancy.
            metadata: Additional metadata to attach to chunks.
        
        Returns:
            List of Chunk objects with metadata.
        """
        if not text or not text.strip():
            return []
        
        metadata = metadata or {}
        chunks = []
        chunk_size = self.config.chunk_size
        chunk_overlap = self.config.chunk_overlap
        
        # Ensure overlap is smaller than chunk size
        if chunk_overlap >= chunk_size:
            chunk_overlap = chunk_size // 2
        
        start = 0
        chunk_index = 0
        text_length = len(text)
        
        while start < text_length:
            # Calculate end position
            end = min(start + chunk_size, text_length)
            
            # Extract chunk text
            chunk_text = text[start:end].strip()
            
            # Skip empty chunks
            if not chunk_text:
                break
            
            # Generate chunk ID
            chunk_id = self._generate_chunk_id(doc_id, chunk_index)
            
            # Create chunk object
            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                tenant_id=tenant_id,
                text=chunk_text,
                start_offset=start,
                end_offset=end,
                chunk_index=chunk_index,
                metadata={**metadata}
            )
            
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            # If this was the last chunk, break
            if end >= text_length:
                break
            
            # Move start forward by (chunk_size - overlap)
            start = start + chunk_size - chunk_overlap
            chunk_index += 1
        
        return chunks
    
    def chunk_document(self, document: Document) -> List[Chunk]:
        """
        Chunk a Document object.
        
        Args:
            document: Document to chunk.
        
        Returns:
            List of chunks.
        """
        metadata = {
            "filename": document.filename,
            "source_path": document.source_path,
            "doc_hash": document.hash
        }
        
        return self.chunk_text(
            text=document.text,
            doc_id=document.doc_id,
            tenant_id=document.tenant_id,
            metadata=metadata
        )
    
    @staticmethod
    def _generate_chunk_id(doc_id: str, chunk_index: int) -> str:
        """Generate a unique chunk ID."""
        content = f"{doc_id}:chunk_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def get_chunk_boundaries_sample(self, chunks: List[Chunk], count: int = 2) -> str:
        """
        Get a sample of chunk boundaries for teaching/debugging.
        
        Args:
            chunks: List of chunks.
            count: Number of chunks to sample.
        
        Returns:
            Formatted string showing chunk boundaries.
        """
        if not chunks:
            return "No chunks to display."
        
        output = []
        for i, chunk in enumerate(chunks[:count]):
            output.append(f"\n--- Chunk {i} (ID: {chunk.chunk_id}) ---")
            output.append(f"Offsets: {chunk.start_offset}-{chunk.end_offset}")
            output.append(f"Length: {len(chunk.text)} chars")
            output.append(f"Text preview: {chunk.text[:100]}...")
            
            # Show overlap with next chunk if exists
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                overlap_start = next_chunk.start_offset
                overlap_end = chunk.end_offset
                if overlap_start < overlap_end:
                    overlap_length = overlap_end - overlap_start
                    output.append(f"Overlap with next chunk: {overlap_length} chars")
        
        return "\n".join(output)
