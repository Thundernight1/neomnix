import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LoginScreen from './components/LoginScreen';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('Login screen', () => {
  it('shows session expiry instead of silently redirecting', () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Theme unavailable')));
    render(<MemoryRouter initialEntries={['/login?reason=expired']}><LoginScreen /></MemoryRouter>);
    expect(screen.getByText(/Your session has expired/)).toBeTruthy();
  });

  it('renders server login errors without storing a bearer token', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, json: async () => ({ detail: 'Incorrect credentials' }),
    }));
    const { container } = render(<MemoryRouter><LoginScreen /></MemoryRouter>);
    fireEvent.change(container.querySelector('input[type=email]')!, { target: { value: 'user@example.com' } });
    fireEvent.change(container.querySelector('input[type=password]')!, { target: { value: 'wrong-password' } });
    fireEvent.submit(container.querySelector('form')!);
    expect(await screen.findByText('Incorrect credentials')).toBeTruthy();
    expect(localStorage.getItem('token')).toBeNull();
  });
});
