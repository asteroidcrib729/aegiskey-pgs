; Inno Setup 6 Installer Script for AegisKey Password Studio

#ifndef AppVersion
  #define AppVersion "2.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\dist\windows\staged\AegisKey"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\dist\windows"
#endif
#ifndef OutputBaseFilename
  #define OutputBaseFilename "AegisKey-" + AppVersion + "-win64-setup"
#endif
#ifndef IconFile
  #define IconFile "..\..\build\windows\assets\AegisKey.ico"
#endif
#ifndef LicenseFile
  #define LicenseFile "..\..\LICENSE"
#endif

[Setup]
AppId={{8D6D4A7E-5D9F-4C61-A53E-9C4E12A7B801}
AppName=AegisKey Password Studio
AppVersion={#AppVersion}
AppVerName=AegisKey Password Studio {#AppVersion}
AppPublisher=AegisKey Open Source Contributors
AppPublisherURL=https://github.com/asteroidcrib729/aegiskey-pgs
AppSupportURL=https://github.com/asteroidcrib729/aegiskey-pgs/issues
DefaultDirName={localappdata}\Programs\AegisKey Password Studio
DefaultGroupName=AegisKey Password Studio
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
LicenseFile={#LicenseFile}
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseFilename}
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\AegisKey.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\AegisKey Password Studio"; Filename: "{app}\AegisKey.exe"
Name: "{group}\Uninstall AegisKey Password Studio"; Filename: "{uninstallexe}"
Name: "{autodesktop}\AegisKey Password Studio"; Filename: "{app}\AegisKey.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AegisKey.exe"; Description: "{cm:LaunchProgram,AegisKey Password Studio}"; Flags: nowait postinstall skipifsilent
