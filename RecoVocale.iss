; Script de création d'installateur Reco Vocal

[Setup]
; Nom du fichier installateur
OutputDir=install
OutputBaseFilename=install_0.92
SetupIconFile=reco.ico
; Nom de l'application
AppName=RecoVocale
; Version de l'application
AppVersion=0.92
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
Source: "C:\Users\LORCYR\Appdata\Roaming\RecoVocale\user_config.ini"; DestDir: "{localappdata}\RecoVocale"; Flags: ignoreversion
Source: "C:\Users\LORCYR\Appdata\Roaming\RecoVocale\micro_actions_config.json"; DestDir: "{localappdata}\RecoVocale"; Flags: ignoreversion
Source: "C:\Users\LORCYR\Appdata\Local\enchant\fr_FR.dic"; DestDir: "{localappdata}\enchant"; Flags: onlyifdoesntexist


[Icons]
; Ajouter une icône pour l'application dans le menu démarrer
Name: "{group}\RecoVocale"; Filename: "{app}\RecoVocale.exe"

[Run]
; Exécuter l'application après l'installation (optionnel)
Filename: "{app}\RecoVocale.exe"; Description: "{cm:LaunchProgram,MonProgramme}"; Flags: nowait postinstall skipifsilent
