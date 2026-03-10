
import os
import logging
from typing import Dict, Any, List
from pypdf import PdfReader
from docx import Document
from .base import Adapter
from ..memory.manager import MemoryManager

class DocumentIngestAdapter(Adapter):
    """
    Document Ingestion Adapter.
    Chunks and indexes PDF, DOCX, and TXT files into ChromaDB.
    """
    name = "doc_ingest"
    description = "Ingest and index PDF, DOCX, or TXT documents into long-term memory."

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.logger = logging.getLogger("DocumentIngestAdapter")

    async def execute(self, file_path: str) -> Dict[str, Any]:
        """
        Reads a document, chunks it, and stores it in memory.
        """
        try:
            if not os.path.exists(file_path):
                return {"status": "error", "message": f"File not found: {file_path}"}

            ext = os.path.splitext(file_path)[1].lower()
            text = ""

            if ext == ".pdf":
                reader = PdfReader(file_path)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            elif ext == ".docx":
                doc = Document(file_path)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            elif ext == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                return {"status": "error", "message": f"Unsupported file type: {ext}"}

            # Simple chunking (e.g., by paragraph or 1000 characters)
            chunks = self._chunk_text(text)
            for i, chunk in enumerate(chunks):
                chunk_id = f"{os.path.basename(file_path)}_{i}"
                await self.memory_manager.store(
                    chunk_id, 
                    chunk, 
                    {"source": file_path, "type": ext[1:]}
                )

            return {
                "status": "success",
                "message": f"Ingested {len(chunks)} chunks from {file_path}",
                "chunks_count": len(chunks)
            }
        except Exception as e:
            self.logger.error(f"Document ingestion failed: {e}")
            return {"status": "error", "message": str(e)}

    def _chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """
        Splits text into manageable chunks.
        """
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
