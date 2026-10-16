#ifndef MyAppVersion
#define MyAppVersion "0.3.10"
#endif
[Setup]
AppId={{DAB3B28C-2B44-477A-A88A-10BDAA635FD1}
AppName=Autotest Platform
AppVersion={#MyAppVersion}
DefaultDirName=D:\AutotestPlatform
DefaultGroupName=Autotest Platform
PrivilegesRequired=lowest
OutputDir=dist-installer
OutputBaseFilename=AutotestPlatformRemoteSetup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
[Types]
Name: "desktop"; Description: "仅桌面客户端"
Name: "mobile"; Description: "桌面客户端与手机执行节点"
Name: "custom"; Description: "自定义"; Flags: iscustom
[Components]
Name: "desktop"; Description: "桌面客户端"; Types: desktop mobile custom; Flags: fixed
Name: "agent"; Description: "本地 Agent（构建所选执行能力）"; Types: mobile
[Files]
Source: "dist\AutotestPlatform\*"; DestDir: "{app}\desktop"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: desktop
Source: "dist\AutotestAgent\*"; DestDir: "{app}\agent"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: agent
Source: "config.example.json"; DestDir: "{app}"; DestName: "client.example.json"; Flags: ignoreversion
[Icons]
Name: "{group}\Autotest Platform"; Filename: "{app}\desktop\AutotestPlatform.exe"
Name: "{userdesktop}\Autotest Platform"; Filename: "{app}\desktop\AutotestPlatform.exe"
Name: "{group}\Autotest Agent"; Filename: "{app}\agent\AutotestAgent.exe"; Parameters: "--tray"; Components: agent
Name: "{userstartup}\Autotest Agent"; Filename: "{app}\agent\AutotestAgent.exe"; Parameters: "--tray"; Components: agent; Tasks: startup
[Tasks]
Name: "startup"; Description: "开机启动本地 Agent"; Flags: unchecked
[Run]
Filename: "{app}\desktop\AutotestPlatform.exe"; Description: "打开 Autotest Platform"; Flags: nowait postinstall skipifsilent
