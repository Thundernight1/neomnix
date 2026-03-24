# 🏗️ Architecture & Logic Design

This document describes the internal engineering of the CyberSurX system.

## 1. The "CyberSurX" Pattern (LangGraph)
The core engine uses **Recursive Alignment Logic**. Unlike static scanners, CyberSurX evaluates the confidence of the data it receives.

- **Sensor Node**: Executes Nmap and OWASP ZAP.
- **QC Node**: Analyzes the raw output. If the finding is ambiguous (Confidence < 0.8), it triggers a loop back to the Scanner with higher intensity.
- **Circuit Breaker**: After 3 loops, the system stops to prevent infinite scanning, providing the best available data.

## 2. Compliance Mapping Engine
The `RegulatoryMapper` agent uses a Knowledge Base of standard controls:
- **HIPAA**: Mapped to 45 CFR Part 164.
- **SOC2**: Mapped to Trust Services Criteria.
- **Process**: Mapping happens only after technical findings are high-confidence, ensuring the report is valid for audits.

## 3. Enterprise Security Deck
- **Zero-Trust Backend**: Every API call requires HS256 JWT tokens.
- **ZAP Tunneling**: The ZAP proxy is locked with a generated API key, preventing unauthorized use of the scanner as an attack tool.
- **Database Architecture**: 
  - `ScanJob`: Persists findings, reports, and metadata.
  - `AuditLog`: Immutable record of user activity (WHO, WHAT, WHEN, WHERE).

## 4. Frontend Design System
Built on **Tailwind CSS** and **Shadcn UI**, the interface follows "Avant-Garde" security semantics:
- **Red**: Critical risks/active threats.
- **Blue**: System activity/orchestration.
- **Green**: Compliance achieved.
