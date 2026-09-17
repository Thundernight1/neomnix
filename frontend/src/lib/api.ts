export interface ScanRequest {
  target: string;
  scan_type: 'quick' | 'full' | 'compliance';
}

export let API_BASE = import.meta.env.VITE_API_URL || '/api';

// Safety check: Ensure protocol exists if it's not a relative path
if (API_BASE.startsWith('localhost') || API_BASE.startsWith('127.0.0.1')) {
  API_BASE = `http://${API_BASE}`;
}

export const api = {
  async triggerScan(target: string, scanType: string) {
    const response = await fetch(`${API_BASE}/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ target, scan_type: scanType }),
    });
    if (!response.ok) throw new Error('Scan failed to start');
    return response.json();
  }
};
