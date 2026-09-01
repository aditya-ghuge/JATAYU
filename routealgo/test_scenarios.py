"""
ResQRoute AI - Comprehensive Test Suite
=======================================
Executes and validates all 9 required test scenarios:
  1. Normal building baseline
  2. High temperature in one corridor
  3. High gas level in one corridor
  4. Flame detected in one room
  5. Multiple dangerous zones (hazard isolation)
  6. One exit unavailable (door blockage / structural failure)
  7. One exit highly congested (crowd load balancing)
  8. Sensor failure / uncertainty handling (OFFLINE/DEGRADED)
  9. Dynamic changing conditions triggering real-time rerouting

Prints formatted: Input -> Risk Calculation -> Route Cost -> Selected Route -> Explanation.
"""

import json
from typing import Dict, Any
from config import SensorHealth, RiskState
from building import BuildingGraph, create_sample_building
from sensor_manager import SensorManager
from risk_engine import RiskEngine
from routing import RoutingEngine, RouteResult


def format_separator(title: str = "", char: str = "=", length: int = 80) -> str:
    if not title:
        return char * length
    prefix = f" {title} "
    total_padding = max(0, length - len(prefix))
    left = total_padding // 2
    right = total_padding - left
    return f"{char * left}{prefix}{char * right}"


def print_test_header(test_num: int, title: str, description: str):
    print("\n" + format_separator(f"TEST CASE {test_num}: {title.upper()}", "="))
    print(f"Goal: {description}")
    print(format_separator("-"))


def print_scenario_result(
    test_num: int,
    title: str,
    inputs: Dict[str, Any],
    building: BuildingGraph,
    sensor_manager: SensorManager,
    risk_engine: RiskEngine,
    result: RouteResult
):
    print(f"\n[1] SENSOR & ENVIRONMENT INPUTS:")
    for k, v in inputs.items():
        print(f"    - {k}: {v}")

    print(f"\n[2] ZONE RISK ASSESSMENTS:")
    # Print risk report for active zones
    for zone_id in ["R1", "R2", "C1", "C2", "C3", "C4", "EXIT1", "EXIT2"]:
        rep = risk_engine.calculate_zone_risk(zone_id, sensor_manager)
        crowd = building.nodes[zone_id].crowd_count
        status_flag = f"[{rep.risk_state.value}]"
        if rep.is_critical:
            status_flag += " (CRITICAL/IMPASSABLE)"
        print(
            f"    * Zone {zone_id:5s} | Risk Score: {rep.risk_score:5.1f}/100 {status_flag:20s} "
            f"| Uncertainty: {rep.uncertainty_score:4.1f}% | Crowd: {crowd:4.1f} | {rep.explanation}"
        )

    print(f"\n[3] ROUTE COST & DIJKSTRA EVALUATION:")
    print(f"    * Selected Exit     : {result.exit}")
    print(f"    * Optimal Route     : {' -> '.join(result.route) if result.route else 'NONE'}")
    print(f"    * Total Route Cost  : {result.total_cost:.2f}")
    print(f"    * Route Risk Level  : {result.risk_level}")
    print(f"    * Is Feasible       : {result.is_feasible}")

    if result.edge_breakdowns:
        print(f"\n    Step-by-step Traversal Cost Breakdown:")
        print(f"    {'From':<6} {'To':<6} {'DistCost':<10} {'RiskCost':<10} {'CrowdCost':<10} {'UncCost':<10} {'Total':<10}")
        print(f"    {'-'*60}")
        for eb in result.edge_breakdowns:
            print(
                f"    {eb.source:<6} {eb.target:<6} {eb.distance_cost:<10.2f} "
                f"{eb.risk_cost:<10.2f} {eb.crowd_cost:<10.2f} {eb.uncertainty_cost:<10.2f} {eb.total_edge_cost:<10.2f}"
            )

    print(f"\n[4] EXPLAINABLE REASONING:")
    print(f"    >> \"{result.reason}\"")
    print(format_separator("="))


