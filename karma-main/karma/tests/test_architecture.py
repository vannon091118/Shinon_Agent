#!/usr/bin/env python3
"""
KARMA Architecture Meta-Tests

These tests verify ARCHITECTURAL INVARIANTS, not code behavior.
They prevent the system from drifting into an Orakel.

Run: pytest karma/tests/test_architecture.py -v
"""

import pytest
from pathlib import Path
import sys

# Add karma to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from karma.domains.loader import create_loader


class TestDomainArchitecture:
    """Architectural invariants for Domain System."""

    def setup_method(self):
        self.loader = create_loader()

    def test_no_project_domain_in_core(self):
        """
        CRITICAL: Core domains must never reference project domains.
        
        If this fails, the global layer has been contaminated
        with project-specific knowledge.
        """
        self.loader.load_all()  # Load only global (no project)
        global_domains = list(self.loader._domains.keys())
        
        project_domains = [d for d in global_domains if d.startswith("syxcraft") or d.startswith("vigilguard")]
        assert len(project_domains) == 0, f"Project domains leaked into global: {project_domains}"

    def test_core_domains_are_global_scope_only(self):
        """Core layer must only contain global-scope domains."""
        self.loader.load_all()
        for domain_id, domain in self.loader._domains.items():
            if domain.layer == "core":
                assert domain.scope == "global", f"Core domain {domain_id} has scope {domain.scope}, must be global"

    def test_technology_domains_are_global_scope_only(self):
        """Technology layer must only contain global-scope domains."""
        self.loader.load_all()
        for domain_id, domain in self.loader._domains.items():
            if domain.layer == "technology":
                assert domain.scope == "global", f"Technology domain {domain_id} has scope {domain.scope}, must be global"

    def test_infrastructure_domains_are_global_scope_only(self):
        """Infrastructure layer must only contain global-scope domains."""
        self.loader.load_all()
        for domain_id, domain in self.loader._domains.items():
            if domain.layer == "infrastructure":
                assert domain.scope == "global", f"Infrastructure domain {domain_id} has scope {domain.scope}, must be global"

    def test_project_domains_are_project_scope_only(self):
        """Project layer must only contain project-scope domains."""
        for project in ["vigilguard", "syxcraft"]:
            self.loader = create_loader()
            self.loader.load_all(project)
            for domain_id, domain in self.loader._domains.items():
                if domain.layer == "project":
                    assert domain.scope == "project", f"Project domain {domain_id} has scope {domain.scope}, must be project"

    def test_project_isolation_vigilguard_no_syxcraft(self):
        """VigilGuard must never load SyxCraft domains."""
        self.loader.load_all("vigilguard")
        vigilguard_domains = set(self.loader._domains.keys())
        
        forbidden = {"syxcraft", "syxcraft-engine"}
        leaked = vigilguard_domains & forbidden
        assert len(leaked) == 0, f"VigilGuard leaked SyxCraft domains: {leaked}"

    def test_project_isolation_syxcraft_no_vigilguard(self):
        """SyxCraft must never load VigilGuard domains."""
        self.loader.load_all("syxcraft")
        syxcraft_domains = set(self.loader._domains.keys())
        
        forbidden = {"vigilguard-compliance"}
        leaked = syxcraft_domains & forbidden
        assert len(leaked) == 0, f"SyxCraft leaked VigilGuard domains: {leaked}"

    def test_no_cross_project_dependencies(self):
        """Project domains must not depend on other project domains."""
        self.loader.load_all("vigilguard")
        is_isolated, violations = self.loader.validate_project_isolation("vigilguard")
        assert is_isolated, f"Cross-project dependencies: {violations}"

        self.loader = create_loader()
        self.loader.load_all("syxcraft")
        is_isolated, violations = self.loader.validate_project_isolation("syxcraft")
        assert is_isolated, f"Cross-project dependencies: {violations}"

    def test_unknown_domain_never_falls_to_engine(self):
        """
        CRITICAL: Unknown domains must never silently fall back to 'engine'/'runtime'.
        
        This was the root cause of VigilGuard getting SyxCraft domains.
        """
        # The loader should NOT auto-map unknown to engine/runtime
        # This test verifies the current behavior
        domains = self.loader.load_all("vigilguard")
        
        # engine and runtime should only be loaded if they exist as valid domains
        # They should NOT be loaded as fallbacks for unknown requests
        # (This test documents the invariant; if fallbacks are added, this fails)
        assert "engine" not in domains or domains.get("engine").layer == "core"
        assert "runtime" not in domains or domains.get("runtime").layer == "core"

    def test_all_domains_have_evidence_rules(self):
        """Every domain must declare evidence_rules - no Orakel domains allowed."""
        for project in [None, "vigilguard", "syxcraft"]:
            self.loader = create_loader()
            self.loader.load_all(project)
            for domain_id, domain in self.loader._domains.items():
                assert domain.evidence_rules, f"Domain {domain_id} has no evidence_rules - would be an Orakel"
                assert len(domain.evidence_rules) > 0, f"Domain {domain_id} has empty evidence_rules"

    def test_all_domains_have_capabilities(self):
        """Every domain must declare capabilities - no skill-mapping domains."""
        for project in [None, "vigilguard", "syxcraft"]:
            self.loader = create_loader()
            self.loader.load_all(project)
            for domain_id, domain in self.loader._domains.items():
                assert domain.capabilities, f"Domain {domain_id} has no capabilities"
                assert len(domain.capabilities) > 0, f"Domain {domain_id} has empty capabilities"

    def test_all_domains_have_ownership(self):
        """Every domain must declare ownership for governance."""
        for project in [None, "vigilguard", "syxcraft"]:
            self.loader = create_loader()
            self.loader.load_all(project)
            for domain_id, domain in self.loader._domains.items():
                assert domain.ownership, f"Domain {domain_id} has no ownership"
                assert "mutable_by" in domain.ownership, f"Domain {domain_id} ownership missing mutable_by"
                assert len(domain.ownership["mutable_by"]) > 0, f"Domain {domain_id} has empty mutable_by"

    def test_domain_version_format(self):
        """All domains must use semantic versioning."""
        import re
        semver_pattern = re.compile(r'^\d+\.\d+\.\d+$')
        for project in [None, "vigilguard", "syxcraft"]:
            self.loader = create_loader()
            self.loader.load_all(project)
            for domain_id, domain in self.loader._domains.items():
                assert semver_pattern.match(domain.version), f"Domain {domain_id} version '{domain.version}' not semver"

    def test_layer_order_respected(self):
        """Load order must respect layer hierarchy: core -> technology -> infrastructure -> project."""
        for project in [None, "vigilguard", "syxcraft"]:
            self.loader = create_loader()
            self.loader.load_all(project)
            
            layer_order = ["core", "technology", "infrastructure", "project"]
            loaded_layers = []
            for domain in sorted(self.loader._domains.values(), key=lambda d: layer_order.index(d.layer)):
                loaded_layers.append(domain.layer)
            
            # Verify ordering
            for i in range(len(loaded_layers) - 1):
                assert layer_order.index(loaded_layers[i]) <= layer_order.index(loaded_layers[i+1]), \
                    f"Layer order violated: {loaded_layers}"

    def test_global_domains_have_no_project_deps(self):
        """Global domains must never depend on project domains."""
        self.loader.load_all()
        for domain_id, domain in self.loader._domains.items():
            if domain.scope == "global":
                for dep in domain.depends_on:
                    # Check if dependency is a project domain
                    assert not dep.startswith("syxcraft"), f"Global domain {domain_id} depends on SyxCraft: {dep}"
                    assert not dep.startswith("vigilguard"), f"Global domain {domain_id} depends on VigilGuard: {dep}"

    def test_schema_validates_all_domains(self):
        """All domain files must pass JSON Schema validation."""
        domains_root = Path(__file__).parent.parent / "karma" / "domains"
        loader = create_loader(domains_root)
        
        # This will fail if any domain is invalid
        loader.load_all("vigilguard")
        loader.load_all("syxcraft")
        
        # Also test global only
        loader2 = create_loader(domains_root)
        loader2.load_all()  # No project
        
        assert True  # If we get here, all validation passed


