# Project Deployment Report: Writing Analytics & Typing Dynamics Platform

**Course:** Semester 3 Final Research Project  
**Project Title:** Typing Dynamics & Writing Effort: An Explainable Machine Learning Platform  
**Researcher / Student:** Ayesha Cheulkar  
**Date:** September 2026  
**Status:** Live & Deployed in Production  

---

## 1. Executive Summary

This document presents the deployment architecture and live access details for the **Typing Dynamics & Writing Analytics Platform**. 

The platform is an end-to-end research environment designed to capture high-resolution keystroke behavioural dynamics during free-text writing, assess self-reported writing effort on a 1–5 scale, evaluate predictive machine learning models (Random Forest and Linear Regression), and deliver plain-language behavioural explanations using **SHAP (SHapley Additive exPlanations)**.

The entire application is deployed on a dedicated cloud hosting infrastructure with continuous 24/7 availability, persistent transactional database storage, and role-based access security.

---

## 2. Live Access & Deployment URLs

| Portal | URL | Access / Credentials |
| :--- | :--- | :--- |
| **Participant Platform** *(Home / Landing)* | `https://ayeshacheulkar.pythonanywhere.com/` | Public Access |
| **Writing Test & Live Report** | `https://ayeshacheulkar.pythonanywhere.com/test` | Public Access |
| **Researcher / Admin Analytics Portal** | `https://ayeshacheulkar.pythonanywhere.com/admin/login` | **Username:** `admin`<br>**Password:** `admin` |
| **Git Version Control Repository** | `https://github.com/AyeshaCheulkar/typing-dynamics` | Public Academic Repo |

---

## 3. Infrastructure & Deployment Architecture

```
                       [ Public Internet / HTTPS ]
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │             PythonAnywhere Production Server            │
       │                   (Linux / Python 3.10)                 │
       │                                                         │
       │   [ Nginx Reverse Proxy / SSL Termination ]             │
       │                            │                            │
       │   [ WSGI Application Gateway: proto_wsgi.py ]          │
       │                            │                            │
       │   [ Flask Web Framework: prototype_platform/app.py ]    │
       │        │                   │                   │        │
       │        ▼                   ▼                   ▼        │
       │  [ SQLite DB ]    [ ML Model Artifact ]   [ SHAP Engine ]
       │  (prototype.db)     (effort_model.pkl)    (TreeExplainer)
       └─────────────────────────────────────────────────────────┘
```

### Why PythonAnywhere was Selected Over Serverless (e.g. Vercel)
1. **Persistent SQLite File Storage:**  
   The study records live, millisecond-accurate keystroke streams into SQLite database tables (`pt_sessions`, `pt_keystrokes`). Serverless platforms (such as Vercel or AWS Lambda) have read-only, ephemeral filesystems that destroy local database files when the serverless function terminates. PythonAnywhere provides persistent disk storage, ensuring participant data is never lost.
2. **24/7 High-Availability Web Host:**  
   Unlike local tunnels that terminate when a researcher's laptop closes, PythonAnywhere maintains permanent HTTPS availability without requiring local hardware to stay awake.
3. **Scientific Python Stack Support:**  
   Native Linux WSGI support optimized for computation-heavy Python scientific libraries (`scikit-learn`, `numpy`, `scipy`, `pandas`, `shap`, `joblib`).

---

## 4. Platform Modules & Functional Scope

### A. Participant Interface (`/` and `/test`)
* **Writing Test Environment:** Presents standardized writing tasks across difficulty levels (Everyday Writing vs. Describe & Explain).
* **High-Precision Keystroke Logger (`capture.js`):** Intercepts client-side `keydown` events, recording absolute timestamps (in milliseconds), key identities, and caret navigation offsets while enforcing strict data hygiene (disabling external copy-paste and virtual IME tampering).
* **Effort Self-Rating:** Captures the participant's subjective writing effort immediately following submission (1–5 Likert scale).
* **Instant Behavioural & Diagnostic Report (`/report/<session_id>`):** Displays an objective visual timeline of typing bursts, revision intervals, and thinking pauses alongside an experimental effort estimation.

