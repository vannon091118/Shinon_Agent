"""Shinon Red Team — Governance-Tests gegen LLM-Faulheit & Bias-Drift.

KEIN Security-Red-Team gegen Cyberangriffe. Dieses Red Team greift die
DETERMINISTISCHE Governance-Schicht an (KARMA ConfidenceResolver,
FalsificationGate, Memory-Provenance, Contract-Validierung), um zu beweisen,
dass Shinon sich NICHT selbst belügen kann.

Prinzip: Governance darf nicht nur im Prompt existieren. Wenn der Runtime-Code
kein "no valid gate decision → execution impossible" erzwingt, ist es keine
Governance — es ist ein sehr höflicher Prompt.
"""

__version__ = "0.1.0"
