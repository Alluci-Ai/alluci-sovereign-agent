import pytest
pytestmark = pytest.mark.unit

import os
from backend.engine.intent_decomposer import IntentDecomposer, IntentType
from backend.engine.grounding_providers import (
    ModularGroundingOrchestrator,
    SkillsAndToolsManifestProvider,
    ArchitectureGroundingProvider,
    TargetFileGroundingProvider,
    GitStateGroundingProvider
)


@pytest.mark.asyncio
async def test_skills_and_tools_provider_matches_inventory_query():
    provider = SkillsAndToolsManifestProvider()
    decomposer = IntentDecomposer()
    
    prompt = "Hello Alluci, can you please list and explain all your Skills and Tools"
    parsed = decomposer.decompose(prompt)
    
    assert await provider.can_handle(prompt, parsed) is True
    result = await provider.provide_grounding(prompt, parsed)
    
    assert result is not None
    assert "[AUTHENTIC DISK MANIFEST: 26 SPECIALIZED SKILLS & FRAMEWORKS]" in result.content
    assert "[AUTHENTIC DISK MANIFEST: 15 CAPABILITY TOOLS]" in result.content
    assert "codi_01" in result.content
    assert "spe_01" in result.content
    assert "autonomous_software_engineering_tool" in result.content
    assert result.specialized_directive is not None
    assert "Directly enumerate and explain all 26 skills" in result.specialized_directive


@pytest.mark.asyncio
async def test_skills_provider_ignores_pure_architecture_query():
    provider = SkillsAndToolsManifestProvider()
    decomposer = IntentDecomposer()
    
    prompt = "Can you explain your system architecture, 6 functional domains, and topological physics?"
    parsed = decomposer.decompose(prompt)
    
    assert await provider.can_handle(prompt, parsed) is False


@pytest.mark.asyncio
async def test_architecture_provider_matches_system_query():
    provider = ArchitectureGroundingProvider()
    decomposer = IntentDecomposer()
    
    prompt = "Explain your system architecture, 6 functional domains, and topological physics"
    parsed = decomposer.decompose(prompt)
    
    assert await provider.can_handle(prompt, parsed) is True
    result = await provider.provide_grounding(prompt, parsed)
    
    assert result is not None
    assert "[AUTHENTIC SYSTEM ARCHITECTURE & 6-DOMAIN CAPABILITIES]" in result.content
    assert "Functional Domains:" in result.content


@pytest.mark.asyncio
async def test_target_file_provider_reads_readme():
    provider = TargetFileGroundingProvider()
    decomposer = IntentDecomposer()
    
    prompt = "Please read the README.md and summarize its setup section"
    parsed = decomposer.decompose(prompt)
    
    assert await provider.can_handle(prompt, parsed) is True
    result = await provider.provide_grounding(prompt, parsed)
    
    assert result is not None
    assert "[VERIFIED DISK CONTENT: `README.md`" in result.content


@pytest.mark.asyncio
async def test_modular_orchestrator_scoping():
    orchestrator = ModularGroundingOrchestrator()
    decomposer = IntentDecomposer()
    
    # 1. Skills Query is strictly scoped (no architecture pollution)
    p_skills = "Hello Alluci, can you please list and explain all your Skills and Tools"
    g_skills, d_skills = await orchestrator.resolve_grounding(p_skills, decomposer.decompose(p_skills))
    assert "[AUTHENTIC DISK MANIFEST: 26 SPECIALIZED" in g_skills
    assert "[AUTHENTIC DISK MANIFEST: 15 CAPABILITY" in g_skills
    assert "[AUTHENTIC SYSTEM ARCHITECTURE" not in g_skills
    assert d_skills is not None
    
    # 2. Architecture Query is strictly scoped (no 26-skill manifest dump)
    p_arch = "Can you explain your system architecture and 6 functional domains?"
    g_arch, d_arch = await orchestrator.resolve_grounding(p_arch, decomposer.decompose(p_arch))
    assert "[AUTHENTIC SYSTEM ARCHITECTURE" in g_arch
    assert "[AUTHENTIC DISK MANIFEST: 26 SPECIALIZED" not in g_arch
