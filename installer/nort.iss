[Setup]
AppId={{5CA2B7D2-606D-44F2-96E2-DBF5EEB181C7}
AppName=NORT Desktop AI
AppVersion=0.1.0
AppPublisher=NORT
DefaultDirName={localappdata}\Programs\NORT Desktop AI
DefaultGroupName=NORT Desktop AI
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=NORT-Desktop-AI-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\NORT-Desktop-AI.exe

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "..\dist\NORT-Desktop-AI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NORT Desktop AI"; Filename: "{app}\NORT-Desktop-AI.exe"
Name: "{autodesktop}\NORT Desktop AI"; Filename: "{app}\NORT-Desktop-AI.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NORT-Desktop-AI.exe"; Description: "Abrir NORT Desktop AI"; Flags: nowait postinstall skipifsilent
