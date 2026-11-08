import os
import tempfile
import xml.etree.ElementTree as ET

from litewin import unattend
from litewin import qemu
from litewin import bench
from litewin import repack
from litewin import iso


def test_unattend_xml_structure():
    content = unattend.generate(edition="Windows 11 Pro", lang="en-US")
    assert "windowsPE" in content
    assert "specialize" in content
    assert "oobeSystem" in content
    assert "BypassTPMCheck" in content
    assert "setup-firefox.cmd" in content
    assert "apply-privacy.ps1" in content
    assert "remove-packages.ps1" in content

    # verify valid XML syntax
    root = ET.fromstring(content)
    assert root.tag.endswith("unattend")


def test_qemu_command_builder():
    with tempfile.NamedTemporaryFile(suffix=".iso", delete=False) as f:
        f.write(b"dummy iso")
        temp = f.name
    try:
        cmd = qemu.makecmd(temp, ram="8G", cpus=2)
        assert any("qemu-system-x86_64" in arg for arg in cmd)
        assert "-cdrom" in cmd
        assert temp in cmd
        assert "8G" in cmd
    finally:
        os.unlink(temp)


def test_bench_compare():
    stock = {
        "process count": 185,
        "startup apps": 8,
        "used ram mb": 3800,
        "used disk gb": 28.5,
        "boot time sec": 24.2,
    }
    lite = {
        "process count": 110,
        "startup apps": 2,
        "used ram mb": 2100,
        "used disk gb": 19.2,
        "boot time sec": 15.1,
    }
    res = bench.compare(stock, lite)
    assert res["delta"]["process count"]["difference"] == -75
    assert "-40.5%" == res["delta"]["process count"]["percent change"]
    assert res["delta"]["used ram mb"]["difference"] == -1700

    report = bench.markdown(res, conditions="QEMU KVM 4 vCPU 4GB RAM")
    assert "Stock Windows 11" in report
    assert "LiteWin" in report
    assert "-75" in report


def test_repack_mock_tree():
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        # create mock structure with boot files
        os.makedirs(os.path.join(src, "boot"), exist_ok=True)
        os.makedirs(os.path.join(src, "efi", "microsoft", "boot"), exist_ok=True)
        with open(os.path.join(src, "boot", "etfsboot.com"), "wb") as f:
            f.write(b"\x00" * 2048)
        with open(os.path.join(src, "efi", "microsoft", "boot", "efisys.bin"), "wb") as f:
            f.write(b"\x00" * 2048)
        with open(os.path.join(src, "setup.exe"), "wb") as f:
            f.write(b"mock setup")

        out_iso = os.path.join(out, "test_out.iso")
        res = repack.repack(src, out_iso, volid="TEST_ISO")
        assert os.path.isfile(res["iso path"])
        assert res["size bytes"] > 0