class TestDispatcherArchitecture:
    """Architectural invariants for Dispatcher/Skill Resolution."""

    def test_no_hardcoded_domain_to_skill_mapping(self):
        """
        CRITICAL: Dispatcher must NOT have hardcoded domain_to_group mapping.
        
        Old code had:
            domain_to_group = {"engine": "syxcraft", "repository": "quality"}
            
        This test fails if that pattern exists.
        """
        import karma.cli as cli_module
        import inspect
        
        source = inspect.getsource(cli_module)
        
        # These patterns must NOT exist
        forbidden_patterns = [
            'domain_to_group',
            'domain_to_skill',
            '"engine": "syxcraft"',
            '"runtime": "syxcraft"',
            '"save": "syxcraft"',
        ]
        
        for pattern in forbidden_patterns:
            assert pattern not in source, f"Hardcoded mapping found in cli.py: {pattern}"

    def test_dispatcher_uses_loader(self):
        """Dispatcher should use DomainLoader for skill resolution."""
        import karma.cli as cli_module
        import inspect
        
        source = inspect.getsource(cli_module)
        
        # Should use loader or capability resolution
        assert "DomainLoader" in source or "resolve_skills" in source or "capabilities" in source, \
            "Dispatcher doesn't use DomainLoader for skill resolution"

    def test_no_fallback_to_engine_runtime(self):
        """
        CRITICAL: Dispatcher must NOT fallback to engine/runtime for unknown domains.
        
        Old behavior: _match_domains returns {"engine", "runtime"} on no match.
        This test ensures that pattern is removed.
        """
        import karma.cli as cli_module
        import inspect
        
        source = inspect.getsource(cli_module)
        
        # The fallback pattern must not exist
        forbidden = [
            'matched = {"engine", "runtime"}',
            'matched = {\"engine\", \"runtime\"}',
            'fallback.*engine.*runtime',
        ]
        
        for pattern in forbidden:
            assert pattern not in source, f"Fallback to engine/runtime found: {pattern}"


