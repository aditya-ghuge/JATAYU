"""
ResQRoute AI - Building Graph Module
====================================
Represents building floorplans as graphs with Rooms, Corridors, Junctions, and Exits.
Supports JSON import/export, dynamic crowd updates, exit availability toggles,
and provides seamless interoperability with NetworkX.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Set, Any
import networkx as nx


@dataclass
class ZoneNode:
    """Represents a discrete physical zone inside the building."""
    id: str
    name: str
    zone_type: str                  # "room", "corridor", "junction", "exit"
    is_exit: bool = False
    is_available: bool = True       # Can be disabled if an exit door is locked/collapsed
    crowd_count: float = 0.0        # Zone congestion level (0.0 to 100.0)
    capacity: int = 50
    floor: int = 1
    coordinates: Tuple[float, float] = (0.0, 0.0)  # (x, y) for UI rendering / mapping


@dataclass
class PathEdge:
    """Represents a walkable connection between two zones."""
    source: str
    target: str
    distance: float                 # Physical distance in meters
    is_blocked: bool = False        # Physical debris or locked security door
    bidirectional: bool = True


class BuildingGraph:
    """
    Graph-based spatial model of the facility.
    """

    def __init__(self, name: str = "ResQRoute Facility"):
        self.name = name
        self.nodes: Dict[str, ZoneNode] = {}
        self.edges: List[PathEdge] = []
        self._adjacency: Dict[str, Dict[str, PathEdge]] = {}

    def add_zone(
        self,
        zone_id: str,
        name: str,
        zone_type: str,
        is_exit: bool = False,
        is_available: bool = True,
        crowd_count: float = 0.0,
        coordinates: Tuple[float, float] = (0.0, 0.0)
    ) -> ZoneNode:
        """Register a node in the building graph."""
        node = ZoneNode(
            id=zone_id,
            name=name,
            zone_type=zone_type,
            is_exit=is_exit,
            is_available=is_available,
            crowd_count=crowd_count,
            coordinates=coordinates
        )
        self.nodes[zone_id] = node
        if zone_id not in self._adjacency:
            self._adjacency[zone_id] = {}
        return node

    def add_connection(
        self,
        source: str,
        target: str,
        distance: float,
        bidirectional: bool = True,
        is_blocked: bool = False
    ):
        """Register a walkable edge between two zones."""
        edge = PathEdge(
            source=source,
            target=target,
            distance=float(distance),
            is_blocked=is_blocked,
            bidirectional=bidirectional
        )
        self.edges.append(edge)

        # Update adjacency
        if source not in self._adjacency:
            self._adjacency[source] = {}
        self._adjacency[source][target] = edge

        if bidirectional:
            if target not in self._adjacency:
                self._adjacency[target] = {}
            reverse_edge = PathEdge(
                source=target,
                target=source,
                distance=float(distance),
                is_blocked=is_blocked,
                bidirectional=True
            )
            self._adjacency[target][source] = reverse_edge

    def get_neighbors(self, zone_id: str) -> List[Tuple[str, PathEdge]]:
        """Get all adjacent zones and edge details."""
        if zone_id not in self._adjacency:
            return []
        return [(neighbor, edge) for neighbor, edge in self._adjacency[zone_id].items()]

    def get_available_exits(self) -> List[str]:
        """Return list of exit node IDs that are currently available/open."""
        return [
            nid for nid, node in self.nodes.items()
            if node.is_exit and node.is_available
        ]

    def update_crowd_data(self, zone_id: str, crowd_count: float):
        """Update real-time crowd congestion (from CCTV / OpenCV or manual input)."""
        if zone_id in self.nodes:
            self.nodes[zone_id].crowd_count = max(0.0, float(crowd_count))

    def update_exit_status(self, exit_id: str, is_available: bool):
        """Toggle exit door availability (e.g. exit blocked by fire or locked)."""
        if exit_id in self.nodes:
            self.nodes[exit_id].is_available = bool(is_available)

    def set_edge_blockage(self, source: str, target: str, is_blocked: bool):
        """Mark an edge as blocked or cleared."""
        if source in self._adjacency and target in self._adjacency[source]:
            self._adjacency[source][target].is_blocked = is_blocked
        if target in self._adjacency and source in self._adjacency[target]:
            self._adjacency[target][source].is_blocked = is_blocked

    def to_networkx(self) -> nx.Graph:
        """Convert internal structure to NetworkX Graph for analysis and plotting."""
        G = nx.Graph()
        for nid, node in self.nodes.items():
            G.add_node(
                nid,
                name=node.name,
                zone_type=node.zone_type,
                is_exit=node.is_exit,
                is_available=node.is_available,
                crowd_count=node.crowd_count,
                pos=node.coordinates
            )
        for edge in self.edges:
            G.add_edge(
                edge.source,
                edge.target,
                distance=edge.distance,
                is_blocked=edge.is_blocked
            )
        return G

    def to_dict(self) -> Dict[str, Any]:
        """Export building layout to Python dictionary."""
        return {
            "name": self.name,
            "nodes": [asdict(n) for n in self.nodes.values()],
            "edges": [asdict(e) for e in self.edges]
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize layout to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildingGraph":
        """Reconstruct a building graph from dictionary."""
        building = cls(name=data.get("name", "Imported Facility"))
        for n in data.get("nodes", []):
            building.add_zone(
                zone_id=n["id"],
                name=n["name"],
                zone_type=n["zone_type"],
                is_exit=n.get("is_exit", False),
                is_available=n.get("is_available", True),
                crowd_count=n.get("crowd_count", 0.0),
                coordinates=tuple(n.get("coordinates", (0.0, 0.0)))
            )
        for e in data.get("edges", []):
            building.add_connection(
                source=e["source"],
                target=e["target"],
                distance=e["distance"],
                bidirectional=e.get("bidirectional", True),
                is_blocked=e.get("is_blocked", False)
            )
        return building

    @classmethod
    def from_json_file(cls, filepath: str) -> "BuildingGraph":
        """Load building graph from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


