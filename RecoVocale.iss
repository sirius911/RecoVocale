; Script de création d'installateur Reco Vocal

[Setup]
; Nom du fichier installateur
OutputDir=install
OutputBaseFilename=install_2.01
SetupIconFile=reco.ico

; Nom de l'application
AppName=RecoVocale
; Version de l'application
AppVersion=2.01
; Répertoire par défaut d'installation
DefaultDirName={pf}\RecoVocale
; Répertoire par défaut dans le menu démarrer
DefaultGroupName=RecoVocale

; Fichier de licence (optionnel)
LicenseFile="C:\\Users\\lorcyr\\RecoVocale\\LICENSE.txt"

[Files]
; Inclure le fichier exécutable et d'autres fichiers nécessaires
; pour le Flags:ignoreversion / onlyifdoesntexist / promptifolder 
Source: "dist\RecoVocale.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\lorcyr\RecoVocale\srcs\config\user_config.ini"; DestDir: "{localappdata}\RecoVocale"; Flags: ignoreversion
Source: "C:\Users\lorcyr\RecoVocale\srcs\config\micro_actions_config.json"; DestDir: "{localappdata}\RecoVocale"; Flags: ignoreversion
Source: "C:\Users\lorcyr\Appdata\Local\enchant\fr_FR.dic"; DestDir: "{localappdata}\enchant"; Flags: onlyifdoesntexist
Source: "C:\Users\lorcyr\RecoVocale\srcs\config\insertions.xml"; DestDir: "{localappdata}\RecoVocale"; Flags: onlyifdoesntexist
Source: "dist\bin\ffmpeg.exe"; DestDir: "{app}\bin"; Flags: onlyifdoesntexist
; Source: "dist\bin\recovocale_engine.dll"; DestDir: "{app}\bin"; Flags: ignoreversion

[Icons]
; Ajouter une icône pour l'application dans le menu démarrer
Name: "{group}\RecoVocale"; Filename: "{app}\RecoVocale.exe"; Comment: "RecoVocale {#SetupSetting('AppVersion')}"

[Run]
; Exécuter l'application après l'installation (optionnel)
Filename: "{app}\RecoVocale.exe"; Description: "{cm:LaunchProgram,MonProgramme}"; Flags: nowait postinstall skipifsilent