class TestEvidenceArchitecture:
    """Architectural invariants for Evidence Layer."""

    def test_evidence_is_immutable(self):
        """
        Evidence objects must be immutable after creation.
        
        No setattr on confidence, type, or source after __init__.
        """
        from karma.core.evidence import Evidence
        
        ev = Evidence.create(
            claim_id="test",
            evidence_type="source",
            source="test",
            confidence=0.5
        )
        
        # Verify no public setters for core fields
        assert not hasattr(Evidence, "confidence") or not hasattr(Evidence.confidence, "setter"), \
            "Evidence.confidence should not have a setter"
        assert not hasattr(Evidence, "evidence_type") or not hasattr(Evidence.evidence_type, "setter"), \
            "Evidence.evidence_type should not have a setter"
        assert not hasattr(Evidence, "source") or not hasattr(Evidence.source, "setter"), \
            "Evidence.source should not have a setter"

    def test_claim_requires_evidence(self):
        """
        Claims must not be creatable without evidence path.
        
        A claim without evidence is a belief, not a Claim.
        """
        from karma.core.evidence import Claim, Evidence, EvidenceType
        
        # Claim creation should work but status should be UNVERIFIED
        claim = Claim.create("test-project", "Test claim", "test")
        
        # Initially no evidence
        assert len(claim.evidences) == 0
        
        # Status should be UNVERIFIED
        from karma.core.evidence import ConfidenceResolver
        result = ConfidenceResolver.resolve(claim)
        assert result["status"] == "unverified", f"Claim without evidence should be unverified, got {result['status']}"

    def test_resolver_requires_minimum_evidence(self):
        """ConfidenceResolver must require minimum evidence for CONFIRMED."""
        from karma.core.evidence import Claim, Evidence, EvidenceType, ConfidenceResolver
        
        claim = Claim.create("test", "Has tests", "quality")
        
        # Add single SOURCE evidence (low confidence)
        claim.evidences.append(Evidence.create(
            claim_id=claim.claim_id,
            evidence_type=EvidenceType.SOURCE,
            source="README",
            confidence=0.4
        ))
        
        result = ConfidenceResolver.resolve(claim)
        assert result["status"] in ["unverified", "supported"], \
            f"Single weak evidence should not CONFIRM, got {result['status']}"

    def test_conflict_detection_works(self):
        """Resolver must detect SOURCE+RUNTIME conflicts as CONFLICTED."""
        from karma.core.evidence import Claim, Evidence, EvidenceType, ConfidenceResolver
        
        claim = Claim.create("test", "Works in prod", "runtime")
        
        # Add positive SOURCE (doc says it works)
        claim.evidences.append(Evidence.create(
            claim_id=claim.claim_id,
            evidence_type=EvidenceType.SOURCE,
            source="docs",
            confidence=0.5
        ))
        
        # Add negative RUNTIME (actually fails)
        claim.evidences.append(Evidence.create(
            claim_id=claim.claim_id,
            evidence_type=EvidenceType.RUNTIME,
            source="integration_test",
            confidence=0.0  # Failed
        ))
        
        result = ConfidenceResolver.resolve(claim)
        assert result["status"] == "conflicted", f"SOURCE+RUNTIME conflict should be CONFLICTED, got {result['status']}"

    def test_refuted_verdict_exists(self):
        """ClaimStatus must have an active REFUTED verdict (not only passive unverified)."""
        from karma.core.evidence import ClaimStatus
        assert hasattr(ClaimStatus, "REFUTED"), "ClaimStatus must expose REFUTED"
        assert ClaimStatus.REFUTED.value == "refuted"

    def test_negative_runtime_without_support_is_refuted(self):
        """Negative runtime evidence with NO positive support → REFUTED (active rejection)."""
        from karma.core.evidence import Claim, Evidence, EvidenceType, ConfidenceResolver

        claim = Claim.create("test", "The adapter is transactional", "runtime")
        claim.evidences.append(Evidence.create(
            claim_id=claim.claim_id,
            evidence_type=EvidenceType.RUNTIME,
            source="integration_test",
            confidence=0.0,  # FAILED
            metadata={"probe_name": "test_adapter_transactional", "result": "FAIL"},
        ))

        result = ConfidenceResolver.resolve(claim)
        assert result["status"] == "refuted", f"Expected REFUTED, got {result['status']}"

    def test_refuted_produces_rework_with_scope_budget(self):
        """Refuted claims must return a rework directive with a scope-deviation budget.

        Kein Hard-Reject: der Rework trägt scope_deviation, max_scope_deviation,
        within_budget und requires_user_approval.
        """
        from karma.core.evidence import Claim, Evidence, EvidenceType, ConfidenceResolver

        claim = Claim.create("test", "The adapter is transactional", "runtime")
        claim.evidences.append(Evidence.create(
            claim_id=claim.claim_id,
            evidence_type=EvidenceType.RUNTIME,
            source="integration_test",
            confidence=0.0,
            metadata={"probe_name": "test_adapter_transactional", "result": "FAIL"},
        ))

        result = ConfidenceResolver.resolve(claim)
        rework = result.get("rework")
        assert rework is not None, "Refuted claim must carry a rework directive"
        assert rework["required"] is True
        assert isinstance(rework["scope_deviation"], float)
        assert isinstance(rework["max_scope_deviation"], float)
        assert isinstance(rework["within_budget"], bool)
        assert isinstance(rework["requires_user_approval"], bool)

    def test_scope_deviation_over_budget_requires_user(self):
        """Scope deviation beyond budget must require user approval (no silent drift)."""
        from karma.core.evidence import (
            Claim, Evidence, EvidenceType, ConfidenceResolver,
            scope_deviation, DEFAULT_MAX_SCOPE_DEVIATION,
        )

        # Der einzige RUNTIME-Test deckt NICHTS vom Claim ab (disjunkt) →
        # rework_scope_deviation = 1.0 > Budget → requires_user_approval.
        claim = Claim.create("test", "The adapter is transactional", "runtime")
        claim.evidences.append(Evidence.create(
            claim_id=claim.claim_id,
            evidence_type=EvidenceType.RUNTIME,
            source="integration_test",
            confidence=0.0,
            metadata={"probe_name": "test_adapter_transactional", "result": "FAIL"},
        ))

        result = ConfidenceResolver.resolve(claim)
        assert result["status"] == "refuted", f"Expected REFUTED, got {result['status']}"
        rework = result["rework"]
        assert rework["requires_user_approval"] is True, \
            f"Full scope loss must require user approval, got {rework}"
        assert rework["within_budget"] is False
        assert rework["scope_deviation"] > DEFAULT_MAX_SCOPE_DEVIATION

        # scope_deviation ist deterministisch: identisch → 0.0, disjunkt → 1.0
        assert scope_deviation("abc def", "abc def") == 0.0
        assert scope_deviation("abc def", "xyz qrs") == 1.0




