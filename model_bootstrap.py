#!/usr/bin/env python3
"""
model_bootstrap.py — SmolLM2-360M Lazy-Download + llama.cpp-Bootstrap

Opt-in Provisioning. KEIN Auto-Download:

    * ensure_model() / ensure_llama_cli() (bzw. --model / --llama-cli) sind
      die EINZIGEN Stellen, die etwas herunterladen oder auf die Platte
      schreiben. Sie werden NUR auf expliziten Aufruf ausgeführt.
    * render()/render_prosa.py laden NIE automatisch — sie rufen nur
      resolve_model_path()/resolve_llama_cli() auf und fallen deterministisch
      auf den Mood-Fallback zurück, solange Modell oder Binary fehlen.

Layout:
    $SHINON_HOME/models/smolm2-360m-instruct-q4_k_m.gguf   (~258 MB, Q4_K_M)
    $SHINON_HOME/bin/llama-cli                             (llama.cpp release)

Usage:
    python3 model_bootstrap.py --status       was ist vorhanden?
    python3 model_bootstrap.py --model        SmolLM2-360M herunterladen
    python3 model_bootstrap.py --llama-cli    llama.cpp-Binary bootstrappen
    python3 model_bootstrap.py --model --force   neu laden (überschreibt)

Env-Overrides:
    SHINON_PROSA_MODEL      expliziter Modell-Pfad
    SHINON_PROSA_MODEL_URL  alternative Modell-URL
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from paths import MODELS_DIR, BIN_DIR

UA = "shinon-bootstrap/1.0"

DEFAULT_MODEL_FILENAME = "smolm2-360m-instruct-q4_k_m.gguf"
DEFAULT_MODEL_URL = (
    "https://huggingface.co/bartowski/SmolLM2-360M-Instruct-GGUF/"
    "resolve/main/SmolLM2-360M-Instruct-Q4_K_M.gguf"
)
# ~270.590.880 Bytes (Q4_K_M). Alles darunter gilt als abgebrochener Download.
DEFAULT_MODEL_MIN_SIZE = 200 * 1024 * 1024

LLAMA_RELEASE_API = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"


# ─── Resolution (read-only) ───────────────────────────────────────────

def resolve_model_path() -> Path:
    """Modell-Pfad (Env-Override → $SHINON_HOME/models/default). Read-only."""
    env = os.environ.get("SHINON_PROSA_MODEL")
    if env:
        return Path(env).expanduser()
    return MODELS_DIR / DEFAULT_MODEL_FILENAME


def resolve_llama_cli() -> str | None:
    """llama-cli finden: PATH → $SHINON_HOME/bin. Read-only, kein Download."""
    for name in ("llama-cli", "llama-cli.exe"):
        found = shutil.which(name)
        if found:
            return found
    for cand in (BIN_DIR / "llama-cli", BIN_DIR / "llama-cli.exe"):
        if cand.exists():
            return str(cand)
    return None


# ─── Platform detection ───────────────────────────────────────────────

def detect_platform_key() -> str | None:
    """Mappt die laufende Plattform auf das llama.cpp-Release-Asset-Suffix."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    arm = machine in ("aarch64", "arm64")
    if system == "linux":
        return "ubuntu-arm64" if arm else "ubuntu-x64"
    if system == "darwin":
        return "macos-arm64" if arm else "macos-x64"
    if system == "windows":
        return "win-cpu-arm64" if arm else "win-cpu-x64"
    return None


def _asset_for_platform(assets: list[dict], key: str) -> dict | None:
    """Finde das PLAIN-CPU-Asset (ohne CUDA/ROCm/Vulkan/…) für key."""
    for a in assets:
        name = a.get("name", "")
        stem = re.sub(r"^llama-b\d+-bin-", "", name)
        stem = re.sub(r"\.(zip|tar\.gz)$", "", stem)
        if stem == key:
            return a
    return None


# ─── Download (streaming, atomar) ─────────────────────────────────────

