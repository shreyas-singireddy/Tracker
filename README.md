# FitOS - Offline AI Fitness Operating System

Welcome to the **FitOS** system architecture repository. FitOS is an edge-first, offline-isolated operating system designed to run on personal devices (smartphones, wearables, smart mirrors) to provide real-time biomechanical feedback, voice-guided athletic training, and adaptive physical coaching.

Because FitOS operates entirely offline, it is designed from the ground up for **absolute data privacy, ultra-low latency execution (sub-100ms real-time loop), and battery-conscious scheduling.**

---

## 🗺️ System Architecture Index

During **Sprint 0 (Architecture Lock Phase)**, we have defined the complete system blueprints, data structures, and constraints before any source code implementation begins. Explore the following core documents:

1. 🏛️ **[docs/architecture_overview.md](file:///c:/Users/shrey/OneDrive/Desktop/Tracker/tracker/docs/architecture_overview.md)**
   * Describes the multi-layered edge-first block diagram.
   * Explores the hardware sensor inputs, NPU inference modules (Pose CV, local SLMs), and feedback loop details.
   * Illustrates data flow pipelines (100ms biomechanical loop vs. multi-second conversational loop).

2. 📜 **[docs/contracts_and_schemas.md](file:///c:/Users/shrey/OneDrive/Desktop/Tracker/tracker/docs/contracts_and_schemas.md)**
   * Defines local database schemas (SQLite / SQLCipher tables for telemetry logs, user profiles, and sqlite-vss vector database structures).
   * Establishes Type/Interface contracts for IMU streams, Heart Rate events, ASR inputs, and AI keypoint outputs.
   * Defines the actuation payload contracts for haptics, voice alerts, and UI adjustments.

3. ⚖️ **[docs/engineering_rules.md](file:///c:/Users/shrey/OneDrive/Desktop/Tracker/tracker/docs/engineering_rules.md)**
   * Details memory budgets (active system RAM capped at 2.61 GB; 4-bit model quantization criteria).
   * Lays out latency budgets (Camera-to-Haptic feedback loop < 100ms; SLM TTFT < 750ms).
   * Implements strict Privacy Guidelines (local-only storage, zero internet access boundaries).
   * Details the **Graceful Degradation Levels** (Level 1 Full, Level 2 Balanced, Level 3 Sensor-Only fallback) to conserve host battery and prevent thermal throttling.

4. 🔄 **[docs/system_lifecycle.md](file:///c:/Users/shrey/OneDrive/Desktop/Tracker/tracker/docs/system_lifecycle.md)**
   * Details the system state transitions (Boot, Standby, Calibration, Active, Cooldown, Sync & Optimize).
   * Describes the memory-swapping routine (evicting/loading heavy model weights dynamically to fit active RAM budgets).
   * Details dynamic polling frequencies for cameras, wearables, and voice activity detectors across each state.

---

## 🚀 Key Design Philosophies

*   **Privacy-by-Default**: User heart rates, workout videos, and conversations are highly personal. FitOS enforces zero network communication; all weights, contexts, and embeddings remain strictly locked on the local device.
*   **Latency-First Actuation**: Real-time form correction requires instant feedback. If form correction takes more than 150ms, the user has already finished the movement, rendering the correction useless or distracting. We target a sub-100ms pipeline from image sensor to haptic engine.
*   **Dynamic Resource Allocation**: Run on device batteries without triggering OS warnings or excessive battery drain. When the host device runs low on charge or overheats, FitOS degrades gracefully from rich visual-verbal coaching to lightweight IMU heuristic tracking, ensuring the workout is logged without shutting down.
