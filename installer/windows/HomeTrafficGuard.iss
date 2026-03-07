; Inno Setup script для Home Traffic Guard

#define MyAppName "Home Traffic Guard"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Home Traffic Guard"
#define MyAppExeName "HomeTrafficGuard.exe"
#define MyVCRedistExe "vc_redist.x64.exe"

[Setup]
AppId={{2E247B97-1056-4E0C-96AA-3C7DBAD6E542}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Home Traffic Guard
DefaultGroupName=Home Traffic Guard
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=HomeTrafficGuardSetup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\HomeTrafficGuard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "prereqs\{#MyVCRedistExe}"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{autoprograms}\Home Traffic Guard"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Home Traffic Guard"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,Home Traffic Guard}"; Flags: nowait postinstall skipifsilent

[Code]
function IsVCRedistInstalled: Boolean;
var
  Installed: Cardinal;
begin
  Result := False;
  if RegQueryDWordValue(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed) then
    Result := Installed = 1;
end;

procedure InstallVCRedistIfNeeded;
var
  ResultCode: Integer;
  ExePath: string;
begin
  if IsVCRedistInstalled then
    Exit;

  ExePath := ExpandConstant('{tmp}\{#MyVCRedistExe}');
  if not FileExists(ExePath) then
    RaiseException('Не найден пакет Microsoft Visual C++ Redistributable в установщике.');

  if not Exec(ExePath, '/install /quiet /norestart', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    RaiseException('Не удалось запустить установщик Microsoft Visual C++ Redistributable.');

  if not ((ResultCode = 0) or (ResultCode = 1638) or (ResultCode = 3010)) then
    RaiseException(
      'Ошибка установки Microsoft Visual C++ Redistributable. Код: ' + IntToStr(ResultCode)
    );
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    InstallVCRedistIfNeeded;
end;
