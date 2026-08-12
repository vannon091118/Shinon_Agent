---
name: ai-ml-router
description: "Router für 28 AI/ML-Skills (HuggingFace 12 + NVIDIA 11 + OpenAI 5). Leitet ML-Intents an den richtigen Sub-Skill. Use bei HuggingFace CLI, Datasets, Transformers.js, Gradio, NVIDIA cuOpt, Dynamo, Omniverse, Nemoclaw, OpenAI Agents SDK, ChatGPT Apps, API Troubleshooting."
category: ai-ml
stack: LOGISCH + SELF-IMPROVE
risk: medium
side_effects: network_calls
requires_approval: false
version: "1.0.0"
last_verified: "2026-08-11"
---

# 🤖 AI/ML Router — 28 Skills

> **Router für `ai-ml/`** — Wählt Sub-Skill basierend auf Framework, Plattform und Task-Typ.

---

## 🗺️ Routing-Tabelle

### HuggingFace (12 Skills) — `ai-ml/hugging-face/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "HuggingFace CLI", "hf CLI", "huggingface-cli" | `cli` | `hugging-face/cli` |
| "HuggingFace datasets", "load dataset", "HF dataset" | `datasets` | `hugging-face/datasets` |
| "Transformers.js", "browser ML", "client-side inference" | `transformers.js` | `hugging-face/transformers.js` |
| "Gradio", "ML demo", "build UI for model" | `gradio` | `hugging-face/gradio` |
| "train LLM", "fine-tune LLM", "LLM trainer" | `llm-trainer` | `hugging-face/llm-trainer` |
| "vision trainer", "train image model", "fine-tune vision" | `vision-trainer` | `hugging-face/vision-trainer` |
| "HF jobs", "HuggingFace job", "training job" | `jobs` | `hugging-face/jobs` |
| "HF papers", "research paper", "arxiv HF" | `papers` | `hugging-face/papers` |
| "publish paper", "paper publisher", "HF paper" | `paper-publisher` | `hugging-face/paper-publisher` |
| "community evals", "evaluate model HF", "model eval" | `community-evals` | `hugging-face/community-evals` |
| "TrackIO", "track training", "ML tracking" | `trackio` | `hugging-face/trackio` |

### NVIDIA (11 Skills) — `ai-ml/nvidia/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "NVIDIA cuOpt", "route optimization", "vehicle routing" | `cuopt-user-rules` | `nvidia/cuopt-user-rules` |
| "NVIDIA Dynamo", "Dynamo router", "Dynamo starter" | `dynamo-router-starter` | `nvidia/dynamo-router-starter` |
| "Dynamo interconnect", "Dynamo check" | `dynamo-interconnect-check` | `nvidia/dynamo-interconnect-check` |
| "NVIDIA AIQ deploy", "AIQ inference" | `aiq-deploy` | `nvidia/aiq-deploy` |
| "NVIDIA AIQ research", "AIQ research" | `aiq-research` | `nvidia/aiq-research` |
| "NVIDIA Omniverse", "CAD to sim", "simready" | `omniverse-cad-to-simready` | `nvidia/omniverse-cad-to-simready` |
| "Omniverse viewer", "realtime viewer" | `omniverse-realtime-viewer` | `nvidia/omniverse-realtime-viewer` |
| "Omniverse USD", "USD performance", "USD tuning" | `omniverse-usd-performance-tuning` | `nvidia/omniverse-usd-performance-tuning` |
| "NVIDIA Nemoclaw", "Nemoclaw get started" | `nemoclaw-user-get-started` | `nvidia/nemoclaw-user-get-started` |
| "Physical AI infra", "physical AI setup", "resilient scaling" | `physical-ai-infrastructure-setup-and-resilient-scaling` | `nvidia/physical-ai-infrastructure-setup-and-resilient-scaling` |
| "Physical AI neural", "neural reconstruction" | `physical-ai-neural-reconstruction` | `nvidia/physical-ai-neural-reconstruction` |

### OpenAI Developers (4 Skills) — `ai-ml/openai-developers/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "OpenAI Agents SDK", "OpenAI agent", "build agent OpenAI" | `agents-sdk` | `openai-developers/agents-sdk` |
| "build ChatGPT app", "ChatGPT plugin", "GPT app" | `build-chatgpt-app` | `openai-developers/build-chatgpt-app` |
| "ChatGPT app submission", "submit GPT", "GPT store" | `chatgpt-app-submission` | `openai-developers/chatgpt-app-submission` |
| "OpenAI API key", "platform API key", "OpenAI key setup" | `openai-platform-api-key` | `openai-developers/openai-platform-api-key` |
| "OpenAI API troubleshooting", "API error", "OpenAI debug" | `openai-api-troubleshooting` | `openai-developers/openai-api-troubleshooting` |

### OpenAI Ads Conversions (1 Skill) — `ai-ml/openai-ads-conversions/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "OpenAI ads conversions", "ads measurement", "conversion setup" | `openai-ads-conversions-setup` | `openai-ads-conversions/openai-ads-conversions-setup` |

---

## 🔀 Routing-Logik

```
User-Intent erkennen:
├─ "HuggingFace", "HF", "Transformers", "Gradio", "datasets"
│  → ai-ml/hugging-face/<skill>
│
├─ "NVIDIA", "cuOpt", "Dynamo", "Omniverse", "AIQ", "Physical AI"
│  → ai-ml/nvidia/<skill>
│
├─ "OpenAI", "ChatGPT", "GPT", "Agents SDK", "API key"
│  → ai-ml/openai-developers/<skill>
│
├─ "train model", "fine-tune" → hugging-face/llm-trainer
├─ "deploy model", "inference" → nvidia/aiq-deploy
└─ Unklar? → Frage: "HuggingFace, NVIDIA, oder OpenAI?"
```

---

## Verwendung

```
User: "Fine-tune ein LLM mit HuggingFace"
→ Router: ai-ml/hugging-face/llm-trainer

User: "Optimiere Routen mit NVIDIA cuOpt"
→ Router: ai-ml/nvidia/cuopt-user-rules

User: "Erstelle einen Agenten mit OpenAI SDK"
→ Router: ai-ml/openai-developers/agents-sdk
```

_28 Skills · HuggingFace 12 + NVIDIA 11 + OpenAI 5 · August 2026_
