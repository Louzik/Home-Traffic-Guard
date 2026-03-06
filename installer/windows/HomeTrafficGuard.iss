; Inno Setup script для Home Traffic Guard

#define MyAppName "Home Traffic Guard"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Home Traffic Guard"
#define MyAppExeName "HomeTrafficGuard.exe"

[Setup]
AppId={{2E247B97-1056-4E0C-96AA-3C7DBAD6E542}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Home Traffic Guard
DefaultGroupName=Home Traffic Guard
DisableProgramGroupPage=yes
OutputDir=installer\windows\output
OutputBaseFilename=HomeTrafficGuardSetup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\HomeTrafficGuard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Home Traffic Guard"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Home Traffic Guard"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,Home Traffic Guard}"; Flags: nowait postinstall skipifsilent
