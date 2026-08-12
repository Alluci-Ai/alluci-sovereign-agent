#!/usr/bin/env python3
import os, sys, shutil, json, hashlib, datetime, re, sqlite3

def run_migration():
    print("=== Sovereign Research Artifact Directory Migration & Re-alignment ===")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    artifacts_dir = os.path.join(project_root, "workspace", "artifacts", "research")
    db_path = os.path.join(project_root, "polytope_data.db")
    
    if not os.path.exists(artifacts_dir):
        print(f"Artifacts directory '{artifacts_dir}' not found. Nothing to migrate.")
        return

    # Fetch primary objective from polytope_data.db for run_1
    run_1_objective = "Ai/ML Research Grants for Human Centered Ai, Human Ai-Symbiosis, Human Agency in Ai, Human Centered Intelligent or Autonomous Systems, Machine Consciousness"
    try:
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT context FROM task_record WHERE run_id = 1 AND context IS NOT NULL LIMIT 1;")
            row = c.fetchone()
            if row and row[0]:
                run_1_objective = row[0]
            conn.close()
    except Exception as e:
        print(f"Notice reading polytope_data.db: {e}")

    target_canonical_folder = os.path.join(artifacts_dir, "2026-08-12_run_1_ai_ml_research_grants")
    os.makedirs(target_canonical_folder, exist_ok=True)
    target_scratch = os.path.join(target_canonical_folder, "scratch")
    os.makedirs(target_scratch, exist_ok=True)

    legacy_folders = ["2026-08-12_applied_sovereignty", "2026-08-12_permanent_link_to_apply", "2026-08-12_ai_ml_research_grants"]
    
    migrated_count = 0
    for legacy_name in legacy_folders:
        legacy_path = os.path.join(artifacts_dir, legacy_name)
        if os.path.exists(legacy_path) and os.path.isdir(legacy_path):
            print(f"Migrating legacy directory: '{legacy_name}' -> '2026-08-12_run_1_ai_ml_research_grants'")
            for item in os.listdir(legacy_path):
                src_item = os.path.join(legacy_path, item)
                if item.startswith("chunk_summary_") or item in ["compounding_digest.md", "report_page_1.md", "report_page_2.md", "report_page_3.md"]:
                    dest_item = os.path.join(target_scratch, item)
                else:
                    dest_item = os.path.join(target_canonical_folder, item)
                
                if not os.path.exists(dest_item):
                    if os.path.isdir(src_item):
                        shutil.copytree(src_item, dest_item, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src_item, dest_item)
                    migrated_count += 1
            
            # Remove legacy empty directory
            try:
                shutil.rmtree(legacy_path)
                print(f"Cleaned up legacy directory '{legacy_name}'.")
            except Exception as rmerr:
                print(f"Notice removing '{legacy_name}': {rmerr}")

    # Generate metadata.json for target_canonical_folder
    metadata_path = os.path.join(target_canonical_folder, "metadata.json")
    obj_bytes = run_1_objective.encode('utf-8')
    metadata_payload = {
        "run_id": "run_1",
        "agent_id": "rocco",
        "subfolder": "artifacts",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "topic_slug": "ai_ml_research_grants",
        "objective_hash": hashlib.sha256(obj_bytes).hexdigest(),
        "objective_text": run_1_objective[:500],
        "migrated": True
    }
    with open(metadata_path, "w", encoding="utf-8") as mf:
        json.dump(metadata_payload, mf, indent=2)

    print(f"=== Migration complete! Migrated {migrated_count} files into '{target_canonical_folder}'. ===")

if __name__ == "__main__":
    run_migration()