class TestEntailmentGateArchitecture:
    """Architectural invariants for the Entailment Gate.

    Background: the resolver refuses to vote positive on any evidence that
    does not ENTAIL the claim. Without this gate the system becomes a
    "digital priest" — 'there is a test, therefore it must be true' —
    laundering low-quality, off-topic, or self-attesting evidence into
    CONFIRMED/SUPPORTED verdicts. These cases pin the gate so it
    cannot regress into a generic confidence aggregator.
    """

    def _claim(self, statement: str, project: str = "rt"):
        from karma.core.evidence import Claim
        return Claim.create(project=project, statement=statement, domain="test")



class TestEntailmentGateArchitecture:
    """Architectural invariants for the Entailment Gate.
    Pin the gate so the resolver refuses to vote positive on any
    evidence that does not ENTAIL the claim.
    """

    def _claim(self, statement: str, project: str = "rt"):
        from karma.core.evidence import Claim
        return Claim.create(project=project, statement=statement, domain="test")



class TestEntailmentGateArchitecture:
    """Architectural invariants for the Entailment Gate.

    Background: the resolver refuses to vote positive on any evidence that
    does not ENTAIL the claim. Without this gate the system becomes a
    "digital priest" — 'there is a test, therefore it must be true' —
    laundering low-quality, off-topic, or self-attesting evidence into
    CONFIRMED/SUPPORTED verdicts. These five cases pin the gate so it
    cannot regress into a generic confidence aggregator.
    """

    def _claim(self, statement: str, project: str = "rt"):
        from karma.core.evidence import Claim
        return Claim.create(project=project, statement=statement, domain="test")

    def test_entailment_gate_blocks_laundering(self):
        """Evidence whose declaration shares a SUBJECT term but not the
        HEAD/predicate term with the claim MUST NOT entail. Classic
        RT-02 laundering attempt: a passing test that merely checks
        'X exists' cannot confirm 'X is deterministic'.

        Lock-in invariant: entails()==False even though shared > 0
        (subject overlap), and the resolver's REASON must explicitly
        name 'head term' so a future regression cannot silently
        downgrade 'subject-only' to 'covered'."""
        from karma.core.evidence import (
            Evidence, EvidenceType, entailment_report, ConfidenceResolver,
        )
        claim = self._claim("Component X is deterministic")
        ev = Evidence.create(
            claim_id=claim.claim_id,
            evidence_type=EvidenceType.TEST,
            source="internal_test",
            confidence=0.95,
            metadata={"test_name": "test_component_x_exists", "result": "PASS"},
        )

        claim.evidences.append(ev)
        report = entailment_report(ev, claim)
        assert report["entails"] is False, (
            f"laundering attempt: 'exists' must NOT entail 'is deterministic', "
            f"got entails={report['entails']!r}"
        )
        # Reason must mention head term — future regressions that drop the
        # predicate guard will change this string and be detected.
        assert "head term" in report["reason"], (
            f"reason must name 'head term' to be auditable, got {report['reason']!r}"
        )

        verdict = ConfidenceResolver.resolve(claim)
        # Resolver must surface entailment_rejected so RT oracles can see
        # what was silently dropped.
        assert verdict["status"] not in ("supported", "confirmed"), (
            f"laundering must NOT produce truth-verdict, got {verdict['status']!r}"
        )
        assert verdict.get("entailment_rejected"), (
            "rejected evidence must be logged in entailment_rejected[]"
        )

    # ── Case 2: bypass without declaration ──────────────────────────

    def test_entailment_gate_blocks_bypass_without_declaration(self):
        """Empirical positive evidence (TEST/RUNTIME/REPLAY with high
        confidence) WITHOUT a metadata declaration MUST NOT entail.

        The alternative — letting high-confidence empirical evidence in
        just because confidence is high — would let any green test
        with a self-attesting name pass through as 'covered' even when
        it doesn't talk about the claim. This is the most common bypass
        attempt: drop the declaration field, hope the resolver
        ignores the absence."""
        from karma.core.evidence import (
            Evidence, EvidenceType, entailment_report, ConfidenceResolver,
        )
        claim = self._claim("The build pipeline prints version on every run")
        ev = Evidence.create(
            claim_id=claim.claim_id,
            evidence_type=EvidenceType.RUNTIME,
            source="integration_test",
            confidence=0.99,  # high confidence — bypass attempt
            metadata={"result": "PASS"},
            # No declaration keys at all — bypass attempt.
            # "probe_name" / "name" / "description" would declare a subject;
            # omitting them strips the verifier of any audit trail for
            # what it covers. (We keep "result" as a non-declaration field
            # so the evidence still has a payload — just not a verifiable one.)
        )

        claim.evidences.append(ev)
        report = entailment_report(ev, claim)
        assert report["entails"] is False, (
            f"positive empirical evidence without declaration must NOT entail, "
            f"got entails={report['entails']!r}"
        )
        # Reason must be explicit about empirical-positive-without-declaration
        # so audit trail can't confuse this with the lenient-source case.
        assert "empirical positive evidence without declaration" in report["reason"], (
            f"reason must name 'empirical positive evidence without declaration' "
            f"to be auditable, got {report['reason']!r}"
        )

        verdict = ConfidenceResolver.resolve(claim)
        assert verdict["status"] != "supported", (
            f"bypass must NOT produce SUPPORTED, got {verdict['status']!r}"
        )
        assert verdict["status"] != "confirmed", (
            f"bypass must NOT produce CONFIRMED, got {verdict['status']!r}"
        )

    # ── Case 2b: lenient-source-without-declaration is allowed ───────

    def test_entailment_gate_lenient_source_without_declaration_is_allowed(self):
        """SOURCE / HUMAN evidence without declaration uses the
        LENIENT pass-through (entails=True). Empirical evidence does
        NOT. This asymmetry is intentional — SOURCE without metadata
        cannot be audited, but is treated as positive signal because
        stripping source attestation is harder than skipping test
        metadata.

        Lock-in: the asymmetry is preserved. If someone removes the
        asymmetric handling, SRC + high confidence test both go to
        either branch — that's a regression."""
        from karma.core.evidence import (
            Evidence, EvidenceType, entailment_report,
        )
        # Pin of the asymmetry: the lenient path applies ONLY to
        # SOURCE / HUMAN (and to empirical-NEGATIVE evidence). If a
        # refactor removes this branch, the test below must fail.
        claim = self._claim("System has documented retry strategy")
        ev = Evidence.create(
            claim_id=claim.claim_id,
            evidence_type=EvidenceType.SOURCE,
            source="architecture_doc",
            confidence=0.6,
            # No declaration keys.
        )

        claim.evidences.append(ev)
        report = entailment_report(ev, claim)
        assert report["entails"] is True, (
            f"SOURCE without declaration MUST take the lenient path "
            f"(entails=True), got entails={report['entails']!r} reason={report['reason']!r}"
        )
        assert "lenient" in report["reason"].lower(), (
            f"reason must mention 'lenient' so the asymmetric path is auditable, "
            f"got {report['reason']!r}"
        )

    # ── Case 3: legitimate case ──────────────────────────────────────

    def test_entailment_gate_accepts_legitimate_match(self):
        """Evidence whose declaration matches ALL content-terms of the
        claim (or at least the head term) MUST entail. This is the
        positive control: without a working green path, every test
        might lock into 'always False' and silently block legitimate
        signals."""
        from karma.core.evidence import (
            Evidence, EvidenceType, entailment_report, ConfidenceResolver,
        )
        claim = self._claim("Component X is deterministic")
        # Declaration shares ALL three claim terms: component, x, deterministic.
        ev = Evidence.create(
            claim_id=claim.claim_id,
            evidence_type=EvidenceType.TEST,
            source="internal_test",
            confidence=0.9,
            metadata={"test_name": "test_component_x_deterministic", "result": "PASS"},
        )

        claim.evidences.append(ev)
        report = entailment_report(ev, claim)
        assert report["entails"] is True, (
            f"legitimate declaration must entail, got entails={report['entails']!r} "
            f"reason={report['reason']!r} shared={report['shared']!r}"
        )
        assert report["reason"] == "covered", (
            f"legitimate case must report reason='covered', got {report['reason']!r}"
        )

        verdict = ConfidenceResolver.resolve(claim)
        # TEST limit is 0.7 → mapped overall confidence at least 0.7 → CONFIRMED.
        assert verdict["status"] == "confirmed", (
            f"legitimate entailment must CONFIRM, got {verdict['status']!r}"
        )
        assert verdict.get("entailment_rejected") == [], (
            f"legitimate evidence must NOT be in entailment_rejected, "
            f"got {verdict.get('entailment_rejected')!r}"
        )

    # ── Case 4: disjunction ──────────────────────────────────────────

    def test_entailment_gate_rejects_disjoint(self):
        """Evidence whose declaration shares ZERO content-terms with the
        claim MUST NOT entail. This is the strongest rejection path:
        'disjoint (no shared terms)'. Without it, two unrelated areas
        could accidentally cross-pollute verdicts just because they
        both happen to be tests."""
        from karma.core.evidence import (
            Evidence, EvidenceType, entailment_report, ConfidenceResolver,
        )
        claim = self._claim("Authentication via OAuth works in production")
        # Declaration has zero overlap with 'authentication', 'oauth', 'works',
        # 'production' — talks entirely about an unrelated component.
        ev = Evidence.create(
            claim_id=claim.claim_id,
            evidence_type=EvidenceType.TEST,
            source="internal_test",
            confidence=0.9,
            metadata={"test_name": "test_database_connection_retry", "result": "PASS"},
        )

        claim.evidences.append(ev)
        report = entailment_report(ev, claim)
        assert report["entails"] is False, (
            f"disjoint evidence must NOT entail, got entails={report['entails']!r}"
        )
        # Reason must explicitly name 'disjoint' so the rejection's strength
        # is auditable — strong rejections and weak rejections must NOT
        # collapse into a single bucket.
        assert report["reason"] == "disjoint (no shared terms)", (
            f"disjoint reason must be exact so strong-vs-weak rejections don't "
            f"collapse into a single bucket, got {report['reason']!r}"
        )
        assert report["shared"] == [], (
            f"disjoint evidence must report empty shared list, "
            f"got {report['shared']!r}"
        )

        verdict = ConfidenceResolver.resolve(claim)
        assert verdict["status"] == "unverified", (
            f"disjoint evidence plus no other support must be unverified, "
            f"got {verdict['status']!r}"
        )


