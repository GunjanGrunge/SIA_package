"""Project skills: derived from the project's requirements, never invented.

The user's contract: SIA writes skills a project needs, "based on the project
requirement and not randomly". These tests hold SIA to it mechanically: a skill
that cannot cite its requirement verbatim is refused.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sia import project_skills  # noqa: E402
from sia.core import Project, SiaError  # noqa: E402
from sia.hooks import subagent_start  # noqa: E402
from sia.mcp_server import call_tool  # noqa: E402

SPEC = """# Churn model

The system must track training loss and validation accuracy after every epoch
and stop early when validation loss stops improving.

Hyperparameters are tuned with Optuna over learning rate and batch size.
"""

BODY = """Track loss per epoch.

1. Run `python train.py --log-every 1`.
2. Read `runs/latest/metrics.jsonl`; flag any epoch where val_loss rises twice.
3. Done when the early-stopping epoch is recorded in the run summary.
"""


def project_with_spec(root: Path) -> Project:
    project = Project(root)
    project.initialize("orchestrator")
    (root / "sdd").mkdir()
    (root / "sdd" / "intake.md").write_text("Goal: predict churn.\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "spec.md").write_text(SPEC, encoding="utf-8")
    project.advance(["sdd/intake.md"])
    project.advance(["docs/spec.md"])
    return project


def loss_skill(**overrides):
    spec = {
        "name": "loss-monitoring",
        "description": "Monitor training and validation loss. Use when training or evaluating the churn model.",
        "body": BODY,
        "requirements": [{"source": "docs/spec.md",
                          "quote": "track training loss and validation accuracy after every epoch"}],
        "paths": ["train.py", "models/**"],
    }
    spec.update(overrides)
    return spec


def write(project: Project, **overrides):
    spec = loss_skill(**overrides)
    return project_skills.write_skill(project, spec["name"], spec["description"], spec["body"],
                                      spec["requirements"], spec.get("paths"), spec.get("hosts"))


# --- grounding --------------------------------------------------------------

def test_context_offers_requirement_sources_not_a_catalog(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    (tmp_path / "requirements.txt").write_text("torch==2.4\noptuna>=3\n", encoding="utf-8")

    context = project_skills.skill_context(project)

    assert context["requirement_sources"] == ["sdd/intake.md", "docs/spec.md"]
    assert context["repository"]["dependencies"]["requirements.txt"] == ["optuna", "torch"]
    assert "suggested_skills" not in context, "skills come from requirements, not a dependency catalog"


def test_a_skill_without_a_requirement_is_refused(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    with pytest.raises(SiaError, match="cite at least one requirement"):
        write(project, requirements=[])


def test_a_quote_that_is_not_in_the_source_is_refused(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    with pytest.raises(SiaError, match="quote not found"):
        write(project, requirements=[{"source": "docs/spec.md", "quote": "deploy the model to a GPU cluster nightly"}])


def test_a_source_that_is_not_a_requirement_is_refused(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    (tmp_path / "notes.md").write_text("track training loss and validation accuracy after every epoch\n", encoding="utf-8")
    with pytest.raises(SiaError, match="not a requirement source"):
        write(project, requirements=[{"source": "notes.md",
                                      "quote": "track training loss and validation accuracy after every epoch"}])


def test_no_skills_before_there_are_requirements(tmp_path: Path) -> None:
    project = Project(tmp_path)
    project.initialize("orchestrator")
    with pytest.raises(SiaError, match="no requirement sources"):
        write(project)


def test_agent_instructions_count_as_requirements(tmp_path: Path) -> None:
    project = Project(tmp_path)
    project.initialize("orchestrator")
    (tmp_path / "AGENTS.md").write_text("Every API change must update openapi.yaml in the same commit.\n", encoding="utf-8")
    write(project, name="api-contract",
          requirements=[{"source": "AGENTS.md", "quote": "Every API change must update openapi.yaml"}])
    assert (tmp_path / ".claude/skills/api-contract/SKILL.md").is_file()


def test_quotes_match_across_line_breaks(tmp_path: Path) -> None:
    """Specs wrap lines; an agent quoting a sentence should not have to."""
    project = project_with_spec(tmp_path)
    write(project, requirements=[{"source": "./docs/spec.md",
                                  "quote": "after every epoch and stop early when validation loss stops improving"}])


def test_a_multiline_quote_keeps_the_manifest_one_row_per_skill(tmp_path: Path) -> None:
    """Found in the first live run: an agent copied a quote with the spec's own
    line break, and the manifest row spilled onto a second line."""
    project = project_with_spec(tmp_path)
    write(project, requirements=[{"source": "docs/spec.md", "quote":
                                  "track training loss and validation accuracy after every epoch\nand stop early when "
                                  "validation loss stops improving"}])
    rows = [line for line in (tmp_path / "sdd/skill-manifest.md").read_text(encoding="utf-8").splitlines()
            if "loss-monitoring" in line or "stop early" in line]
    assert len(rows) == 1 and rows[0].startswith("| loss-monitoring |") and rows[0].endswith("|")
    assert project_skills.list_skills(project)[0]["requirements"][0]["quote"].count("\n") == 0


# --- placement and content --------------------------------------------------

def test_skill_is_installed_where_hosts_discover_it(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    result = write(project)

    for relative in (".claude/skills/loss-monitoring/SKILL.md", ".agents/skills/loss-monitoring/SKILL.md"):
        text = (tmp_path / relative).read_text(encoding="utf-8")
        assert text.startswith("---\nname: loss-monitoring\ndescription: ")
        assert "python train.py --log-every 1" in text
        assert "track training loss and validation accuracy after every epoch" in text, "cites its requirement"
    assert result["version"] == 1
    manifest = (tmp_path / "sdd/skill-manifest.md").read_text(encoding="utf-8")
    assert "| loss-monitoring | active | 1 |" in manifest


def test_description_must_say_when_to_use_it(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    with pytest.raises(SiaError, match="Use when"):
        write(project, description="Monitors loss.")


def test_credentials_are_refused(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    with pytest.raises(SiaError, match="credential"):
        write(project, body=BODY + "\nexport AWS_ACCESS_KEY_ID=AKIAABCDEFGHIJKLMNOP\n")


# --- never clobber ----------------------------------------------------------

def test_an_existing_skill_sia_did_not_write_is_never_overwritten(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    theirs = tmp_path / ".claude/skills/loss-monitoring/SKILL.md"
    theirs.parent.mkdir(parents=True)
    theirs.write_text("the user's own skill\n", encoding="utf-8")

    with pytest.raises(SiaError, match="not written by SIA"):
        write(project)
    assert theirs.read_text(encoding="utf-8") == "the user's own skill\n"


def test_a_hand_edited_skill_is_left_alone(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    write(project)
    edited = tmp_path / ".claude/skills/loss-monitoring/SKILL.md"
    edited.write_text(edited.read_text(encoding="utf-8") + "\nmy own note\n", encoding="utf-8")

    with pytest.raises(SiaError, match="edited by hand"):
        write(project, body=BODY + "\n4. Also plot it.\n")

    project.learn_rule("Never delete checkpoints.", "don't ever delete my checkpoints")
    assert "my own note" in edited.read_text(encoding="utf-8")
    assert "Never delete checkpoints." not in edited.read_text(encoding="utf-8")


def test_an_unedited_skill_updates_and_versions(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    write(project)
    result = write(project, body=BODY + "\n4. Also plot it.\n")
    assert result["version"] == 2
    assert "Also plot it." in (tmp_path / ".agents/skills/loss-monitoring/SKILL.md").read_text(encoding="utf-8")


# --- keeps improving --------------------------------------------------------

def test_learned_rules_flow_into_matching_skills(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    write(project)
    skill = tmp_path / ".claude/skills/loss-monitoring/SKILL.md"
    assert "None learned yet." in skill.read_text(encoding="utf-8")

    everywhere = project.learn_rule("Log metrics as JSON lines, never CSV.", "stop writing csv, use jsonl")
    elsewhere = project.learn_rule("Keep UI copy short.", "shorter button labels", scope="ui/**")
    text = skill.read_text(encoding="utf-8")
    assert "Log metrics as JSON lines, never CSV." in text
    assert "Keep UI copy short." not in text, "a rule scoped elsewhere does not belong in this skill"
    assert "stop writing csv" not in text, "the user's raw words are not repeated into skills"

    project.retire_rule(everywhere["id"], "no longer applies")
    assert "Log metrics as JSON lines" not in skill.read_text(encoding="utf-8")
    assert elsewhere["status"] == "active"


def test_retiring_a_skill_removes_its_files(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    write(project)
    result = project_skills.retire_skill(project, "loss-monitoring", "requirement dropped")

    assert sorted(result["removed"]) == [".agents/skills/loss-monitoring/SKILL.md", ".claude/skills/loss-monitoring/SKILL.md"]
    assert not (tmp_path / ".claude/skills/loss-monitoring").exists()
    assert project_skills.list_skills(project)[0]["status"] == "retired"


# --- reaches subagents and hosts --------------------------------------------

def test_subagents_are_told_which_project_skills_exist(tmp_path: Path) -> None:
    project = project_with_spec(tmp_path)
    write(project)
    output = subagent_start({"cwd": str(tmp_path), "agent_type": "general-purpose"})
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "loss-monitoring: Monitor training and validation loss." in context

    project_skills.retire_skill(project, "loss-monitoring", "gone")
    assert subagent_start({"cwd": str(tmp_path), "agent_type": "general-purpose"}) is None


def test_mcp_tool_writes_a_skill(tmp_path: Path) -> None:
    project_with_spec(tmp_path)
    text, is_error = call_tool("sia_skill_write", {"project_root": str(tmp_path), **loss_skill(hosts=["codex"])})
    assert not is_error, text
    assert json.loads(text)["files"] == [".agents/skills/loss-monitoring/SKILL.md"]
    assert not (tmp_path / ".claude/skills").exists()

    text, is_error = call_tool("sia_skill_write", {"project_root": str(tmp_path),
                                                   **loss_skill(requirements=[{"source": "docs/spec.md", "quote": "invented requirement text"}])})
    assert is_error and "quote not found" in text
