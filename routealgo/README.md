# ResQRoute AI — Safe Evacuation Routing Algorithm

**ResQRoute AI** is an explainable, graph-based emergency evacuation algorithm designed to find the **safest route out of a building**, rather than merely the shortest distance.

---

## Key Highlights

- **Explainable Pathfinding**: Built on transparent multi-sensor fusion and dynamic Dijkstra pathfinding (no black-box AI).
- **Physical Sensor Fusion**: Integrates Temperature (heat build-up), Smoke/Gas (toxicity & visibility), and Flame (direct fire detection).
- **Extensible Architecture**: Easily add new physical sensors (e.g. CO2, structural vibration, thermal cameras).
- **Sensor Health & Uncertainty**: Gracefully handles `ONLINE`, `DEGRADED`, `STALE`, and `OFFLINE` states without assuming unmonitored zones are safe.
- **Dynamic Rerouting**: Continuously monitors environmental hazard spikes and automatically recomputes optimal exit paths in real-time.
- **Crowd & Bottleneck Balancing**: Penalizes congested zones to prevent stampedes and bottleneck delays.
- **Hardware & Dashboard Ready**: Includes production-grade FastAPI REST endpoints and ESP32 Arduino C++ firmware.

---

## 1. System Architecture & Mathematics

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   Temperature   │       │   Smoke / Gas   │       │   Flame Sensor  │
│  (0 - 100 Risk) │       │  (0 - 100 Risk) │       │  (0 - 100 Risk) │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         │  * 0.35 (W_temp)        │  * 0.40 (W_gas)         │  * 0.25 (W_flame)
         └────────────────► ───────┴─────── ◄────────────────┘
                                   │
                      ┌────────────▼────────────┐
                      │    Zone Risk Score      │
                      │    (0 - 100 Scale)      │
                      └────────────┬────────────┘
                                   │
┌─────────────────────────┐        │         ┌─────────────────────────┐
│    Physical Distance    │        │         │   Crowd & Uncertainty   │
│   (Distance * W_dist)   ├────────┼────────►│   (Congestion Penalty)  │
└─────────────────────────┘        │         └─────────────────────────┘
                                   ▼
                   ┌───────────────────────────────┐
                   │       Dynamic Edge Cost       │
                   │    Total Cost Calculation     │
                   └───────────────┬───────────────┘
                                   ▼
                   ┌───────────────────────────────┐
                   │    Dynamic Dijkstra Engine    │
                   │    Lowest-Cost Safe Exit      │
                   └───────────────────────────────┘
```

### Risk Model Formula

Zone risk is calculated via normalized multi-sensor fusion:

$$\text{Risk Score} = (\text{Temp Risk} \times 0.35) + (\text{Gas Risk} \times 0.40) + (\text{Flame Risk} \times 0.25)$$

Risk score categorization:
- **0 – 20**: `SAFE`
- **21 – 40**: `MODERATE`
- **41 – 70**: `HIGH`
- **71 – 100**: `CRITICAL` (Zone marked impassable / blocked)
- **Unreliable / Missing data**: `UNKNOWN` (Applies high uncertainty penalty)

### Dynamic Traversal Cost Formula

For every graph edge connecting zone $u$ to zone $v$:

$$\text{Total Cost}(u \rightarrow v) = (d_{uv} \cdot W_{\text{dist}}) + (\text{Risk}_v \cdot W_{\text{risk}}) + (\text{Crowd}_v \cdot W_{\text{crowd}}) + (\text{Uncertainty}_v \cdot W_{\text{unc}})$$

Configured default weights:
- $W_{\text{dist}} = 1.0$
- $W_{\text{risk}} = 2.5$
- $W_{\text{crowd}} = 0.4$
- $W_{\text{unc}} = 1.5$

---

## 2. Building Graph Topology

The reference building contains 5 Rooms, 4 Corridors, and 2 Emergency Exits:

```
[R1: Conf Room] ───────┐
[R2: Lab Room]  ───────┼─── [C1: North Hall] ─────── [C2: East Hall] ─────── [EXIT1: East Exit]
[R3: Office A]  ───────┘          │                        │
                                  │ (Cross link)           │ (East-West Bypass)
                                  │                        │
