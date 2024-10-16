@echo off

:: Lancer le splash screen et récupérer son ID de processus
start "" "splashScreen.exe"
for /f "tokens=2" %%i in ('tasklist ^| findstr "splashScreen.exe"') do set SPLASH_PID=%%i

:: Lancer RecoVocale.exe en lui passant l'ID du splash screen
start "" "RecoVocale.exe" %SPLASH_PID%

exit
