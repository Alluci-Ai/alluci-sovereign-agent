def replace_in_file(filepath, old, new):
    with open(filepath, 'r') as f:
        content = f.read()
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)

# TaskPanel.tsx
replace_in_file(
    "components/TaskPanel.tsx", 
    "onClick={() => setStatusFilter(s as any)}", 
    "onClick={() => setStatusFilter(s as 'all' | 'active' | 'completed')}"
)
replace_in_file(
    "components/TaskPanel.tsx", 
    "e.target.value as any", 
    "e.target.value as 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'"
)

# AffectiveEnginePanel.tsx
replace_in_file(
    "features/ace/AffectiveEnginePanel.tsx",
    "(e: any) =>",
    "(e: { timestamp: number, event_type: string, details: string, impact_score: number }) =>"
)
replace_in_file(
    "features/ace/AffectiveEnginePanel.tsx",
    "(e: any)",
    "(e: { timestamp: number, event_type: string, details: string, impact_score: number })"
)

# ConfigPanel.tsx
replace_in_file(
    "features/config/ConfigPanel.tsx",
    "(provider: any)",
    "(provider: { id: string, label: string })"
)

