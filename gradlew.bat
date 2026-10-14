@echo off
setlocal
set GRADLE_VERSION=8.7
set GRADLE_ZIP_SHA=https://services.gradle.org/distributions/gradle-8.7-bin.zip
set GRADLE_USER_HOME=%USERPROFILE%\.gradle
set GRADLE_WRAPPER_DIR=%GRADLE_USER_HOME%\wrapper\dists
set DIST_DIR=%GRADLE_WRAPPER_DIR%\gradle-8.7-bin
if not exist "%DIST_DIR%" (
  if not exist "%GRADLE_WRAPPER_DIR%" mkdir "%GRADLE_WRAPPER_DIR%"
  powershell -Command "Invoke-WebRequest '%GRADLE_ZIP_SHA%' -OutFile '%GRADLE_WRAPPER_DIR%\gradle-8.7-bin.zip'"
  cd /d "%GRADLE_WRAPPER_DIR%"
  tar -xf gradle-8.7-bin.zip
)
"%DIST_DIR%\gradle-8.7\bin\gradle.bat" %*
endlocal
