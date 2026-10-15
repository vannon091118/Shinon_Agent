#!/usr/bin/env bash
# Shinon_Agent — Bootstrap der Build-Toolchain ohne Root/sudo.
#
# Lädt JDK 17 und das Android SDK benutzerlokal nach .local/ (gitignored),
# installiert die für compileSdk 34 nötigen SDK-Pakete und schreibt
# local.properties. Danach genügt: scripts/build.sh :app:assembleDebug
#
# Idempotent: bereits vorhandene Komponenten werden nicht erneut geladen.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/.local/toolchains"
SDK="$ROOT/.local/android-sdk"
mkdir -p "$TOOLS" "$SDK"

# --- JDK 17 (Temurin) ---
if [ ! -x "$TOOLS/jdk17/bin/java" ]; then
  echo ">> JDK 17 laden"
  curl -fsSL -o "$TOOLS/jdk17.tar.gz" \
    "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse"
  tar -xzf "$TOOLS/jdk17.tar.gz" -C "$TOOLS"
  rm -f "$TOOLS/jdk17.tar.gz"
  rm -rf "$TOOLS/jdk17"
  mv "$TOOLS"/jdk-17* "$TOOLS/jdk17"
else
  echo ">> JDK 17 vorhanden"
fi

# --- Android Command-line-Tools ---
export JAVA_HOME="$TOOLS/jdk17"
if [ ! -x "$SDK/cmdline-tools/latest/bin/sdkmanager" ]; then
  echo ">> Android commandline-tools laden"
  curl -fsSL -o "$TOOLS/cmdline-tools.zip" \
    "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
  mkdir -p "$SDK/cmdline-tools"
  unzip -q "$TOOLS/cmdline-tools.zip" -d "$SDK/cmdline-tools"
  rm -f "$TOOLS/cmdline-tools.zip"
  mv "$SDK/cmdline-tools/cmdline-tools" "$SDK/cmdline-tools/latest"
else
  echo ">> Android commandline-tools vorhanden"
fi

# --- SDK-Pakete für compileSdk 34 ---
export ANDROID_HOME="$SDK"
export ANDROID_SDK_ROOT="$SDK"
export PATH="$JAVA_HOME/bin:$SDK/cmdline-tools/latest/bin:$PATH"
if [ ! -d "$SDK/platforms/android-34" ] || [ ! -d "$SDK/build-tools/34.0.0" ]; then
  echo ">> SDK-Pakete installieren (platform-34, build-tools 34.0.0, platform-tools)"
  yes | sdkmanager --licenses >/dev/null
  sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0" >/dev/null
else
  echo ">> SDK-Pakete vorhanden"
fi

# --- local.properties (maschinenspezifisch, gitignored) ---
printf 'sdk.dir=%s\n' "$SDK" > "$ROOT/local.properties"
echo ">> local.properties geschrieben: sdk.dir=$SDK"

# --- .local/env.sh als Bequemlichkeit (von scripts/build.sh genutzt) ---
cat > "$ROOT/.local/env.sh" <<'ENVSH'
# Erzeugt von scripts/setup-toolchain.sh — Toolchain in die Shell laden.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export JAVA_HOME="$ROOT/.local/toolchains/jdk17"
export ANDROID_HOME="$ROOT/.local/android-sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"
ENVSH
echo ">> .local/env.sh geschrieben"
echo ">> Fertig. Nächster Schritt: scripts/build.sh :app:assembleDebug"
