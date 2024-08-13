# build.ps1

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

# Construire la commande PyInstaller avec plusieurs --add-data
$pyinstallerCommand = "pyinstaller --onefile --clean --icon=`"$iconPath`" --add-data `"$iconsData`" --add-data `"$configData`" `"$sourcePath`" --name `"$outputName`""

# Exécuter la commande
Write-Host "Running PyInstaller..."
Invoke-Expression $pyinstallerCommand

Write-Host "Build completed."
