from pathlib import Path

from check_language import TOKEN_CODES, is_excluded, scan_repository, scan_text
from paths import ROOT

_STEM = (100, 101, 109, 97, 110, 100)


def _stem() -> str:
    return "".join(chr(code) for code in _STEM)


def test_repository_is_english_only():
    assert scan_repository(ROOT) == []


def test_token_list_covers_the_audit_and_the_work_unit_stem():
    assert len(TOKEN_CODES) == 101
    assert _STEM in TOKEN_CODES
    assert (224,) in TOKEN_CODES
    assert all(codes for codes in TOKEN_CODES)


def test_planted_token_and_accented_letter_fail(tmp_path: Path):
    prose = tmp_path / "note.md"
    prose.write_text(f"See {_stem()} here.\n", encoding="utf-8")
    hits = scan_text("note.md", prose.read_text(encoding="utf-8"))
    assert any(_stem() in hit for hit in hits)
    accented = "cafe" + chr(0x00E9)
    assert scan_text("note.md", accented)


def test_translation_and_license_are_excluded():
    planted = _stem()
    assert is_excluded("README.pt-BR.md")
    assert is_excluded("LICENSE")
    assert scan_text("README.pt-BR.md", planted) == []
    assert scan_text("docs/LICENSE", planted) == []
    assert scan_text("README.md", planted)
