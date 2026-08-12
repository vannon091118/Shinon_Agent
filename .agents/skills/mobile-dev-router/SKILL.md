---
name: mobile-dev-router
description: "Router für 35 Mobile-Dev-Skills (Expo 13 + macOS 11 + iOS 9 + Android 2). Leitet Mobile-Intents an den richtigen Sub-Skill. Use bei Expo Router, EAS, React Native, SwiftUI, AppKit, Android Emulator, iOS Debugger, Signing, Notarization."
category: mobile-dev
stack: LOGISCH + GOVERNANCE
risk: medium
side_effects: code_changes
requires_approval: false
version: "1.0.0"
last_verified: "2026-08-11"
---

# 📱 Mobile Dev Router — 35 Skills

> **Router für `mobile-dev/`** — Wählt Sub-Skill basierend auf Plattform und Task-Typ.

---

## 🗺️ Routing-Tabelle

### Expo (13 Skills) — `mobile-dev/expo/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Expo deployment", "deploy Expo", "EAS submit" | `expo-deployment` | `expo/expo-deployment` |
| "Expo dev client", "dev build", "custom dev client" | `expo-dev-client` | `expo/expo-dev-client` |
| "Expo API routes", "Expo server", "API route Expo" | `expo-api-routes` | `expo/expo-api-routes` |
| "Expo module", "native module Expo" | `expo-module` | `expo/expo-module` |
| "Expo CICD", "CI/CD Expo", "EAS workflow" | `expo-cicd-workflows` | `expo/expo-cicd-workflows` |
| "Expo Tailwind", "Tailwind Expo", "NativeWind" | `expo-tailwind-setup` | `expo/expo-tailwind-setup` |
| "Expo SwiftUI", "native UI Swift Expo" | `expo-ui-swift-ui` | `expo/expo-ui-swift-ui` |
| "Expo Jetpack Compose", "Compose Expo" | `expo-ui-jetpack-compose` | `expo/expo-ui-jetpack-compose` |
| "build native UI Expo", "native components Expo" | `building-native-ui` | `expo/building-native-ui` |
| "upgrade Expo", "Expo SDK upgrade", "update Expo" | `upgrading-expo` | `expo/upgrading-expo` |
| "Expo DOM", "use DOM Expo" | `use-dom` | `expo/use-dom` |
| "native data fetching Expo" | `native-data-fetching` | `expo/native-data-fetching` |
| "Codex Expo run", "Expo run actions" | `codex-expo-run-actions` | `expo/codex-expo-run-actions` |

### macOS (11 Skills) — `mobile-dev/build-macos-apps/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "macOS build run debug", "Xcode build", "run macOS app" | `build-run-debug` | `build-macos-apps/build-run-debug` |
| "macOS signing", "entitlements macOS", "code sign" | `signing-entitlements` | `build-macos-apps/signing-entitlements` |
| "macOS packaging", "notarization", "distribute macOS" | `packaging-notarization` | `build-macos-apps/packaging-notarization` |
| "SwiftUI patterns macOS" | `swiftui-patterns` | `build-macos-apps/swiftui-patterns` |
| "AppKit interop", "AppKit macOS" | `appkit-interop` | `build-macos-apps/appkit-interop` |
| "SwiftPM macOS", "Swift Package Manager" | `swiftpm-macos` | `build-macos-apps/swiftpm-macos` |
| "macOS window management", "window manager" | `window-management` | `build-macos-apps/window-management` |
| "Liquid Glass macOS", "glass effect" | `liquid-glass` | `build-macos-apps/liquid-glass` |
| "macOS view refactor", "refactor view" | `view-refactor` | `build-macos-apps/view-refactor` |
| "macOS telemetry", "app telemetry" | `telemetry` | `build-macos-apps/telemetry` |
| "macOS test triage", "test failure Mac" | `test-triage` | `build-macos-apps/test-triage` |

### iOS (9 Skills) — `mobile-dev/build-ios-apps/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "iOS debugger", "debug iOS app" | `ios-debugger-agent` | `build-ios-apps/ios-debugger-agent` |
| "iOS app intents", "Siri intents", "App Intents" | `ios-app-intents` | `build-ios-apps/ios-app-intents` |
| "iOS simulator browser" | `ios-simulator-browser` | `build-ios-apps/ios-simulator-browser` |
| "iOS memgraph leaks", "memory leak iOS" | `ios-memgraph-leaks` | `build-ios-apps/ios-memgraph-leaks` |
| "iOS et trace performance", "performance trace" | `ios-ettrace-performance` | `build-ios-apps/ios-ettrace-performance` |
| "SwiftUI patterns iOS" | `swiftui-ui-patterns` | `build-ios-apps/swiftui-ui-patterns` |
| "SwiftUI performance audit iOS" | `swiftui-performance-audit` | `build-ios-apps/swiftui-performance-audit` |
| "SwiftUI liquid glass iOS", "glass iOS" | `swiftui-liquid-glass` | `build-ios-apps/swiftui-liquid-glass` |
| "SwiftUI view refactor iOS" | `swiftui-view-refactor` | `build-ios-apps/swiftui-view-refactor` |

### Android (2 Skills) — `mobile-dev/test-android-apps/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Android emulator QA", "test Android emulator" | `android-emulator-qa` | `test-android-apps/android-emulator-qa` |
| "Android performance", "Android perf" | `android-performance` | `test-android-apps/android-performance` |

---

## 🔀 Routing-Logik

```
User-Intent erkennen:
├─ "Expo", "EAS", "React Native"
│  → mobile-dev/expo/<skill>
│
├─ "macOS", "Mac app", "AppKit", "notarization"
│  → mobile-dev/build-macos-apps/<skill>
│
├─ "iOS", "iPhone", "SwiftUI", "Xcode"
│  → mobile-dev/build-ios-apps/<skill>
│
├─ "Android", "emulator"
│  → mobile-dev/test-android-apps/<skill>
│
├─ "signing", "certificate" → build-macos-apps/signing-entitlements
├─ "deploy app" → Frage: "Expo, iOS, oder macOS?"
└─ Unklar? → Frage: "Welche Plattform — Expo, iOS, macOS, oder Android?"
```

---

## Verwendung

```
User: "Deploy meine Expo App via EAS"
→ Router: mobile-dev/expo/expo-deployment

User: "Signing und Notarization für macOS App"
→ Router: mobile-dev/build-macos-apps/signing-entitlements + packaging-notarization

User: "Debugge Memory Leak in iOS App"
→ Router: mobile-dev/build-ios-apps/ios-memgraph-leaks
```

_35 Skills · Expo 13 + macOS 11 + iOS 9 + Android 2 · August 2026_
