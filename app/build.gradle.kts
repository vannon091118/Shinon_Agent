plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}


val shinonRuntimeRelease = providers.gradleProperty("shinonRuntimeRelease").orElse("dev-unavailable").get()
val shinonRuntimeSha256 = providers.gradleProperty("shinonRuntimeSha256").orElse("dev-unavailable").get()
check(shinonRuntimeRelease.matches(Regex("[a-z0-9-]+"))) { "shinonRuntimeRelease must be a lowercase release tag" }
check(shinonRuntimeSha256 == "dev-unavailable" || shinonRuntimeSha256.matches(Regex("[0-9a-f]{64}"))) {
    "shinonRuntimeSha256 must be a lowercase SHA-256 digest"
}

android {
    namespace = "com.vannon.shinon"
    compileSdk = 34
    ndkVersion = "26.3.11579264"

    defaultConfig {
        applicationId = "com.vannon.shinon"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.02"
        buildConfigField("String", "SHINON_RUNTIME_RELEASE", "\"$shinonRuntimeRelease\"")
        buildConfigField("String", "SHINON_RUNTIME_SHA256", "\"$shinonRuntimeSha256\"")
        ndk { abiFilters += "arm64-v8a" }
    }

    signingConfigs {
        create("release") {
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
            //
            // SigningConfig-Datensatz: storeFile, storePassword, keyAlias,
            // keyPassword (die vier Werte, die die APK signiert).
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
            signingConfig = signingConfigs.getByName("release")
            // Default ProGuard-Opt-Regel (AGP-valid): proguard-android-optimize.txt
            // + Projekt-Regel (app/proguard-rules.pro).
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
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
        buildConfig = true
    }

    androidResources {
        noCompress += listOf("xz")
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.3")
    implementation("com.google.android.material:material:1.12.0")
}
