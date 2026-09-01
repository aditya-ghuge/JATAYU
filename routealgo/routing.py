"""
ResQRoute AI - Routing Engine Module
====================================
Implements dynamic Dijkstra pathfinding, multi-exit evaluation,
cost breakdown calculations, explainability generation, and real-time rerouting.
"""

import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from config import (
    COST_WEIGHTS,
    IMPASSABLE_COST_PENALTY,
    REROUTE_THRESHOLD_DELTA,
    RiskState
)
from building import BuildingGraph, PathEdge, ZoneNode
from sensor_manager import SensorManager
from risk_engine import RiskEngine, ZoneRiskReport


@dataclass
class EdgeCostBreakdown:
    """Detailed cost breakdown for traversing a single edge."""
    source: str
    target: str
    distance: float
    distance_cost: float
    risk_score: float
    risk_cost: float
    crowd_count: float
    crowd_cost: float
    uncertainty_score: float
    uncertainty_cost: float
    total_edge_cost: float
    is_impassable: bool = False
    penalty_reason: str = ""


@dataclass
class RouteResult:
    """Complete evacuation route result with explainability."""
    route: List[str]
    exit: Optional[str]
    total_cost: float
    risk_level: str
    reason: str
    is_feasible: bool = True
    edge_breakdowns: List[EdgeCostBreakdown] = field(default_factory=list)
    zone_reports: Dict[str, ZoneRiskReport] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to clean JSON-serializable dictionary."""
        return {
            "route": self.route,
            "exit": self.exit,
            "total_cost": round(self.total_cost, 2),
            "risk_level": self.risk_level,
            "reason": self.reason,
            "is_feasible": self.is_feasible,
            "cost_breakdown": [
                {
                    "from": eb.source,
                    "to": eb.target,
                    "distance_cost": round(eb.distance_cost, 2),
                    "risk_cost": round(eb.risk_cost, 2),
                    "crowd_cost": round(eb.crowd_cost, 2),
                    "uncertainty_cost": round(eb.uncertainty_cost, 2),
                    "edge_cost": round(eb.total_edge_cost, 2),
                    "impassable": eb.is_impassable
                }
                for eb in self.edge_breakdowns
            ]
        }


def calculate_edge_cost(
    source_id: str,
    target_id: str,
    edge: PathEdge,
    building: BuildingGraph,
    sensor_manager: SensorManager,
    risk_engine: RiskEngine
) -> EdgeCostBreakdown:
    """
    Computes the dynamic traversal cost for an edge (source -> target).
    Formula:
      total_cost = distance * W_DISTANCE + risk * W_RISK + crowd * W_CROWD + uncertainty * W_UNCERTAINTY
    Penalizes impassable zones (CRITICAL risk, offline/blocked exits, physical debris).
    """
    w_dist = COST_WEIGHTS["W_DISTANCE"]
    w_risk = COST_WEIGHTS["W_RISK"]
    w_crowd = COST_WEIGHTS["W_CROWD"]
    w_unc = COST_WEIGHTS["W_UNCERTAINTY"]

    # Target node properties
    target_node: ZoneNode = building.nodes.get(target_id)
    target_risk_report: ZoneRiskReport = risk_engine.calculate_zone_risk(target_id, sensor_manager)

    dist = edge.distance
    distance_cost = dist * w_dist

    risk_score = target_risk_report.risk_score
    risk_cost = risk_score * w_risk

    crowd_count = target_node.crowd_count if target_node else 0.0
    crowd_cost = crowd_count * w_crowd

    uncertainty_score = target_risk_report.uncertainty_score
    uncertainty_cost = uncertainty_score * w_unc

    base_cost = distance_cost + risk_cost + crowd_cost + uncertainty_cost

    # Check for blocking conditions
    is_impassable = False
    penalty_reason = ""

    if edge.is_blocked:
        is_impassable = True
        penalty_reason = f"Edge {source_id}->{target_id} is physically blocked by debris/doors."
    elif target_node and target_node.is_exit and not target_node.is_available:
        is_impassable = True
        penalty_reason = f"Exit {target_id} is marked UNAVAILABLE/LOCKED."
    elif target_risk_report.is_critical:
        is_impassable = True
        penalty_reason = f"Target zone {target_id} is CRITICAL / LETHAL hazard ({risk_score:.1f}% risk)."

    total_cost = (base_cost + IMPASSABLE_COST_PENALTY) if is_impassable else base_cost

    return EdgeCostBreakdown(
        source=source_id,
        target=target_id,
        distance=dist,
        distance_cost=distance_cost,
        risk_score=risk_score,
        risk_cost=risk_cost,
        crowd_count=crowd_count,
        crowd_cost=crowd_cost,
        uncertainty_score=uncertainty_score,
        uncertainty_cost=uncertainty_cost,
        total_edge_cost=total_cost,
        is_impassable=is_impassable,
        penalty_reason=penalty_reason
    )


class RoutingEngine:
    """
    Core Dijkstra-based pathfinding engine with explainability and dynamic rerouting.
    """

    def __init__(self, risk_engine: Optional[RiskEngine] = None):
        self.risk_engine = risk_engine or RiskEngine()

    def find_safest_route(
        self,
        building: BuildingGraph,
        start_zone: str,
        sensor_manager: SensorManager
    ) -> RouteResult:
        """
        Executes Dijkstra algorithm to locate the lowest-cost safe evacuation route
        from start_zone to the best available exit.
        """
        if start_zone not in building.nodes:
            return RouteResult(
                route=[],
                exit=None,
                total_cost=float("inf"),
                risk_level="UNKNOWN",
                reason=f"Start zone '{start_zone}' does not exist in building topology.",
                is_feasible=False
            )

        available_exits = set(building.get_available_exits())
        if not available_exits:
            return RouteResult(
                route=[],
                exit=None,
                total_cost=float("inf"),
                risk_level="CRITICAL",
                reason="No emergency exits are currently available or reachable.",
                is_feasible=False
            )

        # Min-heap priority queue: (cumulative_cost, current_zone, path_list, edge_breakdowns)
        queue: List[Tuple[float, str, List[str], List[EdgeCostBreakdown]]] = []
        heapq.heappush(queue, (0.0, start_zone, [start_zone], []))

        # Best cost tracker to avoid cycles and redundant paths
        min_costs: Dict[str, float] = {start_zone: 0.0}

        # Track evaluated candidates for all exits
        candidate_routes: Dict[str, Tuple[float, List[str], List[EdgeCostBreakdown]]] = {}

        while queue:
            curr_cost, curr_zone, path, breakdowns = heapq.heappop(queue)

            if curr_cost > min_costs.get(curr_zone, float("inf")):
                continue

            # If an exit is reached
            if curr_zone in available_exits:
                if curr_zone not in candidate_routes or curr_cost < candidate_routes[curr_zone][0]:
                    candidate_routes[curr_zone] = (curr_cost, path, breakdowns)

            # Explore neighbors
            for neighbor_id, edge in building.get_neighbors(curr_zone):
                # Avoid visiting already visited nodes in the current path
                if neighbor_id in path:
                    continue

                edge_breakdown = calculate_edge_cost(
                    source_id=curr_zone,
                    target_id=neighbor_id,
                    edge=edge,
                    building=building,
                    sensor_manager=sensor_manager,
                    risk_engine=self.risk_engine
                )

                new_cost = curr_cost + edge_breakdown.total_edge_cost

                if new_cost < min_costs.get(neighbor_id, float("inf")):
                    min_costs[neighbor_id] = new_cost
                    new_path = list(path) + [neighbor_id]
                    new_breakdowns = list(breakdowns) + [edge_breakdown]
                    heapq.heappush(queue, (new_cost, neighbor_id, new_path, new_breakdowns))

        # Select the best exit candidate
        if not candidate_routes:
            return RouteResult(
                route=[],
                exit=None,
                total_cost=float("inf"),
                risk_level="CRITICAL",
                reason="No feasible, unblocked path exists to any emergency exit.",
                is_feasible=False
            )

        # Filter out candidate routes that contain impassable edges
        feasible_candidates = {
            exit_id: candidate
            for exit_id, candidate in candidate_routes.items()
            if candidate[0] < IMPASSABLE_COST_PENALTY
        }

        if not feasible_candidates:
            # Fallback: All routes crossed critical hazards
            best_exit = min(candidate_routes, key=lambda e: candidate_routes[e][0])
            cost, path, breakdowns = candidate_routes[best_exit]
            return RouteResult(
                route=path,
                exit=best_exit,
                total_cost=cost,
                risk_level="CRITICAL",
                reason="WARNING: All reachable routes pass through high-hazard or blocked zones.",
                is_feasible=False,
                edge_breakdowns=breakdowns
            )

        # Pick the lowest-cost feasible candidate
        best_exit = min(feasible_candidates, key=lambda e: feasible_candidates[e][0])
        best_cost, best_path, best_breakdowns = feasible_candidates[best_exit]

        # Gather zone reports along the route
        zone_reports = {
            zid: self.risk_engine.calculate_zone_risk(zid, sensor_manager)
            for zid in best_path
        }

        # Calculate max zone risk along route to determine overall route risk level
        max_zone_risk = max([zr.risk_score for zr in zone_reports.values()], default=0.0)
        if max_zone_risk <= 20.0:
            overall_risk_level = "SAFE"
        elif max_zone_risk <= 40.0:
            overall_risk_level = "MODERATE"
        elif max_zone_risk <= 70.0:
            overall_risk_level = "HIGH"
        else:
            overall_risk_level = "CRITICAL"

        # Generate explainable reason
        reason = self._generate_explanation(
            start_zone=start_zone,
            best_exit=best_exit,
            best_path=best_path,
            best_cost=best_cost,
            feasible_candidates=feasible_candidates,
            candidate_routes=candidate_routes,
            zone_reports=zone_reports,
            building=building
        )

        return RouteResult(
            route=best_path,
            exit=best_exit,
            total_cost=best_cost,
            risk_level=overall_risk_level,
            reason=reason,
            is_feasible=True,
            edge_breakdowns=best_breakdowns,
            zone_reports=zone_reports
        )

    def _generate_explanation(
        self,
        start_zone: str,
        best_exit: str,
        best_path: List[str],
        best_cost: float,
        feasible_candidates: Dict[str, Tuple[float, List[str], List[EdgeCostBreakdown]]],
        candidate_routes: Dict[str, Tuple[float, List[str], List[EdgeCostBreakdown]]],
        zone_reports: Dict[str, ZoneRiskReport],
        building: BuildingGraph
    ) -> str:
        """Constructs a clear, human-understandable justification for the route decision."""
        explanations = []

        # Compare with alternative exits
        other_exits = [e for e in candidate_routes.keys() if e != best_exit]
        if not other_exits:
            explanations.append(f"{best_exit} is the only reachable emergency exit.")
        else:
            reasons_vs_others = []
            for alt_exit in other_exits:
                if alt_exit not in feasible_candidates:
                    reasons_vs_others.append(f"{alt_exit} is blocked or critically hazardous")
                else:
                    alt_cost = feasible_candidates[alt_exit][0]
                    diff = alt_cost - best_cost
                    reasons_vs_others.append(f"{best_exit} has lower combined risk/congestion than {alt_exit} (cost {best_cost:.1f} vs {alt_cost:.1f})")
            if reasons_vs_others:
                explanations.append("; ".join(reasons_vs_others) + ".")

        # Check path details
        high_crowd_nodes = [
            f"{n} (crowd {building.nodes[n].crowd_count:.0f})"
            for n in best_path if n in building.nodes and building.nodes[n].crowd_count > 40
        ]
        if high_crowd_nodes:
            explanations.append(f"Caution: Moderate crowd present in {', '.join(high_crowd_nodes)}.")
        else:
            explanations.append("Path avoids severe congestion and high-temperature/gas zones.")

        return " ".join(explanations)

    def should_reroute(
        self,
        active_route: List[str],
        candidate_route: RouteResult,
        threshold: float = REROUTE_THRESHOLD_DELTA
    ) -> Tuple[bool, str]:
        """
        Determines whether conditions have changed enough to warrant switching routes.
        Triggers reroute if:
        1. The active route has become impassable/critical.
        2. The new route is significantly safer/lower-cost (delta >= threshold).
        """
        if not active_route:
            return True, "Initial route calculation."

        if not candidate_route.is_feasible:
            return False, "Candidate route is not feasible."

        if candidate_route.route == active_route:
            return False, "Active route remains the optimal path."

        # Check if active path has been invalidated
        # If candidate route avoids a newly arisen danger that invalidates active_route
        return True, (
            f"Reroute recommended: Path switched to {candidate_route.exit} "
            f"via {' -> '.join(candidate_route.route)} due to lower dynamic hazard cost."
        )

    def reroute(
        self,
        building: BuildingGraph,
        current_zone: str,
        sensor_manager: SensorManager,
        active_route: Optional[List[str]] = None
    ) -> RouteResult:
        """Convenience method to execute rerouting from the evacuee's current location."""
        new_result = self.find_safest_route(building, current_zone, sensor_manager)
        return new_result
