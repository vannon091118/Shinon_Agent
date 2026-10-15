#!/bin/sh
# Gradle Wrapper-Startskript (Linux/macOS).
# Der Wrapper lädt Gradle 8.7 (gradle/wrapper/gradle-wrapper.properties),
# wenn nicht schon lokal vorhanden.

set -e

# Resolve symbolic links
PROG_NAME=$0
while [ -h "$PROG_NAME" ]; do
  ls=$(ls -ld "$PROG_NAME")
  PROG_NAME=$(expr "$ls" : '.*-> \(.*\)$')
done
SAVE_DIR=$(pwd)
DIRNAME=$(dirname "$PROG_NAME")
cd "$DIRNAME"
APP_HOME=$(find -L . -maxdepth 2 -name gradlew -print -quit | sed 's:/gradlew::')
cd "$SAVE_DIR"
[ -n "${APP_HOME:-}" ] || APP_HOME=$(pwd)

# Determine Gradle distribution
GRADLE_USER_HOME=${GRADLE_USER_HOME:-$HOME/.gradle}
GRADLE_WRAPPER_DIR=$GRADLE_USER_HOME/wrapper/dists
GRADLE_VERSION=8.7
GRADLE_ZIP_SHA="https://services.gradle.org/distributions/gradle-8.7-bin.zip"

# Download & extract if missing
# Wichtig: Der Zielpfad ist erst gültig, wenn das Archiv erfolgreich nach
# $DIST_DIR entpackt wurde. Geprüft wird deshalb auf den Launcher, nicht auf
# die blosse Existenz des Ordners — ein abgebrochener Download darf keinen
# leeren Ordner hinterlassen, der jeden weiteren Lauf blockiert.
DIST_DIR=$GRADLE_WRAPPER_DIR/gradle-8.7-bin
GRADLE_HOME="$DIST_DIR/gradle-8.7"
if [ ! -x "$GRADLE_HOME/bin/gradle" ]; then
  rm -rf "$DIST_DIR"
  mkdir -p "$DIST_DIR"
  curl -fsSL --retry 3 "$GRADLE_ZIP_SHA" -o "$GRADLE_WRAPPER_DIR/gradle-8.7-bin.zip"
  unzip -q "$GRADLE_WRAPPER_DIR/gradle-8.7-bin.zip" -d "$DIST_DIR"
  rm -f "$GRADLE_WRAPPER_DIR/gradle-8.7-bin.zip"
fi

# Run
exec "$GRADLE_HOME/bin/gradle" "$@"
