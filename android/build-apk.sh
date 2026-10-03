#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}"
TOOLS="$SDK/build-tools/36.1.0"
PLATFORM="$SDK/platforms/android-35/android.jar"
export JAVA_HOME="${JAVA_HOME:-/Applications/Android Studio.app/Contents/jbr/Contents/Home}"
export PATH="$JAVA_HOME/bin:$PATH"
JAVA_BIN="$JAVA_HOME/bin"
OUT="$ROOT/android/build"
SIGNING="$ROOT/.local-signing"
mkdir -p "$OUT/res/drawable-nodpi" "$OUT/classes" "$SIGNING" "$ROOT/downloads"
chmod 700 "$SIGNING"
cp "$ROOT/frontend/public/assets/app-icon-192.png" "$OUT/res/drawable-nodpi/icon.png"

if [ ! -f "$SIGNING/password" ]; then
  umask 077
  openssl rand -hex 24 > "$SIGNING/password"
fi
export SHIVA_SIGNING_PASSWORD="$(cat "$SIGNING/password")"
if [ ! -f "$SIGNING/shiva-release.jks" ]; then
  "$JAVA_BIN/keytool" -genkeypair -noprompt -keystore "$SIGNING/shiva-release.jks" -storepass:env SHIVA_SIGNING_PASSWORD -keypass:env SHIVA_SIGNING_PASSWORD -alias shiva -keyalg RSA -keysize 3072 -validity 10000 -dname "CN=Shiva Enterprises, O=Shiva Enterprises, C=IN"
fi

"$TOOLS/aapt2" compile --dir "$OUT/res" -o "$OUT/resources.zip"
"$TOOLS/aapt2" link -o "$OUT/unsigned.apk" -I "$PLATFORM" --manifest "$ROOT/android/AndroidManifest.xml" -R "$OUT/resources.zip"
"$JAVA_BIN/javac" -source 8 -target 8 -bootclasspath "$PLATFORM" -d "$OUT/classes" "$ROOT/android/src/com/shivaenterprises/services/MainActivity.java"
"$TOOLS/d8" --lib "$PLATFORM" --min-api 24 --output "$OUT" "$OUT"/classes/com/shivaenterprises/services/*.class
(cd "$OUT" && zip -q -u unsigned.apk classes.dex)
"$TOOLS/zipalign" -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
"$TOOLS/apksigner" sign --v4-signing-enabled false --ks "$SIGNING/shiva-release.jks" --ks-key-alias shiva --ks-pass env:SHIVA_SIGNING_PASSWORD --key-pass env:SHIVA_SIGNING_PASSWORD --out "$ROOT/downloads/shiva-enterprises-android.apk" "$OUT/aligned.apk"
"$TOOLS/apksigner" verify --verbose "$ROOT/downloads/shiva-enterprises-android.apk"
echo "APK: $ROOT/downloads/shiva-enterprises-android.apk"
