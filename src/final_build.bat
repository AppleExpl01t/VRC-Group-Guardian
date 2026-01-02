@echo off
set "JAVA_HOME=C:\Users\frank\java\17.0.13+11"
set "FLUTTER_ROOT=C:\Users\frank\flutter\3.29.2"
set "FLET_EXE=F:\Python\Scripts\flet.exe"
set "PATH=%JAVA_HOME%\bin;%FLUTTER_ROOT%\bin;%PATH%"

cd ..
echo Cleaning...
if exist "build\apk\app-release.apk" del "build\apk\app-release.apk"

echo Building...
call "%FLET_EXE%" build apk --verbose

if exist "build\apk\app-release.apk" (
    echo Installing...
    call "C:\Users\frank\Downloads\app\Harmony\sdk\platform-tools\adb.exe" install -r "build\apk\app-release.apk"
    echo Launching...
    call "C:\Users\frank\Downloads\app\Harmony\sdk\platform-tools\adb.exe" shell monkey -p com.flet.group_guardian -c android.intent.category.LAUNCHER 1
) else (
    echo Build Failed!
)
