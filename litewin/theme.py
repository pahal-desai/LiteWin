import os
import shutil

DATADIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def findwallpaper(custom=None):
    # locates default or custom wallpaper image
    if custom and os.path.isfile(custom):
        return custom

    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "wallpaper.png"),
        os.path.join(DATADIR, "wallpaper.png"),
        os.path.expanduser("~/Downloads/wallpaper.png"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def makescript(wallpaper_dest="C:\\Windows\\Web\\Wallpaper\\LiteWin\\wallpaper.png", dark=True):
    # generates PowerShell script to apply dark theme and set wallpaper immediately
    lines = [
        "# LiteWin Theme & Wallpaper Customization Script",
        "$ErrorActionPreference = 'SilentlyContinue'",
        "",
        "Write-Output '[LiteWin] Applying dark theme and custom wallpaper...'",
        "",
    ]

    if dark:
        lines.extend([
            "# Apply Dark Theme to current user and default user profile",
            "$themeKeys = @(",
            "    'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize',",
            "    'Registry::HKEY_USERS\\.DEFAULT\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize'",
            ")",
            "foreach ($key in $themeKeys) {",
            "    if (!(Test-Path $key)) { New-Item -Path $key -Force | Out-Null }",
            "    Set-ItemProperty -Path $key -Name 'AppsUseLightTheme' -Type DWord -Value 0 -Force",
            "    Set-ItemProperty -Path $key -Name 'SystemUsesLightTheme' -Type DWord -Value 0 -Force",
            "    Set-ItemProperty -Path $key -Name 'EnableTransparency' -Type DWord -Value 1 -Force",
            "}",
            "",
        ])

    if wallpaper_dest:
        lines.extend([
            f"# Configure wallpaper: {wallpaper_dest}",
            f"$wp = '{wallpaper_dest}'",
            "if (Test-Path $wp) {",
            "    $desktopKeys = @(",
            "        'HKCU:\\Control Panel\\Desktop',",
            "        'Registry::HKEY_USERS\\.DEFAULT\\Control Panel\\Desktop'",
            "    )",
            "    foreach ($dkey in $desktopKeys) {",
            "        if (!(Test-Path $dkey)) { New-Item -Path $dkey -Force | Out-Null }",
            "        Set-ItemProperty -Path $dkey -Name 'Wallpaper' -Value $wp -Force",
            "        Set-ItemProperty -Path $dkey -Name 'WallpaperStyle' -Value '10' -Force",
            "        Set-ItemProperty -Path $dkey -Name 'TileWallpaper' -Value '0' -Force",
            "    }",
            "",
            "    # Invoke Win32 SystemParametersInfo to apply wallpaper without rebooting",
            "    $sig = @'",
            "    using System.Runtime.InteropServices;",
            "    public class Win32Wallpaper {",
            "        [DllImport(\"user32.dll\", CharSet = CharSet.Auto)]",
            "        public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);",
            "    }",
            "'@",
            "    Add-Type -TypeDefinition $sig -ErrorAction SilentlyContinue",
            "    [Win32Wallpaper]::SystemParametersInfo(0x0014, 0, $wp, 0x01 -bor 0x02) | Out-Null",
            "}",
            "",
        ])

    lines.append("Write-Output '[LiteWin] Theme and wallpaper applied.'")
    return "\n".join(lines)


def bundle(oem_root, custom_wallpaper=None, dark=True):
    # copies wallpaper to OEM structure and generates apply-theme.ps1
    # oem_root is $OEM$ path (e.g. extracted/sources/$OEM$)
    wp_src = findwallpaper(custom_wallpaper)
    bundled_wp = None
    target_wp_win = "C:\\Windows\\Web\\Wallpaper\\LiteWin\\wallpaper.png"

    if wp_src:
        oem_wp_dir = os.path.join(oem_root, "$$", "Web", "Wallpaper", "LiteWin")
        os.makedirs(oem_wp_dir, exist_ok=True)
        dest_wp = os.path.join(oem_wp_dir, "wallpaper.png")
        shutil.copy2(wp_src, dest_wp)
        bundled_wp = dest_wp

    scripts_dir = os.path.join(oem_root, "$$", "Setup", "Scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    theme_script_path = os.path.join(scripts_dir, "apply-theme.ps1")

    script_content = makescript(
        wallpaper_dest=target_wp_win if bundled_wp else None,
        dark=dark,
    )
    with open(theme_script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    return {
        "wallpaper source": wp_src,
        "wallpaper bundled": bundled_wp,
        "script": theme_script_path,
        "dark theme": dark,
    }
