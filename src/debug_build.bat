@echo off
set "JAVA_HOME=C:\Users\frank\java\17.0.13+11"
set "FLUTTER_ROOT=C:\Users\frank\flutter\3.29.2"
set "FLET_EXE=C:\Users\frank\.flet\bin\flet-0.28.3\flet\flet.exe"
set "PATH=%JAVA_HOME%\bin;%FLUTTER_ROOT%\bin;%PATH%"

cd ..
echo Starting build debug > build_debug.log
echo Environment: >> build_debug.log
echo JAVA_HOME=%JAVA_HOME% >> build_debug.log
echo FLET_EXE=%FLET_EXE% >> build_debug.log

echo Checking flet version... >> build_debug.log
"%FLET_EXE%" --version >> build_debug.log 2>&1

echo Running build... >> build_debug.log
"%FLET_EXE%" build apk --verbose >> build_debug.log 2>&1

echo Done. >> build_debug.log
