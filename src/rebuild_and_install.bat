@echo off
set "JAVA_HOME=C:\Users\frank\java\17.0.13+11"
set "FLUTTER_ROOT=C:\Users\frank\flutter\3.29.2"
set "FLET_EXE=F:\Python\Scripts\flet.exe"
set "PATH=%JAVA_HOME%\bin;%FLUTTER_ROOT%\bin;%PATH%"

echo Environment Configured:
echo JAVA_HOME=%JAVA_HOME%
echo FLUTTER_ROOT=%FLUTTER_ROOT%
echo FLET_EXE=%FLET_EXE%

cd ..
echo Clean up build artifacts...
if exist "build\apk\app-release.apk" del /q "build\apk\app-release.apk"

echo Running Flet Build...
call "%FLET_EXE%" build apk --verbose

echo Build Complete.
if exist "build\apk\app-release.apk" (
    echo APK found! Installing...
    call "C:\Users\frank\Downloads\app\Harmony\sdk\platform-tools\adb.exe" install -r "build\apk\app-release.apk"
    echo Launching...
    call "C:\Users\frank\Downloads\app\Harmony\sdk\platform-tools\adb.exe" shell monkey -p com.flet.group_guardian -c android.intent.category.LAUNCHER 1
) else (
    echo APK not found. Build failed.
)
