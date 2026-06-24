from pathlib import Path
from textwrap import dedent
from aicoder.config.skills import SkillManager, _parse_skill_md, _scan_dir


def _skill_md(name: str, desc: str, body: str = "# Content") -> str:
    return dedent(f"""\
    ---
    name: {name}
    description: {desc}
    ---
    {body}
    """)


class TestParseSkillMd:
    def test_parse_valid_skill(self, temp_dir):
        f = temp_dir / "SKILL.md"
        f.write_text("---\nname: my-skill\ndescription: A test skill\n---\n# My Skill\nContent here.\n")
        meta = _parse_skill_md(f)
        assert meta["name"] == "my-skill"
        assert meta["description"] == "A test skill"

    def test_parse_no_frontmatter(self, temp_dir):
        f = temp_dir / "SKILL.md"
        f.write_text("# No frontmatter")
        assert _parse_skill_md(f) is None

    def test_parse_empty_file(self, temp_dir):
        f = temp_dir / "SKILL.md"
        f.write_text("")
        assert _parse_skill_md(f) is None

    def test_parse_missing_file(self, temp_dir):
        assert _parse_skill_md(temp_dir / "nonexistent.md") is None


class TestScanDir:
    def test_scan_empty_dir(self, temp_dir):
        skills = _scan_dir(temp_dir, "test")
        assert skills == []

    def test_scan_with_valid_skill(self, temp_dir):
        d = temp_dir / "my-skill"
        d.mkdir()
        (d / "SKILL.md").write_text("---\nname: my-skill\ndescription: Test skill\n---\n# Content\n")
        skills = _scan_dir(temp_dir, "test")
        assert len(skills) == 1
        assert skills[0].name == "my-skill"
        assert skills[0].source == "test"

    def test_scan_skips_invalid(self, temp_dir):
        d = temp_dir / "bad-skill"
        d.mkdir()
        (d / "SKILL.md").write_text("no frontmatter")
        skills = _scan_dir(temp_dir, "test")
        assert len(skills) == 0


class TestSkillManager:
    def test_discover_builtin_skills(self, config_dir, tmp_path):
        builtin = tmp_path / "package" / "skills" / "builtin" / "test-skill"
        builtin.mkdir(parents=True)
        (builtin / "SKILL.md").write_text("---\nname: test-skill\ndescription: A built-in\n---\n# Test\n")
        mgr = SkillManager(config_dir / "skills", tmp_path / "package")
        skills = mgr.discover(".")
        assert len(skills) == 1
        assert skills[0].name == "test-skill"
        assert skills[0].source == "builtin"

    def test_user_skills_override_builtin(self, config_dir, tmp_path):
        builtin = tmp_path / "package" / "skills" / "builtin" / "shared-name"
        builtin.mkdir(parents=True)
        (builtin / "SKILL.md").write_text("---\nname: shared-name\ndescription: builtin version\n---\n# Builtin\n")
        user = config_dir / "skills" / "shared-name"
        user.mkdir(parents=True)
        (user / "SKILL.md").write_text("---\nname: shared-name\ndescription: user version\n---\n# User\n")
        mgr = SkillManager(config_dir, tmp_path / "package")
        skills = mgr.discover(".")
        matching = [s for s in skills if s.name == "shared-name"]
        assert len(matching) == 1
        assert matching[0].source == "user"
        assert matching[0].description == "user version"

    def test_resolve_paths(self, config_dir, tmp_path):
        builtin = tmp_path / "package" / "skills" / "builtin" / "s1"
        builtin.mkdir(parents=True)
        (builtin / "SKILL.md").write_text("---\nname: s1\ndescription: d\n---\n# X\n")
        mgr = SkillManager(config_dir, tmp_path / "package")
        paths = mgr.resolve_paths(".")
        assert len(paths) >= 1
        assert any("builtin" in p for p in paths)

    def test_discover_empty(self, config_dir, tmp_path):
        mgr = SkillManager(config_dir, tmp_path / "package")
        skills = mgr.discover(".")
        assert skills == []


class TestSkillCommands:
    def test_skills_list_empty(self):
        from aicoder.cli.commands import CommandHandler
        handler = CommandHandler()
        handler.set_skill_manager(None, ".")
        assert "not available" in handler.handle("/skills")

    def test_skill_install_no_url(self):
        from aicoder.cli.commands import CommandHandler
        from aicoder.config.skills import SkillManager
        handler = CommandHandler()
        mgr = SkillManager(Path("/tmp/aicoder-test"), Path("/tmp/pkg"))
        handler.set_skill_manager(mgr, ".")
        result = handler.handle("/skill install")
        assert "Usage:" in result
