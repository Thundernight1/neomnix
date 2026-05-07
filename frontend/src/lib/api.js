let API_BASE = import.meta.env.VITE_API_URL || '/api';
// Safety check: Ensure protocol exists if it's not a relative path
if (API_BASE.startsWith('localhost') || API_BASE.startsWith('127.0.0.1')) {
    API_BASE = `http://${API_BASE}`;
}
export const api = {
    async triggerScan(target, scanType) {
        const response = await fetch(`${API_BASE}/scan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target, scan_type: scanType }),
        });
        if (!response.ok)
            throw new Error('Scan failed to start');
        return response.json();
    },
    async executeCommand(command) {
        const response = await fetch(`${API_BASE}/command`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command }),
        });
        if (!response.ok)
            throw new Error('Command failed');
        return response.json();
    }
};
