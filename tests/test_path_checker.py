"""Tests for 5A E2 local path checker."""

from __future__ import annotations

import errno
from pathlib import Path

import pytest

from skill_evidence_lint.models import (
    ContextType,
    EvidenceReference,
    MarkdownContext,
    RefType,
    RuleID,
)
from skill_evidence_lint.path_checker import check_local_paths


def _skip_unless_symlink_allowed(exc: BaseException) -> None:
    """Skip only when symlink creation is genuinely unavailable.

    Every platform first attempts to create the symlink. We skip only when the
    failure is a permission or platform-unsupported error:

    * ``PermissionError`` (``EACCES``) / ``EPERM`` — on Linux/macOS this means a
      sandbox disallows symlinks; on Windows it typically carries
      ``winerror 1314`` (privilege not held / Developer Mode off).
    * ``NotImplementedError`` — platform lacks symlink support entirely.

    Any other OSError (bad path, missing target, invalid argument, ...) is
    re-raised so real bugs surface as test failures instead of being hidden.
    """
    permission_err = isinstance(exc, OSError) and (
        exc.errno in (errno.EPERM, errno.EACCES)
        or getattr(exc, "winerror", None) == 1314
    )
    unsupported = isinstance(exc, NotImplementedError)
    if permission_err or unsupported:
        pytest.skip(f"symlink not creatable in this environment: {exc}")
    raise exc


def _ctx() -> MarkdownContext:
    return MarkdownContext(
        type=ContextType.PARAGRAPH,
        raw_text="see evidence.md",
        start_line=7,
        end_line=7,
        context_id="p-1",
    )


def _ref(raw: str, ref_type: RefType = RefType.LOCAL_PATH) -> EvidenceReference:
    return EvidenceReference(
        raw_path=raw,
        context=_ctx(),
        reference_id="r-1",
        ref_type=ref_type,
        line=7,
    )


# --------------------------------------------------------------------------- #
# Happy paths
# --------------------------------------------------------------------------- #
def test_existing_file_inside_root_passes(tmp_path: Path):
    (tmp_path / "evidence.md").write_text("x", encoding="utf-8")
    findings = check_local_paths([_ref("evidence.md")], tmp_path)
    assert findings == []


def test_existing_subdirectory_inside_root_passes(tmp_path: Path):
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "bench.json").write_text("{}", encoding="utf-8")
    findings = check_local_paths([_ref("evidence/bench.json")], tmp_path)
    assert findings == []


def test_directory_itself_inside_root_passes(tmp_path: Path):
    (tmp_path / "evidence").mkdir()
    # A reference to a directory (not a regular file) is accepted.
    findings = check_local_paths([_ref("evidence")], tmp_path)
    assert findings == []


def test_path_with_spaces_passes(tmp_path: Path):
    (tmp_path / "my evidence.md").write_text("x", encoding="utf-8")
    findings = check_local_paths([_ref("my evidence.md")], tmp_path)
    assert findings == []


# --------------------------------------------------------------------------- #
# Failures -> E2
# --------------------------------------------------------------------------- #
def test_missing_path_emits_e2(tmp_path: Path):
    findings = check_local_paths([_ref("nope.md")], tmp_path)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id is RuleID.E2
    assert f.line == 7
    assert "does not exist" in f.message


def test_dotdot_traversal_emits_e2(tmp_path: Path):
    findings = check_local_paths([_ref("../escape.md")], tmp_path)
    assert len(findings) == 1
    assert findings[0].rule_id is RuleID.E2
    assert "escapes" in findings[0].message


def test_deep_dotdot_traversal_emits_e2(tmp_path: Path):
    findings = check_local_paths([_ref("a/b/../../../escape.md")], tmp_path)
    assert len(findings) == 1
    assert findings[0].rule_id is RuleID.E2


