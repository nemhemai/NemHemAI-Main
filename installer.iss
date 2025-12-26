; NemhemAI Installer Script for Inno Setup
; Download Inno Setup from: https://jrsoftware.org/isdl.php

#define MyAppName "NemhemAI"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Company"
#define MyAppURL "https://yourwebsite.com"
#define MyAppExeName "NemhemAI.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{A8B9C0D1-E2F3-4567-8901-234567890ABC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
OutputDir=installer_output
OutputBaseFilename=NemhemAI-Setup-v{#MyAppVersion}
SetupIconFile=
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application folder (Directory mode - includes EXE and all dependencies)
Source: "dist\NemhemAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation files
Source: "USER_GUIDE.md"; DestDir: "{app}"; DestName: "README.txt"; Flags: ignoreversion isreadme
Source: "BUILD_EXE_GUIDE.md"; DestDir: "{app}\docs"; Flags: ignoreversion; Attribs: readonly
Source: "BUILD_CHECKLIST.md"; DestDir: "{app}\docs"; Flags: ignoreversion; Attribs: readonly

; Create necessary directories
[Dirs]
Name: "{app}\databases"; Permissions: users-modify
Name: "{app}\csv_uploads"; Permissions: users-modify
Name: "{app}\uploads"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"
Name: "{group}\User Guide"; Filename: "{app}\README.txt"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Check for Ollama installation
Filename: "{cmd}"; Parameters: "/c where ollama >nul 2>&1 && echo Ollama is installed || echo Ollama NOT installed"; StatusMsg: "Checking for Ollama..."; Flags: runhidden waituntilterminated

; Option to launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  OllamaCheckPage: TOutputMsgMemoWizardPage;
  OllamaInstalled: Boolean;

function CheckOllama: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c where ollama', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

procedure InitializeWizard;
begin
  OllamaCheckPage := CreateOutputMsgMemoPage(wpWelcome,
    'System Requirements Check', 
    'Checking for required software',
    'NemhemAI requires Ollama to be installed on your system. ' +
    'Checking if Ollama is installed...',
    '');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;
  
  if CurPageID = wpWelcome then
  begin
    OllamaInstalled := CheckOllama;
    
    if OllamaInstalled then
    begin
      OllamaCheckPage.RichEditViewer.Lines.Add('✓ Ollama is installed!');
      OllamaCheckPage.RichEditViewer.Lines.Add('');
      OllamaCheckPage.RichEditViewer.Lines.Add('You can proceed with the installation.');
    end
    else
    begin
      OllamaCheckPage.RichEditViewer.Lines.Add('✗ Ollama is NOT installed!');
      OllamaCheckPage.RichEditViewer.Lines.Add('');
      OllamaCheckPage.RichEditViewer.Lines.Add('NemhemAI requires Ollama to function properly.');
      OllamaCheckPage.RichEditViewer.Lines.Add('');
      OllamaCheckPage.RichEditViewer.Lines.Add('Please install Ollama from:');
      OllamaCheckPage.RichEditViewer.Lines.Add('https://ollama.com/download');
      OllamaCheckPage.RichEditViewer.Lines.Add('');
      OllamaCheckPage.RichEditViewer.Lines.Add('You can continue the installation, but the application');
      OllamaCheckPage.RichEditViewer.Lines.Add('will not work until Ollama is installed.');
      
      if MsgBox('Ollama is not installed. Do you want to download it now?', 
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        ShellExec('open', 'https://ollama.com/download', '', '', SW_SHOW, ewNoWait, ErrorCode);
        Result := False; // Prevent moving to next page
      end;
    end;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create a launcher script for better startup
    SaveStringToFile(ExpandConstant('{app}\Launch.bat'), 
      '@echo off' + #13#10 +
      'echo Starting NemhemAI...' + #13#10 +
      'cd /d "%~dp0"' + #13#10 +
      'start "" "NemhemAI.exe"' + #13#10 +
      'timeout /t 2 >nul' + #13#10 +
      'exit', 
      False);
  end;
end;

[UninstallDelete]
Type: files; Name: "{app}\Launch.bat"
Type: files; Name: "{app}\users.db"
Type: filesandordirs; Name: "{app}\databases"
Type: filesandordirs; Name: "{app}\csv_uploads"
Type: filesandordirs; Name: "{app}\uploads"
Type: filesandordirs; Name: "{app}\__pycache__"

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nNemhemAI is an AI-powered chat assistant with document analysis and data visualization capabilities.%n%nIMPORTANT: This application requires Ollama to be installed on your system.
FinishedLabel=Setup has finished installing [name] on your computer.%n%nIMPORTANT: Make sure Ollama is running before launching NemhemAI.%n%nThe application will open your browser automatically and run on http://localhost:8000
