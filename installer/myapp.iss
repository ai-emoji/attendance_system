#define MyAppInternalName "attendance"
#define MyAppDisplayName "Phần mềm chấm công Tam Niên"
#define MyAppVersion "1.0.2"
#define MyAppPublisher "Attendance System"
#define MyAppExeName "attendance.exe"

[Setup]
AppId={#MyAppInternalName}
AppName={#MyAppDisplayName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\attendance
; NOTE: This must be a real .ico. The repo's app.ico is actually a PNG.
SetupIconFile=..\assets\icons\app_converted.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin
DisableDirPage=no
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename={#MyAppInternalName}-setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\{#MyAppInternalName}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Dirs]
Name: "{app}\assets"; Attribs: hidden system
Name: "{app}\database"; Attribs: hidden system

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài Desktop"; GroupDescription: "Tuỳ chọn bổ sung:"; Flags: checkedonce

[Icons]
Name: "{commonprograms}\{#MyAppDisplayName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppDisplayName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Chạy {#MyAppDisplayName}"; Flags: nowait postinstall skipifsilent

[Code]
const
	MY_INVALID_FILE_ATTRIBUTES = $FFFFFFFF;
	MY_FILE_ATTRIBUTE_HIDDEN = $2;
	MY_FILE_ATTRIBUTE_SYSTEM = $4;

function GetFileAttributesW(lpFileName: string): Cardinal;
	external 'GetFileAttributesW@kernel32.dll stdcall';
function SetFileAttributesW(lpFileName: string; dwFileAttributes: Cardinal): Boolean;
	external 'SetFileAttributesW@kernel32.dll stdcall';

procedure SetHiddenSystem(const Path: string);
var
	Attr: Cardinal;
begin
	if not FileExists(Path) and not DirExists(Path) then
		exit;
	Attr := GetFileAttributesW(Path);
	if Attr = MY_INVALID_FILE_ATTRIBUTES then
		exit;
	SetFileAttributesW(Path, Attr or MY_FILE_ATTRIBUTE_HIDDEN or MY_FILE_ATTRIBUTE_SYSTEM);
end;

procedure HideTree(const Root: string);
var
	FindRec: TFindRec;
	Item: string;
begin
	if not DirExists(Root) then
		exit;

	SetHiddenSystem(Root);

	if FindFirst(Root + '\\*', FindRec) then
	begin
		try
			repeat
				if (FindRec.Name = '.') or (FindRec.Name = '..') then
					continue;
				Item := Root + '\\' + FindRec.Name;
				SetHiddenSystem(Item);
				if DirExists(Item) then
					HideTree(Item);
			until not FindNext(FindRec);
		finally
			FindClose(FindRec);
		end;
	end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
	if CurStep = ssPostInstall then
	begin
		HideTree(ExpandConstant('{app}\\assets'));
		HideTree(ExpandConstant('{app}\\database'));
		SetHiddenSystem(ExpandConstant('{app}\\creater_database.SQL'));
	end;
end;
