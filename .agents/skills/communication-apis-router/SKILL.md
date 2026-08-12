---
name: communication-apis-router
description: "Router für 108 Communication-API-Skills (Twilio 55 + Zoom 53). Leitet User-Intents automatisch an den richtigen Sub-Skill weiter. Use bei SMS, Voice, Video, WhatsApp, Email, OAuth, Webhooks, Meeting-SDK, Video-SDK, SendGrid. Routing-Tabelle im Body."
category: communication-apis
stack: AUTONOM + GOVERNANCE
risk: medium
side_effects: network_calls
requires_approval: true
version: "1.0.0"
last_verified: "2026-08-11"

---
# 📡 Communication APIs Router — 108 Skills

> **Router für `communication-apis/`** — Wählt automatisch den richtigen Sub-Skill basierend auf User-Intent.

---

## 🗺️ Routing-Tabelle

### Twilio (55 Skills) — `communication-apis/twilio-developer-kit/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "send SMS", "text message", "SMS versenden" | `twilio-send-message` | `twilio-developer-kit/twilio-send-message` |
| "send WhatsApp", "WhatsApp message", "WhatsApp senden" | `twilio-whatsapp-send-message` | `twilio-developer-kit/twilio-whatsapp-send-message` |
| "manage WhatsApp senders", "WhatsApp sender" | `twilio-whatsapp-manage-senders` | `twilio-developer-kit/twilio-whatsapp-manage-senders` |
| "send email", "SendGrid send", "email API" | `twilio-email-send` | `twilio-developer-kit/twilio-email-send` |
| "SendGrid setup", "email account" | `twilio-sendgrid-account-setup` | `twilio-developer-kit/twilio-sendgrid-account-setup` |
| "SendGrid webhooks", "email events" | `twilio-sendgrid-webhooks` | `twilio-developer-kit/twilio-sendgrid-webhooks` |
| "SendGrid deliverability", "email deliverability" | `twilio-sendgrid-deliverability-advisor` | `twilio-developer-kit/twilio-sendgrid-deliverability-advisor` |
| "SendGrid settings", "email settings" | `twilio-sendgrid-email-settings` | `twilio-developer-kit/twilio-sendgrid-email-settings` |
| "SendGrid suppressions", "email bounces" | `twilio-sendgrid-suppressions` | `twilio-developer-kit/twilio-sendgrid-suppressions` |
| "SendGrid inbound", "inbound email parse" | `twilio-sendgrid-inbound-parse` | `twilio-developer-kit/twilio-sendgrid-inbound-parse` |
| "SendGrid engagement", "email quality" | `twilio-sendgrid-engagement-quality` | `twilio-developer-kit/twilio-sendgrid-engagement-quality` |
| "voice call", "outbound call", "make call" | `twilio-voice-outbound-calls` | `twilio-developer-kit/twilio-voice-outbound-calls` |
| "TwiML", "voice TwiML", "call flow" | `twilio-voice-twiml` | `twilio-developer-kit/twilio-voice-twiml` |
| "call recording", "voice recording" | `twilio-call-recordings` | `twilio-developer-kit/twilio-call-recordings` |
| "conference call", "voice conference" | `twilio-conference-calls` | `twilio-developer-kit/twilio-conference-calls` |
| "voice relay", "conversation relay" | `twilio-voice-conversation-relay` | `twilio-developer-kit/twilio-voice-conversation-relay` |
| "verify", "OTP", "one time password", "2FA" | `twilio-verify-send-otp` | `twilio-developer-kit/twilio-verify-send-otp` |
| "identity verification", "verify advisor" | `twilio-identity-verification-advisor` | `twilio-developer-kit/twilio-identity-verification-advisor` |
| "account setup", "Twilio account", "new Twilio" | `twilio-account-setup` | `twilio-developer-kit/twilio-account-setup` |
| "IAM auth", "API key", "Twilio auth" | `twilio-iam-auth-setup` | `twilio-developer-kit/twilio-iam-auth-setup` |
| "messaging service", "sender pool" | `twilio-messaging-services` | `twilio-developer-kit/twilio-messaging-services` |
| "messaging overview", "which channel" | `twilio-messaging-overview` | `twilio-developer-kit/twilio-messaging-overview` |
| "messaging channel", "pick channel" | `twilio-messaging-channel-advisor` | `twilio-developer-kit/twilio-messaging-channel-advisor` |
| "RCS messaging", "RCS" | `twilio-rcs-messaging` | `twilio-developer-kit/twilio-rcs-messaging` |
| "SMS send", "SMS only" | `twilio-sms-send-message` | `twilio-developer-kit/twilio-sms-send-message` |
| "SMS ISV", "SMS provider setup" | `twilio-sms-isv-setup` | `twilio-developer-kit/twilio-sms-isv-setup` |
| "content template", "message template" | `twilio-content-template-builder` | `twilio-developer-kit/twilio-content-template-builder` |
| "compliance", "A2P", "10DLC", "regulatory" | `twilio-compliance-onboarding` | `twilio-developer-kit/twilio-compliance-onboarding` |
| "compliance traffic", "traffic compliance" | `twilio-compliance-traffic` | `twilio-developer-kit/twilio-compliance-traffic` |
| "regulatory bundle", "compliance bundle" | `twilio-regulatory-compliance-bundles` | `twilio-developer-kit/twilio-regulatory-compliance-bundles` |
| "HIPAA", "security compliance" | `twilio-security-compliance-hipaa` | `twilio-developer-kit/twilio-security-compliance-hipaa` |
| "security hardening", "Twilio security" | `twilio-security-hardening` | `twilio-developer-kit/twilio-security-hardening` |
| "security API auth", "Twilio auth security" | `twilio-security-api-auth` | `twilio-developer-kit/twilio-security-api-auth` |
| "reliability patterns", "Twilio patterns" | `twilio-reliability-patterns` | `twilio-developer-kit/twilio-reliability-patterns` |
| "debugging", "observability", "Twilio debug" | `twilio-debugging-observability` | `twilio-developer-kit/twilio-debugging-observability` |
| "webhook architecture", "Twilio webhooks" | `twilio-webhook-architecture` | `twilio-developer-kit/twilio-webhook-architecture` |
| "messaging webhooks", "message webhooks" | `twilio-messaging-webhooks` | `twilio-developer-kit/twilio-messaging-webhooks` |
| "notifications", "alerts", "Twilio alerts" | `twilio-notifications-alerts-advisor` | `twilio-developer-kit/twilio-notifications-alerts-advisor` |
| "lookup", "phone intelligence", "number lookup" | `twilio-lookup-phone-intelligence` | `twilio-developer-kit/twilio-lookup-phone-intelligence` |
| "numbers", "phone numbers", "senders" | `twilio-numbers-senders` | `twilio-developer-kit/twilio-numbers-senders` |
| "organizations", "Twilio org setup" | `twilio-organizations-setup` | `twilio-developer-kit/twilio-organizations-setup` |
| "CLI reference", "Twilio CLI" | `twilio-cli-reference` | `twilio-developer-kit/twilio-cli-reference` |
| "enterprise knowledge", "Twilio enterprise" | `twilio-enterprise-knowledge` | `twilio-developer-kit/twilio-enterprise-knowledge` |
| "AI agent architect", "build AI agent Twilio" | `twilio-ai-agent-architect` | `twilio-developer-kit/twilio-ai-agent-architect` |
| "agent augmentation", "augment agent" | `twilio-agent-augmentation-architect` | `twilio-developer-kit/twilio-agent-augmentation-architect` |
| "agent connect", "connect agent" | `twilio-agent-connect` | `twilio-developer-kit/twilio-agent-connect` |
| "customer support", "support architect" | `twilio-customer-support-architect` | `twilio-developer-kit/twilio-customer-support-architect` |
| "customer memory", "Twilio customer data" | `twilio-customer-memory` | `twilio-developer-kit/twilio-customer-memory` |
| "conversation intelligence", "Twilio intel" | `twilio-conversation-intelligence` | `twilio-developer-kit/twilio-conversation-intelligence` |
| "conversation orchestrator" | `twilio-conversation-orchestrator` | `twilio-developer-kit/twilio-conversation-orchestrator` |
| "conversations API", "classic conversations" | `twilio-conversations-classic-api` | `twilio-developer-kit/twilio-conversations-classic-api` |
| "TaskRouter", "task routing" | `twilio-taskrouter-routing` | `twilio-developer-kit/twilio-taskrouter-routing` |
| "email deliverability" (non-SendGrid) | `twilio-email-deliverability-advisor` | `twilio-developer-kit/twilio-email-deliverability-advisor` |
| "marketing promotions", "Twilio marketing" | `twilio-marketing-promotions-advisor` | `twilio-developer-kit/twilio-marketing-promotions-advisor` |

