#!/usr/bin/env bash
# Shinon_Agent — Gradle-Aufruf mit Toolchain aus .local/ und Speicherdeckel.
#
# Warum der Deckel: gradle.properties setzt org.gradle.jvmargs=-Xmx2048m.
# In Umgebungen mit wenig RAM (verifiziert: 3,8 GB, ~2,4 GB Page-Cache in
# derselben Memory-Cgroup) beendet der OOM-Killer den Build sonst mitten im
# Lauf: Kernellog "Memory cgroup out of memory", Shell-Exit 137.
# Mit den hier gesetzten Werten läuft :app:assembleDebug durch.
#
# Voraussetzung: scripts/setup-toolchain.sh wurde einmal ausgeführt.
#
# Verwendung:
#   scripts/build.sh :app:assembleDebug
#   scripts/build.sh :app:dependencies --configuration debugRuntimeClasspath
#   scripts/build.sh :app:lintDebug          # braucht mehr RAM als hier verfügbar
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT"

if [ -f "$ROOT/.local/env.sh" ]; then
  # shellcheck source=../.local/env.sh
  . "$ROOT/.local/env.sh"
fi
: "${JAVA_HOME:=$ROOT/.local/toolchains/jdk17}"
: "${ANDROID_HOME:=$ROOT/.local/android-sdk}"
export JAVA_HOME ANDROID_HOME
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$PATH"

exec ./gradlew "$@" \
  --max-workers=1 \
  "-Dorg.gradle.jvmargs=-Xmx768m -XX:MaxMetaspaceSize=256m" \
  "-Dkotlin.compiler.execution.strategy=in-process" \
  "-Dorg.gradle.vfs.watch=false"
