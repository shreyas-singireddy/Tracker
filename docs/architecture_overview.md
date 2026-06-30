# FitOS Architecture Overview

This document defines the high-level system architecture of the **Offline AI Fitness Operating System (FitOS)**. FitOS is designed as an edge-first, offline-isolated system that processes multi-modal sensor inputs to provide real-time fitness coaching and form correction.

---

## 1. System Block Diagram

The block diagram below illustrates the flow from raw hardware inputs to local execution units, down to stateful routing and immediate audio/haptic outputs.

```mermaid
flowchart TB
    subgraph Hardware Layer
        IMU["Wearable IMUs\n(Accelerometer, Gyroscope)"]
        HR["Heart Rate Sensor\n(PPG)"]
        CAM["Device Camera\n(RGB @ 30/60 FPS)"]
        MIC["Device Microphone\n(PCM Audio)"]
    end

    subgraph Sensor Fusion & Ingestion Layer
        SFC["Sensor Fusion Controller\n(Kalman Filtering & Resampling)"]
        FrameBuffer["Circular Frame Buffer\n(RGB Arrays)"]
        AudioBuffer["PCM Audio Stream buffer"]
    end

    subgraph Edge Inference Engine (Local NPU/GPU/CPU)
        CV["Pose Estimation Module\n(Quantized MediaPipe / YOLO-Pose)"]
        SLM["Local SLM\n(e.g., Qwen-2.5-3B-Instruct 4-bit)"]
        ASR_TTS["ASR & TTS Engines\n(Whisper-Tiny & Local Piper TTS)"]
    end

    subgraph Stateful Reasoning & Context Engine
        Router["Decision Router & Agent\n(Stateful Event Orchestrator)"]
        LocalDB["State & Metric DB\n(SQLite: Logs & Profiles)"]
        VectorDB["Local Vector Store\n(sqlite-vss: Exercise & Injury Memory)"]
    end

    subgraph Actuation & Feedback Layer
        HapticCtrl["Haptic Pattern Generator"]
        AudioActuator["Audio Mixer & Playback"]
        UIRenderer["Skeletal & Metric UI Overlay"]
    end

    %% Wiring
    IMU --> SFC
    HR --> SFC
    CAM --> FrameBuffer
    MIC --> AudioBuffer

    SFC --> Router
    FrameBuffer --> CV
    AudioBuffer --> ASR_TTS

    CV -- "Pose Coordinates (Keypoints)" --> Router
    ASR_TTS -- "Transcribed Command Text" --> SLM
    SLM -- "Generated Dialogue Text" --> ASR_TTS
    ASR_TTS -- "Audio Stream" --> AudioActuator

    Router <--> LocalDB
    Router <--> VectorDB
    Router -- "Immediate Correction Flags" --> HapticCtrl
    Router -- "UI State Updates" --> UIRenderer
    Router -- "Verbal Coaching Trigger" --> SLM
```

---

## 2. Core Architectural Layers

### 2.1 Hardware & Sensor Ingestion Layer
*   **Sensor Ingestion**: Continually polls data from:
    *   **Wearable IMUs**: 6-axis accelerometer and gyroscope data at 50Hz–100Hz.
    *   **Heart Rate Sensor (PPG)**: Heart rate and heart rate variability (HRV) at 1Hz–5Hz.
    *   **Device Camera**: RGB frames captured at 30 FPS or 60 FPS.
    *   **Device Microphone**: Raw mono PCM audio channel sampled at 16kHz.
*   **Sensor Fusion Controller (SFC)**: Performs temporal alignment, Kalman filtering, and spatial transformation of wearable IMU sensors. It matches IMU acceleration events with visual frame timestamps.

### 2.2 Edge Inference Engine
*   **Pose Estimation Module (CV)**:
    *   Runs a quantized 2D/3D pose estimation model (e.g., MediaPipe Pose or YOLOv8-pose INT8/FP16) on the local NPU.
    *   Extracts a 33-point skeletal landmark array per frame.
    *   Computes joint angles, velocities, and tracking metrics.
