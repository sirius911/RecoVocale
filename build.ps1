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

# Transformer 2.03 -> tuple (2,3,0,0)
$parts = $version.Split('.')
while ($parts.Count -lt 4) { $parts += '0' }
[int[]]$vt = $parts | ForEach-Object {[int]$_}

# Mise à jour des versions dans version_file.txt
$VerInfoPath = ".\version_info.txt"
@"
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($($vt[0]), $($vt[1]), $($vt[2]), $($vt[3])),
    prodvers=($($vt[0]), $($vt[1]), $($vt[2]), $($vt[3])),
    mask=0x3f,
    flags=0x0,
    OS=0x4,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'CH-Perigueux'),
            StringStruct(u'FileDescription', u'RecoVocale $version'),
            StringStruct(u'FileVersion', u'$version'),
            StringStruct(u'InternalName', u'RecoVocale'),
            StringStruct(u'LegalCopyright', u'CH-Perigueux © 2025'),
            StringStruct(u'OriginalFilename', u'RecoVocale.exe'),
            StringStruct(u'ProductName', u'RecoVocale'),
            StringStruct(u'ProductVersion', u'$version')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"@ | Set-Content -Encoding UTF8 $VerInfoPath

# Mise à jour des versions dans RecoVocale.iss
$issFile = ".\RecoVocale.iss"
(Get-Content $issFile) `
    -replace 'OutputBaseFilename\s*=\s*.*', "OutputBaseFilename=install_$version" `
    -replace 'AppVersion\s*=\s*.*', "AppVersion=$version" |
    Set-Content $issFile
Write-Host "Mise à jour de la version dans RecoVocale.iss"

# Copie de la DLL Rust dans srcs/bin/ pour l'inclusion par PyInstaller
# $dllSource = "C:\Users\lorcyr\recovocale_engine\target\release\recovocale_engine.dll"
# $dllTarget = ".\srcs\bin\recovocale_engine.dll"

if (-not (Test-Path ".\srcs\bin")) {
    New-Item -ItemType Directory -Path ".\srcs\bin" | Out-Null
}
# if (Test-Path $dllSource) {
#     Copy-Item -Path $dllSource -Destination $dllTarget -Force
#     Write-Host "✅ DLL Rust copiée dans srcs/bin/"
# } else {
#     Write-Host "❌ DLL Rust non trouvée à $dllSource"
# }

# 🧹 Supprimer les anciens dossiers de build et dist pour forcer une recompilation propre
if (Test-Path ".\build") {
    Remove-Item -Recurse -Force ".\build"
}
if (Test-Path ".\dist") {
    Remove-Item -Recurse -Force ".\dist"
}
Write-Host "🧹 Dossiers build/ et dist/ supprimés"

# 📦 Compilation avec PyInstaller
$specFile = ".\RecoVocale.spec"
Write-Host "📦 Compilation avec PyInstaller..."
pyinstaller $specFile

# 🔁 Recrée manuellement le dossier bin dans dist si nécessaire
$distBin = ".\dist\bin"

if (-not (Test-Path $distBin)) {
    New-Item -ItemType Directory -Path $distBin | Out-Null
}

# 🔁 Copie ffmpeg.exe et la DLL Rust manuellement
Copy-Item -Path ".\srcs\bin\ffmpeg.exe" -Destination "$distBin\" -Force
Write-Host "✅ Copie manuelle de ffmpeg.exe dans dist/bin/"

# --- Stage espeak-ng ultra-min (FR only, 64-bit) ---
$Src   = "C:\Program Files\eSpeak NG"   # <- 64-bit
$Stage = "dist\espeak-ng-ultra"

if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
New-Item -ItemType Directory -Force -Path "$Stage\espeak-ng-data\lang\roa" | Out-Null

# Binaires essentiels
Copy-Item "$Src\espeak-ng.exe"    -Destination "$Stage\" -Force
Copy-Item "$Src\libespeak-ng.dll" -Destination "$Stage\" -Force

# *** DLL dépendantes fréquentes (copier si présentes) ***
@("libgcc_s_seh-1.dll","libstdc++-6.dll","libwinpthread-1.dll") | ForEach-Object {
  if (Test-Path (Join-Path $Src $_)) {
    Copy-Item (Join-Path $Src $_) -Destination "$Stage\" -Force
  }
}

# Données essentielles FR uniquement
$DataSrc = Join-Path $Src "espeak-ng-data"
Copy-Item (Join-Path $DataSrc "phondata")           -Destination "$Stage\espeak-ng-data\" -Force
Copy-Item (Join-Path $DataSrc "phondata-manifest")  -Destination "$Stage\espeak-ng-data\" -Force
Copy-Item (Join-Path $DataSrc "phontab")            -Destination "$Stage\espeak-ng-data\" -Force
Copy-Item (Join-Path $DataSrc "phonindex")          -Destination "$Stage\espeak-ng-data\" -Force
Copy-Item (Join-Path $DataSrc "fr_dict")            -Destination "$Stage\espeak-ng-data\" -Force
Copy-Item (Join-Path $DataSrc "lang\roa\fr")        -Destination "$Stage\espeak-ng-data\lang\roa\" -Force
Copy-Item (Join-Path $DataSrc "intonations")        -Destination "$Stage\espeak-ng-data\" -Force
Get-ChildItem "$Stage" | Where-Object { $_.Name -match '^(libgcc_s_seh-1|libstdc\+\+-6|libwinpthread-1)\.dll$' } | Format-Table Name,Length

Write-Host "Espeak-ng ultra-min 64-bit prêt: $Stage"

Write-Host "✅ Build terminé pour la version $version"
