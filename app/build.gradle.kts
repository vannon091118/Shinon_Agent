plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.vannon.shinon"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.vannon.shinon"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.0.1"
    }

    signingConfigs {
        release {
            // Release-Keystore wird NIE im Repo liegen. Stattdessen:
            //   1. .jks-Datei lokal (nie nach git) — Konvertierung via Base64:
            //      base64 -w0 my-release-key.jks > my-release-key.b64
            //   2. Base64-String + Passwörter + Alias in GitHub Repository
            //      Secrets (Settings → Secrets and variables → Actions):
            //      - SHINON_KEYSTORE_B64   (Base64-String der .jks)
            //      - SHINON_KEYSTORE_ALIAS (Alias-Name)
            //      - SHINON_KEYSTORE_PASS  (Keystore-Passwort)
            //      - SHINON_KEY_ALIAS_PASS (Alias-Passwort)
            //   3. Der CI-Workflow dekodiert das Keystore-Base64 temporär
            //      in der Runner-Umgebung (niemals im Repo, niemals im Log).
            storeFile = file(System.getenv("SHINON_KEYSTORE_PATH") ?: "keystore/release.jks")
            storePassword = System.getenv("SHINON_KEYSTORE_PASS") ?: System.getenv("SHINON_KEYSTORE_PASS_DEFAULT") ?: ""
            keyAlias = System.getenv("SHINON_KEYSTORE_ALIAS") ?: ""
            keyPassword = System.getenv("SHINON_KEY_ALIAS_PASS") ?: storePassword
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isDebuggable = false
            signingConfig = signingConfigs.release
            proguardFiles(getDefaultProguardFile("proguard-rules-opt.txt"), "proguard-rules.pro")
        }
        debug {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    // Die WebView-Bridge + AndroidX für die App
    buildFeatures {
        viewBinding = false
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.webkit:webkit:1.11.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.3")
    implementation("com.google.android.material:material:1.12.0")
}
