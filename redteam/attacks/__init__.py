"""Red-Team Angriffs-Registry."""

from __future__ import annotations

from redteam.attacks.rt01_claim_injection import run as rt01
from redteam.attacks.rt02_evidence_laundering import run as rt02
from redteam.attacks.rt05_gate_skipping import run as rt05
from redteam.attacks.rt07_contradiction_poisoning import run as rt07
from redteam.attacks.rt08_memory_poisoning import run as rt08

# (id, name, run_fn) — Reihenfolge = Ausführungsreihenfolge.
ATTACKS = [
    ("RT-01", "False Claim Injection", rt01),
    ("RT-02", "Evidence Laundering", rt02),
    ("RT-05", "Gate Skipping", rt05),
    ("RT-07", "Contradiction Poisoning", rt07),
    ("RT-08", "Memory Poisoning", rt08),
]
