; Script de création d'installateur Reco Vocal

[Setup]
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Nom du fichier installateur
OutputDir=install
OutputBaseFilename=install_2.10
SetupIconFile=reco.ico

; Nom de l'application
AppName=RecoVocale
; Version de l'application
AppVersion=2.10
; Répertoire par défaut d'installation
AppVerName={#SetupSetting("AppName")} {#SetupSetting("AppVersion")}
DefaultDirName={pf64}\RecoVocale
; Répertoire par défaut dans le menu démarrer
DefaultGroupName=RecoVocale

; Fichier de licence (optionnel)
LicenseFile="C:\\Users\\lorcyr\\RecoVocale\\LICENSE.txt"

[Files]
; Inclure le fichier exécutable et d'autres fichiers nécessaires
; pour le Flags:ignoreversion / onlyifdoesntexist / promptifolder

; binaire app
Source: "dist\RecoVocale.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\bin\ffmpeg.exe"; DestDir: "{app}\bin"; Flags: onlyifdoesntexist

; modèles “read-only” communs à la machine
Source: "srcs\config\insertions.xml";           DestDir: "{app}\defaults"; Flags: ignoreversion
Source: "srcs\config\pas_a_pas.json";           DestDir: "{app}\defaults"; Flags: ignoreversion
Source: "srcs\config\my.dic";                   DestDir: "{app}\defaults"; Flags: ignoreversion
Source: "srcs\config\user_config.ini";          DestDir: "{app}\defaults"; Flags: ignoreversion
Source: "srcs\config\micro_actions_config.json";DestDir: "{app}\defaults"; Flags: ignoreversion

; --- espeak-ng embarqué (ultra-min) ---
Source: "dist\espeak-ng-ultra\espeak-ng.exe"; DestDir: "{app}\espeak-ng"; Flags: ignoreversion
Source: "dist\espeak-ng-ultra\libespeak-ng.dll"; DestDir: "{app}\espeak-ng"; Flags: ignoreversion
Source: "dist\espeak-ng-ultra\espeak-ng-data\*"; DestDir: "{app}\espeak-ng\espeak-ng-data"; Flags: recursesubdirs createallsubdirs ignoreversion

Source: "dist\espeak-ng-ultra\*.dll"; Excludes: "libespeak-ng.dll"; DestDir: "{app}\espeak-ng"; Flags: ignoreversion skipifsourcedoesntexist

[Code]
const
  WM_SETTINGCHANGE   = $001A;
  SMTO_ABORTIFHUNG   = $0002;

function SendMessageTimeout(hWnd: LongWord; Msg: LongWord; wParam: LongWord;
  lParam: String; fuFlags: LongWord; uTimeout: LongWord; var lpdwResult: LongWord): LongWord;
  external 'SendMessageTimeoutW@user32.dll stdcall setuponly';

procedure BroadcastEnvironmentChange;
var
  Res: LongWord;
begin
  { Préviens les applis de la session que les variables d'env ont changé }
  SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0, 'Environment',
    SMTO_ABORTIFHUNG, 5000, Res);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    BroadcastEnvironmentChange;
end;

function InitializeSetup(): Boolean;
var
  Code: Integer;
begin
  if FileExists('C:\Program Files (x86)\RecoVocale\unins000.exe') then
  begin
    Exec('C:\Program Files (x86)\RecoVocale\unins000.exe',
         '/VERYSILENT /NORESTART', '', SW_HIDE, ewWaitUntilTerminated, Code);
  end;
  Result := True;
end;

[Icons]
; Menu Démarrer
Name: "{group}\RecoVocale"; Filename: "{app}\RecoVocale.exe"
; (Optionnel) Bureau
Name: "{commondesktop}\RecoVocale"; Filename: "{app}\RecoVocale.exe"

[Run]
; Supprimer l'ancien raccourci épinglé (32 bits) s'il existe (nom exact ou variantes)
Filename: "{cmd}"; Parameters: "/C if exist ""%AppData%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\RecoVocale*.lnk"" del /Q ""%AppData%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\RecoVocale*.lnk"""; Flags: runhidden

; Exécuter l'application après l'installation (optionnel)
Filename: "{app}\RecoVocale.exe"; Description: "{cm:LaunchProgram,MonProgramme}"; Flags: nowait postinstall skipifsilent

[InstallDelete]
; Supprime les anciens raccourcis versionnés dans le menu Démarrer
Type: files; Name: "{group}\RecoVocale *.lnk"

; (Optionnel) supprime aussi les anciens raccourcis versionnés du Bureau
Type: files; Name: "{commondesktop}\RecoVocale *.lnk"
Type: files; Name: "{userdesktop}\RecoVocale *.lnk"
