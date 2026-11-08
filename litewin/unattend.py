def make_specialize_commands(disable_defender=False, disable_updates=True, dark_theme=True, wallpaper=True):
    cmds = [
        ("Configure LiteWin Privacy", "powershell.exe -ExecutionPolicy Bypass -NoProfile -File C:\\Windows\\Setup\\Scripts\\apply-privacy.ps1")
    ]
    if disable_defender:
        cmds.extend([
            ("Disable Windows Defender Services", 'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender" /v DisableAntiSpyware /t REG_DWORD /d 1 /f'),
            ("Disable Defender Realtime Monitoring", 'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Real-Time Protection" /v DisableRealtimeMonitoring /t REG_DWORD /d 1 /f'),
            ("Disable WinDefend Service", 'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\WinDefend" /v Start /t REG_DWORD /d 4 /f'),
            ("Disable WdFilter Driver", 'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\WdFilter" /v Start /t REG_DWORD /d 4 /f'),
        ])
    cmds.extend([
        ("Lock BypassNRO on installed system", "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\OOBE /v BypassNRO /t REG_DWORD /d 1 /f"),
        ("Block Microsoft Account Enforcement", "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v NoConnectedUser /t REG_DWORD /d 1 /f"),
    ])
    if disable_updates:
        cmds.extend([
            ("Permanently Disable Windows Update", "powershell.exe -ExecutionPolicy Bypass -NoProfile -File C:\\Windows\\Setup\\Scripts\\disable-updates.ps1"),
            ("Disable wuauserv Service", "reg add HKLM\\SYSTEM\\CurrentControlSet\\Services\\wuauserv /v Start /t REG_DWORD /d 4 /f"),
            ("Disable WaaSMedicSvc Service", "reg add HKLM\\SYSTEM\\CurrentControlSet\\Services\\WaaSMedicSvc /v Start /t REG_DWORD /d 4 /f"),
            ("Disable UsoSvc Service", "reg add HKLM\\SYSTEM\\CurrentControlSet\\Services\\UsoSvc /v Start /t REG_DWORD /d 4 /f"),
            ("Disable dosvc Service", "reg add HKLM\\SYSTEM\\CurrentControlSet\\Services\\dosvc /v Start /t REG_DWORD /d 4 /f"),
        ])
    if dark_theme:
        cmds.extend([
            ("Set Dark Theme System", "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize /v SystemUsesLightTheme /t REG_DWORD /d 0 /f"),
            ("Set Dark Theme Apps", "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize /v AppsUseLightTheme /t REG_DWORD /d 0 /f"),
        ])
    if wallpaper:
        cmds.extend([
            ("Set LiteWin Wallpaper Policy", "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v Wallpaper /t REG_SZ /d C:\\Windows\\Web\\Wallpaper\\LiteWin\\wallpaper.png /f"),
            ("Set LiteWin Wallpaper Style", "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v WallpaperStyle /t REG_SZ /d 10 /f"),
        ])

    xml_lines = []
    for order, (desc, path) in enumerate(cmds, start=1):
        xml_lines.append(f"""        <RunSynchronousCommand wcm:action="add" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
          <Order>{order}</Order>
          <Description>{desc}</Description>
          <Path>{path}</Path>
        </RunSynchronousCommand>""")
    return "\n".join(xml_lines)


def make_first_logon_commands():
    cmds = [
        ("Remove non-essential bloat packages", "powershell.exe -ExecutionPolicy Bypass -NoProfile -File C:\\Windows\\Setup\\Scripts\\remove-packages.ps1"),
        ("Setup Mozilla Firefox", "cmd.exe /c C:\\Windows\\Setup\\Scripts\\setup-firefox.cmd"),
        ("Apply Dark Theme and Wallpaper", "powershell.exe -ExecutionPolicy Bypass -NoProfile -File C:\\Windows\\Setup\\Scripts\\apply-theme.ps1"),
    ]
    xml_lines = []
    for order, (desc, cmd) in enumerate(cmds, start=1):
        xml_lines.append(f"""        <SynchronousCommand wcm:action="add" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
          <Order>{order}</Order>
          <Description>{desc}</Description>
          <CommandLine>{cmd}</CommandLine>
        </SynchronousCommand>""")
    return "\n".join(xml_lines)