class TestScenariosRunner:
    """Executes all test scenarios with programmatic assertions."""

    def __init__(self):
        self.building = create_sample_building()
        self.sensor_manager = SensorManager()
        self.risk_engine = RiskEngine()
        self.routing_engine = RoutingEngine(risk_engine=self.risk_engine)

    def reset_environment(self):
        """Reset building and sensor state between tests."""
        self.sensor_manager.reset_all()
        for node in self.building.nodes.values():
            node.crowd_count = 0.0
            node.is_available = True
        for edge in self.building.edges:
            edge.is_blocked = False

    # -------------------------------------------------------------
    # Test 1: Normal Building Baseline
    # -------------------------------------------------------------
    def test_1_normal_building(self) -> RouteResult:
        self.reset_environment()
        # Normal baseline readings across all zones
        for zid in self.building.nodes:
            self.sensor_manager.update_sensor_data(zid, "temperature", 22.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "gas", 35.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "flame", 0.0, SensorHealth.ONLINE)

        result = self.routing_engine.find_safest_route(self.building, "R1", self.sensor_manager)

        inputs = {"All Zones": "Temperature=22°C (Safe), Gas=35ppm (Safe), Flame=0 (None), Crowd=0"}
        print_scenario_result(1, "Normal Building Baseline", inputs, self.building, self.sensor_manager, self.risk_engine, result)

        assert result.is_feasible, "Normal building route must be feasible."
        assert result.exit == "EXIT1", "Shortest normal path from R1 is via C1->C2->EXIT1."
        assert result.risk_level == "SAFE", "Risk level should be SAFE."
        return result

    # -------------------------------------------------------------
    # Test 2: High Temperature in One Corridor (C1)
    # -------------------------------------------------------------
    def test_2_high_temperature(self) -> RouteResult:
        self.reset_environment()
        # Baseline normal for all
        for zid in self.building.nodes:
            self.sensor_manager.update_sensor_data(zid, "temperature", 22.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "gas", 35.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "flame", 0.0, SensorHealth.ONLINE)

        # Spike temperature in C2 (East Hallway) to 75°C
        self.sensor_manager.update_sensor_data("C2", "temperature", 75.0, SensorHealth.ONLINE)

        result = self.routing_engine.find_safest_route(self.building, "R1", self.sensor_manager)

        inputs = {
            "Zone C2": "Temperature=75.0°C (High thermal hazard)",
            "Other Zones": "Normal baseline (22°C, 35ppm, flame=0)"
        }
        print_scenario_result(2, "High Temperature in East Corridor (C2)", inputs, self.building, self.sensor_manager, self.risk_engine, result)

        assert result.exit == "EXIT2", "Algorithm must avoid hot corridor C2 and route to EXIT2 via C3->C4."
        assert "C2" not in result.route, "Corridor C2 must be bypassed."
        return result

    # -------------------------------------------------------------
    # Test 3: High Gas Level in One Corridor (C2)
    # -------------------------------------------------------------
    def test_3_high_gas_level(self) -> RouteResult:
        self.reset_environment()
        for zid in self.building.nodes:
            self.sensor_manager.update_sensor_data(zid, "temperature", 22.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "gas", 35.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "flame", 0.0, SensorHealth.ONLINE)

        # High toxic smoke / gas in corridor C2
        self.sensor_manager.update_sensor_data("C2", "gas", 360.0, SensorHealth.ONLINE)

        result = self.routing_engine.find_safest_route(self.building, "R1", self.sensor_manager)

        inputs = {
            "Zone C2": "Gas/Smoke=360 ppm (Hazardous smoke / near lethal)",
            "Other Zones": "Normal baseline"
        }
        print_scenario_result(3, "High Gas/Smoke Level in Corridor (C2)", inputs, self.building, self.sensor_manager, self.risk_engine, result)

        assert result.exit == "EXIT2", "Algorithm must route away from smoke-filled C2 to EXIT2."
        assert "C2" not in result.route, "Corridor C2 must not be present in the route."
        return result

    # -------------------------------------------------------------
    # Test 4: Flame Detected in One Room (R2)
    # -------------------------------------------------------------
    def test_4_flame_in_room(self) -> RouteResult:
        self.reset_environment()
        for zid in self.building.nodes:
            self.sensor_manager.update_sensor_data(zid, "temperature", 22.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "gas", 35.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "flame", 0.0, SensorHealth.ONLINE)

        # Direct flame detection in R2
        self.sensor_manager.update_sensor_data("R2", "flame", 1.0, SensorHealth.ONLINE)
        self.sensor_manager.update_sensor_data("R2", "temperature", 65.0, SensorHealth.ONLINE)

        result = self.routing_engine.find_safest_route(self.building, "R1", self.sensor_manager)

        inputs = {
            "Zone R2": "Flame=1.0 (Direct Fire), Temp=65°C",
            "Start Zone": "R1 (Adjacent to R2)"
        }
        print_scenario_result(4, "Flame Detected in Room (R2)", inputs, self.building, self.sensor_manager, self.risk_engine, result)

        assert result.is_feasible, "R1 should still safely reach an exit."
        assert "R2" not in result.route, "Route must never enter room R2."
        return result

    # -------------------------------------------------------------
    # Test 5: Multiple Dangerous Zones (C1 and C2 Compromised)
    # -------------------------------------------------------------
    def test_5_multiple_dangerous_zones(self) -> RouteResult:
        self.reset_environment()
        for zid in self.building.nodes:
            self.sensor_manager.update_sensor_data(zid, "temperature", 22.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "gas", 35.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "flame", 0.0, SensorHealth.ONLINE)

        # Severe multi-zone hazard: C2 has high temp & gas, C4 has moderate smoke
        self.sensor_manager.update_sensor_data("C2", "temperature", 85.0, SensorHealth.ONLINE)
        self.sensor_manager.update_sensor_data("C2", "gas", 380.0, SensorHealth.ONLINE)
        self.sensor_manager.update_sensor_data("C2", "flame", 1.0, SensorHealth.ONLINE)

        self.sensor_manager.update_sensor_data("C4", "gas", 110.0, SensorHealth.ONLINE)

        result = self.routing_engine.find_safest_route(self.building, "R1", self.sensor_manager)

        inputs = {
            "Zone C2": "CRITICAL Fire & Smoke (Temp 85°C, Gas 380ppm, Flame 1.0)",
            "Zone C4": "MODERATE Smoke (Gas 110ppm)",
            "Goal": "Test algorithm's ability to pick safest alternative among imperfect paths."
        }
        print_scenario_result(5, "Multiple Dangerous Zones", inputs, self.building, self.sensor_manager, self.risk_engine, result)

        assert result.exit == "EXIT2", "Must choose EXIT2, completely avoiding critical fire in C2."
        assert "C2" not in result.route
        return result

    # -------------------------------------------------------------
    # Test 6: One Exit Unavailable (EXIT1 Locked/Blocked)
    # -------------------------------------------------------------
    def test_6_exit_unavailable(self) -> RouteResult:
        self.reset_environment()
        for zid in self.building.nodes:
            self.sensor_manager.update_sensor_data(zid, "temperature", 22.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "gas", 35.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "flame", 0.0, SensorHealth.ONLINE)

        # Mark EXIT1 as disabled / locked
        self.building.update_exit_status("EXIT1", is_available=False)

        result = self.routing_engine.find_safest_route(self.building, "R1", self.sensor_manager)

        inputs = {
            "EXIT1 Status": "UNAVAILABLE (Emergency door blocked / locked)",
            "EXIT2 Status": "AVAILABLE"
        }
        print_scenario_result(6, "One Exit Unavailable (EXIT1 Locked)", inputs, self.building, self.sensor_manager, self.risk_engine, result)

        assert result.exit == "EXIT2", "Algorithm must divert route to available EXIT2."
        assert result.route[-1] == "EXIT2"
        return result

    # -------------------------------------------------------------
    # Test 7: One Exit Highly Congested (Crowd Load Balancing)
    # -------------------------------------------------------------
    def test_7_exit_congested(self) -> RouteResult:
        self.reset_environment()
        for zid in self.building.nodes:
            self.sensor_manager.update_sensor_data(zid, "temperature", 22.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "gas", 35.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "flame", 0.0, SensorHealth.ONLINE)

        # High crowd congestion in East wing corridor leading to EXIT1
        self.building.update_crowd_data("C2", crowd_count=90.0)
        self.building.update_crowd_data("EXIT1", crowd_count=85.0)

        # West wing corridor has no crowd
        self.building.update_crowd_data("C3", crowd_count=5.0)
        self.building.update_crowd_data("C4", crowd_count=0.0)

        result = self.routing_engine.find_safest_route(self.building, "R1", self.sensor_manager)

        inputs = {
            "Zone C2 & EXIT1": "Crowd Congestion = 90 & 85 (Bottleneck)",
            "Zone C3 & C4 & EXIT2": "Crowd Congestion = 5 & 0 (Clear path)"
        }
        print_scenario_result(7, "One Exit Highly Congested (Load Balancing)", inputs, self.building, self.sensor_manager, self.risk_engine, result)

        assert result.exit == "EXIT2", "Algorithm should balance crowd congestion and route to clearer EXIT2."
        return result

    # -------------------------------------------------------------
    # Test 8: Sensor Failure / Uncertainty
    # -------------------------------------------------------------
    def test_8_sensor_failure(self) -> RouteResult:
        self.reset_environment()
        for zid in self.building.nodes:
            self.sensor_manager.update_sensor_data(zid, "temperature", 22.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "gas", 35.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "flame", 0.0, SensorHealth.ONLINE)

        # Sensors in C2 fail completely (OFFLINE)
        self.sensor_manager.update_sensor_data("C2", "temperature", 22.0, SensorHealth.OFFLINE)
        self.sensor_manager.update_sensor_data("C2", "gas", 35.0, SensorHealth.OFFLINE)
        self.sensor_manager.update_sensor_data("C2", "flame", 0.0, SensorHealth.OFFLINE)

        result = self.routing_engine.find_safest_route(self.building, "R1", self.sensor_manager)

        inputs = {
            "Zone C2 Sensors": "OFFLINE / Disconnected (High uncertainty penalty)",
            "Zone C3, C4 Sensors": "ONLINE & Confirmed Safe"
        }
        print_scenario_result(8, "Sensor Failure & Uncertainty Handling", inputs, self.building, self.sensor_manager, self.risk_engine, result)

        assert result.exit == "EXIT2", "Algorithm should prefer routes with reliable ONLINE sensor data."
        return result

    # -------------------------------------------------------------
    # Test 9: Changing Conditions Causing Dynamic Rerouting
    # -------------------------------------------------------------
    def test_9_dynamic_rerouting(self):
        self.reset_environment()
        print("\n" + format_separator("TEST CASE 9: DYNAMIC REROUTING SIMULATION", "="))
        print("Scenario: Evacuee starts from R1. Initial conditions are normal (Route -> EXIT1).")
        print("Suddenly, a fire and gas leak erupts in corridor C2 while evacuee is navigating.")
        print("System must automatically detect hazard change, invalidate path, and reroute to EXIT2.")
        print(format_separator("-"))

        # Step 1: Initial Normal State
        for zid in self.building.nodes:
            self.sensor_manager.update_sensor_data(zid, "temperature", 22.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "gas", 35.0, SensorHealth.ONLINE)
            self.sensor_manager.update_sensor_data(zid, "flame", 0.0, SensorHealth.ONLINE)

        initial_route = self.routing_engine.find_safest_route(self.building, "R1", self.sensor_manager)
        print(f"\n[PHASE 1 - INITIAL STATE]")
        print(f"  Active Route : {' -> '.join(initial_route.route)}")
        print(f"  Target Exit  : {initial_route.exit}")
        print(f"  Route Cost   : {initial_route.total_cost:.2f}")
        assert initial_route.exit == "EXIT1", "Initial normal route must be EXIT1."

        # Step 2: Dynamic Hazard Spike in C2
        print(f"\n[PHASE 2 - HAZARD OCCURRENCE: Fire & Gas in C2]")
        self.sensor_manager.update_sensor_data("C2", "temperature", 78.0, SensorHealth.ONLINE)
        self.sensor_manager.update_sensor_data("C2", "gas", 340.0, SensorHealth.ONLINE)
        self.sensor_manager.update_sensor_data("C2", "flame", 1.0, SensorHealth.ONLINE)

        # Evaluate reroute check
        candidate_route = self.routing_engine.find_safest_route(self.building, "R1", self.sensor_manager)
        needs_reroute, reroute_msg = self.routing_engine.should_reroute(initial_route.route, candidate_route)

        print(f"  Reroute Check: Needs Reroute = {needs_reroute}")
        print(f"  Reason       : {reroute_msg}")
        print(f"  New Route    : {' -> '.join(candidate_route.route)}")
        print(f"  New Target   : {candidate_route.exit}")
        print(f"  New Cost     : {candidate_route.total_cost:.2f}")

        assert needs_reroute is True, "System must trigger dynamic rerouting."
        assert candidate_route.exit == "EXIT2", "Rerouted path must lead to safe EXIT2."
        assert "C2" not in candidate_route.route, "Rerouted path must not pass through C2."
        print("\n>> Dynamic rerouting successfully executed and verified!")
        print(format_separator("="))


def run_all_tests():
    runner = TestScenariosRunner()
    print("\n" + "#" * 80)
    print("  RUNNING RESQROUTE AI TEST SUITE (9 COMPREHENSIVE SCENARIOS)")
    print("#" * 80)

    runner.test_1_normal_building()
    runner.test_2_high_temperature()
    runner.test_3_high_gas_level()
    runner.test_4_flame_in_room()
    runner.test_5_multiple_dangerous_zones()
    runner.test_6_exit_unavailable()
    runner.test_7_exit_congested()
    runner.test_8_sensor_failure()
    runner.test_9_dynamic_rerouting()

    print("\n" + "#" * 80)
    print("  ALL 9 TEST CASES PASSED SUCCESSFULLY!")
    print("#" * 80 + "\n")


if __name__ == "__main__":
    run_all_tests()
