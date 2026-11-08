# LiteWin

> **Windows, without the baggage.**

LiteWin is a Linux-native Windows 11 customization builder. It produces a lightweight, privacy-conscious, clean, and reliable Windows 11 installation experience directly from Linux.

Unlike typical post-install debloater scripts that execute aggressively after Windows is already running, LiteWin customizes the official Windows installation media declaratively before first boot.

---

## Core Principles

- **Performance:** Eliminates non-essential preinstalled applications (Clipchamp, news feeds, casual game ads, redundant promotional wrappers) and background telemetry activity to minimize idle RAM and CPU overhead.
- **Privacy:** Enforces sensible privacy defaults via documented Group Policies and registry settings (disabling Advertising ID, timeline uploads, and Start menu Bing queries) without breaking core Windows functionality.
- **Reliability:** Strictly preserves Windows Update, system recovery, hardware drivers, and core runtime libraries (including WebView2).
- **Security:** Preserves all native security infrastructure (Windows Defender, Firewall, SmartScreen, and User Account Control). LiteWin does not disable security services to chase artificial benchmark gains.
- **Transparency:** Produces verifiable SHA-256 build manifests and human-readable Markdown audit reports detailing every change made to the installation media.
- **Firefox-First Experience:** Bundles and configures Mozilla Firefox as the default browser out-of-the-box using official enterprise deployment policies and Windows OEM default associations.

---

## Architecture

```
LiteWin CLI
    │
Build Orchestrator
    ├── ISO Handling (Inspection, SHA-256 streaming, safe extraction)
    ├── Windows Image Engine (WIM/ESD metadata extraction, edition selection)
    ├── Package Management (Cataloged, safe-to-remove app filtering)
    ├── Privacy Configuration (Documented policies & registry tweaks)
    ├── Firefox Integration (Enterprise policies.json & AppAssoc.xml)
    ├── Compatibility Database (Data-driven component and dependency checks)
    ├── Audit & Manifest Reporting (JSON manifest + Markdown audit report)
    ├── Benchmarking Framework (Real metrics collector & comparator)
    └── Bootable ISO Generation (xorriso UEFI + BIOS repacking)
    │
Final Customized Windows 11 ISO
```

LiteWin operates at the orchestration level on Linux. Windows image servicing is abstracted: on Linux, it leverages `wimlib-imagex` and declarative OEM unattended execution; when delegating to Windows environments, it generates native PowerShell / DISM servicing scripts.

---

## Requirements

### Host Environment
- **Linux:** Pop!_OS, Ubuntu 22.04+, Debian 12+, or any modern x86_64 Linux distribution.
- **Python:** Python 3.10 or newer.

### External Tool Dependencies
- `7zz` or `7z` (p7zip) — for safe ISO file inspection and extraction.
- `xorriso` — for creating bootable UEFI / BIOS Windows ISOs.
- `wimlib-imagex` (`wimtools`) — for inspecting and exporting WIM images.
- `qemu-system-x86_64` & `ovmf` *(optional)* — for testing the generated ISO in a virtual machine with UEFI.

---

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/pahal-desai/LiteWin.git
cd LiteWin
pip install -e .
```

To run test suites:
```bash
pytest -v
```

---

## Usage Guide

LiteWin provides an intuitive CLI:

```bash
litewin --help
```

### 1. Check and Inspect Windows 11 ISO
Inspect required boot files and verify the ISO:
```bash
litewin check /path/to/Windows11.iso
```

Calculate SHA-256 hash and verify against known official Microsoft release checksums:
```bash
litewin inspect /path/to/Windows11.iso --hash
```

### 2. List Available Windows Editions
List all installable Windows editions contained within the image without extracting gigabytes of data:
```bash
litewin editions /path/to/Windows11.iso
```

Output:
```
[1] Windows 11 Home (Core) - build 26300.9457 [x64]
[2] Windows 11 Home N (CoreN) - build 26300.9457 [x64]
...
[6] Windows 11 Pro (Professional) - build 26300.9457 [x64]
```

### 3. Preview Customization Plan
Review the proposed removals, retained essential packages, and privacy tweaks before building:
```bash
litewin plan --profile standard
```

### 4. Build Customized Windows 11 ISO
Build the customized bootable ISO and generate the audit report:
```bash
litewin build /path/to/Windows11.iso --edition 6 --profile standard
```

For maximum image size reduction (exports only the selected edition):
```bash
litewin build /path/to/Windows11.iso --edition 6 --single-edition
```

### 5. Test in Virtual Machine (QEMU)
Preview or launch the generated ISO in QEMU with KVM and OVMF UEFI:
```bash
litewin test /path/to/LiteWin.iso
```

To boot interactively:
```bash
litewin test /path/to/LiteWin.iso --run --ram 4G --cpus 4
```

### 6. Performance Benchmarking
Generate the PowerShell metrics collector script to run inside Windows:
```bash
litewin bench collector > collect-metrics.ps1
```

Compare live collected results:
```bash
litewin bench compare --stock stock.json --litewin litewin.json
```

---

## Customization Profiles

| Profile | Description |
| :--- | :--- |
| `minimal` | Removes only third-party promotional bloatware (Solitaire ads, Clipchamp, Office stub). Retains all utility apps. |
| `standard` (Default) | Removes all safe-to-remove promotional apps, MSN news feeds, and background telemetry tools. Strictly retains essential apps (Store, Winget, Terminal, Notepad, Calculator, Snipping Tool). |
| `clean` | Standard profile with optional OneDrive removal. |

### Preserved Essential Packages

LiteWin protects critical system packages from accidental removal:
- `Microsoft.WindowsStore` (Store updates and licensing)
- `Microsoft.DesktopAppInstaller` (Winget package manager)
- `Microsoft.StorePurchaseApp` (UWP license manager)
- `Microsoft.WindowsTerminal` (Terminal console)
- `Microsoft.WindowsCalculator`
- `Microsoft.WindowsNotepad`
- `Microsoft.ScreenSketch` (Snipping Tool)
- Media format extensions (HEIF, VP9, WebMedia, WebP)

---

## Privacy & Security Model

Every setting altered by LiteWin is documented in `data/privacy.json`:
- **Telemetry Level:** Set to Required/Basic (level 1) — stops capture of web browsing history and user typing/inking while preserving Windows Update.
- **Advertising Identifier:** Disabled.
- **Activity History:** Syncing and cloud timeline upload disabled.
- **Start Menu Search:** Local search only; Bing query transmission disabled.
- **Security Services:** Windows Defender, Windows Firewall, SmartScreen, and User Account Control (UAC) are strictly preserved.

---

## Current Status & Limitations

- **Image Servicing Backend:** LiteWin uses declarative OEM setup injection (`$OEM$` + `autounattend.xml`) and `wimlib-imagex` on Linux. Offline native DISM servicing can be delegated to Windows environments via generated PowerShell scripts.
- **No Binary Redistribution:** LiteWin does not distribute proprietary Microsoft binaries or ISOs. Users must supply their own official Windows 11 installation media.
- **Licensing:** LiteWin does not bypass or tamper with Windows licensing or activation. Users are responsible for complying with Microsoft licensing agreements.

---

## License

This project is licensed under the [MIT License](LICENSE).