def create_sample_building() -> BuildingGraph:
    """
    Creates the reference building layout:
    - 5 Rooms: R1, R2, R3, R4, R5
    - 4 Corridors: C1, C2, C3, C4
    - 2 Exits: EXIT1 (East Wing), EXIT2 (West Wing)

    Topology Layout:
        R1 (Start Room) ───\
                            ├── C1 (North Hall) ─── C2 (East Hall) ─── EXIT1 (East Exit)
        R2 (Lab Room)   ───/        │                   │
                                    │                   │ (Cross bypass corridor)
        R3 (Office A)   ────────────┘                   │
                                                        │
        R4 (Office B)   ─── C3 (South Hall) ─── C4 (West Hall) ─── EXIT2 (West Exit)
        R5 (Storage)    ───/
    """
    b = BuildingGraph(name="ResQRoute AI Demo Complex")

    # 1. Rooms
    b.add_zone("R1", "Main Conference Room R1", "room", coordinates=(0, 4))
    b.add_zone("R2", "Hardware Lab R2", "room", coordinates=(0, 3))
    b.add_zone("R3", "Executive Office R3", "room", coordinates=(0, 2))
    b.add_zone("R4", "Server Room R4", "room", coordinates=(0, 1))
    b.add_zone("R5", "Storage & Utility R5", "room", coordinates=(0, 0))

    # 2. Corridors
    b.add_zone("C1", "North Main Corridor C1", "corridor", coordinates=(2, 3.5))
    b.add_zone("C2", "East Wing Hallway C2", "corridor", coordinates=(4, 3.5))
    b.add_zone("C3", "South Main Corridor C3", "corridor", coordinates=(2, 0.5))
    b.add_zone("C4", "West Wing Hallway C4", "corridor", coordinates=(4, 0.5))

    # 3. Exits
    b.add_zone("EXIT1", "Emergency Exit 1 (East Wing)", "exit", is_exit=True, coordinates=(6, 3.5))
    b.add_zone("EXIT2", "Emergency Exit 2 (West Wing)", "exit", is_exit=True, coordinates=(6, 0.5))

    # 4. Connections & Physical Distances (meters)
    # Room connections to corridors
    b.add_connection("R1", "C1", distance=5.0)
    b.add_connection("R2", "C1", distance=6.0)
    b.add_connection("R3", "C1", distance=7.0)
    b.add_connection("R4", "C3", distance=5.0)
    b.add_connection("R5", "C3", distance=6.0)

    # Corridor backbone network
    b.add_connection("C1", "C2", distance=8.0)
    b.add_connection("C1", "C3", distance=10.0)    # Vertical cross-corridor link
    b.add_connection("C2", "C4", distance=12.0)    # Alternate East-West connector bypass
    b.add_connection("C3", "C4", distance=8.0)

    # Exit access
    b.add_connection("C2", "EXIT1", distance=6.0)
    b.add_connection("C4", "EXIT2", distance=7.0)

    return b
