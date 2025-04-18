# Lecture de la version depuis le fichier
$versionFile = ".\version.txt"
$version = Get-Content $versionFile | Select-Object -First 1
$version = $version.Trim()
Write-Host "Version lue depuis version.txt : $version"

# Mettre à jour la version dans info.py
$infoContent = Get-Content "srcs/info.py"
$infoContent = $infoContent -replace "VERSION = '.*'", "VERSION = '$version'"
$infoContent | Set-Content "srcs/info.py"
Write-Host "Version d'info.py à jour"

# Mise à jour des versions dans RecoVocale.iss
$issFile = ".\RecoVocale.iss"
(Get-Content $issFile) `
    -replace 'OutputBaseFilename\s*=\s*.*', "OutputBaseFilename=install_$version" `
    -replace 'AppVersion\s*=\s*.*', "AppVersion=$version" |
    Set-Content $issFile
Write-Host "Mise à jour de la version dans RecoVocale.iss"


# Compilation avec PyInstaller en utilisant le fichier .spec
$specFile = ".\RecoVocale.spec"
Write-Host "Compilation avec PyInstaller..."
pyinstaller $specFile

# Copie de ffmpeg.exe dans le bon dossier de distribution
$ffmpegSource = ".\srcs\bin\ffmpeg.exe"
$ffmpegTargetDir = ".\dist\bin"
$ffmpegTarget = Join-Path $ffmpegTargetDir "ffmpeg.exe"

if (-not (Test-Path $ffmpegTargetDir)) {
    New-Item -ItemType Directory -Path $ffmpegTargetDir | Out-Null
}

if (Test-Path $ffmpegSource) {
    Copy-Item -Path $ffmpegSource -Destination $ffmpegTarget -Force
    Write-Host "ffmpeg.exe copié dans $ffmpegTarget"
} else {
    Write-Host "ffmpeg.exe non trouvé dans $ffmpegSource"
}

Write-Host "Build terminé pour la version $version"