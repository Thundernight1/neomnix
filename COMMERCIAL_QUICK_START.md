# CyberSurX GRC — Commercial Quick Start Guide

> **Version:** 2.0.0 &nbsp;|&nbsp; **Audience:** System Administrators & End Users &nbsp;|&nbsp; **Classification:** Commercial

---

## Table of Contents

1. [Welcome to CyberSurX GRC](#1-welcome-to-cybersurx-grc)
2. [System Requirements](#2-system-requirements)
3. [Installation — Automated Setup](#3-installation--automated-setup)
4. [First Login & Mandatory Password Change](#4-first-login--mandatory-password-change)
5. [Running Your First Compliance Scan](#5-running-your-first-compliance-scan)
6. [Accessing the Audit Log](#6-accessing-the-audit-log)
7. [Downloading PDF Compliance Reports](#7-downloading-pdf-compliance-reports)
8. [White-Label Branding Configuration](#8-white-label-branding-configuration)
9. [Managing Users](#9-managing-users)
10. [Stopping & Restarting the Platform](#10-stopping--restarting-the-platform)
11. [Support & Licensing](#11-support--licensing)

---

## 1. Welcome to CyberSurX GRC

**CyberSurX GRC** is a self-hosted, enterprise-grade Governance, Risk & Compliance (GRC) platform purpose-built for organizations operating under **HIPAA, SOC 2, NIST SP 800-53,** and **ISO 27001** frameworks.

The platform provides:

| Capability | Description |
|---|---|
| **Autonomous Compliance Scanning** | AI-driven network, web application, and cloud posture scanning |
| **Multi-Framework Mapping** | Automatic cross-mapping of findings to HIPAA, SOC 2, and NIST controls |
| **Executive PDF Reports** | Audit-ready compliance reports generated per scan, per framework |
| **Immutable Audit Trail** | Every user action is logged with timestamp, IP, and actor identity |
| **Role-Based Access Control** | Granular `admin`, `analyst`, and `viewer` roles |
| **AI Command Terminal** | Natural-language interface to the compliance scanning engine |
| **White-Label Ready** | Full platform branding customization with no code changes required |

CyberSurX GRC runs entirely within your own infrastructure. No data leaves your network.

---

## 2. System Requirements

### Minimum Requirements

| Component | Requirement |
|---|---|
| **Operating System** | macOS 12+, Ubuntu 20.04+, Debian 11+, Windows 10/11 (64-bit) |
| **CPU** | 4-core, 2.0 GHz |
| **RAM** | 8 GB |
| **Disk Space** | 20 GB free |
| **Network** | Internet access (for initial image pull only) |

### Required Software

| Software | Minimum Version | Download |
|---|---|---|
| **Docker Engine** or **Docker Desktop** | 24.x | [docker.com/get-docker](https://www.docker.com/get-docker) |
| **Docker Compose** (v2 plugin preferred) | 2.20 | Included with Docker Desktop |

### Firewall / Port Requirements

The following local ports must be available:

| Port | Service | Note |
|---|---|---|
| `3000` | Frontend UI (Nginx) | Primary user-facing port |
| `8000` | Backend API (FastAPI) | API and auto-docs |
| `6379` | Redis | Internal only — bind to `127.0.0.1` in production |
| `8080` | OWASP ZAP | Internal scanner — restrict external access |

---

## 3. Installation — Automated Setup

> **Time estimate:** 5–10 minutes (3–5 minutes for image build on first run)

### Linux / macOS

1. Open **Terminal** and navigate to the CyberSurX GRC directory:
   ```bash
   cd /path/to/cybersurx-grc
   ```

2. Make the setup script executable and run it:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. Follow the interactive prompts:
   - **Admin Email** — the email address for your administrator account
   - **Admin Password** — a temporary password (you will be required to change this on first login)
   - **JWT Secret Key** — a cryptographic secret; press ENTER to accept the auto-generated value
   - **LLM Model** — the AI model for compliance analysis

4. The script will:
   - Validate Docker prerequisites
   - Generate a `.env` configuration file
   - Build and start all containers
   - Confirm the platform is healthy
   - Display your access URL and credentials

### Windows

1. Open **File Explorer** and navigate to the CyberSurX GRC folder.
2. Double-click **`setup.bat`**  
   *(If prompted by Windows Defender SmartScreen, click "More info" → "Run anyway")*
3. Follow the interactive prompts as above.
4. The script will automatically open `http://localhost:3000` in your browser when ready.

### Verifying the Installation

After setup completes, confirm all services are running:

```bash
docker compose ps
```

All services should show `Up (healthy)` or `Up` status:

```
NAME              STATUS          PORTS
aegis-api         Up (healthy)    0.0.0.0:8000->8000/tcp
aegis-worker      Up              
aegis-redis       Up (healthy)    0.0.0.0:6379->6379/tcp
aegis-zap         Up              0.0.0.0:8080->8080/tcp
aegis-frontend    Up              0.0.0.0:3000->80/tcp
```

---

## 4. First Login & Mandatory Password Change

### Accessing the Dashboard

Open your browser and navigate to:

```
http://localhost:3000
```

For a remote or server installation, replace `localhost` with the server's IP address or hostname.

### Logging In

1. Enter the **Admin Email** and **Admin Password** you configured during setup.
2. Click **Sign In**.

### Mandatory First-Login Password Change

Upon first login, you will be presented with a **Security Action Required** modal. This is by design — the platform enforces that no default or temporary credentials remain active in production.

You must:
1. Enter your **current (temporary) password**
2. Choose a **new password** meeting the following requirements:
   - Minimum **10 characters**
   - At least one **uppercase letter**
   - At least one **number**
   - At least one **special character** (e.g., `!@#$%^&*`)
3. Confirm the new password
4. Click **Set New Password & Continue**

> **Note:** This modal cannot be dismissed. It must be completed before accessing any platform features.

After a successful password change, you will be redirected to the main dashboard.

---

## 5. Running Your First Compliance Scan

### Initiating a Scan

1. From the **Dashboard**, locate the **Run New Compliance Scan** panel.
2. Select a **Scan Type** from the dropdown:
   | Scan Type | Description |
   |---|---|
   | **Quick Scan** | Lightweight port and service enumeration |
   | **Deep Web Scan** | Full OWASP ZAP active web application scan |
   | **Full Compliance Audit** | Maximum depth; comprehensive framework mapping |
   | **Cloud CSPM** | AWS / Azure cloud posture assessment |
3. Enter a **Target** — an IP address, hostname, or URL (e.g., `https://api.yourapp.com`).
4. Click **START SCAN**.

You will be redirected to the Scan Detail page, which updates in real time.

### Interpreting Results

Once a scan completes, you will see:

- **Compliance Score** — 0-100 score computed from finding severity
- **Findings** — categorized as Critical, High, Medium, or Low
- **Control Mapping** — findings mapped to specific HIPAA / SOC 2 / NIST controls
- **Compliance Verdict** — `compliant` or `non-compliant` determination

> **Scan targets:** Only scan systems and networks you own or have explicit written authorization to test. CyberSurX GRC is a powerful security tool and must be used responsibly.

---

## 6. Accessing the Audit Log

The Audit Log provides a complete, tamper-evident record of all platform activity. It is available to **administrator accounts only**.

1. From any page, click **Audit Logs** in the top navigation bar.
2. The log displays:
   | Field | Description |
   |---|---|
   | **User** | Email of the actor |
   | **Action** | Event type (e.g., `login`, `scan_initiated`, `report_downloaded`) |
   | **Resource** | Affected scan job ID or user ID |
   | **Details** | Contextual metadata |
   | **Timestamp** | UTC timestamp of the event |
   | **IP Address** | Source IP of the request |

3. Up to 500 records are displayed per page. For bulk export, contact your platform administrator or use the API endpoint `GET /audit/logs`.

---

## 7. Downloading PDF Compliance Reports

CyberSurX GRC generates framework-specific executive PDF reports for every completed scan.

1. Navigate to a completed scan's detail page by clicking the scan in the **Recent Activity** table.
2. Locate the **Reports** section.
3. Click the download button for your desired framework:
   - **HIPAA** Report
   - **SOC 2 Type II** Report
   - **NIST SP 800-53** Report
4. The PDF is generated and downloaded to your device.

Reports are branded with your organization's name as configured in `theme.json` and are suitable for direct submission to auditors.

---

## 8. White-Label Branding Configuration

CyberSurX GRC supports full white-labeling. You can change the platform name, tagline, colors, and logo without touching any code or rebuilding Docker images.

### Editing the Theme

1. Open **`theme.json`** in the root of the CyberSurX GRC directory using any text editor.
2. Modify the relevant fields:

   ```json
   {
     "platform": {
       "name": "Your Company GRC",
       "shortName": "Your Company",
       "tagline": "Enterprise Risk Management",
       "supportEmail": "security@yourcompany.com",
       "copyrightHolder": "Your Company, Inc."
     },
     "branding": {
       "primaryColor": "#0070f3",
       "accentColor": "#7c3aed"
     },
     "loginPage": {
       "headline": "Secure. Compliant. Reliable.",
       "securityBadgeText": "Protected by Your Company Security"
     }
   }
   ```

3. Save the file, then apply the changes:
   ```bash
   docker compose restart frontend
   ```

Changes take effect immediately — no rebuild required.

### Replacing the Logo

1. Place your logo file (SVG recommended, or PNG at 2x resolution) in the `frontend/public/` directory. Name it `logo.svg` (or update `logoPath` in `theme.json`).
2. Restart the frontend: `docker compose restart frontend`.

---

## 9. Managing Users

### Creating Additional Users

User management is performed via the API. An administrator can create new users with the following command:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "analyst@yourcompany.com",
    "password": "SecurePassword123!",
    "full_name": "Jane Analyst",
    "role": "analyst"
  }'
```

### User Roles

| Role | Permissions |
|---|---|
| **admin** | Full access; user management; audit logs; all scan operations |
| **analyst** | Initiate scans; view scan results and reports |
| **viewer** | Read-only access to scan results and reports |

### Retrieving Your Admin Token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@cybersurx.io&password=YourPassword"
```

The response will contain an `access_token`. Use this as the `Bearer` token for API calls.

---

## 10. Stopping & Restarting the Platform

### Stop All Services
```bash
docker compose down
```

### Start All Services (without rebuilding)
```bash
docker compose up -d
```

### Restart a Single Service
```bash
docker compose restart api
docker compose restart frontend
docker compose restart worker
```

### View Live Logs
```bash
docker compose logs -f              # All services
docker compose logs -f api          # API only
docker compose logs -f worker       # Celery worker only
```

### Update the Platform

When a new version of CyberSurX GRC is provided:
```bash
docker compose down
docker compose up -d --build
```

> **Data persistence:** Scan results and the user database are stored in the `./backend` volume mount. They are preserved across restarts and updates.

---

## 11. Support & Licensing

### License

This software is provided under the terms of your commercial license agreement. Unauthorized redistribution, modification, or resale is prohibited. See `LICENSE.md` for full terms.

### Technical Support

| Channel | Details |
|---|---|
| **Email** | support@cybersurx.io |
| **Documentation** | Refer to `COMMERCIAL_QUICK_START.md` (this document) |
| **API Reference** | Available at `http://localhost:8000/docs` when the platform is running |

### Data & Privacy

CyberSurX GRC operates entirely within your infrastructure. No scan data, user credentials, or audit logs are transmitted to external services. The only external network calls are:
- Docker image pulls during initial setup (registry.docker.com, ghcr.io)
- LLM API calls to your configured AI provider (if using a cloud LLM model)

---

*CyberSurX GRC v2.0.0 — Confidential Commercial Software*  
*© 2026 CyberSurX, Inc. All Rights Reserved.*
