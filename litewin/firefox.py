import os
import shutil
import urllib.request

MOZILLA_URL = "https://download.mozilla.org/?product=firefox-latest-ssl&os=win64&lang=en-US"

POLICIES = """{
  "policies": {
    "DisableTelemetry": true,
    "DisableFirefoxStudies": true,
    "EnableTrackingProtection": {
      "Value": true,
      "Locked": false,
      "Cryptomining": true,
      "Fingerprinting": true
    },
    "OverrideFirstRunPage": "",
    "OverridePostUpdatePage": "",
    "DontCheckDefaultBrowser": false
  }
}
"""

APP_ASSOC = """<?xml version="1.0" encoding="UTF-8"?>
<DefaultAssociations>
  <Association Identifier=".htm" ProgId="FirefoxHTML-308046B0AF4A39CB" ApplicationName="Firefox" />
  <Association Identifier=".html" ProgId="FirefoxHTML-308046B0AF4A39CB" ApplicationName="Firefox" />
  <Association Identifier="http" ProgId="FirefoxURL-308046B0AF4A39CB" ApplicationName="Firefox" />
  <Association Identifier="https" ProgId="FirefoxURL-308046B0AF4A39CB" ApplicationName="Firefox" />
</DefaultAssociations>
"""


def getpolicy():
    return POLICIES


def getassoc():
    return APP_ASSOC


def fetch(dest, url=MOZILLA_URL):
    # downloads official Mozilla Firefox offline installer
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 LiteWin-Builder"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)
    return dest


def bundle(targetdir):
    # generates all necessary files in the target folder for silent setup during Windows install
    os.makedirs(targetdir, exist_ok=True)

    policypath = os.path.join(targetdir, "policies.json")
    with open(policypath, "w", encoding="utf-8") as f:
        f.write(POLICIES)

    assocpath = os.path.join(targetdir, "AppAssoc.xml")
    with open(assocpath, "w", encoding="utf-8") as f:
        f.write(APP_ASSOC)

    scriptpath = os.path.join(targetdir, "setup-firefox.cmd")
    script = (
        "@echo off\r\n"
        "echo [LiteWin] Installing Mozilla Firefox...\r\n"
        "if exist \"%~dp0FirefoxSetup.exe\" (\r\n"
        "    \"%~dp0FirefoxSetup.exe\" -ms\r\n"
        ")\r\n"
        "timeout /t 5 /nobreak >nul\r\n"
        "set FFDIR=%ProgramFiles%\\Mozilla Firefox\r\n"
        "if exist \"%FFDIR%\" (\r\n"
        "    mkdir \"%FFDIR%\\distribution\" 2>nul\r\n"
        "    copy /y \"%~dp0policies.json\" \"%FFDIR%\\distribution\\policies.json\" >nul\r\n"
        ")\r\n"
        "if exist \"%~dp0AppAssoc.xml\" (\r\n"
        "    dism.exe /Online /Import-DefaultAppAssociations:\"%~dp0AppAssoc.xml\" >nul\r\n"
        ")\r\n"
        "echo [LiteWin] Firefox setup complete.\r\n"
    )
    with open(scriptpath, "w", encoding="utf-8") as f:
        f.write(script)

    return {
        "policies": policypath,
        "associations": assocpath,
        "script": scriptpath,
    }