[R4: Server Rm] ───────┬─── [C3: South Hall] ─────── [C4: West Hall] ─────── [EXIT2: West Exit]
[R5: Storage]   ───────┘
```

---

## 3. Project Structure

```
d:/routing algo/
├── config.py                 # Centralized thresholds, weights, and health states
├── building.py               # Building topology, graph nodes/edges, NetworkX bridge
├── sensor_manager.py         # Telemetry management, sensor timeouts, uncertainty scoring
├── risk_engine.py            # Normalized sensor fusion and risk classification
├── routing.py                # Dynamic Dijkstra engine, explainability, rerouting
├── api.py                    # FastAPI REST service for ESP32 & CCTV ingestion
├── main.py                   # Interactive CLI runner
├── test_scenarios.py         # 9 automated test scenarios
├── building_layout.json      # JSON schema of building floorplan
├── esp32_sensor_node.ino     # C++ Arduino sketch for ESP32 IoT nodes
└── cctv_crowd_detector.py    # OpenCV / CCTV crowd feeder simulation
```

---

## 4. Running the Project

### Running the 9 Comprehensive Test Cases
```bash
python main.py --all
```
or
```bash
python test_scenarios.py
```

### Running the Interactive CLI
```bash
python main.py
```

### Running the FastAPI REST Server
```bash
uvicorn api:app --reload --port 8000
```
API Documentation will be interactively available at: `http://localhost:8000/docs`.

---

## 5. Summary of 9 Test Cases

| # | Scenario | Condition / Hazard | Dynamic Decision & Selected Route |
|---|----------|---------------------|-----------------------------------|
| **1** | **Normal Building** | All sensors safe (22°C, 35ppm, 0 flame) | Routes shortest path to `EXIT1`: `R1 -> C1 -> C2 -> EXIT1` (Cost: 31.75) |
| **2** | **High Temperature** | C2 reaches 75°C (East corridor fire) | Bypasses C2, safely routes to `EXIT2`: `R1 -> C1 -> C3 -> C4 -> EXIT2` |
| **3** | **High Gas / Smoke** | C2 gas reaches 360 ppm | Bypasses toxic corridor C2, routes to `EXIT2` |
| **4** | **Flame in Room R2** | Fire detected in R2 | Keeps R1 evacuees away from R2, exits via `EXIT1` safely |
| **5** | **Multiple Hazards** | C2 has critical fire, C4 has moderate smoke | Avoids lethal fire in C2, picks manageable route to `EXIT2` |
| **6** | **Exit 1 Unavailable** | EXIT1 emergency door locked / blocked | Automatically diverts evacuees to available `EXIT2` |
| **7** | **Exit 1 Congested** | C2 & EXIT1 crowd congestion = 90% | Load-balances traffic away from stampede to clear `EXIT2` |
| **8** | **Sensor Failure** | C2 sensors go OFFLINE (Uncertainty = 85%) | Penalizes unmonitored C2, prefers monitored safe path to `EXIT2` |
| **9** | **Dynamic Rerouting** | Fire erupts mid-evacuation in C2 | Real-time trigger detects hazard, switches active path to `EXIT2` |

---

## 6. Connecting ESP32 Microcontrollers

1. Flash `esp32_sensor_node.ino` to your ESP32 with DHT22 (Temp), MQ-2 (Gas), and IR Flame sensors attached.
2. In the sketch, set your WiFi SSID, Password, and target API URL: `http://<YOUR_PC_IP>:8000/telemetry`.
3. The ESP32 sends telemetry every 2 seconds:
```json
{
  "zone_id": "C1",
  "temperature": 27.5,
  "gas": 45.0,
  "flame": 0.0,
  "status": "ONLINE"
}
```
4. ResQRoute AI recalculates zone risks and immediately updates route recommendations for all dashboard clients!
