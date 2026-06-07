# Neomnix Healthcare Compliance Tracker (PROPRIETARY)

## Overview
Neomnix is an AI-driven Governance, Risk & Compliance (GRC) platform built **exclusively** for the healthcare sector. It automates technical vulnerability mapping strictly against **HIPAA-2026** and **Washington MHMDA (RCW 19.373)** standards.

⚠️ **CONFIDENTIAL & CLOSED SOURCE:** This codebase is proprietary. Unauthorized distribution, copying, modification, or external hosting of this project, via any medium, is strictly prohibited and legally actionable.

## Tech Stack
- **Frontend:** React, TypeScript, Vite, Tailwind CSS
- **Backend:** Python 3, FastAPI, SQLAlchemy
- **AI Engine:** Local LLM integration (Ollama)
- **Infrastructure:** Docker, PostgreSQL, Redis, Celery

## Local Development & Setup

### 1. Start Core Services (Database & Cache)
```bash
docker compose up -d
```
