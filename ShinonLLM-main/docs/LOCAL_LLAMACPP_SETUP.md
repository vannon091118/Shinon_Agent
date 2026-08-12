# Local llama.cpp Setup (Quick-QA + Kandidaten)

Stand: 2026-04-02

## Ziel

Lokaler `llama.cpp` Betrieb fuer schnelle QA mit GGUF-Modellen, passend zur Runtime-First Ausrichtung.

## Quick-QA Basismodell (empfohlen)

- Modell-Datei: `ops/models/qwen2.5-0.5b-instruct-q4_k_m.gguf`
- Groesse: ca. 491 MB
- Quelle: [Qwen/Qwen2.5-0.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF)

Hinweis:

- GGUF-Binaries sind absichtlich nicht Teil des Git-Repos (`ops/models/*.gguf` ist gitignored).
- Lege die Datei lokal unter `ops/models/` ab und committe sie nicht.

## Starten (Docker Compose)

Voraussetzung: Docker Desktop installiert und im PATH.

```powershell
.\ops\scripts\run-local.ps1
```

`run-local.ps1` prueft jetzt vorab, ob die konfigurierte GGUF-Datei in `ops/models` existiert.

Optional anderes Modell:

```powershell
$env:LLAMACPP_MODEL_FILE = "dein-modell.gguf"
.\ops\scripts\run-local.ps1
```

## Quick-QA ausfuehren

```powershell
.\ops\scripts\quick-qa-llamacpp.ps1
```

Der Script ruft `http://127.0.0.1:8000/v1/chat/completions` auf.

## Open-Source Kandidaten (weitere Optionen)

1. Schnell/leicht (QA, Low-RAM):
- [Qwen/Qwen2.5-0.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF)

2. Besseres Reasoning bei noch moderatem Footprint:
- [Qwen/Qwen2.5-1.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF)

3. Starker allgemeiner Instruct-Kandidat (community GGUF):
- [unsloth/Qwen2.5-3B-Instruct-GGUF](https://huggingface.co/unsloth/Qwen2.5-3B-Instruct-GGUF)

4. Gemma-Option fuer lokale QA:
- [unsloth/gemma-3-1b-it-GGUF](https://huggingface.co/unsloth/gemma-3-1b-it-GGUF)

## llama.cpp API Referenz

- OpenAI-kompatibler Server und Chat-Endpoint (`/v1/chat/completions`):
  [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)
