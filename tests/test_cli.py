import subprocess
import sys


def test_cli_help():
    res = subprocess.run([sys.executable, "-m", "litewin.cli", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "LiteWin" in res.stdout
    assert "check" in res.stdout


def test_cli_check_missing_file():
    res = subprocess.run([sys.executable, "-m", "litewin.cli", "check", "/missing.iso"], capture_output=True, text=True)
    assert res.returncode == 1
