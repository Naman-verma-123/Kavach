# Contributing to KAVACH

First off, thank you for considering contributing to **KAVACH**! Project success depends on clear collaboration, structured workflows, and smooth integration across all module leads.

---

## 1. Team Roles & Assigned Modules

Please refer to the designated module leads before making changes or submitting code to specific sections of the repository:

### 👤 Naman Verma — Frontend & Android Native Lead
* **Primary Scope:** Mobile App UI/UX, Senior-Friendly Accessibility, System Interceptors, Native Bridges.
* **Key Tasks:**
  * Build the 6 core UI screens (Login, Home, WhatsApp Paste, Risk Result, Report Scam, Settings) using HTML5/CSS/JS.
  * Design senior-friendly accessibility elements (high contrast buttons, large typography, minimal steps).
  * Implement Android `BroadcastReceiver` in Kotlin for automatic SMS scanning.
  * Handle unknown APK Intents via Android Intent routing.
  * Integrate JS Interface Bridge for WebView-to-Kotlin background service communication.

---

### 👤 Palak Prajapati — Backend & Scam Intelligence Lead
* **Primary Scope:** Core REST API, Threat Intelligence Integration, AI/LLM Scanners.
* **Key Tasks:**
  * Setup main Python FastAPI server to handle incoming payload requests.
  * Integrate Gemini API / LLM models for natural language scam classification & urgency intent analysis.
  * Write specialized prompt templates to generate simple 2-line explanations and risk scores (High/Medium/Low).
  * Connect Google Safe Browsing API to detect phishing links and malicious URLs.

---

### 👤 Om Pratap Singh — APK Analysis & Database Lead
* **Primary Scope:** Static Malware Analysis, Hashing, Database Storage, FCM Alerts.
* **Key Tasks:**
  * Build Python static analysis pipeline using `Androguard` to parse APK files.
  * Generate SHA-256 hashes and integrate VirusTotal API for reputation checks.
  * Extract dangerous Android permissions (`READ_SMS`, `BIND_ACCESSIBILITY_SERVICE`) and embedded endpoints.
  * Design Firestore / PostgreSQL schema for user logs and Room DB for offline mobile storage.
  * Setup Firebase Cloud Messaging (FCM) engine for real-time family/trusted contact alerts.

---

### 👤 Prameet Singh — Language, Voice, Security & Cloud Lead
* **Primary Scope:** Multi-lingual Localization, Audio Synthesis, Security, DevOps Deployment.
* **Key Tasks:**
  * Maintain 10+ regional language JSON translations and dynamic switching mechanisms.
  * Build AI Text-to-Speech (TTS) pipeline (gTTS / ElevenLabs) to turn explanations into clear audio notes.
  * Implement Firebase Authentication (Mobile OTP) and TLS/SSL App Check tokens.
  * Containerize the backend services using Docker.
  * Deploy backend API to cloud platforms (GCP / Cloud Run / Render) with SSL and domain management.

---

## 2. Git Workflow & Branching Strategy

To keep the main branch stable, please follow these branching guidelines:

1. **Branch Naming:**
   * Features: `feature/<lead-name>-<feature-description>` (e.g., `feature/naman-sms-receiver`, `feature/palak-gemini-api`)
   * Bug fixes: `bugfix/<issue-number>-<short-description>`

2. **Pull Requests (PR):**
   * Do not commit directly to `main`.
   * Open a PR against `main` or `dev` branch once your module task is tested.
   * Tag at least one other team member for PR review before merging.

---

## 3. Local Development Setup

### Backend Setup:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload