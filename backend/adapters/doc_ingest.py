
import os
from ..logging_config import get_logger
from typing import Dict, Any, List
try:
    from pypdf import PdfReader
except ImportError:
    class PdfReader:
        def __init__(self, file_path):
            self.pages = []  # No pages; stub
        # If needed, could implement minimal interface

try:
    from docx import Document
except ImportError:
    class Document:
        def __init__(self, file_path=None):
            self.paragraphs = []  # Empty list of paragraphs

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
        self.logger = get_logger("DocumentIngestAdapter")

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reads a document, chunks it, and stores each chunk in long-term memory.

        args:
            file_path (str): Absolute or relative path to the file to ingest.
                             Also accepted as 'path' for convenience.
        """
        # Accept both 'file_path' and 'path' keys for flexibility
        file_path = args.get("file_path") or args.get("path") if isinstance(args, dict) else str(args)

        if not file_path:
            return {"status": "error", "message": "No 'file_path' provided in args."}

        try:
            if not os.path.exists(file_path):
                return {"status": "error", "message": f"File not found: {file_path}"}

            ext = os.path.splitext(file_path)[1].lower()
            text = ""

            if ext == ".pdf":
                reader = PdfReader(file_path)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            elif ext == ".docx":
                doc = Document(file_path)
                for para in doc.paragraphs:
                    if para.text.strip():
                        text += para.text + "\n"
            elif ext in [".txt", ".md"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                return {"status": "error", "message": f"Unsupported file type: {ext}. Supported: .pdf, .docx, .txt, .md"}

            if not text.strip():
                return {"status": "error", "message": f"No extractable text found in {file_path}"}


            chunks = self._chunk_text(text, ext=ext)
            filename = os.path.basename(file_path)

            for i, chunk in enumerate(chunks):
                # store(content, metadata) — content is the chunk text, metadata is the provenance
                await self.memory_manager.store(
                    content=chunk,
                    metadata={
                        "source": file_path,
                        "filename": filename,
                        "file_type": ext[1:],
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                    },
                )
                # Future: Route the chunk through the LLM to extract L3 Kuzu Graph nodes/edges
                self._extract_entities_for_graph(chunk)

            self.logger.info(f"[ DOC_INGEST ] Ingested {len(chunks)} chunks from '{filename}'")
            return {
                "status": "success",
                "message": f"Ingested {len(chunks)} chunks from {filename}",
                "chunks_count": len(chunks),
                "file_path": file_path,
            }
        except Exception as e:
            self.logger.error(f"Document ingestion failed for '{file_path}': {e}")
            return {"status": "error", "message": str(e)}

    def _chunk_text(self, text: str, chunk_size: int = 1000, ext: str = ".txt") -> List[str]:
        """
        Splits text into manageable chunks.
        For markdown files, it attempts to split by headers semantically.
        """
        if ext == ".md":
            import re
            # Split by markdown headers
            chunks = re.split(r'(?m)^#{1,6}\s+.*$', text)
            headers = re.findall(r'(?m)^#{1,6}\s+.*$', text)
            
            result = []
            if chunks and chunks[0].strip():
                result.append(chunks[0].strip())
            
            for i, header in enumerate(headers):
                if i + 1 < len(chunks):
                    chunk_content = header + "\n" + chunks[i + 1].strip()
                    if chunk_content.strip():
                        result.append(chunk_content.strip())
            
            # If the chunks are too large, fallback to byte-chunking
            final_chunks = []
            for c in result:
                if len(c) > chunk_size * 2:
                    final_chunks.extend([c[i:i + chunk_size] for i in range(0, len(c), chunk_size)])
                else:
                    final_chunks.append(c)
            if final_chunks:
                return final_chunks
                
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    def _extract_entities_for_graph(self, chunk: str) -> None:
        """
        Extracts Graph entities (Nodes/Edges) for L3 Kuzu ingestion.
        Implemented via cognitive LLM pass in the broader ingestion pipeline.
        """
        # Scaffolding for Kuzu L3 Memory Pipeline
        pass
