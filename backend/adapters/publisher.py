import os, json, logging, html
from typing import Dict, Any, Optional

logger = logging.getLogger("MultiFormatPublisher")

def publish_report_bundle(task_dir: str, markdown_content: str, metadata: Dict[str, Any]) -> Dict[str, str]:
    """
    Generates multi-format report publishing outputs in the task artifact directory:
    - deep_research_report.md
    - deep_research_report.html
    - deep_research_report.json
    """
    os.makedirs(task_dir, exist_ok=True)
    outputs = {}

    # 1. Write Markdown report
    md_path = os.path.join(task_dir, "deep_research_report.md")
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        outputs["markdown"] = md_path
    except Exception as e:
        logger.error(f"Failed writing markdown report: {e}")

    # 2. Write JSON-LD Structured Knowledge Graph metadata
    json_path = os.path.join(task_dir, "deep_research_report.json")
    try:
        json_payload = {
            "@context": "https://schema.org",
            "@type": "Report",
            "name": metadata.get("topic_slug", "Deep Research Report"),
            "identifier": metadata.get("run_id", "run_1"),
            "datePublished": metadata.get("timestamp"),
            "author": {
                "@type": "Agent",
                "name": metadata.get("agent_id", "Rocco")
            },
            "about": metadata.get("objective_text"),
            "articleBody": markdown_content[:2000]
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_payload, f, indent=2)
        outputs["json_ld"] = json_path
    except Exception as e:
        logger.error(f"Failed writing JSON-LD report: {e}")

    # 3. Write Styled Self-Contained HTML Dashboard
    html_path = os.path.join(task_dir, "deep_research_report.html")
    try:
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(metadata.get("topic_slug", "Deep Research Synthesis Report"))}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', Roboto, sans-serif; background: #0c0d0e; color: #e1e3e6; padding: 2rem; line-height: 1.6; max-width: 900px; margin: 0 auto; }}
        h1, h2, h3 {{ color: #30d158; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.3rem; }}
        pre, code {{ background: #1c1c1e; padding: 0.2rem 0.4rem; border-radius: 4px; font-family: monospace; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; background: #121315; }}
        th, td {{ border: 1px solid #2c2c2e; padding: 8px 12px; text-align: left; }}
        th {{ background: #1c1d20; color: #30d158; }}
        a {{ color: #64d2ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .meta-tag {{ background: rgba(48, 209, 88, 0.15); color: #30d158; padding: 4px 8px; border-radius: 12px; font-size: 0.85rem; font-weight: 600; display: inline-block; margin-bottom: 1rem; }}
    </style>
</head>
<body>
    <div class="meta-tag">RUN ID: {html.escape(metadata.get("run_id", "run_1"))} | {html.escape(metadata.get("timestamp", ""))}</div>
    <div id="content">
        <pre style="white-space: pre-wrap; font-family: inherit;">{html.escape(markdown_content)}</pre>
    </div>
</body>
</html>"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        outputs["html"] = html_path
    except Exception as e:
        logger.error(f"Failed writing HTML report: {e}")

    return outputs
