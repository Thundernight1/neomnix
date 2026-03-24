# Automated Compliance Testing with TestSprite

This project is configured for automated validation using the **TestSprite MCP Agent**.

## 1. Setup (One-Time)

To enable the TestSprite agent in your IDE (Cursor/VS Code), add the following configuration to your MCP settings:

**File:** `~/.config/Cursor/User/globalStorage/mcp-servers.json` (or via IDE Settings > MCP)

```json
{
  "mcpServers": {
    "TestSprite": {
      "command": "npx",
      "args": [
        "@testsprite/testsprite-mcp@latest"
      ],
      "env": {
        "API_KEY": "sk-user-VAapAHyF1T0fq36fo1a0HbSCZ8ADmaTb1FuYZKgzI1-HRwBUCAZkDxXqJfG1W-fxmrhae9PNabAKjPO-SlhZvYWIOyu04OcywbRbdWnThhThR8nhuJArNrDpuLqL_oVvwwA"
      }
    }
  }
}
```

> **Note:** The API Key is pre-configured for this project environment.

## 2. Preparing the Environment

Before running tests, ensure the full stack is running:

```bash
docker-compose up --build -d
```

## 3. Running a Test

1. Open **Cursor Chat** (Command+L).
2. Type the following prompt:
   > "Can you test the Scan Trigger form on the Dashboard?"
3. TestSprite will ask for configuration. Use these values:

| Setting | Value |
| :--- | :--- |
| **Testing Type** | `Frontend` (for UI) or `Backend` (for API) |
| **Frontend URL** | `http://localhost:3000` |
| **Backend URL** | `http://localhost:8000` |
| **Credentials** | *Leave empty* (No auth required yet) |

## 4. Expected Validation Outcomes

TestSprite will automatically:

1. **Analyze** the `Dashboard.tsx` component.
2. **Generate** a test plan for the "Target URL" and "Scan Type" inputs.
3. **Execute** the integration with the real backend API.
4. **Report** any UI bugs or API connection failures.