def generate(edition="Windows 11 Pro", lang="en-US", disable_defender=False, username="User", disable_updates=True, dark_theme=True, wallpaper=True):
    # Generates standard, reliable autounattend.xml using official Microsoft passes
    # Completely bypasses Microsoft Account (MSA) enforcement and configures an offline local account
    # Permanently disables Windows Update, enforces dark mode, and applies custom LiteWin wallpaper
    protect_pc = "3" if disable_defender else "1"
    specialize_cmds = make_specialize_commands(
        disable_defender=disable_defender,
        disable_updates=disable_updates,
        dark_theme=dark_theme,
        wallpaper=wallpaper,
    )
    first_logon_cmds = make_first_logon_commands()

    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
  <settings pass="windowsPE">
    <component name="Microsoft-Windows-International-Core-WinPE" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <SetupUILanguage>
        <UILanguage>{lang}</UILanguage>
      </SetupUILanguage>
      <InputLocale>{lang}</InputLocale>
      <SystemLocale>{lang}</SystemLocale>
      <UILanguage>{lang}</UILanguage>
      <UserLocale>{lang}</UserLocale>
    </component>
    <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <RunSynchronous>
        <RunSynchronousCommand wcm:action="add" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
          <Order>1</Order>
          <Description>Bypass hardware requirements checks</Description>
          <Path>reg add HKLM\\SYSTEM\\Setup\\LabConfig /v BypassTPMCheck /t REG_DWORD /d 1 /f</Path>
        </RunSynchronousCommand>
        <RunSynchronousCommand wcm:action="add" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
          <Order>2</Order>
          <Description>Bypass SecureBoot check</Description>
          <Path>reg add HKLM\\SYSTEM\\Setup\\LabConfig /v BypassSecureBootCheck /t REG_DWORD /d 1 /f</Path>
        </RunSynchronousCommand>
        <RunSynchronousCommand wcm:action="add" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
          <Order>3</Order>
          <Description>Bypass RAM check</Description>
          <Path>reg add HKLM\\SYSTEM\\Setup\\LabConfig /v BypassRAMCheck /t REG_DWORD /d 1 /f</Path>
        </RunSynchronousCommand>
        <RunSynchronousCommand wcm:action="add" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
          <Order>4</Order>
          <Description>Bypass Network &amp; MSA Requirement</Description>
          <Path>reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\OOBE /v BypassNRO /t REG_DWORD /d 1 /f</Path>
        </RunSynchronousCommand>
      </RunSynchronous>
    </component>
  </settings>
  <settings pass="specialize">
    <component name="Microsoft-Windows-Deployment" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <RunSynchronous>
{specialize_cmds}
      </RunSynchronous>
    </component>
  </settings>
  <settings pass="oobeSystem">
    <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <OOBE>
        <HideEULAPage>true</HideEULAPage>
        <HideOnlineAccountScreens>true</HideOnlineAccountScreens>
        <HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE>
        <NetworkLocation>Work</NetworkLocation>
        <ProtectYourPC>{protect_pc}</ProtectYourPC>
      </OOBE>
      <UserAccounts>
        <LocalAccounts>
          <LocalAccount wcm:action="add">
            <Name>{username}</Name>
            <DisplayName>{username}</DisplayName>
            <Group>Administrators</Group>
            <Password>
              <Value></Value>
              <PlainText>true</PlainText>
            </Password>
          </LocalAccount>
        </LocalAccounts>
      </UserAccounts>
      <AutoLogon>
        <Password>
          <Value></Value>
          <PlainText>true</PlainText>
        </Password>
        <Enabled>true</Enabled>
        <LogonCount>1</LogonCount>
        <Username>{username}</Username>
      </AutoLogon>
      <FirstLogonCommands>
{first_logon_cmds}
      </FirstLogonCommands>
    </component>
  </settings>
</unattend>
"""
    return xml
