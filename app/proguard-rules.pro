# --- Shinon release signing rules ---
# Keystore wird NIE im Repo liegen (Base64 via GitHub Secrets).
-keep class com.vannon.shinon.** { *; }
-keep class androidx.webkit.** { *; }
-dontwarn org.webkit.**
# Release-Build: kein debuggable, kein minify-Overhead jenseits ProGuard-Standard.
-keepattributes Signature
-keep class * extends android.app.Activity