def test_absolute_path_outside_root_emits_e2(tmp_path: Path):
    outside = tmp_path.parent / "outside.md"
    outside.write_text("x", encoding="utf-8")
    try:
        findings = check_local_paths([_ref(str(outside))], tmp_path)
        assert len(findings) == 1
        assert findings[0].rule_id is RuleID.E2
    finally:
        outside.unlink(missing_ok=True)


def test_empty_path_emits_e2(tmp_path: Path):
    findings = check_local_paths([_ref("   ")], tmp_path)
    assert len(findings) == 1
    assert findings[0].rule_id is RuleID.E2


# --------------------------------------------------------------------------- #
# Non-local reference types are ignored
# --------------------------------------------------------------------------- #
def test_url_does_not_produce_e2(tmp_path: Path):
    findings = check_local_paths(
        [_ref("https://example.com/x", RefType.URL)], tmp_path
    )
    assert findings == []


def test_command_does_not_produce_e2(tmp_path: Path):
    findings = check_local_paths(
        [_ref("python run.py", RefType.COMMAND)], tmp_path
    )
    assert findings == []


# --------------------------------------------------------------------------- #
# Multiple bad paths, one E2 each
# --------------------------------------------------------------------------- #
def test_multiple_bad_paths_each_get_one_e2(tmp_path: Path):
    refs = [_ref("a.md"), _ref("b.md"), _ref("../c.md")]
    findings = check_local_paths(refs, tmp_path)
    assert len(findings) == 3
    assert {f.rule_id for f in findings} == {RuleID.E2}


def test_empty_input_returns_empty(tmp_path: Path):
    assert check_local_paths([], tmp_path) == []


# --------------------------------------------------------------------------- #
# Symlink escaping the root
# --------------------------------------------------------------------------- #
def test_symlink_outside_root_emits_e2(tmp_path: Path):
    outside = tmp_path.parent / "secret.md"
    outside.write_text("top secret", encoding="utf-8")
    link = tmp_path / "link.md"
    try:
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            _skip_unless_symlink_allowed(exc)
        findings = check_local_paths([_ref("link.md")], tmp_path)
        assert len(findings) == 1
        assert findings[0].rule_id is RuleID.E2
        assert "escapes" in findings[0].message
    finally:
        link.unlink(missing_ok=True)
        outside.unlink(missing_ok=True)


def test_symlink_inside_root_passes(tmp_path: Path):
    target = tmp_path / "real.md"
    target.write_text("x", encoding="utf-8")
    link = tmp_path / "alias.md"
    try:
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            _skip_unless_symlink_allowed(exc)
        findings = check_local_paths([_ref("alias.md")], tmp_path)
        assert findings == []
    finally:
        link.unlink(missing_ok=True)


def test_does_not_read_or_open_target_content(tmp_path: Path, monkeypatch):
    """E2 must only stat metadata; opening/reading evidence is forbidden."""
    target = tmp_path / "secret.md"
    target.write_text("secret payload", encoding="utf-8")

    def forbidden_read(*_args, **_kwargs):  # noqa: ANN002
        raise AssertionError("path_checker must not open or read evidence files")

    monkeypatch.setattr(Path, "read_text", forbidden_read)
    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    monkeypatch.setattr(Path, "open", forbidden_read)

    findings = check_local_paths([_ref("secret.md")], tmp_path)
    assert findings == []


# --------------------------------------------------------------------------- #
# Fail-safe: a broken stat must not crash the run
# --------------------------------------------------------------------------- #
def test_filesystem_error_does_not_crash(tmp_path: Path, monkeypatch):
    (tmp_path / "ok.md").write_text("x", encoding="utf-8")

    real_resolve = Path.resolve

    def boom(self):  # type: ignore[no-untyped-def]
        if "ok.md" in str(self):
            raise OSError("simulated IO error")
        return real_resolve(self)

    monkeypatch.setattr(Path, "resolve", boom)
    findings = check_local_paths([_ref("ok.md")], tmp_path)
    assert len(findings) == 1
    assert findings[0].rule_id is RuleID.E2
    assert "could not be resolved" in findings[0].message
