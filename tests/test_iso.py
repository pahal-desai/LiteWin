import hashlib
import os
import tempfile
import pytest

from litewin import iso
from litewin import workspace


def test_sha256_calculation():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"LiteWin test buffer")
        temp = f.name
    try:
        expected = hashlib.sha256(b"LiteWin test buffer").hexdigest()
        assert iso.sha256(temp) == expected
    finally:
        os.unlink(temp)


def test_missing_file_sha256():
    with pytest.raises(FileNotFoundError):
        iso.sha256("/non/existent/path/here.iso")


def test_verify_missing_iso():
    res = iso.verify("/invalid/file.iso")
    assert res["valid"] is False
    assert "not found" in res["error"].lower()


def test_verify_small_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"not an iso")
        temp = f.name
    try:
        res = iso.verify(temp)
        assert res["valid"] is False
        assert "too small" in res["error"]
    finally:
        os.unlink(temp)


def test_workspace_lifecycle():
    ws = workspace.setup(name="testrun")
    assert os.path.isdir(ws["root"])
    assert os.path.isdir(ws["extracted"])
    assert os.path.isdir(ws["staging"])
    assert os.path.isdir(ws["out"])

    st = workspace.status(ws["root"])
    assert st["exists"] is True
    assert st["files"] == 0

    workspace.clean(ws["root"])
    assert not os.path.exists(ws["root"])
