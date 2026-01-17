"""
Paragraph-aware overlapping text chunker for RAG.

Implements intelligent text chunking that:
- Respects paragraph boundaries (\\n\\n)
- Preserves Markdown headings as section markers
- Maintains configurable overlap between chunks
- Handles token counting via tiktoken
"""

import re
import logging
from typing import List, Optional, Tuple
import tiktoken

from .models import Chunk
from .config import ChunkingConfig

logger = logging.getLogger(__name__)


class OverlappingChunker:
    """
    Paragraph-aware chunker with overlapping windows.

    Breaks text into chunks while respecting:
    - Paragraph boundaries (\\n\\n)
    - Markdown headings (# ## ###)
    - Sentence boundaries (. ! ?)
    - Configurable overlap for context continuity
    """

    def __init__(self, config: ChunkingConfig):
        self.config = config
        # Use cl100k_base encoding (GPT-4, GPT-3.5-turbo)
        self.encoding = tiktoken.get_encoding("cl100k_base")

        # Markdown heading pattern
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    def chunk_text(
        self,
        text: str,
        doc_id: str,
        user_id: str,
        filename: str
    ) -> List[Chunk]:
        """
        Chunk text into overlapping segments.

        Args:
            text: Text content to chunk
            doc_id: Document identifier
            user_id: User identifier
            filename: Original filename

        Returns:
            List of Chunk objects with metadata
        """
        if not text.strip():
            logger.warning(f"Empty text provided for chunking: {filename}")
            return []

        # Split into paragraphs first
        paragraphs = self._split_into_paragraphs(text)

        # Build chunks respecting paragraph boundaries
        chunks = []
        current_chunk_text = ""
        current_chunk_start = 0
        current_section_heading = None
        chunk_index = 0

        for para_text, para_start, heading in paragraphs:
            # Update current section heading if we found one
            if heading:
                current_section_heading = heading

            # Count tokens in current chunk + new paragraph
            combined_text = current_chunk_text + "\n\n" + para_text if current_chunk_text else para_text
            combined_tokens = self._count_tokens(combined_text)

            # If adding this paragraph exceeds max chunk size, save current chunk
            if combined_tokens > self.config.chunk_size and current_chunk_text:
                # Save current chunk
                chunk = self._create_chunk(
                    text=current_chunk_text.strip(),
                    doc_id=doc_id,
                    user_id=user_id,
                    chunk_index=chunk_index,
                    start_offset=current_chunk_start,
                    end_offset=current_chunk_start + len(current_chunk_text),
                    filename=filename,
                    section_heading=current_section_heading
                )
                chunks.append(chunk)
                chunk_index += 1

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk_text)
                current_chunk_text = overlap_text + "\n\n" + para_text if overlap_text else para_text
                current_chunk_start = para_start - len(overlap_text)
            else:
                # Add paragraph to current chunk
                if current_chunk_text:
                    current_chunk_text += "\n\n" + para_text
                else:
                    current_chunk_text = para_text
                    current_chunk_start = para_start

        # Add final chunk if any text remains
        if current_chunk_text.strip():
            chunk = self._create_chunk(
                text=current_chunk_text.strip(),
                doc_id=doc_id,
                user_id=user_id,
                chunk_index=chunk_index,
                start_offset=current_chunk_start,
                end_offset=current_chunk_start + len(current_chunk_text),
                filename=filename,
                section_heading=current_section_heading
            )
            chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks for document: {filename}")
        return chunks

    def _split_into_paragraphs(self, text: str) -> List[Tuple[str, int, Optional[str]]]:
        """
        Split text into paragraphs, tracking positions and headings.

        Returns:
            List of (paragraph_text, start_position, heading) tuples
        """
        paragraphs = []
        current_pos = 0

        # Split by double newlines (paragraph boundaries)
        para_texts = re.split(r'\n\n+', text)

        for para_text in para_texts:
            if not para_text.strip():
                current_pos += len(para_text) + 2  # +2 for \n\n
                continue

            # Check if paragraph is a Markdown heading
            heading = None
            if self.config.markdown_heading_aware:
                heading_match = self.heading_pattern.match(para_text.strip())
                if heading_match:
                    heading = heading_match.group(2).strip()

            # Find actual position in original text
            start_pos = text.find(para_text, current_pos)
            paragraphs.append((para_text.strip(), start_pos, heading))

            current_pos = start_pos + len(para_text)

        return paragraphs

    def _get_overlap_text(self, text: str) -> str:
        """
        Extract overlap text from end of previous chunk.

        Returns last N tokens as overlap for next chunk.
        """
        tokens = self.encoding.encode(text)
        overlap_token_count = min(self.config.chunk_overlap, len(tokens))

        if overlap_token_count == 0:
            return ""

        overlap_tokens = tokens[-overlap_token_count:]
        overlap_text = self.encoding.decode(overlap_tokens)

        # Try to break at sentence boundary if configured
        if self.config.respect_sentence_boundary:
            # Find last sentence boundary in overlap
            sentence_breaks = [m.end() for m in re.finditer(r'[.!?]\s+', overlap_text)]
            if sentence_breaks:
                last_break = sentence_breaks[-1]
                overlap_text = overlap_text[last_break:]

        return overlap_text

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoding.encode(text))

    def _create_chunk(
        self,
        text: str,
        doc_id: str,
        user_id: str,
        chunk_index: int,
        start_offset: int,
        end_offset: int,
        filename: str,
        section_heading: Optional[str] = None
    ) -> Chunk:
        """Create a Chunk object with metadata."""
        token_count = self._count_tokens(text)

        metadata = {
            "filename": filename,
        }

        if section_heading:
            metadata["section_heading"] = section_heading

        return Chunk(
            doc_id=doc_id,
            user_id=user_id,
            text=text,
            chunk_index=chunk_index,
            start_offset=start_offset,
            end_offset=end_offset,
            token_count=token_count,
            metadata=metadata
        )
