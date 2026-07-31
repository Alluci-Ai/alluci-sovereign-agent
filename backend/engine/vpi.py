import logging
import gc
from typing import List, Dict, Any, Optional

try:
    import mlx.core as mx
    from mlx_vlm import load, generate
except ImportError:
    mx = None

from ..config import settings

logger = logging.getLogger("VPI")

class VisualPolytopeIngestor:
    """
    Visual Polytope Ingestor (VPI)
    ==============================
    
    Responsible for ingesting chaotic raw documents (PDF pages converted to images),
    and utilizing the Gemma 4 Edge (E2B) visual model to extract flawless, mathematically
    accurate semantic data (Markdown, LaTeX equations, and structural tables).
    
    Follows the VRAM Hypervisor protocol to aggressively unload models and 
    prevent Apple Silicon Unified Memory fragmentation.
    """
    
    def __init__(self):
        # We fetch the target model from configuration, defaulting to the E2B 4-bit variant
        self.model_path = getattr(settings, "LOCAL_MODEL_VISUAL", "mlx-community/alluci-polytope-gemma-4-e2b-it-4bit")
        
    def _vram_hypervisor_cleanup(self, model: Any = None, processor: Any = None):
        """
        VRAM Hypervisor Protocol: Aggressively cleans up MLX memory structures.
        Ensures that the E2B visual model is completely purged from Unified Memory 
        so the system can safely promote to the 12B or 31B models without OOM panics.
        """
        logger.debug("Executing VRAM Hypervisor cleanup...")
        if model is not None:
            del model
        if processor is not None:
            del processor
            
        # Force Python garbage collection to destroy loose references
        gc.collect()
        
        # Explicitly instruct MLX Metal to clear its cached compute graphs and buffers
        if mx is not None:
            mx.clear_cache()
            logger.debug("MLX Metal cache cleared successfully.")

    def ingest_document_pages(
        self, 
        image_paths: List[str], 
        document_id: str, 
        namespace: str = "general",
        max_tokens: int = 2048,
        temperature: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Processes a list of document page images and extracts structured semantic Markdown.
        
        Args:
            image_paths: List of absolute paths to high-res page images.
            document_id: Unique identifier for this document (for Isolated Fidelity filtering).
            namespace: The domain namespace (e.g., 'finance', 'medical').
            max_tokens: Maximum tokens to generate per page.
            temperature: Low temperature for deterministic semantic extraction.
            
        Returns:
            A list of dictionaries representing the extracted structured data for each page.
        """
        if mx is None:
            logger.error("MLX or mlx_vlm is not installed. VPI cannot execute on Apple Silicon.")
            raise ImportError("mlx and mlx_vlm are required for the Visual Polytope Ingestor.")
            
        if not image_paths:
            logger.warning(f"VPI received 0 images for document '{document_id}'.")
            return []

        logger.info(f"VPI initiating ingestion for document '{document_id}' ({len(image_paths)} pages) in namespace '{namespace}'.")
        
        extracted_pages = []
        model = None
        processor = None
        
        try:
            # Load the visual model into Unified Memory
            logger.info(f"Loading visual model '{self.model_path}' into memory...")
            model, processor = load(self.model_path)
            
            # The prompt used to enforce flawless structural extraction
            extraction_prompt = (
                "You are an expert document parser. Carefully analyze this image. "
                "Extract all text, tables, and mathematical equations exactly as they appear. "
                "Format your output in flawless Markdown. Preserve the logical structure, headings, "
                "and relationships. Use LaTeX formatting for all mathematical equations."
            )
            
            for index, img_path in enumerate(image_paths):
                logger.debug(f"Parsing page {index + 1}/{len(image_paths)}: {img_path}")
                
                # Depending on the exact mlx_vlm version, the generate function signature varies.
                # Usually it accepts the prompt and image directly.
                # For Gemma 4, we use the standard completion format.
                prompt_formatted = f"User: <image>\n{extraction_prompt}\nAssistant:"
                
                try:
                    response = generate(
                        model,
                        processor,
                        prompt_formatted,
                        image=[img_path],
                        max_tokens=max_tokens,
                        temperature=temperature,
                        verbose=False
                    )
                    
                    extracted_pages.append({
                        "page_number": index + 1,
                        "document_id": document_id,
                        "namespace": namespace,
                        "source_image": img_path,
                        "extracted_markdown": response.strip(),
                        "extraction_status": "success"
                    })
                except Exception as e:
                    logger.error(f"Failed to parse page {index + 1} ({img_path}): {e}")
                    extracted_pages.append({
                        "page_number": index + 1,
                        "document_id": document_id,
                        "namespace": namespace,
                        "source_image": img_path,
                        "extracted_markdown": "",
                        "extraction_status": f"error: {str(e)}"
                    })
                    
        except Exception as e:
            logger.error(f"VPI encountered a critical failure during document ingestion: {e}")
            raise
            
        finally:
            # VRAM Hypervisor: Guarantee that the massive VLM is wiped from Unified Memory
            # even if an exception occurred during the loop.
            self._vram_hypervisor_cleanup(model, processor)
            
        logger.info(f"VPI successfully processed {len(extracted_pages)} pages for document '{document_id}'.")
        return extracted_pages
