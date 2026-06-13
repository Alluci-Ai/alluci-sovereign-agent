import os

file_path = "styles/tokens.css"

with open(file_path, "r") as f:
    content = f.read()

# 1. Update Dark Theme Variables
dark_old = """    --glass-bg: rgba(44, 44, 46, 0.72);
    --glass-bg-hover: rgba(58, 58, 60, 0.80);
    --glass-bg-pressed: rgba(30, 30, 32, 0.60);"""
dark_new = """    --glass-bg: #2C2C2E;
    --glass-bg-hover: #3A3A3C;
    --glass-bg-pressed: #1E1E20;
    --glass-noise: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.03'/%3E%3C/svg%3E");"""

content = content.replace(dark_old, dark_new)

# 2. Update Light Theme Variables
light_old = """    --glass-bg: rgba(255, 255, 255, 0.72);
    --glass-bg-hover: rgba(255, 255, 255, 0.85);
    --glass-bg-pressed: rgba(245, 245, 247, 0.60);"""
light_new = """    --glass-bg: #FFFFFF;
    --glass-bg-hover: #F2F2F7;
    --glass-bg-pressed: #E5E5EA;
    --glass-noise: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.03'/%3E%3C/svg%3E");"""

content = content.replace(light_old, light_new)

# 3. Add background-image noise to .sidebar and .topbar
sidebar_old = """    background: var(--glass-bg);
    backdrop-filter: var(--glass-blur) var(--glass-sat);"""
sidebar_new = """    background: var(--glass-bg);
    background-image: var(--glass-noise);
    backdrop-filter: var(--glass-blur) var(--glass-sat);"""

content = content.replace(sidebar_old, sidebar_new)

# 4. Remove all other backdrop-filter lines that are NOT .sidebar or .topbar
lines = content.splitlines()
new_lines = []
in_structural_block = False

for line in lines:
    if line.startswith('.sidebar {') or line.startswith('.topbar {') or line.startswith('.app-shell__nudge {'):
        in_structural_block = True
    elif line.startswith('}'):
        in_structural_block = False

    if 'backdrop-filter:' in line:
        if in_structural_block or '--glass-blur:' in line or '--glass-blur-heavy:' in line:
            new_lines.append(line)
        else:
            pass
    else:
        new_lines.append(line)

content = os.linesep.join(new_lines) + os.linesep

with open(file_path, "w") as f:
    f.write(content)

print("CSS Refactor complete!")
