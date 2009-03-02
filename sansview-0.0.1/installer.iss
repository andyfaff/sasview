; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

[Setup]
AppName=SansView-0.1
AppVerName=SansView 0.1
AppPublisher=University of Tennessee
AppPublisherURL=http://danse.chem.utk.edu/
AppSupportURL=http://danse.chem.utk.edu/
AppUpdatesURL=http://danse.chem.utk.edu/
DefaultDirName={userappdata}\SansView-0.1
DefaultGroupName=DANSE\SansView-0.1
DisableProgramGroupPage=yes
LicenseFile=license.txt
OutputBaseFilename=setupSansView
SetupIconFile=images\ball.ico
Compression=lzma
SolidCompression=yes
PrivilegesRequired=none

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\SansView.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "images\*"; DestDir: "{app}\images"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\SansView"; Filename: "{app}\SansView.exe"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,SansView}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\SansView 0.1"; Filename: "{app}\SansView.exe"; Tasks: desktopicon; WorkingDir: "{app}"

[Run]
Filename: "{app}\SansView.exe"; Description: "{cm:LaunchProgram,SansView}"; Flags: nowait postinstall skipifsilent