### Zoom (53 Skills) — `communication-apis/zoom/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "start with Zoom", "Zoom getting started" | `start` | `zoom/start` |
| "choose Zoom approach", "which Zoom API" | `choose-zoom-approach` | `zoom/choose-zoom-approach` |
| "plan Zoom integration", "Zoom architecture" | `plan-zoom-integration` | `zoom/plan-zoom-integration` |
| "plan Zoom product", "Zoom product plan" | `plan-zoom-product` | `zoom/plan-zoom-product` |
| "Zoom general", "Zoom overview" | `general` | `zoom/general` |
| "Zoom OAuth", "setup Zoom OAuth", "Zoom auth" | `setup-zoom-oauth` | `zoom/setup-zoom-oauth` |
| "Zoom OAuth concepts", "OAuth details" | `oauth` | `zoom/oauth` |
| "Zoom Meeting SDK", "meeting SDK" | `meeting-sdk` | `zoom/meeting-sdk` |
| "Meeting SDK web", "meeting browser" | `meeting-sdk` → `web/component-view` | `zoom/meeting-sdk/web` |
| "Meeting SDK iOS", "meeting iPhone" | `meeting-sdk` → `ios` | `zoom/meeting-sdk/ios` |
| "Meeting SDK Android" | `meeting-sdk` → `android` | `zoom/meeting-sdk/android` |
| "Meeting SDK macOS" | `meeting-sdk` → `macos` | `zoom/meeting-sdk/macos` |
| "Meeting SDK Windows" | `meeting-sdk` → `windows` | `zoom/meeting-sdk/windows` |
| "Meeting SDK Linux" | `meeting-sdk` → `linux` | `zoom/meeting-sdk/linux` |
| "Meeting SDK React Native" | `meeting-sdk` → `react-native` | `zoom/meeting-sdk/react-native` |
| "Meeting SDK Electron" | `meeting-sdk` → `electron` | `zoom/meeting-sdk/electron` |
| "Meeting SDK Unreal" | `meeting-sdk` → `unreal` | `zoom/meeting-sdk/unreal` |
| "Zoom Video SDK" | `video-sdk` | `zoom/video-sdk` |
| "Video SDK web/android/ios/etc" | `video-sdk` → platform | `zoom/video-sdk/<platform>` |
| "build Zoom meeting app" | `build-zoom-meeting-app` | `zoom/build-zoom-meeting-app` |
| "build Zoom bot" | `build-zoom-bot` | `zoom/build-zoom-bot` |
| "Zoom Apps SDK" | `zoom-apps-sdk` | `zoom/zoom-apps-sdk` |
| "Zoom Contact Center" | `contact-center` | `zoom/contact-center` |
| "Zoom Phone" | `phone` | `zoom/phone` |
| "Zoom Team Chat" | `team-chat` | `zoom/team-chat` |
| "Zoom Webhooks" | `webhooks` | `zoom/webhooks` |
| "Zoom WebSockets" | `websockets` | `zoom/websockets` |
| "Zoom REST API" | `rest-api` | `zoom/rest-api` |
| "Zoom RTMS" | `rtms` | `zoom/rtms` |
| "Zoom Scribe" | `scribe` | `zoom/scribe` |
| "Zoom UI Toolkit" | `ui-toolkit` | `zoom/ui-toolkit` |
| "Zoom Virtual Agent" | `virtual-agent` | `zoom/virtual-agent` |
| "Zoom Cobrowse SDK" | `cobrowse-sdk` | `zoom/cobrowse-sdk` |
| "Zoom Probe SDK" | `probe-sdk` | `zoom/probe-sdk` |
| "Zoom Rivet SDK" | `rivet-sdk` | `zoom/rivet-sdk` |
| "debug Zoom", "Zoom troubleshooting" | `debug-zoom` | `zoom/debug-zoom` |
| "debug Zoom integration" | `debug-zoom-integration` | `zoom/debug-zoom-integration` |

