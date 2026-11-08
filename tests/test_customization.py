import os
import tempfile
import pytest

from litewin import packages
from litewin import privacy
from litewin import firefox


def test_packages_loading():
    apps = packages.loadapps()
    assert len(apps) > 0
    ids = {a["id"] for a in apps}
    assert "Microsoft.WindowsStore" in ids
    assert "Clipchamp.Clipchamp" in ids


def test_packages_standard_profile():
    res = packages.filterapps(profile="standard")
    removed_ids = {a["id"] for a in res["remove"]}
    retained_ids = {a["id"] for a in res["retain"]}

    # Clipchamp should be removed in standard
    assert "Clipchamp.Clipchamp" in removed_ids
    # Store and Terminal MUST be retained
    assert "Microsoft.WindowsStore" in retained_ids
    assert "Microsoft.WindowsTerminal" in retained_ids


def test_packages_reject_essential_removal():
    with pytest.raises(ValueError) as exc:
        packages.filterapps(profile="custom", custom=["Microsoft.WindowsStore"])
    assert "essential" in str(exc.value)


def test_privacy_loading():
    rules = privacy.loadprivacy()
    assert len(rules) > 0
    names = [r["name"] for r in rules]
    assert any("Diagnostic" in n for n in names)
    assert any("Advertising" in n for n in names)


def test_privacy_reg_generation():
    rules = privacy.loadprivacy()
    reg = privacy.makereg(rules)
    assert "Windows Registry Editor Version 5.00" in reg
    assert "AllowTelemetry" in reg


def test_privacy_script_generation():
    rules = privacy.loadprivacy()
    script = privacy.makescript(rules)
    assert "Set-ItemProperty" in script
    assert "AllowTelemetry" in script


def test_firefox_bundle():
    with tempfile.TemporaryDirectory() as tmp:
        res = firefox.bundle(tmp)
        assert os.path.isfile(res["policies"])
        assert os.path.isfile(res["associations"])
        assert os.path.isfile(res["script"])

        with open(res["policies"], "r", encoding="utf-8") as f:
            content = f.read()
            assert "DisableTelemetry" in content
            assert "DontCheckDefaultBrowser" in content

        with open(res["associations"], "r", encoding="utf-8") as f:
            content = f.read()
            assert "FirefoxHTML" in content
            assert "FirefoxURL" in content
