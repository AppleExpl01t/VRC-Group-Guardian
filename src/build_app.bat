@echo off
set "JAVA_HOME=C:\Users\frank\java\17.0.13+11"
set "PATH=%JAVA_HOME%\bin;%PATH%"
echo JAVA_HOME is %JAVA_HOME%
java -version
cd ..
cd build\flutter\android
call gradlew.bat clean assembleRelease
