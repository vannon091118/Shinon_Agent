"""
Agent Runtime Kernel — Knowledge Graph
v2: Domains 4.1-4.6 complete

4.1 Node/Relation Types + CRUD (existing)
4.2 Graph Traversal (existing)
4.3 Evidence Graph: link claims→facts→files, cross-reference
4.4 Impact Analysis: trace affected nodes when claim refuted
4.5 Pattern Detection: clusters, cycles, hotspots
4.6 Snapshot & Diff: serializable state, structural drift
"""

from __future__ import annotations
import json
import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from karma.core.persistence import PersistenceLayer, create_project_persistence


class NodeTypes:
    REPOSITORY   = "repository"
    MODULE       = "module"
    FILE         = "file"
    CLASS        = "class"
    DEPENDENCY   = "dependency"
    HISTORY      = "history"
    OWNER        = "owner"
    PROBLEM      = "problem"
    RISK         = "risk"
    # 4.3 Evidence Graph additions
    CLAIM        = "claim"
    FACT         = "fact"
    EVIDENCE     = "evidence"
    # 4.6 Snapshot
    SNAPSHOT     = "snapshot"


class RelationTypes:
    CONTAINS        = "contains"        # Repo→Module, Module→File, File→Class
    DEPENDS_ON      = "depends_on"      # Class→Class, Module→Module
    AUTHORED_BY     = "authored_by"     # File→Owner, History→Owner
    AFFECTS         = "affects"         # Problem→Class/File, Risk→Module
    HAS_HISTORY     = "has_history"     # File→History
    REVEALS         = "reveals"         # History→Problem
    MITIGATES       = "mitigates"       # Class→Risk
    # 4.3 Evidence Graph additions
    SUPPORTS        = "supports"        # Evidence→Claim
    REFUTES         = "refutes"         # Evidence→Claim
    DERIVED_FROM    = "derived_from"    # Claim→Fact, Fact→File
    CROSS_REFERENCES = "cross_references"  # Claim→Claim
    # 4.4 Impact
    IMPACTS         = "impacts"         # Refuted claim→affected node
    # 4.5 Pattern detection
    SIMILAR_TO      = "similar_to"      # Node→Node (cluster edges)
    HOTSPOT         = "hotspot"         # Node is a hotspot marker
    # 4.6 Snapshot
    SNAPSHOT_OF     = "snapshot_of"     # Snapshot→Node


# ─── 4.1-4.2: Core Graph (existing, enhanced) ──────────────────────────


