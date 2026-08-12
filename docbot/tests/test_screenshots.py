"""The §5 chain: filename convention → image→page index → affected chapters.
All deterministic, so all of it is testable without a model."""

from __future__ import annotations

import json

from docbot import manual, screenshots


def test_classifies_the_e2e_naming_convention():
    shot = screenshots.classify(
        "screenshots/settings_password_page-Should_not_save_when_current_pass_is_wrong.png"
    )
    assert shot.kind == "e2e"
    assert shot.spec == "settings_password_page"
    assert shot.test == "Should not save when current pass is wrong"


def test_test_names_may_contain_hyphens():
    """Real case from combined.html: the test title is "Should save e-mail
    settings", so the filename carries a second hyphen. Splitting on anything
    but the first one misfiles it as hand-captured."""
    shot = screenshots.classify("screenshots/generaldeviceconfig_page-Should_save_e-mail_settings.png")
    assert shot.kind == "e2e"
    assert shot.spec == "generaldeviceconfig_page"
    assert shot.test == "Should save e-mail settings"


def test_spec_names_may_be_parameterised_by_an_account():
    """Also real: some specs are parameterised with an email address."""
    shot = screenshots.classify(
        "screenshots/Single_Device_page_for__s3beyaz@boryazilim_com-should_start_within_correct_page.png"
    )
    assert shot.kind == "e2e"
    assert shot.test == "should start within correct page"


def test_underscore_prefixed_but_test_shaped_names_are_flagged_not_guessed():
    """`_iosApp_page-should_add_new_iosApp_page_1.png` carries both signals.
    Undecidable from the filename, so it stays an orphan (the audit will demand
    a registry entry) but the ambiguity is recorded rather than hidden."""
    shot = screenshots.classify("screenshots/_iosApp_page-should_add_new_iosApp_page_1.png")
    assert shot.kind == "orphan"
    assert shot.ambiguous is True


def test_classifies_hand_captured_orphans():
    """§5.1 — ad-hoc names, no test behind them."""
    for src in ("images/_ldapSettings_1.png", "img/_wifiConfigs_add_2.png", "img/logo.png"):
        assert screenshots.classify(src).kind == "orphan", src


def test_parses_headings_and_collapses_wrapped_text(mini_manual):
    parsed = manual.parse(mini_manual)
    h1s = [h.text for h in parsed.headings if h.level == 1]
    assert h1s == ["CHAPTER 1: USERS", "CHAPTER 2: ROLES"]


def test_toc_is_not_mistaken_for_content(mini_manual):
    """Pandoc repeats every heading inside <nav>. Counting those would double
    the chapter count and attribute images to the wrong place."""
    parsed = manual.parse(mini_manual)
    assert sum(1 for h in parsed.headings if h.level == 1) == 2


def test_index_records_every_use_of_a_reused_image(mini_manual):
    index = screenshots.build_index(mini_manual)
    entry = next(
        img for img in index["images"]
        if img["basename"] == "users_create_page-Should_add_user_from_ldap.png"
    )
    sections = [use["section"] for use in entry["uses"]]
    assert sections == ["Add User", "Edit User"]
    assert index["counts"]["unique_images"] < index["counts"]["image_references"]


def test_index_counts_split_e2e_from_orphans(mini_manual):
    counts = screenshots.build_index(mini_manual)["counts"]
    assert counts["e2e_derived"] == 2
    assert counts["orphans"] == 2  # the logo and _ldapSettings_1
    assert counts["chapters"] == 2


def test_changed_image_resolves_to_its_chapters(mini_manual):
    index = screenshots.build_index(mini_manual)
    result = screenshots.impact(
        index, ["docs/screenshots/users_create_page-Should_add_user_from_ldap.png"]
    )
    assert result["screenshot_impact"] is True
    assert result["affected_pages"] == ["CHAPTER 1: USERS > Add User", "CHAPTER 1: USERS > Edit User"]


def test_changed_spec_implicates_the_screenshots_it_captures(mini_manual):
    """The Phase 1 deliverable: 'this change alters N screenshots used in
    chapters X and Y', with zero false positives."""
    index = screenshots.build_index(mini_manual)
    result = screenshots.impact(index, ["cypress/e2e/roles_page.spec.ts"])
    assert result["screenshot_impact"] is True
    assert [e["image"] for e in result["implicated_by_spec"]] == [
        "screenshots/roles_page-should_start_with_admin_role_only.png"
    ]
    assert result["affected_pages"] == ["CHAPTER 2: ROLES > Edit Role"]


def test_unrelated_source_change_produces_nothing(mini_manual):
    index = screenshots.build_index(mini_manual)
    result = screenshots.impact(index, ["src/protocol/apns/PushTransport.ts"])
    assert result["screenshot_impact"] is False
    assert result["affected_pages"] == []


def test_spec_with_no_indexed_screenshot_is_reported(mini_manual):
    index = screenshots.build_index(mini_manual)
    result = screenshots.impact(index, ["cypress/e2e/billing_page.spec.ts"])
    assert result["specs_with_no_screenshots"] == ["cypress/e2e/billing_page.spec.ts"]


def test_audit_flags_orphans_without_a_registry_entry(mini_manual, tmp_path):
    """§5.1 — the CI lint that stops the registry rotting within two releases."""
    index = screenshots.build_index(mini_manual)
    report = screenshots.audit(index)
    assert report["ok"] is False
    assert "screenshots/_ldapSettings_1.png" in report["unregistered_orphans"]

    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "- file: screenshots/_ldapSettings_1.png\n"
        "  renders: ['src/console/settings/LdapSettings.tsx']\n"
        "  captured: '2025-11-14'\n"
        "  version: '4.2'\n"
        "- file: ../../img/logo.png\n",
        encoding="utf-8",
    )
    report = screenshots.audit(index, registry)
    assert report["unregistered_orphans"] == []
    assert report["ok"] is True


def test_audit_detects_images_missing_on_disk(mini_manual, tmp_path):
    index = screenshots.build_index(mini_manual)
    report = screenshots.audit(index, images_root=tmp_path)
    assert report["counts"]["missing_on_disk"] == index["counts"]["unique_images"]
    assert report["ok"] is False


def test_index_is_json_serialisable(mini_manual):
    json.dumps(screenshots.build_index(mini_manual))