---

## 🔀 Routing-Logik

```
User-Intent erkennen:
├─ "Twilio", "SMS", "SendGrid", "TwiML", "WhatsApp", "Verify", "TaskRouter"
│  → communication-apis/twilio-developer-kit/<skill>
│
├─ "Zoom", "Meeting SDK", "Video SDK", "Zoom App", "Contact Center"
│  → communication-apis/zoom/<skill>
│
├─ Unklar? → Frage: "Twilio oder Zoom?"
└─ Beide? → Starte mit choose-zoom-approach ODER twilio-messaging-overview
```

---

## 📋 Vollständiges Sub-Skill-Register

### Twilio (55)

| # | Skill | Pfad |
|---|---|------|
| 1 | twilio-account-setup | twilio-developer-kit/twilio-account-setup |
| 2 | twilio-agent-augmentation-architect | twilio-developer-kit/twilio-agent-augmentation-architect |
| 3 | twilio-agent-connect | twilio-developer-kit/twilio-agent-connect |
| 4 | twilio-ai-agent-architect | twilio-developer-kit/twilio-ai-agent-architect |
| 5 | twilio-call-recordings | twilio-developer-kit/twilio-call-recordings |
| 6 | twilio-cli-reference | twilio-developer-kit/twilio-cli-reference |
| 7 | twilio-compliance-onboarding | twilio-developer-kit/twilio-compliance-onboarding |
| 8 | twilio-compliance-traffic | twilio-developer-kit/twilio-compliance-traffic |
| 9 | twilio-conference-calls | twilio-developer-kit/twilio-conference-calls |
| 10 | twilio-content-template-builder | twilio-developer-kit/twilio-content-template-builder |
| 11 | twilio-conversation-intelligence | twilio-developer-kit/twilio-conversation-intelligence |
| 12 | twilio-conversation-orchestrator | twilio-developer-kit/twilio-conversation-orchestrator |
| 13 | twilio-conversations-classic-api | twilio-developer-kit/twilio-conversations-classic-api |
| 14 | twilio-customer-memory | twilio-developer-kit/twilio-customer-memory |
| 15 | twilio-customer-support-architect | twilio-developer-kit/twilio-customer-support-architect |
| 16 | twilio-debugging-observability | twilio-developer-kit/twilio-debugging-observability |
| 17 | twilio-email-deliverability-advisor | twilio-developer-kit/twilio-email-deliverability-advisor |
| 18 | twilio-email-send | twilio-developer-kit/twilio-email-send |
| 19 | twilio-enterprise-knowledge | twilio-developer-kit/twilio-enterprise-knowledge |
| 20 | twilio-iam-auth-setup | twilio-developer-kit/twilio-iam-auth-setup |
| 21 | twilio-identity-verification-advisor | twilio-developer-kit/twilio-identity-verification-advisor |
| 22 | twilio-lookup-phone-intelligence | twilio-developer-kit/twilio-lookup-phone-intelligence |
| 23 | twilio-marketing-promotions-advisor | twilio-developer-kit/twilio-marketing-promotions-advisor |
| 24 | twilio-messaging-channel-advisor | twilio-developer-kit/twilio-messaging-channel-advisor |
| 25 | twilio-messaging-overview | twilio-developer-kit/twilio-messaging-overview |
| 26 | twilio-messaging-services | twilio-developer-kit/twilio-messaging-services |
| 27 | twilio-messaging-webhooks | twilio-developer-kit/twilio-messaging-webhooks |
| 28 | twilio-notifications-alerts-advisor | twilio-developer-kit/twilio-notifications-alerts-advisor |
| 29 | twilio-numbers-senders | twilio-developer-kit/twilio-numbers-senders |
| 30 | twilio-organizations-setup | twilio-developer-kit/twilio-organizations-setup |
| 31 | twilio-rcs-messaging | twilio-developer-kit/twilio-rcs-messaging |
| 32 | twilio-regulatory-compliance-bundles | twilio-developer-kit/twilio-regulatory-compliance-bundles |
| 33 | twilio-reliability-patterns | twilio-developer-kit/twilio-reliability-patterns |
| 34 | twilio-security-api-auth | twilio-developer-kit/twilio-security-api-auth |
| 35 | twilio-security-compliance-hipaa | twilio-developer-kit/twilio-security-compliance-hipaa |
| 36 | twilio-security-hardening | twilio-developer-kit/twilio-security-hardening |
| 37 | twilio-send-message | twilio-developer-kit/twilio-send-message |
| 38 | twilio-sendgrid-account-setup | twilio-developer-kit/twilio-sendgrid-account-setup |
| 39 | twilio-sendgrid-deliverability-advisor | twilio-developer-kit/twilio-sendgrid-deliverability-advisor |
| 40 | twilio-sendgrid-email-send | twilio-developer-kit/twilio-sendgrid-email-send |
| 41 | twilio-sendgrid-email-settings | twilio-developer-kit/twilio-sendgrid-email-settings |
| 42 | twilio-sendgrid-engagement-quality | twilio-developer-kit/twilio-sendgrid-engagement-quality |
| 43 | twilio-sendgrid-inbound-parse | twilio-developer-kit/twilio-sendgrid-inbound-parse |
| 44 | twilio-sendgrid-suppressions | twilio-developer-kit/twilio-sendgrid-suppressions |
| 45 | twilio-sendgrid-webhooks | twilio-developer-kit/twilio-sendgrid-webhooks |
| 46 | twilio-sms-isv-setup | twilio-developer-kit/twilio-sms-isv-setup |
| 47 | twilio-sms-send-message | twilio-developer-kit/twilio-sms-send-message |
| 48 | twilio-taskrouter-routing | twilio-developer-kit/twilio-taskrouter-routing |
| 49 | twilio-verify-send-otp | twilio-developer-kit/twilio-verify-send-otp |
| 50 | twilio-voice-conversation-relay | twilio-developer-kit/twilio-voice-conversation-relay |
| 51 | twilio-voice-outbound-calls | twilio-developer-kit/twilio-voice-outbound-calls |
| 52 | twilio-voice-twiml | twilio-developer-kit/twilio-voice-twiml |
| 53 | twilio-webhook-architecture | twilio-developer-kit/twilio-webhook-architecture |
| 54 | twilio-whatsapp-manage-senders | twilio-developer-kit/twilio-whatsapp-manage-senders |
| 55 | twilio-whatsapp-send-message | twilio-developer-kit/twilio-whatsapp-send-message |

