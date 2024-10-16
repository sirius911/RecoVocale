# Lire la version du fichier version.txt
$versionFilePath = "version.txt"
$version = Get-Content $versionFilePath

# Mettre à jour la version dans info.py
$infoContent = Get-Content "srcs/info.py"
$infoContent = $infoContent -replace "VERSION = '.*'", "VERSION = '$version'"
$infoContent | Set-Content "srcs/info.py"

# Diviser la version en ses composants
$versionParts = $version.Split('.')

# Vérifiez que vous avez bien deux parties (majeure, mineure) dans $versionParts
if ($versionParts.Count -ne 2) {
    Write-Error "La version doit être au format majeur.mineur, par exemple : 0.71"
    exit 1
}

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

# Construire le fichier version_file.txt dynamique à partir de version.txt
$versionFileContent = @"
VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=($($versionParts[0]), $($versionParts[1]), 0, 0),
        prodvers=($($versionParts[0]), $($versionParts[1]), 0, 0),
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo([
            StringTable(
                u'040904B0',
                [StringStruct(u'CompanyName', u'CH-Perigueux'),
                 StringStruct(u'FileDescription', u'Reco Vocale'),
                 StringStruct(u'FileVersion', u'$($versionParts[0]).$($versionParts[1]).0.0'),
                 StringStruct(u'InternalName', u'recovocale'),
                 StringStruct(u'LegalCopyright', u'Copyright (c) CH-Perigueux. All rights reserved.'),
                 StringStruct(u'OriginalFilename', u'recovocale.exe'),
                 StringStruct(u'ProductName', u'Recovocale'),
                 StringStruct(u'ProductVersion', u'$($versionParts[0]).$($versionParts[1]).0.0')])
        ]),
        VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
    ]
)
"@

# Enregistrer le contenu dans le fichier version_file.txt
Set-Content -Path "version_file.txt" -Value $versionFileContent

# Construire la commande PyInstaller avec plusieurs --add-data et le fichier de version
$pyinstallerCommand = "pyinstaller --onefile --clean --icon=`"$iconPath`" --add-data `"$iconsData`" --add-data `"$configData`" `"$sourcePath`" --name `"$outputName`" --noconsole --version-file version_file.txt"

# Exécuter la commande
Write-Host "Running PyInstaller..."
Invoke-Expression $pyinstallerCommand

# Remplacer la version dans le fichier .iss (Inno Setup)
$issContent = Get-Content "RecoVocale.iss"
$issContent = $issContent -replace 'AppVersion=\d+(\.\d+)*', "AppVersion=$version"
$issContent = $issContent -replace 'OutputBaseFilename=.*', "OutputBaseFilename=install_$version"
$issContent | Set-Content "RecoVocale.iss"

# Remplacer la version dans le fichier .spec pour s'adapter à toute version
$specContent = Get-Content "RecoVocale.spec"
$specContent = $specContent -replace 'filevers=\([\d, ]+\)', "filevers=($($versionParts[0]), $($versionParts[1]), 0, 0)"
$specContent = $specContent -replace 'prodvers=\([\d, ]+\)', "prodvers=($($versionParts[0]), $($versionParts[1]), 0, 0)"
$specContent | Set-Content "RecoVocale.spec"

# # Mettre à jour la version dans info.py
# $infoContent = Get-Content "srcs/info.py"
# $infoContent = $infoContent -replace "VERSION = '.*'", "VERSION = '$version'"
# $infoContent | Set-Content "srcs/info.py"

Write-Host "Build completed."
