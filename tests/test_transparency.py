import os
import tempfile

from litewin import compat
from litewin import manifest


def test_compatibility_loading():
    db = compat.loadcompat()
    assert len(db) > 0
    names = {d["component name"] for d in db}
    assert "Microsoft.WindowsStore" in names
    assert "WindowsUpdate" in names


def test_compatibility_audit_pass():
    plan = {
        "build": "26100.9457",
        "removals": [
            {"id": "Clipchamp.Clipchamp"},
            {"id": "Microsoft.BingNews"},
        ],
    }
    res = compat.audit(plan)
    assert res["compatible"] is True
    assert len(res["errors"]) == 0


def test_compatibility_audit_detects_unsupported():
    plan = {
        "build": "26100.9457",
        "removals": [
            {"id": "WindowsUpdate"},
        ],
    }
    res = compat.audit(plan)
    assert res["compatible"] is False
    assert any("WindowsUpdate" in err for err in res["errors"])


def test_manifest_creation_and_markdown():
    data = {
        "iso": {"iso path": "dummy.iso", "sha256": "abcdef12345"},
        "image": {
            "name": "Windows 11 Pro",
            "edition": "Professional",
            "build": "26100.9457",
            "architecture": "x64",
        },
        "username": "CustomLocalUser",
        "removals": [{"name": "Clipchamp", "id": "Clipchamp.Clipchamp", "reason": "video editor"}],
        "retained": [{"name": "Microsoft Store", "id": "Microsoft.WindowsStore", "reason": "essential"}],
        "privacy": [{"name": "Limit Telemetry", "hive": "HKLM\\Software", "value": "AllowTelemetry", "data": 1}],
    }
    mf = manifest.create(data)
    assert mf["litewin version"] == "0.1.0"
    assert len(mf["components removed"]) == 1
    assert mf["account"]["username"] == "CustomLocalUser"
    assert mf["account"]["msa bypass"] is True

    md = manifest.markdown(mf)
    assert "LiteWin Build & Audit Report" in md
    assert "Windows 11 Pro" in md
    assert "Clipchamp" in md
    assert "Windows Defender" in md
    assert "CustomLocalUser" in md
    assert "BypassNRO" in md

    with tempfile.TemporaryDirectory() as tmp:
        paths = manifest.save(mf, tmp)
        assert os.path.isfile(paths["manifest"])
        assert os.path.isfile(paths["report"])