def _download(url: str, dest: Path, label: str, min_size: int = 0) -> Path:
    """Stream-Download nach <dest>.part, dann atomar umbenennen."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            with open(tmp, "wb") as out:
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = done * 100 // total
                        print(f"\r  {label}: {pct:3d}% "
                              f"({done // (1024*1024)} / {total // (1024*1024)} MB)",
                              end="", flush=True)
            print()
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"download fehlgeschlagen ({e})") from e
    if min_size and done < min_size:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            f"download zu klein ({done} bytes < {min_size}) — abgebrochen")
    os.replace(tmp, dest)
    return dest


# ─── ensure_model (opt-in) ────────────────────────────────────────────

def ensure_model(force: bool = False, url: str | None = None) -> Path:
    """SmolLM2-360M herunterladen (NUR auf expliziten Aufruf)."""
    url = url or os.environ.get("SHINON_PROSA_MODEL_URL") or DEFAULT_MODEL_URL
    dest = MODELS_DIR / DEFAULT_MODEL_FILENAME
    if dest.exists() and not force:
        size = dest.stat().st_size
        if size >= DEFAULT_MODEL_MIN_SIZE:
            print(f"Modell vorhanden: {dest} ({size // (1024*1024)} MB)")
            return dest
        print(f"Modell unvollständig ({size} bytes) — lade neu.")
    print(f"Lade SmolLM2-360M (einmalig, ~258 MB):")
    print(f"  → {dest}")
    _download(url, dest, label=DEFAULT_MODEL_FILENAME,
              min_size=DEFAULT_MODEL_MIN_SIZE)
    print(f"✅ Modell bereit: {dest}")
    return dest


# ─── ensure_llama_cli (opt-in) ────────────────────────────────────────

def _extract(archive: Path, dest: Path) -> None:
    """Archiv entpacken, mit Schutz gegen Pfad-Traversal (../)."""
    dest = dest.resolve()
    if archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "r:gz") as tf:
            try:
                # Python 3.12+: filter="data" blockt Traversal + Symlink-Fallen.
                tf.extractall(dest, filter="data")
            except TypeError:
                # < 3.12: manuell prüfen, dass kein Member aus dest entweicht.
                for m in tf.getmembers():
                    if not (dest / m.name).resolve().is_relative_to(dest):
                        raise RuntimeError(f"unsicherer Archiv-Pfad: {m.name}")
                tf.extractall(dest)
    elif archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            for m in zf.infolist():
                if not (dest / m.filename).resolve().is_relative_to(dest):
                    raise RuntimeError(f"unsicherer Archiv-Pfad: {m.filename}")
            zf.extractall(dest)
    else:
        raise RuntimeError(f"unbekanntes Archiv-Format: {archive.name}")


def _find_binary(root: Path, key: str) -> Path | None:
    target = "llama-cli.exe" if key.startswith("win-") else "llama-cli"
    for p in Path(root).rglob(target):
        if p.is_file():
            return p
    return None


def _find_shared_libs(root: Path, key: str) -> list[Path]:
    """Shared Libraries der Plattform.

    llama.cpp-Prebuilts setzen RUNPATH=$ORIGIN → die libs müssen im selben
    Verzeichnis wie llama-cli liegen (sonst "cannot open shared object file").
    """
    if key.startswith("win-"):
        marker = ".dll"
    elif key.startswith("macos-"):
        marker = ".dylib"
    else:
        marker = ".so"
    return sorted(p for p in Path(root).rglob("*") if p.is_file() and marker in p.name)


def ensure_llama_cli(force: bool = False) -> str | None:
    """llama.cpp-Binary bootstrappen (NUR auf expliziten Aufruf)."""
    existing = resolve_llama_cli()
    if existing and not force:
        print(f"llama-cli vorhanden: {existing}")
        return existing

    key = detect_platform_key()
    if not key:
        print("Kein unterstütztes Plattform-Target für den Auto-Download.")
        print("Manuell: https://github.com/ggerganov/llama.cpp/releases/latest")
        return None

    req = urllib.request.Request(LLAMA_RELEASE_API, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            release = json.load(r)
    except Exception as e:
        print(f"GitHub-Release nicht erreichbar ({e}).")
        return None

    asset = _asset_for_platform(release.get("assets", []), key)
    if not asset:
        print(f"Kein llama.cpp-Asset für '{key}' im Release gefunden.")
        print("Manuell: https://github.com/ggerganov/llama.cpp/releases/latest")
        return None

    name = asset["name"]
    dl_dir = BIN_DIR / ".dl"
    dl_dir.mkdir(parents=True, exist_ok=True)
    archive = dl_dir / name
    print(f"Lade {name} …")
    try:
        _download(asset["browser_download_url"], archive, label=name)
        _extract(archive, dl_dir)
    except RuntimeError as e:
        print(f"FAIL: {e}")
        return None

    binary = _find_binary(dl_dir, key)
    if not binary:
        print("llama-cli nicht im Archiv gefunden.")
        return None

    dest_name = "llama-cli.exe" if key.startswith("win-") else "llama-cli"
    dest = BIN_DIR / dest_name
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(binary, dest)
    if not key.startswith("win-"):
        dest.chmod(dest.stat().st_mode | 0o755)
    # RUNPATH=$ORIGIN: die Shared Libraries müssen NEBEN dem Binary liegen,
    # sonst startet llama-cli nicht. Alle .so/.dll/.dylib mitkopieren.
    for lib in _find_shared_libs(dl_dir, key):
        shutil.copyfile(lib, BIN_DIR / lib.name)
    # Aufräumen: restliche Distribution (llama-server, llama-bench, …) entsorgen.
    shutil.rmtree(dl_dir, ignore_errors=True)
    print(f"✅ llama-cli installiert: {dest}")
    return str(dest)


# ─── CLI ──────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="model_bootstrap.py",
        description="SmolLM2-360M + llama.cpp Provisioning (opt-in, kein Auto-Download).")
    p.add_argument("--status", action="store_true", help="Vorhandenes anzeigen.")
    p.add_argument("--model", action="store_true", help="SmolLM2-360M herunterladen.")
    p.add_argument("--llama-cli", action="store_true", help="llama.cpp-Binary bootstrappen.")
    p.add_argument("--force", action="store_true", help="Neu laden (überschreibt).")
    p.add_argument("--url", default=None, help="Modell-URL überschreiben.")
    args = p.parse_args(argv)

    if args.status:
        model = resolve_model_path()
        print(f"Modell:   {model}")
        if model.exists():
            print(f"  Größe:  {model.stat().st_size // (1024 * 1024)} MB")
        else:
            print("  Status: FEHLT (deterministischer Fallback aktiv)")
        print(f"llama-cli: {resolve_llama_cli() or 'FEHLT (Fallback aktiv)'}")
        return 0

    if args.model:
        try:
            ensure_model(force=args.force, url=args.url)
        except RuntimeError as e:
            print(f"FAIL: {e}")
            return 1
        return 0

    if args.llama_cli:
        try:
            result = ensure_llama_cli(force=args.force)
        except RuntimeError as e:
            print(f"FAIL: {e}")
            return 1
        return 0 if result else 1

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
