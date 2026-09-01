"""
ResQRoute AI - Main Interactive Entry Point
===========================================
Interactive console application for demonstration, testing, and real-time evacuation simulation.

Usage:
  python main.py             # Launches interactive CLI menu
  python main.py --all       # Runs all 9 test scenarios automatically
"""

import sys
import json
from test_scenarios import TestScenariosRunner, run_all_tests
from building import create_sample_building
from sensor_manager import SensorManager
from risk_engine import RiskEngine
from routing import RoutingEngine
from config import SensorHealth


def print_banner():
    print("""
================================================================================
  ____            ___  ____             _          _    ___ 
 |  _ \  ___ ___ / _ \|  _ \ ___  _   _| |_ ___   / \  |_ _|
 | |_) |/ _ \ __| | | | |_) / _ \| | | | __/ _ \ / _ \  | | 
 |  _ <|  __\__ \ |_| |  _ < (_) | |_| | ||  __// ___ \ | | 
 |_| \_\\___|___/\__\_\|_| \_\___/ \__,_|\__\___/_/   \_\___|
  EMERGENCY EVACUATION & SAFE ROUTE PATHFINDING ENGINE (v1.0)
================================================================================
    """)


def print_menu():
    print("""
Select an option:
  [1] Run All 9 Test Scenarios (Comprehensive Evaluation)
  [2] Scenario 1: Normal Building Baseline
  [3] Scenario 2: High Temperature in Corridor C2 (75°C)
  [4] Scenario 3: High Gas / Smoke in Corridor C2 (360 ppm)
  [5] Scenario 4: Flame Detected in Room R2
  [6] Scenario 5: Multiple Dangerous Zones (Hazard Isolation)
  [7] Scenario 6: One Exit Unavailable (EXIT1 Locked)
  [8] Scenario 7: One Exit Highly Congested (Crowd Balancing)
  [9] Scenario 8: Sensor Failure / Uncertainty Handling
  [10] Scenario 9: Dynamic Rerouting Simulation
  [11] Custom Query (Input start room and test dynamic routing)
  [12] Export Current Building Topology to JSON
  [0] Exit
    """)


def custom_query_interactive():
    building = create_sample_building()
    sensor_manager = SensorManager()
    risk_engine = RiskEngine()
    routing_engine = RoutingEngine(risk_engine=risk_engine)

    print("\n--- Custom Dynamic Safe Route Query ---")
    start = input("Enter starting zone [default 'R1']: ").strip().upper() or "R1"
    if start not in building.nodes:
        print(f"Error: Zone '{start}' not in building topology.")
        return

    # Inquire custom sensor updates
    print("\nOptionally simulate hazard in a zone (leave empty to skip):")
    zone_hazard = input("Hazard Zone ID (e.g. C1, C2, C3): ").strip().upper()
    if zone_hazard and zone_hazard in building.nodes:
        t_str = input("Temperature (°C) [default 22.0]: ").strip()
        g_str = input("Gas concentration (ppm) [default 35.0]: ").strip()
        f_str = input("Flame detected (0 or 1) [default 0]: ").strip()

        temp = float(t_str) if t_str else 22.0
        gas = float(g_str) if g_str else 35.0
        flame = float(f_str) if f_str else 0.0

        sensor_manager.update_sensor_data(zone_hazard, "temperature", temp)
        sensor_manager.update_sensor_data(zone_hazard, "gas", gas)
        sensor_manager.update_sensor_data(zone_hazard, "flame", flame)

    # Inquire crowd
    crowd_zone = input("\nOptionally add crowd congestion zone (e.g. C2): ").strip().upper()
    if crowd_zone and crowd_zone in building.nodes:
        c_str = input("Crowd count (0-100): ").strip()
        if c_str:
            building.update_crowd_data(crowd_zone, float(c_str))

    result = routing_engine.find_safest_route(building, start, sensor_manager)
    print("\n" + "=" * 60)
    print(f"SAFEST EVACUATION ROUTE FOR {start}:")
    print(f"Path          : {' -> '.join(result.route)}")
    print(f"Target Exit   : {result.exit}")
    print(f"Total Cost    : {result.total_cost:.2f}")
    print(f"Risk Level    : {result.risk_level}")
    print(f"Reason        : {result.reason}")
    print("=" * 60)


def main():
    print_banner()

    if len(sys.argv) > 1 and sys.argv[1] in ["--all", "-a", "test"]:
        run_all_tests()
        return

    runner = TestScenariosRunner()

    while True:
        print_menu()
        choice = input("Enter choice (0-12): ").strip()

        if choice == "0":
            print("\nExiting ResQRoute AI. Stay Safe!")
            break
        elif choice == "1":
            run_all_tests()
        elif choice == "2":
            runner.test_1_normal_building()
        elif choice == "3":
            runner.test_2_high_temperature()
        elif choice == "4":
            runner.test_3_high_gas_level()
        elif choice == "5":
            runner.test_4_flame_in_room()
        elif choice == "6":
            runner.test_5_multiple_dangerous_zones()
        elif choice == "7":
            runner.test_6_exit_unavailable()
        elif choice == "8":
            runner.test_7_exit_congested()
        elif choice == "9":
            runner.test_8_sensor_failure()
        elif choice == "10":
            runner.test_9_dynamic_rerouting()
        elif choice == "11":
            custom_query_interactive()
        elif choice == "12":
            b = create_sample_building()
            print("\n--- Building JSON Topology ---")
            print(b.to_json(indent=2))
        else:
            print("Invalid selection. Please choose an option from 0 to 12.")


if __name__ == "__main__":
    main()
