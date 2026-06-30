# FitOS Interface Contracts & Database Schemas

This document defines the data structures, local storage schemas, and software interfaces for **FitOS**. Ensuring strict data contracts is vital for zero-network execution and deterministic coordination across local modules.

---

## 1. Local Database Schema (SQLite & SQLCipher)

To ensure privacy, all user settings, metrics, histories, and semantic profile details are persisted locally. Below is the SQLite schema definition.

```sql
-- User Profile Table
CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    birth_date TEXT NOT NULL,
    weight_kg REAL NOT NULL,
    height_cm REAL NOT NULL,
    resting_hr INTEGER,
    max_hr INTEGER,
    fitness_level TEXT CHECK(fitness_level IN ('beginner', 'intermediate', 'advanced')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exercises Dictionary
CREATE TABLE exercises (
    exercise_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT CHECK(category IN ('strength', 'cardio', 'mobility')),
    primary_muscles TEXT, -- JSON array of muscles
    form_rules TEXT NOT NULL -- JSON configuration of target angles
);

-- Workout Sessions
CREATE TABLE workout_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT FOREIGN KEY REFERENCES user_profiles(user_id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status TEXT CHECK(status IN ('in_progress', 'completed', 'aborted')),
    calories_burned_kcal REAL DEFAULT 0.0,
    avg_heart_rate INTEGER
);

-- Detailed Metrics Time-Series (High frequency, cleaned)
CREATE TABLE biometric_telemetry (
    telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT FOREIGN KEY REFERENCES workout_sessions(session_id),
    timestamp TIMESTAMP NOT NULL,
    heart_rate INTEGER,
    calories_burned_delta REAL,
    active_imu_state TEXT -- JSON representation of current pose state
);

-- Workout Sets & Reps
CREATE TABLE workout_logs (
    log_id TEXT PRIMARY KEY,
    session_id TEXT FOREIGN KEY REFERENCES workout_sessions(session_id),
    exercise_id TEXT FOREIGN KEY REFERENCES exercises(exercise_id),
    set_number INTEGER NOT NULL,
    target_reps INTEGER,
    completed_reps INTEGER NOT NULL,
    average_velocity REAL, -- m/s from pose estimation
    form_score REAL CHECK(form_score BETWEEN 0.0 AND 1.0),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Semantic Context Storage (RAG for SLM)
CREATE TABLE user_context_memories (
    memory_id TEXT PRIMARY KEY,
    user_id TEXT FOREIGN KEY REFERENCES user_profiles(user_id),
    category TEXT CHECK(category IN ('injury', 'preference', 'feedback', 'goal')),
    memory_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- sqlite-vss Vector Table (Virtual Table for semantic retrieval)
CREATE VIRTUAL TABLE user_context_embeddings USING vss0 (
    memory_id TEXT,
    memory_vector(384) -- 384-dimensional embeddings (e.g. MiniLM-L6-v2)
);
```

---

## 2. Sensor Ingestion Contracts

### 2.1 Wearable IMU Telemetry (50Hz Stream)
```typescript
interface IMUTelemetry {
  deviceId: string;
  timestampMs: number; // Unix timestamp with millisecond resolution
  accelerometer: {
    x: number; // m/s^2
    y: number;
    z: number;
  };
  gyroscope: {
    x: number; // rad/s
    y: number;
    z: number;
  };
}
```

### 2.2 Heart Rate Telemetry (1Hz Stream)
```typescript
interface BiometricTelemetry {
  deviceId: string;
  timestampMs: number;
  heartRateBpm: number;
  hrvMs?: number; // Heart Rate Variability (optional)
}
```

---

## 3. Edge Inference Interface Contracts

### 3.1 Computer Vision Pose Landmark Output
Following the standard 33-point skeletal landmark structure (MediaPipe Pose):

```typescript
interface Keypoint3D {
  x: number;        // Coordinate normalized to [0.0, 1.0] in image plane
  y: number;        // Coordinate normalized to [0.0, 1.0] in image plane
  z: number;        // Depth relative to hips (negative is closer to camera)
  visibility: number; // Probability of point being visible [0.0, 1.0]
}

interface PoseLandmarks {
  frameId: number;
  timestampMs: number;
  landmarks: {
    [key in LandmarkName]: Keypoint3D;
  };
  inferredMetrics: {
    jointAngles: {
      leftKneeFlexion: number;  // degrees
      rightKneeFlexion: number;
      leftHipFlexion: number;
      rightHipFlexion: number;
      backIncline: number;
    };
    detectedRepetition: boolean;
    repCount: number;
  };
}

type LandmarkName = 
  | 'nose' | 'left_eye' | 'right_eye' | 'left_ear' | 'right_ear'
  | 'left_shoulder' | 'right_shoulder' | 'left_elbow' | 'right_elbow'
  | 'left_wrist' | 'right_wrist' | 'left_hip' | 'right_hip'
  | 'left_knee' | 'right_knee' | 'left_ankle' | 'right_ankle'
  | 'left_heel' | 'right_heel' | 'left_foot_index' | 'right_foot_index';
```

### 3.2 Speech Transcription Event
```typescript
interface AudioTranscription {
  sessionId: string;
  timestampMs: number;
  transcriptionText: string;
  confidence: number; // [0.0, 1.0]
  latencyMs: number;  // Processing duration
}
```

### 3.3 SLM Prompt & Context Interface
```typescript
interface SLMContextPayload {
  userId: string;
  userMessage: string;
  workoutState: {
    currentExerciseId: string;
    completedRepsThisSet: number;
    currentHeartRateBpm: number;
    recentFormViolations: string[]; // e.g. ["butt_wink", "forward_knees"]
  };
  relevantMemories: string[]; // RAG output e.g. ["User has lower back stiffness history"]
  systemPromptTemplate: string; // Dynamic instruction template based on state
}
```

---

## 4. Actuation & Output Contracts

### 4.1 Feedback Command Payload
The Decision Router sends this command to trigger hardware outputs.

```typescript
interface FeedbackCommand {
  commandId: string;
  timestampMs: number;
  haptic: {
    pattern: 'NONE' | 'SINGLE_SHORT' | 'DOUBLE_SHORT' | 'LONG_ALERT' | 'SUCCESS_CHIME';
    intensity: number; // [0.0, 1.0]
  };
  audio: {
    playText?: string;     // Text to synthesize via TTS
    audioFileUri?: string; // Pre-synthesized wave file Uri (high priority)
    audioCategory: 'FORM_ALERT' | 'MOTIVATION' | 'SYSTEM';
    duckBackgroundMusic: boolean;
  };
  uiUpdate: {
    highlightJoints: LandmarkName[];
    skeletonColorHex: string;
    metricsDisplay: {
      repCount: number;
      tempoVelocity: number;
    };
  };
}
```
