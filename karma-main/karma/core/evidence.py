"""
KARMA Evidence Core — Epistemische Kontrolle

Trennt reine Behauptungen (Claims) von messbarer Realität (Evidence).
Die EvidenceStore Klasse kümmert sich um die Persistenz in der SQLite Datenbank.
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict
import datetime
import json
import re
import uuid

from karma.core.persistence import PersistenceLayer


class EvidenceType(Enum):
    SOURCE = "source"           # Dokumentation, ADR, Design Doc
    RUNTIME = "runtime"         # Laufzeit-Log, Execution, Gate-Pass
    TEST = "test"               # Testlauf
    REPLAY = "replay"           # Erfolgreicher Retro-Test
    HUMAN = "human"             # User-Feedback / Approved


@dataclass
class Evidence:
    evidence_id: str
    claim_id: str
    evidence_type: EvidenceType
    source: str
    confidence: float
    timestamp: str
    metadata: dict

    @classmethod
    def create(cls, claim_id: str, evidence_type: EvidenceType, source: str, confidence: float, metadata: Optional[dict] = None) -> "Evidence":
        return cls(
            evidence_id=str(uuid.uuid4()),
            claim_id=claim_id,
            evidence_type=evidence_type,
            source=source,
            confidence=confidence,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            metadata=metadata or {}
        )

    def entails(self, claim: Union[str, "Claim"]) -> bool:
        """Return whether this evidence deterministically covers ``claim``.

        ``claim`` may be a :class:`Claim` or its statement for compatibility.
        This is deliberately structural: confidence is never used to invent
        entailment. A passing test about ``component exists`` therefore cannot
        support ``component is deterministic``.
        """
        return evidence_entails(self, claim)


@dataclass
class Claim:
    claim_id: str
    project: str
    statement: str
    domain: str
    evidences: List[Evidence] = field(default_factory=list)

    @classmethod
    def create(cls, project: str, statement: str, domain: str) -> "Claim":
        return cls(
            claim_id=str(uuid.uuid4()),
            project=project,
            statement=statement,
            domain=domain
        )


class ClaimStatus(Enum):
    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    CONFIRMED = "confirmed"
    CONFLICTED = "conflicted"
    DEPRECATED = "deprecated"
    REFUTED = "refuted"  # aktive Ablehnung: Evidence widerspricht dem Claim


# ─── Entailment (Evidence ≠ Evidence-for-Claim) ─────────────────────
# Ein Test, der "Component X exists" prüft, ENTAILT NICHT den Claim
# "Component X is deterministic". Der Resolver darf nicht zum "digitalen
# Priester" werden ("Es gibt einen Test, also stimmt es"). Deterministischer
# Check: Wenn das Evidence DEKLARIERT, was es verifiziert (metadata-Feld wie
# test_name/verifies/about/claim), muss diese Deklaration die Behauptung
# abdecken — mindestens 2 geteilte Inhaltsterme ODER den Head-Term (letzter
# Inhaltsterm = das Prädikat) der Behauptung. Ohne Deklaration (nacktes
# Evidence) bleibt der Check lenient — kein diskriminierendes Signal, kein
# Abstrafen.

# metadata-Keys, die als "das verifiziert dieses Evidence"-Deklaration gelten.
_ENTAILMENT_DECLARATION_KEYS = (
    "verifies", "about", "claim", "claim_statement",
    "test_name", "probe", "probe_name", "name", "description",
)

_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "has", "have", "had", "do", "does", "did", "of", "to", "in", "on", "at",
    "by", "for", "with", "and", "or", "not", "no", "but", "if", "then",
    "this", "that", "these", "those", "it", "its", "as", "from", "into",
    "der", "die", "das", "ist", "sind", "war", "und", "oder", "nicht",
    "kein", "keine", "ein", "eine", "mit", "von", "für", "auf", "aus",
})


def _content_terms(text: str) -> List[str]:
    """Normalisierte Inhaltsterme (lowercase, alphanumerisch, ≥3 Zeichen,
    ohne Stopwörter, ohne reine Zahlen). Reihenfolge erhalten (der letzte
    Term ist der Head-Term = das Prädikat der Behauptung)."""
    if not isinstance(text, str):
        return []
    tokens = re.findall(r"[a-zA-Z0-9äöüÄÖÜß]+", text.lower())
    terms: List[str] = []
    for t in tokens:
        if len(t) < 3 or t in _STOPWORDS or t.isdigit():
            continue
        if t not in terms:
            terms.append(t)
    return terms


def _evidence_declaration(ev: Evidence) -> str:
    """Was das Evidence selbst BEHAUPTET zu verifizieren (deklarierte Subject)."""
    m = ev.metadata or {}
    parts: List[str] = []
    for key in _ENTAILMENT_DECLARATION_KEYS:
        val = m.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val)
    return " ".join(parts)


def entailment_report(ev: Evidence, claim: Union[str, "Claim"]) -> Dict[str, Any]:
    """Deterministischer Entailment-Befund: entscheidet UND begründet.

    Regel:
      * Kein deklariertes Signal (keine metadata-Deklaration):
          - fail-closed für EMPIRISCHE POSITIVE Evidenz (TEST/RUNTIME/REPLAY
            mit confidence > 0.5): ohne Deklaration lässt sich Entailment
            nicht herstellen → NICHT als Stütze werten (kein Bypass durch
            Weglassen der Deklaration).
          - lenient für SOURCE/HUMAN und für widerlegende (negative) Evidenz.
      * Deklariert: die deklarierten Terme müssen die Behauptung abdecken —
        mindestens 2 geteilte Inhaltsterme ODER den Head-Term (letzter
        Inhaltsterm = das Prädikat). Ein deklariertes, aber DISJUNKTES
        Evidence entailed NICHT (z. B. test_component_exists vs.
        "Component X is deterministic").
    """
    claim_statement = claim.statement if isinstance(claim, Claim) else claim
    ev_terms = _content_terms(_evidence_declaration(ev))
    claim_terms = _content_terms(claim_statement)

    if not ev_terms:
        positive_empirical = (
            ev.evidence_type in (EvidenceType.TEST, EvidenceType.RUNTIME, EvidenceType.REPLAY)
            and ev.confidence > 0.5
        )
        return {
            "entails": not positive_empirical,
            "reason": ("empirical positive evidence without declaration"
                       if positive_empirical else "no declaration (lenient)"),
            "declared_terms": [],
            "claim_terms": claim_terms,
            "shared": [],
        }
    if not claim_terms:
        return {
            "entails": True, "reason": "claim has no content terms",
            "declared_terms": ev_terms, "claim_terms": [], "shared": [],
        }
    shared = [t for t in ev_terms if t in claim_terms]
    if not shared:
        return {
            "entails": False, "reason": "disjoint (no shared terms)",
            "declared_terms": ev_terms, "claim_terms": claim_terms, "shared": [],
        }
    # Subject overlap is not claim coverage. The decisive predicate/head term
    # must be present in the declaration: `test_component_exists` therefore
    # cannot entail `Component X is deterministic` even though both mention
    # the same component. This keeps the check deterministic and fail-closed.
    head = claim_terms[-1]
    entails = head in shared
    return {
        "entails": entails,
        "reason": "covered" if entails else "subject-only overlap (head term not covered)",
        "declared_terms": ev_terms,
        "claim_terms": claim_terms,
        "shared": shared,
    }


def evidence_entails(ev: Evidence, claim: Union[str, "Claim"]) -> bool:
    """Boolean deterministic entailment check (never confidence aggregation)."""
    return entailment_report(ev, claim)["entails"]


# ─── Scope-Deviation-Budget (Rework-Loop statt Hard-Reject) ─────────
# Shinon lehnt nicht hart ab ("ablehnen ist auch schlecht"). Stattdessen
# geht ein widerlegter Claim zurück in den Loop mit einem ANGEPASSTEN
# Scope. Der darf maximal X vom Original abweichen — darüber fragt Shinon
# den User (Checkpoint), statt still weiter zu verengen.

DEFAULT_MAX_SCOPE_DEVIATION = 0.5  # X: Budget für Scope-Abweichung


def max_scope_deviation() -> float:
    """Budget X: env KARMA_MAX_SCOPE_DEVIATION überschreibt den Default.

    Der User kann die Schwelle ("bevor Shinon fragt") justieren, ohne den
    Code anzufassen.
    """
    import os
    raw = os.environ.get("KARMA_MAX_SCOPE_DEVIATION")
    if raw:
        try:
            val = float(raw)
            if 0.0 <= val <= 1.0:
                return val
        except ValueError:
            pass
    return DEFAULT_MAX_SCOPE_DEVIATION


def scope_deviation(original: str, adjusted: str) -> float:
    """Deterministische Scope-Abweichung: 0.0 = identisch, 1.0 = komplett anders.

    Misst den Anteil der Original-Terme, der im angepassten Scope fehlt.
    """
    orig = _content_terms(original)
    if not orig:
        return 0.0
    adj = _content_terms(adjusted)
    removed = [t for t in orig if t not in adj]
    return round(len(removed) / len(orig), 4)


def _positive_support(ev: Evidence) -> bool:
    """Konsistentes Prädikat für "positive Stütze" — MUSS mit den Flags in
    resolve() übereinstimmen (runtime/test/replay > 0.5, source > 0.0,
    human > 0.5), sonst widerspricht die Scope-Abweichung dem Verdict."""
    if ev.evidence_type in (EvidenceType.RUNTIME, EvidenceType.TEST, EvidenceType.REPLAY):
        return ev.confidence > 0.5
    if ev.evidence_type == EvidenceType.SOURCE:
        return ev.confidence > 0.0
    if ev.evidence_type == EvidenceType.HUMAN:
        return ev.confidence > 0.5
    return False


def rework_scope_deviation(claim: Claim) -> Dict[str, Any]:
    """Deterministischer Rework-Befund für einen widerlegten Claim.

    Der angepasste Scope = die Teilmenge der Claim-Terme, die noch von
    positiver, entailender Evidenz gedeckt ist. scope_deviation() misst die
    Abweichung dieses angepassten Scopes vom Original. Vollständig
    widerlegt → 1.0 (nichts bleibt) → User-Checkpoint.
    """
    claim_terms = _content_terms(claim.statement)
    if not claim_terms:
        return {
            "scope_deviation": 0.0,
            "adjusted_scope": "",
            "retained_terms": [],
            "dropped_terms": [],
        }
    supported = set()
    for ev in claim.evidences:
        if _positive_support(ev) and evidence_entails(ev, claim.statement):
            supported.update(_content_terms(_evidence_declaration(ev)))
    retained = [t for t in claim_terms if t in supported]
    dropped = [t for t in claim_terms if t not in supported]
    adjusted_scope = " ".join(retained)
    dev = scope_deviation(claim.statement, adjusted_scope)
    return {
        "scope_deviation": dev,
        "adjusted_scope": adjusted_scope,
        "retained_terms": retained,
        "dropped_terms": dropped,
    }


class ConfidenceResolver:
    """Berechnet mehrdimensionale Confidence basierend auf Evidenz-Limits und
    weist einen Status zu. Prüft VOR der Aggregation, ob jedes Evidence die
    Behauptung überhaupt ENTAILT (evidence.entails(claim)) — sonst wäre der
    Resolver ein "digitaler Priester" ("Es gibt einen Test, also stimmt es")."""
    
    LIMITS = {
        EvidenceType.SOURCE: 0.4,
        EvidenceType.TEST: 0.7,
        EvidenceType.RUNTIME: 0.9,
        EvidenceType.REPLAY: 0.95,
        EvidenceType.HUMAN: 1.0
    }

    @staticmethod
    def resolve(claim: Claim) -> Dict[str, Any]:
        scores = {t.value: 0.0 for t in EvidenceType}
        counts = {t: 0 for t in EvidenceType}
        sums = {t: 0.0 for t in EvidenceType}

        has_positive_runtime = False
        has_negative_runtime = False
        has_positive_source = False
        has_negative_source = False

        # Entailment-Gate: Evidence, das die Behauptung NICHT entailed, ist
        # irrelevant (weder Stütze noch Widerlegung) und wird aus der
        # Aggregation ausgeschlossen. Der Befund (warum) wird mitgeloggt.
        entailment_rejected: List[Dict[str, Any]] = []

        for ev in claim.evidences:
            report = entailment_report(ev, claim.statement)
            if not report["entails"]:
                entailment_rejected.append({
                    "evidence_id": ev.evidence_id,
                    "source": ev.source,
                    "reason": report["reason"],
                    "declared_terms": report["declared_terms"],
                    "claim_terms": report["claim_terms"],
                    "shared": report["shared"],
                })
                continue

            counts[ev.evidence_type] += 1
            sums[ev.evidence_type] += ev.confidence
            
            # Simple heuristic for conflict detection:
            # For this prototype, we assume evidence confidence near 0.0 for a claim means it was refuted.
            if ev.evidence_type in (EvidenceType.RUNTIME, EvidenceType.TEST, EvidenceType.REPLAY):
                if ev.confidence > 0.5:
                    has_positive_runtime = True
                else:
                    has_negative_runtime = True
            elif ev.evidence_type == EvidenceType.SOURCE:
                if ev.confidence > 0.0:
                    has_positive_source = True
                else:
                    has_negative_source = True

        overall = 0.0

        for etype in EvidenceType:
            if counts[etype] > 0:
                avg = sums[etype] / counts[etype]
                capped = min(avg, ConfidenceResolver.LIMITS[etype])
                scores[etype.value] = capped
                if capped > overall:
                    overall = capped  # Highest valid evidence defines overall confidence

        scores["overall"] = round(overall, 4)
        scores["entailment_checked"] = True
        scores["entailment_rejected"] = entailment_rejected
        
        # Determine Status
        status = ClaimStatus.UNVERIFIED
        
        # Active rejection: evidence contradicts the claim (negative runtime/
        # test OR negative source evidence) and NOTHING supports it → REFUTED.
        if (has_positive_source and has_negative_runtime) or (has_positive_runtime and has_negative_runtime):
            status = ClaimStatus.CONFLICTED
        elif (has_negative_runtime or has_negative_source) and not (has_positive_runtime or has_positive_source):
            status = ClaimStatus.REFUTED
        elif has_positive_runtime and overall >= 0.7:
            status = ClaimStatus.CONFIRMED
        elif has_positive_source and overall > 0.0:
            status = ClaimStatus.SUPPORTED
            
        scores["status"] = status.value

        # Rework-Direktive: statt hart abzulehnen → zurück in den Loop mit
        # angepasstem Scope. Abweichung > X → User fragen (kein stiller Drift).
        # Der angepasste Scope (retained_terms) wird MITGELIEFERT, damit der
        # Rework-Loop ihn konkret übernehmen kann.
        if status == ClaimStatus.REFUTED:
            rework = rework_scope_deviation(claim)
            dev = rework["scope_deviation"]
            budget = max_scope_deviation()
            scores["rework"] = {
                "required": True,
                "adjusted_scope": rework["adjusted_scope"],
                "retained_terms": rework["retained_terms"],
                "dropped_terms": rework["dropped_terms"],
                "scope_deviation": dev,
                "max_scope_deviation": budget,
                "within_budget": dev <= budget,
                "requires_user_approval": dev > budget,
            }
        return scores


class EvidenceStore:
    """Persistence for Claims and Evidence."""
    
    def __init__(self, persistence: PersistenceLayer):
        self.persistence = persistence
        self.persistence.ensure_schema("evidence_store", self._create_schema)

    def _create_schema(self) -> None:
        self.persistence.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                claim_id TEXT PRIMARY KEY,
                project TEXT NOT NULL,
                statement TEXT NOT NULL,
                domain TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self.persistence.execute("""
            CREATE TABLE IF NOT EXISTS evidences (
                evidence_id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT NOT NULL,
                FOREIGN KEY(claim_id) REFERENCES claims(claim_id) ON DELETE CASCADE
            )
        """)
        self.persistence.execute("CREATE INDEX IF NOT EXISTS idx_claims_project ON claims(project)")
        self.persistence.execute("CREATE INDEX IF NOT EXISTS idx_evidences_claim ON evidences(claim_id)")

    def save_claim(self, claim: Claim) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self.persistence.transaction() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO claims (claim_id, project, statement, domain, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (claim.claim_id, claim.project, claim.statement, claim.domain, now))
            
            for ev in claim.evidences:
                conn.execute("""
                    INSERT OR IGNORE INTO evidences (evidence_id, claim_id, evidence_type, source, confidence, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    ev.evidence_id, 
                    ev.claim_id, 
                    ev.evidence_type.value, 
                    ev.source, 
                    ev.confidence, 
                    ev.timestamp, 
                    json.dumps(ev.metadata)
                ))

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        claim_row = self.persistence.fetchone("SELECT * FROM claims WHERE claim_id = ?", (claim_id,))
        if not claim_row:
            return None
            
        evidence_rows = self.persistence.fetchall("SELECT * FROM evidences WHERE claim_id = ?", (claim_id,))
        evidences = []
        for r in evidence_rows:
            evidences.append(Evidence(
                evidence_id=r["evidence_id"],
                claim_id=r["claim_id"],
                evidence_type=EvidenceType(r["evidence_type"]),
                source=r["source"],
                confidence=r["confidence"],
                timestamp=r["timestamp"],
                metadata=json.loads(r["metadata"])
            ))
            
        return Claim(
            claim_id=claim_row["claim_id"],
            project=claim_row["project"],
            statement=claim_row["statement"],
            domain=claim_row["domain"],
            evidences=evidences
        )

    def get_claims_by_project(self, project: str) -> List[Claim]:
        rows = self.persistence.fetchall("SELECT claim_id FROM claims WHERE project = ?", (project,))
        claims = []
        for r in rows:
            claim = self.get_claim(r["claim_id"])
            if claim:
                claims.append(claim)
        return claims

