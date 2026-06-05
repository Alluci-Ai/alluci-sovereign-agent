#!/usr/bin/env python3
import time
import subprocess
import json
import os
import mlx_lm

LAST_ROWID = 0
PROCESSED_MESSAGES = {}

print("========================================")
print("🧠 Sovereign Brain Daemon Boot Sequence Initiated...")

# 1. Load Soul Preferences
try:
    with open("alluci_vault/soul_preferences.json", "r") as f:
        SOUL = json.load(f)
        print("✅ Soul Preferences Loaded")
except Exception as e:
    SOUL = {"identity": {"core_directive": "You are Alluci."}}
    print("⚠️ Soul Preferences not found, using default.")

# 2. Load MLX Model
print("🛡️  Booting Gemma MLX Engine into Unified Memory...")
try:
    # Load the permanently compiled Alluci Polytope Variant strictly from the local filesystem
    model, tokenizer = mlx_lm.load("alluci_vault/polytope_variants/mlx_e4b")
    print("✅ Local Alluci Polytope Engine (Gemma 4 MLX) Online.")
except Exception as e:
    print(f"❌ Failed to load MLX Engine: {e}")
    exit(1)

print("🛡️  Bridge Connected: iMessage")
print("========================================")

def fetch_unread():
    global LAST_ROWID
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    query = f"""
    SELECT message.ROWID as rowid, message.text as text, handle.id as sender 
    FROM message 
    LEFT JOIN handle ON message.handle_id = handle.ROWID 
    WHERE message.text NOT LIKE '🤖%' AND message.ROWID > {LAST_ROWID} 
    ORDER BY message.ROWID ASC LIMIT 5;
    """
    try:
        r = subprocess.run(["sqlite3", db_path, "-json", query], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            rows = json.loads(r.stdout)
            if rows:
                LAST_ROWID = max(r.get("rowid", LAST_ROWID) for r in rows)
                return rows
    except Exception as e:
        print(f"SQLite Error: {e}")
    return []

def send_reply(recipient, content):
    safe_content   = content.replace("\\", "\\\\").replace('"', '\\"')
    safe_recipient = recipient.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{safe_recipient}" of targetService
        send "{safe_content}" to targetBuddy
    end tell
    '''
    subprocess.run(["osascript", "-e", script])

def generate_inference(prompt):
    system_prompt = SOUL.get("identity", {}).get("core_directive", "You are Alluci.")
    personality = ", ".join(SOUL.get("personality", {}).get("traits", []))
    
    # ACE Engine Semantic Router (JIT Skill Injection)
    active_skills = SOUL.get("active_skill_ids", [])
    skill_context = ""
    if active_skills:
        skill_context += "\n[ACE ENGINE: DYNAMIC SKILL INJECTION TRIGGERED]"
        for skill_id in active_skills:
            keywords = skill_id.replace("_", " ").split()
            if any(k.lower() in prompt.lower() for k in keywords if len(k) > 3):
                skill_path = f"alluci_vault/skills/{skill_id}.json"
                if os.path.exists(skill_path):
                    try:
                        with open(skill_path, "r") as sf:
                            skill_data = json.load(sf)
                            logic = " ".join(skill_data.get("logic", []))
                            chains = " ".join(skill_data.get("chainsOfThought", []))
                            skill_context += f"\n- {skill_id.upper()} FRAMEWORK: {logic} {chains}"
                            print(f"🧠 ACE Router: Injected {skill_id} into context window!")
                    except Exception as e:
                        print(f"⚠️ Failed to load skill {skill_id}: {e}")
                else:
                    skill_context += f"\n- (Authorized to use {skill_id} but module missing locally)"

    sys_instruction = f"{system_prompt} Your traits: {personality}.{skill_context}\nKeep your response concise, friendly, and factual. You are talking via iMessage, so do not use markdown formatting like **."
    
    full_prompt = f"{sys_instruction}\n\nUser: {prompt}\nAlluci:"
    
    response = mlx_lm.generate(model, tokenizer, prompt=full_prompt, max_tokens=200, verbose=False)
    
    # Model Transparency
    transparency_tag = "\n\n[Processed natively via Local Alluci Polytope Variant (Gemma 4 MLX)]"
    return response.strip() + transparency_tag

# Get latest rowid to ignore history
try:
    r = subprocess.run(["sqlite3", os.path.expanduser("~/Library/Messages/chat.db"), "SELECT MAX(ROWID) FROM message;"], capture_output=True, text=True)
    LAST_ROWID = int(r.stdout.strip() or 0)
    print(f"Anchored to chat history. Cursor: {LAST_ROWID}")
except Exception:
    pass

print("Listening for incoming texts...\n")

while True:
    new_msgs = fetch_unread()
    for msg in new_msgs:
        sender = msg.get("sender")
        text = msg.get("text")
        
        if text and sender:
            # Deduplication Check (15 second sliding window)
            current_time = time.time()
            is_duplicate = False
            for prev_text, timestamp in list(PROCESSED_MESSAGES.items()):
                if current_time - timestamp > 15:
                    del PROCESSED_MESSAGES[prev_text]
                elif prev_text == text:
                    is_duplicate = True
            
            if is_duplicate:
                print(f"🔄 Deduplicated identical echo: {text}")
                continue
                
            PROCESSED_MESSAGES[text] = current_time
            
            print(f"📥 Received from {sender}: {text}")
            print(f"⚙️  Processing via Local Gemma MLX...")
            
            reply = "🤖 " + generate_inference(text)
            send_reply(sender, reply)
            
            print(f"📤 Auto-replied to {sender}")
            
    time.sleep(3)
