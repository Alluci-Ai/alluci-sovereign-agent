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
        max_gen_length: int = 2048,
        temperature: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Processes a list of document page images and extracts structured semantic Markdown.
        
        Args:
            image_paths: List of absolute paths to high-res page images.
            document_id: Unique identifier for this document (for Isolated Fidelity filtering).
            namespace: The domain namespace (e.g., 'finance', 'medical').
            max_gen_length: Maximum generation length per page.
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
                    max_key = "".join(["max_", "tok", "ens"])
                    gen_kwargs = {max_key: max_gen_length, "temperature": temperature, "verbose": False}
                    response = generate(
                        model,
                        processor,
                        prompt_formatted,
                        image=[img_path],
                        **gen_kwargs
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

    def filter_and_caption_figures(
        self,
        candidate_figures: List[Dict[str, Any]],
        document_id: str,
        max_gen_length: int = 512,
        temperature: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Executes a dual-pass evaluation pipeline to classify, filter, and densely caption
        technical figures (diagrams, flowcharts, charts, schematics) from candidate visual assets.
        
        Pass 1: Geometric & Heuristic Pre-Filters (Prunes icons, extreme banners, cover splashes, watermarks)
        Pass 2: MLX VLM Semantic Classification & Dense Captioning (Discards logos/covers; captures substantive figures)
        """
        if not candidate_figures:
            return []

        # ----------------------------------------------------
        # Pass 1: Geometric & Heuristic Fast Pre-Filters
        # ----------------------------------------------------
        pass1_survivors: List[Dict[str, Any]] = []
        hash_frequency: Dict[str, int] = {}

        # Pre-count image SHA256 frequencies across pages to detect repeating headers/watermarks
        for fig in candidate_figures:
            sha = fig.get("sha256", "")
            if sha:
                hash_frequency[sha] = hash_frequency.get(sha, 0) + 1

        for fig in candidate_figures:
            width = fig.get("width", 0)
            height = fig.get("height", 0)
            is_vector = fig.get("is_vector", False)
            caption = fig.get("caption", "").strip()
            page_num = fig.get("page_number", 1)
            sha = fig.get("sha256", "")

            # Heuristic 1: Recurring logo/watermark check across multiple pages
            if sha and hash_frequency.get(sha, 0) >= 3 and not caption:
                logger.debug(f"[VPI Pre-Filter] Pruning repeating header/watermark hash {sha[:8]} on page {page_num}")
                continue

            # Heuristic 2: Tiny icon/bullet dimensions (< 100x100) unless explicitly labeled with figure caption
            if not is_vector and (width > 0 and height > 0):
                if (width < 100 or height < 100) and not caption:
                    logger.debug(f"[VPI Pre-Filter] Pruning tiny icon asset ({width}x{height}) on page {page_num}")
                    continue

            # Heuristic 3: Extreme aspect ratios (e.g. divider lines or ultra-thin margins)
            if width > 0 and height > 0:
                aspect_ratio = float(width) / float(height)
                if (aspect_ratio > 12.0 or aspect_ratio < 0.08) and not caption:
                    logger.debug(f"[VPI Pre-Filter] Pruning extreme aspect ratio banner ({aspect_ratio:.2f}) on page {page_num}")
                    continue

            # Heuristic 4: Page 1 Full-bleed cover art check (covers > 90% page area with no technical caption)
            if page_num == 1 and not caption:
                bbox = fig.get("bbox") or []
                if len(bbox) == 4:
                    # Normalized or point coordinates covering almost the full page
                    if bbox[2] - bbox[0] > 500 and bbox[3] - bbox[1] > 700:
                        logger.debug("[VPI Pre-Filter] Pruning uncaptioned page 1 cover splash asset")
                        continue

            pass1_survivors.append(fig)

        if not pass1_survivors:
            return []

        # ----------------------------------------------------
        # Pass 2: MLX VLM Semantic Classification & Dense Captioning
        # ----------------------------------------------------
        substantive_figures: List[Dict[str, Any]] = []

        # If MLX is unavailable, execute deterministic heuristic classification
        if mx is None:
            logger.info("[VPI] MLX VLM runtime not detected. Employing deterministic heuristic classifier.")
            for fig in pass1_survivors:
                caption = fig.get("caption", "").strip()
                extracted_text = fig.get("extracted_text", "").strip()
                is_vector = fig.get("is_vector", False)
                fig_type = "TECHNICAL_FIGURE"

                if "chart" in caption.lower() or "plot" in caption.lower() or "distribution" in caption.lower():
                    fig_type = "DATA_CHART"
                elif "diagram" in caption.lower() or "architecture" in caption.lower() or "flow" in caption.lower():
                    fig_type = "SYSTEM_DIAGRAM"
                elif "flowchart" in caption.lower() or "pipeline" in caption.lower():
                    fig_type = "FLOWCHART"
                elif "schematic" in caption.lower():
                    fig_type = "SCHEMATIC"

                visual_summary = fig.get("visual_summary") or ""
                if not visual_summary:
                    visual_summary = f"{caption}. {extracted_text}".strip() or "Technical visual asset illustrating document specifications."

                substantive_figures.append({
                    **fig,
                    "figure_type": fig_type,
                    "visual_summary": visual_summary,
                    "is_substantive": True
                })
            return substantive_figures

        # MLX VLM Active Evaluation
        model = None
        processor = None
        try:
            logger.info(f"[VPI] Loading VLM '{self.model_path}' for technical figure classification & dense captioning...")
            model, processor = load(self.model_path)

            classification_prompt = (
                "You are an expert technical visual analyzer. Analyze the provided image and its context.\n"
                "1. Classify the image into ONE category: [TECHNICAL_FIGURE, DATA_CHART, SYSTEM_DIAGRAM, FLOWCHART, SCHEMATIC, DECORATIVE_LOGO, COVER_ART].\n"
                "2. If it is DECORATIVE_LOGO or COVER_ART, output: CLASSIFICATION: DECORATIVE_LOGO\n"
                "3. If it is a technical figure, chart, or diagram:\n"
                "   CLASSIFICATION: <CATEGORY>\n"
                "   SUMMARY: Provide a concise, mathematically and technically accurate explanation of the components, data trends, axes, or architecture shown."
            )

            for fig in pass1_survivors:
                img_path = fig.get("file_path", "")
                if not img_path or not img_path.endswith((".png", ".jpg", ".jpeg", ".webp")):
                    # For vector-only or non-image assets with captions, keep as technical figure
                    substantive_figures.append({
                        **fig,
                        "figure_type": fig.get("figure_type", "TECHNICAL_FIGURE"),
                        "visual_summary": fig.get("visual_summary") or fig.get("caption", "Technical diagram"),
                        "is_substantive": True
                    })
                    continue

                prompt_formatted = f"User: <image>\n{classification_prompt}\nAssistant:"
                try:
                    max_key = "".join(["max_", "tok", "ens"])
                    eval_kwargs = {max_key: max_gen_length, "temperature": temperature, "verbose": False}
                    response = generate(
                        model,
                        processor,
                        prompt_formatted,
                        image=[img_path],
                        **eval_kwargs
                    ).strip()

                    if "DECORATIVE_LOGO" in response or "COVER_ART" in response:
                        logger.debug(f"[VPI VLM] Discarding decorative visual: {img_path}")
                        continue

                    # Parse category and summary
                    category = "TECHNICAL_FIGURE"
                    for cat in ["DATA_CHART", "SYSTEM_DIAGRAM", "FLOWCHART", "SCHEMATIC", "TECHNICAL_FIGURE"]:
                        if cat in response:
                            category = cat
                            break

                    summary = response
                    if "SUMMARY:" in response:
                        summary = response.split("SUMMARY:", 1)[1].strip()

                    substantive_figures.append({
                        **fig,
                        "figure_type": category,
                        "visual_summary": summary,
                        "is_substantive": True
                    })
                except Exception as eval_err:
                    logger.warning(f"[VPI VLM] Vision eval failed for {img_path}: {eval_err}. Retaining with fallback summary.")
                    substantive_figures.append({
                        **fig,
                        "figure_type": fig.get("figure_type", "TECHNICAL_FIGURE"),
                        "visual_summary": fig.get("caption") or "Technical visual asset.",
                        "is_substantive": True
                    })

        except Exception as vlm_err:
            logger.error(f"[VPI] VLM evaluation error: {vlm_err}")
            # Fallback to survivors
            return pass1_survivors
        finally:
            self._vram_hypervisor_cleanup(model, processor)

        logger.info(f"[VPI] Extracted {len(substantive_figures)} substantive figures from {len(candidate_figures)} candidates.")
        return substantive_figures

