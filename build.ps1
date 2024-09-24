# Assurez-vous que PyInstaller est installé
$pyInstallerPath = (Get-Command pyinstaller).Source

if (-not $pyInstallerPath) {
    Write-Error "PyInstaller n'est pas installé. Veuillez l'installer avec 'pip install pyinstaller'."
    exit 1
}

# Définir les chemins et les options
$iconPath = "reco.ico"
$sourcePath = "srcs/RecoVocale.py"
$iconsData = "srcs/Icons;Icons"
$configData = "srcs/config;config"
$outputName = "RecoVocale"
$versionFilePath = "version_file.txt"  # Ajoutez le chemin vers votre fichier de version

# Construire la commande PyInstaller avec plusieurs --add-data et le fichier de version
$pyinstallerCommand = "pyinstaller --onefile --clean --icon=`"$iconPath`" --add-data `"$iconsData`" --add-data `"$configData`" `"$sourcePath`" --name `"$outputName`" --noconsole --version-file `"$versionFilePath`""

# Exécuter la commande
Write-Host "Running PyInstaller..."
Invoke-Expression $pyinstallerCommand

Write-Host "Build completed."
