from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import KnowledgeBaseConfig, knowledge_base_config


@dataclass
class GraphSnapshot:
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: list[dict[str, Any]] = field(default_factory=list)
    adjacency: dict[str, set[str]] = field(default_factory=dict)


class GraphSearchService:
    """Reads the embedded GraphML index and exposes knowledge graph views."""

    def __init__(self, config: KnowledgeBaseConfig | None = None) -> None:
        self.config = config or knowledge_base_config
        self.graph_path = self.config.working_dir / "graph_chunk_entity_relation.graphml"
        self._snapshot: GraphSnapshot | None = None
        self._mtime: float | None = None

    def list_labels(self, *, limit: int = 120) -> list[str]:
        graph = self._load_graph()
        return sorted(graph.nodes.keys())[:limit]

    def popular_labels(self, *, limit: int = 24) -> list[dict[str, Any]]:
        graph = self._load_graph()
        rows = [
            {
                "label": node_id,
                "degree": len(graph.adjacency.get(node_id, set())),
                "entity_type": graph.nodes.get(node_id, {}).get("entity_type", "concept"),
            }
            for node_id in graph.nodes
        ]
        return sorted(rows, key=lambda row: row["degree"], reverse=True)[:limit]

    def search_labels(self, query: str, *, limit: int = 30) -> list[dict[str, Any]]:
        q = (query or "").strip().lower()
        if not q:
            return self.popular_labels(limit=limit)
        graph = self._load_graph()
        rows: list[dict[str, Any]] = []
        for node_id, props in graph.nodes.items():
            haystack = f"{node_id} {props.get('description', '')} {props.get('entity_type', '')}".lower()
            if q in haystack:
                rows.append(
                    {
                        "label": node_id,
                        "degree": len(graph.adjacency.get(node_id, set())),
                        "entity_type": props.get("entity_type", "concept"),
                        "description": str(props.get("description") or "")[:220],
                    }
                )
        return sorted(rows, key=lambda row: row["degree"], reverse=True)[:limit]

    def get_graph(self, label: str | None = None, *, max_depth: int = 2, max_nodes: int | None = None) -> dict[str, Any]:
        graph = self._load_graph()
        if not graph.nodes:
            return {"nodes": [], "edges": []}

        limit = min(max_nodes or self.config.max_graph_nodes, self.config.max_graph_nodes)
        root = self._resolve_label(label, graph) or next(iter(graph.nodes.keys()))
        selected: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(root, 0)])

        while queue and len(selected) < limit:
            current, depth = queue.popleft()
            if current in selected:
                continue
            selected.add(current)
            if depth >= max_depth:
                continue
            neighbors = sorted(graph.adjacency.get(current, set()), key=lambda node: len(graph.adjacency.get(node, set())), reverse=True)
            for neighbor in neighbors:
                if neighbor not in selected and len(selected) + len(queue) < limit:
                    queue.append((neighbor, depth + 1))

        nodes = [self._node_payload(node_id, graph.nodes[node_id], root) for node_id in selected if node_id in graph.nodes]
        edges = [
            edge
            for edge in graph.edges
            if edge.get("source") in selected and edge.get("target") in selected
        ][: max(0, limit * 2)]
        return {
            "root": root,
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "max_depth": max_depth,
                "source": "embedded_graph_index",
            },
        }

    def status(self) -> dict[str, Any]:
        graph = self._load_graph()
        return {
            "graph_path": str(self.graph_path),
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "popular_labels": self.popular_labels(limit=8),
        }

    def _resolve_label(self, label: str | None, graph: GraphSnapshot) -> str | None:
        if not label:
            return None
        if label in graph.nodes:
            return label
        lowered = label.lower()
        for node_id in graph.nodes:
            if node_id.lower() == lowered:
                return node_id
        for node_id in graph.nodes:
            if lowered in node_id.lower():
                return node_id
        return None

    def _node_payload(self, node_id: str, props: dict[str, Any], root: str) -> dict[str, Any]:
        return {
            "id": node_id,
            "label": node_id,
            "entity_type": props.get("entity_type") or "concept",
            "description": str(props.get("description") or "")[:420],
            "file_path": props.get("file_path") or "",
            "degree": int(props.get("degree") or 0),
            "root": node_id == root,
            "properties": props,
        }

    def _load_graph(self) -> GraphSnapshot:
        try:
            mtime = self.graph_path.stat().st_mtime
        except OSError:
            return GraphSnapshot()
        if self._snapshot is not None and self._mtime == mtime:
            return self._snapshot

        snapshot = GraphSnapshot()
        try:
            tree = ET.parse(self.graph_path)
        except ET.ParseError:
            self._snapshot = snapshot
            self._mtime = mtime
            return snapshot

        root = tree.getroot()
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}")[0].strip("{")
        ns = {"g": namespace} if namespace else {}
        key_map: dict[str, str] = {}
        key_xpath = "g:key" if namespace else "key"
        for key in root.findall(key_xpath, ns):
            key_id = key.attrib.get("id")
            attr_name = key.attrib.get("attr.name")
            if key_id and attr_name:
                key_map[key_id] = attr_name

        graph_xpath = ".//g:graph" if namespace else ".//graph"
        graph_el = root.find(graph_xpath, ns)
        if graph_el is None:
            self._snapshot = snapshot
            self._mtime = mtime
            return snapshot

        node_xpath = "g:node" if namespace else "node"
        edge_xpath = "g:edge" if namespace else "edge"
        data_xpath = "g:data" if namespace else "data"

        for node in graph_el.findall(node_xpath, ns):
            node_id = node.attrib.get("id")
            if not node_id:
                continue
            props: dict[str, Any] = {}
            for data in node.findall(data_xpath, ns):
                key = key_map.get(data.attrib.get("key", ""), data.attrib.get("key", ""))
                props[key] = data.text or ""
            props.setdefault("entity_id", node_id)
            snapshot.nodes[node_id] = props
            snapshot.adjacency.setdefault(node_id, set())

        for index, edge in enumerate(graph_el.findall(edge_xpath, ns)):
            source = edge.attrib.get("source")
            target = edge.attrib.get("target")
            if not source or not target:
                continue
            props: dict[str, Any] = {}
            for data in edge.findall(data_xpath, ns):
                key = key_map.get(data.attrib.get("key", ""), data.attrib.get("key", ""))
                props[key] = data.text or ""
            edge_payload = {
                "id": edge.attrib.get("id") or f"edge-{index}",
                "source": source,
                "target": target,
                "type": props.get("keywords") or "related",
                "description": str(props.get("description") or "")[:360],
                "weight": props.get("weight") or "",
                "file_path": props.get("file_path") or "",
                "properties": props,
            }
            snapshot.edges.append(edge_payload)
            snapshot.adjacency.setdefault(source, set()).add(target)
            snapshot.adjacency.setdefault(target, set()).add(source)

        for node_id in snapshot.nodes:
            snapshot.nodes[node_id]["degree"] = len(snapshot.adjacency.get(node_id, set()))

        self._snapshot = snapshot
        self._mtime = mtime
        return snapshot


graph_search_service = GraphSearchService()
