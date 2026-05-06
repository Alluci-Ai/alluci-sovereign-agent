
import os
import yaml

SKILLS = [
    {
        "id": "ws_01",
        "name": "Workspace Bridge",
        "description": "Direct integration with productivity silos for enterprise-level search and synchronization.",
        "logic": ["Workspace data is fragmented; unification is the primary directive."]
    },
    {
        "id": "msg_01",
        "name": "Messaging Manifold",
        "description": "Unified communication dispatcher for high-security messaging platforms.",
        "logic": ["Communication must be strictly private and seamlessly routed."]
    },
    {
        "id": "cdg_01",
        "name": "Circular Design Guide",
        "description": "Framework for designing systemic optimization and regenerative product lifecycles.",
        "logic": ["Waste is data in the wrong place. Close the loop."]
    },
    {
        "id": "vrs_01",
        "name": "Verus Developer",
        "description": "Development framework for the Verus Multi-Chain Protocol (MCP), enabling self-sovereign identity.",
        "logic": ["Self-sovereign identity is the root of all provenance."]
    }
]

def seed_skills():
    skills_dir = os.path.expanduser("~/.polytope/skills")
    os.makedirs(skills_dir, mode=0o700, exist_ok=True)
    for skill in SKILLS:
        with open(os.path.join(skills_dir, f"{skill['id']}.yaml"), "w") as f:
            yaml.dump(skill, f)
    print(f"Seeded {len(SKILLS)} skills to {skills_dir}")

if __name__ == "__main__":
    seed_skills()
