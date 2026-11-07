"""Skill prompt catalogs have stable order across discovery order changes."""

from agent.skills.formatter import (
    format_skill_entries_for_prompt,
    format_unavailable_skills_for_prompt,
    format_skills_for_prompt,
)
from agent.skills.types import Skill, SkillEntry


def _skill(name, file_path=None, *, description=None, content="", disabled=False):
    return Skill(
        name=name,
        description=description or f"{name} description",
        file_path=file_path or f"/skills/{name}/SKILL.md",
        base_dir=f"/skills/{name}",
        source="custom",
        content=content,
        disable_model_invocation=disabled,
    )


def test_available_skill_prompt_is_stable_for_reversed_entry_order():
    entries = [
        SkillEntry(_skill("zeta", description="Last description")),
        SkillEntry(_skill("alpha", description="First description")),
        SkillEntry(_skill("same", "/z/SKILL.md", description="Z path")),
        SkillEntry(_skill("same", "/a/SKILL.md", description="A path")),
    ]

    prompt = format_skill_entries_for_prompt(entries)

    assert prompt == format_skill_entries_for_prompt(list(reversed(entries)))
    assert prompt.index("<name>alpha</name>") < prompt.index("<name>same</name>")
    assert prompt.index("<location>/a/SKILL.md</location>") < prompt.index(
        "<location>/z/SKILL.md</location>"
    )
    assert prompt.index("<name>zeta</name>") > prompt.index("Z path")
    for text in (
        "First description",
        "Last description",
        "A path",
        "Z path",
        "/skills/alpha",
        "/skills/zeta",
    ):
        assert text in prompt


def test_available_skill_prompt_still_excludes_model_disabled_skills():
    visible = _skill("visible")
    hidden = _skill("hidden", disabled=True)

    prompt = format_skills_for_prompt([hidden, visible])

    assert "<name>visible</name>" in prompt
    assert "<name>hidden</name>" not in prompt
    assert "hidden description" not in prompt


def test_unavailable_skill_prompt_is_stable_and_keeps_setup_details():
    first = SkillEntry(
        _skill(
            "zeta",
            content="## Setup\nInstall zeta package.\nThen set ZETA_HOME.\n\n## Usage\nRun it.",
        )
    )
    second = SkillEntry(
        _skill("alpha", content="## Setup\nInstall alpha package.\n")
    )
    hidden = SkillEntry(_skill("hidden", content="## Setup\nDo not show.", disabled=True))
    entries = [first, hidden, second]
    missing = {
        "zeta": {"bins": ["zeta"]},
        "alpha": {"env": ["ALPHA_TOKEN"]},
        "hidden": {"bins": ["hidden"]},
    }

    prompt = format_unavailable_skills_for_prompt(entries, missing)

    assert prompt == format_unavailable_skills_for_prompt(list(reversed(entries)), missing)
    assert prompt.index("<name>alpha</name>") < prompt.index("<name>zeta</name>")
    assert "env: ALPHA_TOKEN" in prompt
    assert "Install alpha package." in prompt
    assert "bins: zeta" in prompt
    assert "Install zeta package. Then set ZETA_HOME." in prompt
    assert "<name>hidden</name>" not in prompt
    assert "Do not show." not in prompt
