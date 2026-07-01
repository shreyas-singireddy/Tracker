# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

FitOS takes security seriously. If you discover a security vulnerability, please do NOT file a public issue.

Instead, send a private report to the maintainers.

You should receive a response within 48 hours. If you don't, please follow up.

## Disclosure Policy

- The vulnerability will be investigated and confirmed.
- A fix will be developed and tested.
- A security advisory will be published.
- A patch release will be made available.

## Security Design

FitOS is designed as an **offline-first** application with the following security properties:

- **Zero network calls**: No data ever leaves the device.
- **Local-only storage**: All user data (workouts, nutrition, health metrics) is stored locally in SQLite.
- **No authentication required**: Since the app is fully offline, there is no user authentication system.
- **No external dependencies for runtime**: Only Python standard library and Streamlit for the UI.
- **WAL mode SQLite**: Write-Ahead Logging for safe concurrent access.
- **Parameterized queries**: All database operations use parameterized queries to prevent SQL injection.

## Data Privacy

- All user data remains on the local device.
- No telemetry, analytics, or crash reporting is sent externally.
- No third-party services are accessed.