class TestKnowledgeGraphArchitecture:

    """Architectural invariants for Knowledge Graph."""

    def test_edges_require_evidence_ids(self):
        """
        Graph edges must carry evidence_ids.
        
        An edge without evidence is an assertion, not knowledge.
        """
        # This test documents the requirement.
        # Implementation will fail until Graph stores evidence_ids.
        from karma.core.knowledge_graph import KnowledgeGraph
        import inspect
        
        source = inspect.getsource(KnowledgeGraph.add_relation) if hasattr(KnowledgeGraph, 'add_relation') else ""
        
        # Should have evidence_ids parameter
        assert "evidence" in source.lower() or "evidence_id" in source.lower(), \
            "KnowledgeGraph.add_relation should accept evidence_ids"


class TestProjectArchitecture:
    """Architectural invariants for Project System."""

    def test_project_profile_exists(self):
        """Every onboarded project must have a project.json profile."""
        from karma.core.persistence import create_persistence
        
        p = create_persistence()
        # This will fail until project profiles are implemented
        # p.get_project_profile("vigilguard")
        pass  # Placeholder until implemented

    def test_onboarding_creates_claims(self):
        """
        Onboarding scanner must create Claim objects, not just set domains.
        
        Domain selection without Claims is just keyword matching.
        """
        pass  # Placeholder until onboarding implemented


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])