class KnowledgeGraph:
    """KnowledgeGraph API — builds, queries, and analyzes the property graph."""

    def __init__(self, persistence: PersistenceLayer, project: str) -> None:
        self.persistence = persistence
        self.project = project

    # ── CRUD ──────────────────────────────────────────────────────

    def add_relation(
        self, source_type: str, source_id: str, relation_type: str,
        target_type: str, target_id: str, metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.persistence.add_relation(
            self.project, source_type, source_id, relation_type, target_type, target_id, metadata
        )

    def delete_relation(
        self, source_type: str, source_id: str, relation_type: str,
        target_type: str, target_id: str,
    ) -> bool:
        return self.persistence.delete_relation(
            self.project, source_type, source_id, relation_type, target_type, target_id
        )

    def get_outgoing(self, source_id: str, source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.persistence.get_relations(
            self.project, source_id=source_id, source_type=source_type
        )

    def get_incoming(self, target_id: str, target_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.persistence.get_relations(
            self.project, target_id=target_id, target_type=target_type
        )

    def get_related(self, node_id: str, relation_type: Optional[str] = None,
                    node_type: Optional[str] = None) -> List[Tuple[Dict[str, Any], str]]:
        outgoing = self.persistence.get_relations(
            self.project, source_id=node_id, source_type=node_type, relation_type=relation_type
        )
        incoming = self.persistence.get_relations(
            self.project, target_id=node_id, target_type=node_type, relation_type=relation_type
        )
        return [(r, "outgoing") for r in outgoing] + [(r, "incoming") for r in incoming]

    def traverse(self, start_id: str, max_depth: int = 3,
                 visited: Optional[Set[str]] = None) -> Dict[str, Any]:
        if visited is None:
            visited = set()
        if start_id in visited or max_depth < 0:
            return {}
        visited.add(start_id)
        outgoing = self.get_outgoing(start_id)
        nodes: Dict[str, Any] = {}
        edges: List[Dict[str, Any]] = []
        for r in outgoing:
            target_id = r["target_id"]
            edges.append({
                "source": start_id, "relation": r["relation_type"],
                "target": target_id, "target_type": r["target_type"],
                "metadata": r["metadata"],
            })
            subgraph = self.traverse(target_id, max_depth - 1, visited)
            if subgraph:
                edges.extend(subgraph.get("edges", []))
                nodes.update(subgraph.get("nodes", {}))
        nodes[start_id] = {"id": start_id}
        return {"nodes": nodes, "edges": edges}

    # ── 4.3: Evidence Graph ───────────────────────────────────────

    def link_claim_to_fact(self, claim_id: str, fact_id: str) -> None:
        """Link a claim to a supporting fact (DERIVED_FROM)."""
        self.add_relation(NodeTypes.CLAIM, claim_id, RelationTypes.DERIVED_FROM,
                          NodeTypes.FACT, fact_id)

    def link_evidence_to_claim(self, evidence_id: str, claim_id: str,
                                supports: bool = True) -> None:
        """Link evidence to a claim (SUPPORTS or REFUTES)."""
        rel = RelationTypes.SUPPORTS if supports else RelationTypes.REFUTES
        self.add_relation(NodeTypes.EVIDENCE, evidence_id, rel,
                          NodeTypes.CLAIM, claim_id)

    def cross_reference_claims(self, claim_a: str, claim_b: str) -> None:
        """Cross-reference two related claims."""
        self.add_relation(NodeTypes.CLAIM, claim_a, RelationTypes.CROSS_REFERENCES,
                          NodeTypes.CLAIM, claim_b)

    def get_evidence_chain(self, claim_id: str) -> Dict[str, Any]:
        """Get the full evidence chain for a claim: claim→facts→files→modules."""
        chain = {"claim": claim_id, "supporting": [], "refuting": [], "facts": [], "files": []}

        # Incoming from ALL node types (evidence, claims, facts can all link to claims)
        for rel, direction in self.get_related(claim_id, node_type=None):
            rtype = rel["relation_type"]
            src = rel.get("source_id", "")
            tgt = rel.get("target_id", "")
            
            if rtype == RelationTypes.SUPPORTS and tgt == claim_id:
                chain["supporting"].append(src)
            elif rtype == RelationTypes.REFUTES and tgt == claim_id:
                chain["refuting"].append(src)
            elif rtype == RelationTypes.DERIVED_FROM:
                # DERIVED_FROM: claim → fact or claim → file
                if src == claim_id:
                    chain["facts"].append(tgt)
                elif tgt == claim_id:
                    chain["facts"].append(src)

        return chain

    # ── 4.4: Impact Analysis ──────────────────────────────────────

    def trace_impact(self, claim_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """Trace all nodes affected when a claim is refuted.
        
        Traverses: claim→facts→files→modules→risk nodes,
        collecting all affected nodes and their dependency chains.
        """
        affected: Set[str] = set()
        chains: List[List[str]] = []

        def _trace(current: str, depth: int, path: List[str]) -> None:
            if depth > max_depth or current in path:
                return
            path = path + [current]
            affected.add(current)
            
            outgoing = self.get_outgoing(current)
            if not outgoing and depth > 0:
                chains.append(path)
            
            for r in outgoing:
                _trace(r["target_id"], depth + 1, path)

        _trace(claim_id, 0, [])

        # Also trace incoming: what depends on the affected nodes?
        for node_id in list(affected):
            for rel, _ in self.get_related(node_id):
                dep_id = rel.get("source_id") if rel.get("target_id") == node_id else rel.get("target_id")
                if dep_id and dep_id not in affected:
                    affected.add(dep_id)

        return {
            "claim_id": claim_id,
            "affected_nodes": sorted(affected),
            "affected_count": len(affected),
            "impact_chains": chains[:10],
            "depth": max_depth,
        }

    def get_blast_radius(self, file_id: str) -> Dict[str, Any]:
        """Calculate the blast radius of changes to a file.
        
        How many modules, classes, and dependencies would be affected?
        """
        subgraph = self.traverse(file_id, max_depth=2)
        
        files = sum(1 for n in subgraph.get("nodes", {}) if n.startswith("file:"))
        modules = sum(1 for n in subgraph.get("nodes", {}) if n.startswith("module:"))
        classes = sum(1 for n in subgraph.get("nodes", {}) if n.startswith("class:"))
        deps = sum(1 for e in subgraph.get("edges", [])
                   if e.get("relation") == RelationTypes.DEPENDS_ON)
        risks = sum(1 for e in subgraph.get("edges", [])
                    if e.get("target_type") == NodeTypes.RISK)
        
        return {
            "file": file_id,
            "edges": len(subgraph.get("edges", [])),
            "affected_files": files,
            "affected_modules": modules,
            "affected_classes": classes,
            "dependencies": deps,
            "risks": risks,
            "blast_score": deps * 2 + risks * 5 + files,  # Weighted score
        }

    # ── 4.5: Pattern Detection ────────────────────────────────────

    def find_clusters(self, node_type: str = NodeTypes.FILE,
                       relation: str = RelationTypes.DEPENDS_ON,
                       min_cluster_size: int = 2) -> List[List[str]]:
        """Find tightly-coupled clusters of nodes.
        
        Uses simple connected-components via breadth-first search on
        nodes of the given type connected by the given relation.
        """
        # Get all nodes of the given type
        all_relations = self.persistence.get_relations(self.project, relation_type=relation)
        
        # Build adjacency list
        adj: Dict[str, Set[str]] = defaultdict(set)
        for r in all_relations:
            if r["source_type"] == node_type and r["target_type"] == node_type:
                adj[r["source_id"]].add(r["target_id"])
                adj[r["target_id"]].add(r["source_id"])

        visited: Set[str] = set()
        clusters: List[List[str]] = []

        for node in adj:
            if node in visited:
                continue
            # BFS
            component: List[str] = []
            queue = [node]
            visited.add(node)
            while queue:
                current = queue.pop(0)
                component.append(current)
                for neighbor in adj[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            if len(component) >= min_cluster_size:
                clusters.append(sorted(component))

        return sorted(clusters, key=len, reverse=True)

    def find_cycles(self, node_type: str = NodeTypes.FILE,
                     relation: str = RelationTypes.DEPENDS_ON,
                     max_cycles: int = 20) -> List[List[str]]:
        """Detect cyclic dependencies in the graph.
        
        Uses DFS-based cycle detection on the adjacency graph.
        """
        all_relations = self.persistence.get_relations(self.project, relation_type=relation)
        
        adj: Dict[str, List[str]] = defaultdict(list)
        for r in all_relations:
            if r["source_type"] == node_type and r["target_type"] == node_type:
                adj[r["source_id"]].append(r["target_id"])

        cycles: List[List[str]] = []
        
        def _dfs(node: str, path: List[str], in_path: Set[str]) -> None:
            if len(cycles) >= max_cycles:
                return
            if node in in_path:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if len(cycle) >= 2:
                    cycles.append(cycle)
                return
            in_path.add(node)
            path.append(node)
            for neighbor in adj.get(node, []):
                _dfs(neighbor, path, in_path)
            path.pop()
            in_path.discard(node)

        for node in list(adj.keys()):
            if len(cycles) >= max_cycles:
                break
            _dfs(node, [], set())

        # Deduplicate (same cycle can be found from different start nodes)
        unique = []
        seen = set()
        for cycle in cycles:
            canonical = tuple(sorted(cycle[:-1]))
            if canonical not in seen:
                seen.add(canonical)
                unique.append(cycle)
        return unique[:max_cycles]

    def get_hotspots(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Identify hotspot nodes with the most problems, risks, and dependencies.
        
        Hotspot score = problem_count * 5 + risk_count * 3 + dependency_count * 1
        """
        all_relations = self.persistence.get_relations(self.project)
        
        # Count per node
        scores: Dict[str, Dict[str, int]] = defaultdict(lambda: {"problems": 0, "risks": 0, "deps": 0})
        
        for r in all_relations:
            target = r["target_id"]
            source = r["source_id"]
            
            if r["relation_type"] == RelationTypes.AFFECTS:
                if r["source_type"] == NodeTypes.PROBLEM:
                    scores[target]["problems"] += 1
                elif r["source_type"] == NodeTypes.RISK:
                    scores[target]["risks"] += 1
            elif r["relation_type"] == RelationTypes.DEPENDS_ON:
                scores[source]["deps"] += 1

        scored = []
        for node, counts in scores.items():
            hot = counts["problems"] * 5 + counts["risks"] * 3 + counts["deps"]
            if hot > 0:
                scored.append({
                    "node": node,
                    "hotspot_score": hot,
                    "problems": counts["problems"],
                    "risks": counts["risks"],
                    "dependencies": counts["deps"],
                })

        return sorted(scored, key=lambda x: x["hotspot_score"], reverse=True)[:top_n]

    # ── 4.6: Snapshot & Diff ──────────────────────────────────────

    def snapshot(self, label: str = "") -> Dict[str, Any]:
        """Create a serializable snapshot of the entire knowledge graph.
        
        Returns a JSON-serializable dict with all nodes, edges, and a
        deterministic hash for drift detection.
        """
        all_relations = self.persistence.get_relations(self.project)
        
        # Collect unique nodes
        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []
        
        for r in all_relations:
            sid = r["source_id"]; tid = r["target_id"]
            if sid not in nodes:
                nodes[sid] = {"id": sid, "type": r["source_type"]}
            if tid not in nodes:
                nodes[tid] = {"id": tid, "type": r["target_type"]}
            edges.append({
                "source": sid, "target": tid,
                "relation": r["relation_type"],
                "metadata": r.get("metadata"),
            })

        # Sort for deterministic output
        sorted_edges = sorted(edges, key=lambda e: (e["source"], e["target"], e["relation"]))
        sorted_nodes = dict(sorted(nodes.items()))

        snapshot_data = {
            "nodes": sorted_nodes,
            "edges": sorted_edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }
        
        # Deterministic hash
        hash_input = json.dumps(snapshot_data, sort_keys=True, ensure_ascii=False)
        snapshot_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        return {
            "label": label or datetime.now(timezone.utc).isoformat(),
            "project": self.project,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hash": snapshot_hash,
            "data": snapshot_data,
        }

    def diff_snapshots(self, snap_a: Dict[str, Any],
                        snap_b: Dict[str, Any]) -> Dict[str, Any]:
        """Diff two snapshots — detect structural drift.
        
        Returns added/removed nodes and edges, and a drift score.
        """
        a_nodes = set(snap_a["data"]["nodes"].keys())
        b_nodes = set(snap_b["data"]["nodes"].keys())
        
        a_edges = {(e["source"], e["target"], e["relation"]) for e in snap_a["data"]["edges"]}
        b_edges = {(e["source"], e["target"], e["relation"]) for e in snap_b["data"]["edges"]}

        added_nodes = sorted(b_nodes - a_nodes)
        removed_nodes = sorted(a_nodes - b_nodes)
        added_edges = sorted(b_edges - a_edges)
        removed_edges = sorted(a_edges - b_edges)

        total_changes = len(added_nodes) + len(removed_nodes) + len(added_edges) + len(removed_edges)
        total_size = max(len(a_nodes) + len(b_nodes) + len(a_edges) + len(b_edges), 1)
        drift_pct = round(total_changes / total_size * 100, 1)

        return {
            "hash_a": snap_a["hash"],
            "hash_b": snap_b["hash"],
            "hashes_match": snap_a["hash"] == snap_b["hash"],
            "nodes_added": len(added_nodes),
            "nodes_removed": len(removed_nodes),
            "edges_added": len(added_edges),
            "edges_removed": len(removed_edges),
            "total_changes": total_changes,
            "drift_pct": drift_pct,
            "added_nodes": added_nodes[:20],
            "removed_nodes": removed_nodes[:20],
            "added_edges": [list(e) for e in added_edges][:20],
            "removed_edges": [list(e) for e in removed_edges][:20],
            "stable": total_changes == 0,
        }

    def detect_drift(self, prev_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Take current snapshot and diff against a previous one."""
        current = self.snapshot()
        return self.diff_snapshots(prev_snapshot, current)
