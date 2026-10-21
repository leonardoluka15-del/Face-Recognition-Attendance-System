# FacePass — Face Recognition Attendance System

A Python attendance prototype with a dark dashboard, browser camera enrolment, CPU face recognition, reviewed check-ins/check-outs, and CSV/Excel reporting.

## Features
- Password-protected administrator workspace
- Consent-based registration with three to ten face samples per person
- OpenCV Haar face detection and LBPH recognition, without external model downloads
- Unknown/ambiguous face rejection and explicit match confirmation
- One check-in and check-out per person per local calendar day
- Manual attendance alternative, department directory, daily metrics and activity chart
- Person deletion cascades to samples and attendance
- SQLite storage; biometric samples are excluded from Git

## Run locally
Python 3.11 or 3.12 recommended.

```bash
python -m venv .venv
# Activate: Windows .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` (never commit it):

```toml
ADMIN_PASSWORD = "replace-with-a-long-unique-password"
```

```bash
streamlit run app.py
```

Open the displayed localhost URL and allow camera access. Enrol a consenting person with at least three distinct photos, then go to Camera attendance, recognise, and confirm the proposed match. No paid AI API is required.

## Run online without installing on your laptop
Deploy this repository using a Streamlit-compatible Python host. Set `app.py` as the entry point and add `ADMIN_PASSWORD` in host secrets. Browser camera access requires HTTPS (or localhost). Hosting is separate from this source repository; this commit does not create a live website.

**Storage:** the default database is `private/attendance.db`. Use persistent storage and set `ATTENDANCE_DB` to its path for durable deployment. Ephemeral hosting may erase records on restart. All app visitors who know the administrator password share the same workspace. Do not use real biometric data on a public demo host.

## Prototype limits
This is snapshot capture, not continuous video. LBPH is a baseline that needs evaluation under your lighting, cameras and population. Its distance is not a confidence percentage. The threshold is configurable; unknown and ambiguous matches are rejected, but false matches remain possible. A single enrolled identity has no competing-identity ambiguity check.

**No liveness or anti-spoofing is implemented.** A printed photo or phone screen may pass. Attendance is confirmed by the operator and must not automatically determine pay, discipline, grades, or access. Multi-camera operation, roles, audit trails, stronger embeddings and validated anti-spoofing remain future work.

Face crops are stored unencrypted in the SQLite database, not the original full photos. Use only a controlled demo with volunteers until access controls, encryption, retention policies and recognition evaluation are completed. Exported attendance contains personal information. Delete enrolments through People when no longer required.

## Tests
```bash
python -m unittest discover -s tests -v
```
