# Architecture

VisionTrafficAI uses a layered pipeline so inference, domain policy, persistence, presentation, and delivery remain independently testable.

```mermaid
flowchart LR
    V[Traffic Video] --> D[YOLOv8 Detector]
    D --> T[ByteTrack]
    T --> C[Virtual Line Counter]
    T --> E[Density Estimator]
    E --> S[Adaptive Signal Controller]
    C --> P[Frame Statistics]
    S --> P
    P --> DB[(SQLite)]
    P --> O[Annotated MP4]
    DB --> A[CSV and Charts]
    DB --> API[FastAPI]
```

## Design decisions

- YOLO is loaded lazily, so the REST API does not need model weights or GPU initialization.
- Ultralytics ByteTrack supplies stable identities while `VehicleCounter` owns counting policy.
- Density means the number of supported vehicles visible in the current frame; type counts are cumulative line crossings.
- SQLite connections are short-lived and parameterized, making CLI and API access safe across threads.
- Configuration is immutable and centralized in `app/config.py`.
