---
name: ecommerce-router
description: "Router für 26 E-Commerce-Skills (Shopify 20 + Stripe 2 + Wix 4). Leitet Commerce-Intents an den richtigen Sub-Skill. Use bei Shopify Admin, Hydrogen, Liquid, Polaris, Functions, Stripe Payments, Wix Apps, Headless, Design System."
category: ecommerce
stack: GOVERNANCE + AUTONOM
risk: high
side_effects: money_movement
requires_approval: true
version: "1.0.0"
last_verified: "2026-08-11"
---

# 🛒 E-Commerce Router — 26 Skills

> **Router für `ecommerce/`** — Wählt Sub-Skill basierend auf Plattform und Task-Typ. **⚠️ Geldbewegungen — Approval required!**

---

## 🗺️ Routing-Tabelle

### Shopify (20 Skills) — `ecommerce/shopify/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Shopify admin", "Shopify API admin", "manage store" | `shopify-admin` | `shopify/shopify-admin` |
| "Shopify dev", "Shopify development", "Shopify app dev" | `shopify-dev` | `shopify/shopify-dev` |
| "Shopify CLI", "use Shopify CLI", "shopify command" | `shopify-use-shopify-cli` | `shopify/shopify-use-shopify-cli` |
| "Shopify onboarding dev", "new Shopify dev" | `shopify-onboarding-dev` | `shopify/shopify-onboarding-dev` |
| "Shopify onboarding merchant", "new Shopify store" | `shopify-onboarding-merchant` | `shopify/shopify-onboarding-merchant` |
| "Shopify Hydrogen", "headless Shopify", "Hydrogen storefront" | `shopify-hydrogen` | `shopify/shopify-hydrogen` |
| "Shopify Liquid", "Shopify theme", "liquid template" | `shopify-liquid` | `shopify/shopify-liquid` |
| "Shopify Storefront GraphQL", "Storefront API" | `shopify-storefront-graphql` | `shopify/shopify-storefront-graphql` |
| "Shopify Functions", "Shopify extensibility" | `shopify-functions` | `shopify/shopify-functions` |
| "Shopify Polaris admin extensions" | `shopify-polaris-admin-extensions` | `shopify/shopify-polaris-admin-extensions` |
| "Shopify Polaris app home" | `shopify-polaris-app-home` | `shopify/shopify-polaris-app-home` |
| "Shopify Polaris checkout extensions" | `shopify-polaris-checkout-extensions` | `shopify/shopify-polaris-checkout-extensions` |
| "Shopify Polaris customer account" | `shopify-polaris-customer-account-extensions` | `shopify/shopify-polaris-customer-account-extensions` |
| "Shopify custom data", "metaobjects", "metafields" | `shopify-custom-data` | `shopify/shopify-custom-data` |
| "Shopify customer", "customer API" | `shopify-customer` | `shopify/shopify-customer` |
| "Shopify partner", "Shopify partner API" | `shopify-partner` | `shopify/shopify-partner` |
| "Shopify payments apps", "payment app Shopify" | `shopify-payments-apps` | `shopify/shopify-payments-apps` |
| "Shopify POS", "point of sale UI", "Shopify retail" | `shopify-pos-ui` | `shopify/shopify-pos-ui` |
| "Shopify app store review", "submit app Shopify" | `shopify-app-store-review` | `shopify/shopify-app-store-review` |
| "UCP", "UCP CLI", "product comparison Shopify" | `ucp` | `shopify/ucp` |

### Stripe (2 Skills) — `ecommerce/stripe/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Stripe best practices", "Stripe integration", "Stripe API" | `stripe-best-practices` | `stripe/stripe-best-practices` |
| "upgrade Stripe", "Stripe API version", "migrate Stripe" | `upgrade-stripe` | `stripe/upgrade-stripe` |

### Wix (4 Skills) — `ecommerce/wix/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Wix app", "build Wix app", "Wix application" | `wix-app` | `wix/wix-app` |
| "Wix design system", "Wix UI", "Wix components" | `wix-design-system` | `wix/wix-design-system` |
| "Wix headless", "Wix headless CMS", "Wix API" | `wix-headless` | `wix/wix-headless` |
| "Wix manage", "Wix management", "manage Wix site" | `wix-manage` | `wix/wix-manage` |

---

## 🔀 Routing-Logik

```
User-Intent erkennen:
├─ "Shopify", "Hydrogen", "Liquid", "Polaris", "Storefront"
│  → ecommerce/shopify/<skill>
│
├─ "Stripe", "payment", "checkout"
│  → ecommerce/stripe/<skill>
│
├─ "Wix", "Wix app", "Wix site"
│  → ecommerce/wix/<skill>
│
├─ "payment" ohne Plattform → Frage: "Stripe oder Shopify Payments?"
├─ "storefront", "online shop" → Frage: "Shopify, Wix, oder custom?"
└─ Unklar? → Frage: "Shopify, Stripe, oder Wix?"
```

---

## ⚠️ Governance-Hinweise

| Kategorie | Risk | Approval |
|---|---|---|
| **Shopify Payments** | critical | ✅ required |
| **Stripe** | critical | ✅ required |
| **Shopify Admin** | high | ✅ required |
| **Wix** | medium | ✅ required |

---

## Verwendung

```
User: "Erstelle eine Shopify Hydrogen Storefront"
→ Router: ecommerce/shopify/shopify-hydrogen

User: "Integriere Stripe Payments"
→ Router: ecommerce/stripe/stripe-best-practices
⚠️ APPROVAL REQUIRED — Geldbewegung!

User: "Custom Admin Extension mit Polaris"
→ Router: ecommerce/shopify/shopify-polaris-admin-extensions
```

_26 Skills · Shopify 20 + Stripe 2 + Wix 4 · August 2026_
