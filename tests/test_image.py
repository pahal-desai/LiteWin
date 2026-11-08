from litewin import image

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<WIM>
  <IMAGE INDEX="1">
    <NAME>Windows 11 Pro</NAME>
    <DESCRIPTION>Windows 11 Professional</DESCRIPTION>
    <TOTALBYTES>15000000000</TOTALBYTES>
    <WINDOWS>
      <ARCH>9</ARCH>
      <EDITIONID>Professional</EDITIONID>
      <INSTALLATIONTYPE>Client</INSTALLATIONTYPE>
      <LANGUAGES>
        <DEFAULT>en-US</DEFAULT>
      </LANGUAGES>
      <VERSION>
        <BUILD>26100</BUILD>
        <SPBUILD>1</SPBUILD>
      </VERSION>
    </WINDOWS>
  </IMAGE>
</WIM>
"""


def test_detectenv():
    env = image.detectenv()
    assert "environment" in env
    assert "engine" in env
    assert isinstance(env["supported"], bool)


def test_parsexml():
    items = image.parsexml(SAMPLE_XML)
    assert len(items) == 1
    item = items[0]
    assert item["index"] == 1
    assert item["name"] == "Windows 11 Pro"
    assert item["edition"] == "Professional"
    assert item["architecture"] == "x64"
    assert item["build"] == "26100.1"
    assert item["language"] == "en-US"


def test_makescript():
    script = image.makescript(
        mountdir="C:\\Mount",
        packages=["Clipchamp", "BingNews"],
        registry=[
            {
                "hive": "HKLM\\LiteWinSoftware",
                "key": "Policies\\Microsoft\\Windows\\DataCollection",
                "value": "AllowTelemetry",
                "type": "REG_DWORD",
                "data": 0,
            }
        ],
    )
    assert "C:\\Mount" in script
    assert "Clipchamp" in script
    assert "AllowTelemetry" in script
    assert "reg load" in script
    assert "reg unload" in script
