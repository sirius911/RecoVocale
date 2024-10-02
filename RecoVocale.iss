; Script de création d'installateur Reco Vocal

[Setup]
; Nom du fichier installateur
OutputDir=install
OutputBaseFilename=install_0.75
SetupIconFile=reco.ico
; Nom de l'application
AppName=RecoVocale
; Version de l'application
AppVersion=0.75
; Répertoire par défaut d'installation
DefaultDirName={pf}\RecoVocale
; Répertoire par défaut dans le menu démarrer
DefaultGroupName=RecoVocale
; Fichier de licence (optionnel)
; LicenseFile=license.txt

[Files]
; Inclure le fichier exécutable et d'autres fichiers nécessaires
Source: "dist\RecoVocale.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\corrections.json"; DestDir: "{localappdata}\RecoVocale"; Flags: ignoreversion
Source: "C:\Users\LORCYR\Appdata\Roaming\RecoVocale\user_config.ini"; DestDir: "{localappdata}\RecoVocale"; Flags: ignoreversion
Source: "srcs\config\micro_actions_config.json"; DestDir: "{localappdata}\RecoVocale"; Flags: ignoreversion


[Icons]
; Ajouter une icône pour l'application dans le menu démarrer
Name: "{group}\RecoVocale"; Filename: "{app}\RecoVocale.exe"

[Run]
; Exécuter l'application après l'installation (optionnel)
Filename: "{app}\RecoVocale.exe"; Description: "{cm:LaunchProgram,MonProgramme}"; Flags: nowait postinstall skipifsilent
