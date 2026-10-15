# --- Shinon release signing rules ---
# Keystore wird NIE im Repo liegen (Base64 via GitHub Secrets).
-keep class com.vannon.shinon.** { *; }
# Die Regel -keep class androidx.webkit.** ist entfallen: die Abhängigkeit
# androidx.webkit:webkit wird nicht mehr eingebunden (nirgends importiert).
# -dontwarn org.webkit.** bleibt vorsichtshalber stehen — seine Entfernung
# ließe sich nur mit einem verifizierten R8-Lauf belegen (siehe
# docs/KNOWN-LIMITATIONS.md N-4).
-dontwarn org.webkit.**
# Release-Build: kein debuggable, kein minify-Overhead jenseits ProGuard-Standard.
-keepattributes Signature
-keep class * extends android.app.Activity