### Zoom (53)

| # | Skill | Pfad |
|---|---|------|
| 1 | start | zoom/start |
| 2 | choose-zoom-approach | zoom/choose-zoom-approach |
| 3 | plan-zoom-integration | zoom/plan-zoom-integration |
| 4 | plan-zoom-product | zoom/plan-zoom-product |
| 5 | general | zoom/general |
| 6 | setup-zoom-oauth | zoom/setup-zoom-oauth |
| 7 | oauth | zoom/oauth |
| 8 | meeting-sdk | zoom/meeting-sdk |
| 9-20 | meeting-sdk/<platform> | zoom/meeting-sdk/{web,ios,android,macos,windows,linux,react-native,electron,unreal} |
| 21 | video-sdk | zoom/video-sdk |
| 22-30 | video-sdk/<platform> | zoom/video-sdk/{web,ios,android,macos,windows,linux,react-native,flutter,unity} |
| 31 | build-zoom-meeting-app | zoom/build-zoom-meeting-app |
| 32 | build-zoom-bot | zoom/build-zoom-bot |
| 33 | zoom-apps-sdk | zoom/zoom-apps-sdk |
| 34 | contact-center | zoom/contact-center |
| 35-37 | contact-center/<platform> | zoom/contact-center/{web,ios,android} |
| 38 | phone | zoom/phone |
| 39 | team-chat | zoom/team-chat |
| 40 | webhooks | zoom/webhooks |
| 41 | websockets | zoom/websockets |
| 42 | rest-api | zoom/rest-api |
| 43 | rtms | zoom/rtms |
| 44 | scribe | zoom/scribe |
| 45 | ui-toolkit | zoom/ui-toolkit |
| 46 | virtual-agent | zoom/virtual-agent |
| 47-49 | virtual-agent/<platform> | zoom/virtual-agent/{web,ios,android} |
| 50 | cobrowse-sdk | zoom/cobrowse-sdk |
| 51 | probe-sdk | zoom/probe-sdk |
| 52 | rivet-sdk | zoom/rivet-sdk |
| 53 | debug-zoom | zoom/debug-zoom |
| 54 | debug-zoom-integration | zoom/debug-zoom-integration |

---

## Verwendung

```
User: "Ich will SMS versenden"
→ Router erkennt "SMS" → lädt twilio-send-message

User: "Baue eine Zoom Meeting App"
→ Router erkennt "Zoom Meeting App" → lädt build-zoom-meeting-app

User: "Ich brauche OAuth für Zoom"
→ Router erkennt "OAuth Zoom" → lädt setup-zoom-oauth
```

_108 Skills · Twilio 55 + Zoom 53 · August 2026_
