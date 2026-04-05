[Setup]
AppName=Lead Gen Pro Elite
AppVersion=11.0
DefaultDirName={autopf}\LeadGenProElite
DefaultGroupName=Lead Gen Pro Elite
UninstallDisplayIcon={app}\LeadGenPro_Elite.exe
Compression=lzma2
SolidCompression=yes
OutputDir=dist
OutputBaseFilename=LeadGenPro_Elite_Setup
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Aqui incluimos todo el contenido de la carpeta dist que genere PyInstaller
Source: "dist\LeadGenPro_Elite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Lead Gen Pro Elite"; Filename: "{app}\LeadGenPro_Elite.exe"
Name: "{autodesktop}\Lead Gen Pro Elite"; Filename: "{app}\LeadGenPro_Elite.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LeadGenPro_Elite.exe"; Description: "{cm:LaunchProgram,Lead Gen Pro Elite}"; Flags: nowait postinstall skipifsilent