### B. Researcher Analytics Dashboard (`/admin`)
* **Live Session Overview (`/admin/overview`):** Central dashboard summarizing key study performance indicators (total sessions, unique participants, average self-rated effort, pause distributions).
* **Participant Cohort Manager (`/admin/participants`):** Profiles individual participants across repeated sessions to assess intra-subject vs. inter-subject variance.
* **Typing Timeline Inspector:** Renders color-coded, second-by-second behavioural streams (active typing vs. pauses ≥2000 ms vs. deletions/revisions).
* **Research Signals Analysis (`/admin/research`):** Correlates extracted behavioural markers (typing speed, pause ratio, deletion rate, rhythm variability) against self-rated effort via non-parametric Spearman rank correlations.
* **Model Card & Scientific Evaluation (`/admin/model-card`):** Provides transparent reporting of cross-validation pilot benchmarks, permutation tests, and model performance relative to the mean baseline.
* **CSV Data Export (`/admin/export.csv`):** One-click export for downstream statistical processing in R, SPSS, or Python.

---

## 5. Machine Learning & Explainable AI (XAI) Pipeline

The platform incorporates an end-to-end, reproducible machine learning and explainability pipeline:

1. **Feature Extraction Layer (`features.py`):**  
   Transforms raw keystroke event streams into 6 validated behavioural indices:
   * **Typing Speed:** Net characters per second (`chars_per_sec`).
   * **Pause Ratio:** Proportion of session spent in pauses ≥ 2.0 seconds (`pause_time_ratio`).
   * **Deletion Rate:** Proportion of delete and backspace operations (`delete_rate`).
   * **Burst Revisions:** Corrective sequences per 100 keystrokes (`revisions_per_100`).
   * **Rhythm Variability:** Standard deviation of Inter-Keystroke Intervals (`std_iki_ms`).
   * **Long Pause Frequency:** Pauses > 2.0s normalized per 100 keys (`n_long_pause_per_100`).

2. **Model Training & Inference (`train_model.py`, `effort_model.pkl`):**  
   Fits a Random Forest Regressor and a Standardized Linear Regression pipeline using participant-level leave-one-group-out cross-validation.

3. **SHAP Explainability Engine (`explain.py`):**  
   Implements `shap.TreeExplainer` on the fitted Random Forest. For every completed writing session, SHAP calculates exact Shapley values that decompose the model's prediction into positive and negative behavioural drivers, translated automatically into clear English sentences (e.g., *"Typing-rhythm variability lowered the effort estimate (-0.32)"*).

---

## 6. Academic Rigour, Ethics & Security Protections

* **Tri-Concept Separation:**  
  The user interface explicitly demarcates three distinct conceptual layers using consistent visual coding:
  * **Measured Behaviour (Green):** Objective physical facts derived from keystroke timestamps.
  * **Self-Rated Writing Effort (Blue):** The participant's subjective experience.
  * **Experimental Estimated Effort (Amber):** The machine learning model's output, flagged with mandatory disclaimers clarifying that it does *not* diagnose cognitive capacity, mental strain, intelligence, or psychological status.
* **Credential Isolation:**  
  Sensitive administrative credentials and session secrets (`PROTO_ADMIN_USER`, `PROTO_ADMIN_PASSWORD`, `PROTO_SECRET`) are injected via server environment variables rather than hardcoded in the public repository.
* **Privacy & Data Governance:**  
  Participant names and identifying information are excluded from the repository. All data records are referenced strictly through pseudonymized Participant IDs.

---

## 7. Maintenance & Operational Procedures

* **Data Backup:**  
  The SQLite database file (`prototype.db`) can be retrieved at any point directly via PythonAnywhere's Files Manager or downloaded via the admin CSV export.
* **Hot Code Reloading:**  
  Any subsequent analytical adjustments or updates committed to GitHub master can be pulled directly on the server via `git pull` followed by a single-click Web Worker reload on the PythonAnywhere dashboard.

---

*Submitted for academic evaluation as part of Semester 3 Final Research Project requirements.*
