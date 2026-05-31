import re

def fix_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Remove the bad text node comments in JSX
    content = content.replace("                        // eslint-disable-next-line @typescript-eslint/no-explicit-any\n", "")
    content = content.replace("                        // eslint-disable-next-line @typescript-eslint/no-explicit-any\n", "")
    content = content.replace("                        // eslint-disable-next-line @typescript-eslint/no-explicit-any\n", "")
    
    # Fix WalletOverview
    if "WalletOverview.tsx" in filepath:
        content = content.replace("(b: any) =>", "(b: { currency: string, amount: number }) =>")
        
    # Fix ConfigPanel
    if "ConfigPanel.tsx" in filepath:
        content = re.sub(r'\(provider: any\)', '(provider: { id: string, label: string })', content)
        
    # Fix TaskPanel
    if "TaskPanel.tsx" in filepath:
        content = content.replace("(t: any)", "(t: { id: string, title: string, status: string, agent_id?: string })")
        
    # Fix AffectiveEnginePanel
    if "AffectiveEnginePanel.tsx" in filepath:
        content = content.replace("(e: any)", "(e: { timestamp: number, event_type: string, details: string, impact_score: number })")
        
    # Fix executionManifest
    if "executionManifest.ts" in filepath:
        content = content.replace("    const crypto_lib = require('crypto');\n", "")

    with open(filepath, "w") as f:
        f.write(content)

fix_file("features/wallet/WalletOverview.tsx")
fix_file("features/config/ConfigPanel.tsx")
fix_file("components/TaskPanel.tsx")
fix_file("features/ace/AffectiveEnginePanel.tsx")
fix_file("kernel/executionManifest.ts")