*   **Speech and Voice Modules (ASR & TTS)**:
    *   **Automatic Speech Recognition (ASR)**: Whisper-Tiny (quantized to 4-bit/8-bit) transforms user speech to text.
    *   **Text-to-Speech (TTS)**: Piper TTS or native OS voice engines synthesize coaching responses with latency `< 200ms`.
*   **Local Small Language Model (SLM)**:
    *   A quantized, instruction-tuned model (e.g., Qwen-2.5-3B-Instruct or Llama-3-8B-Instruct quantized via GGUF/W4A16) running on the local CPU or NPU.
    *   Generates context-aware, personalized exercise feedback, answers training questions, and coordinates program adaptations.

### 2.3 Stateful Reasoning & Context Engine
*   **Decision Router (Core Agent)**:
    *   A deterministic event router that evaluates physical parameters (e.g., knee flexion angle during squat > threshold) and compares them against exercise guidelines.
    *   Acts as the central router between the real-time sensor loop (sub-100ms) and the conversational SLM loop (multi-second).
*   **Local Databases**:
    *   **SQLite DB**: Stores profile data, historical workouts, calorie metrics, sets/reps, and sensor telemetry.
    *   **Vector DB (e.g., sqlite-vss or local Faiss)**: Stores user injury context, past training reviews, and safety rules to inject into the SLM prompt context via RAG.

### 2.4 Actuation & Feedback Layer
*   **Haptic Pattern Generator**: Issues low-latency vibration notifications (e.g., short dual-pulse for hyper-extended back, long pulse for set completion).
*   **Audio Mixer**: Prioritizes verbal form corrections over background music.
*   **UI Renderer**: Draws the real-time skeletal node overlay, joint angles, velocity bars, and target rep-counts.

---

## 3. Data Flow Pipelines

FitOS executes two primary data loops with differing requirements for latency and resource allocation.

### 3.1 The Real-Time Feedback Loop (Sub-100ms Latency)
This loop is responsible for immediate form correction, rep counting, and biomechanical monitoring.
1. Camera captures frame $\rightarrow$ FrameBuffer.
2. Wearable streams IMU vector $\rightarrow$ SFC.
3. CV model infers 3D joints on NPU $\rightarrow$ Pose Landmark Array.
4. Decision Router evaluates landmark angles against the target exercise specification.
5. If a critical form deviation is detected:
    *   **Haptic Actuator** fires vibration patterns (`< 50ms` from event detection).
    *   **UI Renderer** colors the offending joint red (`< 33ms` frame update).
    *   **Audio mixer** ducks audio volume and plays a pre-synthesized vocal alert (e.g., "Keep your chest up!").

```
[Camera/Sensors] ──> [Inference (NPU)] ──> [Biomechanical Evaluation] ──> [Haptics / UI Output]
└───────────────────────────────── Target: < 100ms ──────────────────────────────────┘
```

### 3.2 The Conversational/Interactive Loop (Multi-Second)
This loop handles user inquiries, dynamic workout adjustments, and session reflections.
1. Microphone captures audio input $\rightarrow$ AudioBuffer.
2. ASR converts voice input to text.
3. Decision Router reads workout history from Local DB, retrieves user profile context, and constructs a structured system prompt.
4. SLM processes text + context and generates a natural-language response.
5. TTS converts response text to audio.
6. Audio plays back to user.

---

## 4. Offline Edge Isolation Boundary

FitOS maintains a strict zero-dependency network policy. No feature of the core operating system requires internet access:
*   **Local Weights Only**: Model weights for ASR, Pose CV, and SLM are stored directly on the local filesystem and loaded in RAM.
*   **On-Device Embedding Generation**: Search vector embeddings are generated locally using a lightweight embedding model (e.g., BGE-Micro or ONNX MiniLM).
*   **Local Telemetry**: Performance logs and health records are stored in a password-locked SQLite database encrypted with SQLCipher.
