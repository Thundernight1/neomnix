/**
 * useTheme — Runtime white-label theme loader for Neomnix GRC.
 *
 * Fetches /theme.json (volume-mounted into Nginx, editable without rebuild).
 * Performs a DEEP merge against DEFAULT_THEME so partial theme.json files
 * (e.g., only overriding primaryColor) do not clobber all other defaults.
 * Applies CSS custom properties to :root consumed by every component.
 */
import { useState, useEffect, useContext, createContext } from 'react';
export const DEFAULT_THEME = {
    platform: {
        name: 'Neomnix GRC',
        shortName: 'Neomnix',
        tagline: 'Enterprise Compliance & Risk Management Platform',
        logoPath: '/logo.svg',
        faviconPath: '/favicon.ico',
        supportEmail: 'support@neomnix.io',
        privacyPolicyUrl: '',
        termsUrl: '',
        copyrightHolder: 'Neomnix, Inc.',
        version: '2.0.0',
    },
    branding: {
        primaryColor: '#3b82f6',
        primaryColorHover: '#2563eb',
        primaryColorDark: '#1d4ed8',
        accentColor: '#8b5cf6',
        accentColorHover: '#7c3aed',
        dangerColor: '#ef4444',
        successColor: '#22c55e',
        warningColor: '#f59e0b',
        backgroundPage: '#020817',
        backgroundSurface: '#0f172a',
        backgroundCard: '#1e293b',
        borderColor: '#334155',
        textPrimary: '#f1f5f9',
        textSecondary: '#94a3b8',
        textMuted: '#64748b',
        fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
        borderRadius: '8px',
    },
    loginPage: {
        headline: 'Secure Compliance & Risk Management',
        subheadline: 'Sign in to access your GRC dashboard',
        showSecurityBadge: true,
        securityBadgeText: 'Protected by Neomnix Security Architecture',
    },
    dashboard: {
        defaultTarget: '',
        welcomeMessage: 'Welcome to Neomnix GRC',
        showAITerminal: true,
        showRadarChart: true,
        showTrendChart: true,
    },
    features: {
        enableAITerminal: true,
        enableCloudScan: true,
        enableAuditLog: true,
        enablePDFReports: true,
        enableUserManagement: true,
    },
};
// ── Deep merge: handles 1-level-deep nested objects ──────────────────────────
function deepMerge(base, override) {
    const result = { ...base };
    for (const key of Object.keys(override)) {
        const baseVal = base[key];
        const overrideVal = override[key];
        if (baseVal !== null &&
            typeof baseVal === 'object' &&
            !Array.isArray(baseVal) &&
            overrideVal !== null &&
            typeof overrideVal === 'object' &&
            !Array.isArray(overrideVal)) {
            result[key] = { ...baseVal, ...overrideVal };
        }
        else if (overrideVal !== undefined) {
            result[key] = overrideVal;
        }
    }
    return result;
}
// ── Apply CSS custom properties to :root ─────────────────────────────────────
export function applyCSSVariables(branding) {
    const root = document.documentElement;
    // Brand palette — consumed by components via var(--brand-*)
    root.style.setProperty('--brand-primary', branding.primaryColor);
    root.style.setProperty('--brand-primary-hover', branding.primaryColorHover);
    root.style.setProperty('--brand-primary-dark', branding.primaryColorDark);
    root.style.setProperty('--brand-accent', branding.accentColor);
    root.style.setProperty('--brand-accent-hover', branding.accentColorHover);
    root.style.setProperty('--brand-danger', branding.dangerColor);
    root.style.setProperty('--brand-success', branding.successColor);
    root.style.setProperty('--brand-warning', branding.warningColor);
    root.style.setProperty('--brand-bg-page', branding.backgroundPage);
    root.style.setProperty('--brand-bg-surface', branding.backgroundSurface);
    root.style.setProperty('--brand-bg-card', branding.backgroundCard);
    root.style.setProperty('--brand-border', branding.borderColor);
    root.style.setProperty('--brand-text-primary', branding.textPrimary);
    root.style.setProperty('--brand-text-secondary', branding.textSecondary);
    root.style.setProperty('--brand-text-muted', branding.textMuted);
    root.style.setProperty('--brand-font', branding.fontFamily);
    root.style.setProperty('--radius', branding.borderRadius);
    // Apply font family to document
    root.style.setProperty('font-family', branding.fontFamily);
}
// ── Apply document meta (title, favicon) ─────────────────────────────────────
function applyDocumentMeta(platform) {
    document.title = platform.name;
    // Update or create favicon link
    let link = document.querySelector("link[rel~='icon']");
    if (!link) {
        link = document.createElement('link');
        link.rel = 'icon';
        document.head.appendChild(link);
    }
    link.href = platform.faviconPath;
}
// ── Module-level session cache ────────────────────────────────────────────────
let _cachedTheme = null;
let _fetchPromise = null;
// ── React Context for theme (avoids triple hook calls) ───────────────────────
export const ThemeContext = createContext(DEFAULT_THEME);
// ── Initialise theme (call once at app root) ──────────────────────────────────
export function initTheme() {
    if (_cachedTheme)
        return Promise.resolve();
    if (_fetchPromise)
        return _fetchPromise;
    _fetchPromise = fetch('/theme.json', { cache: 'no-store' })
        .then((res) => {
        if (!res.ok)
            throw new Error('theme.json not found');
        return res.json();
    })
        .then((data) => {
        const merged = deepMerge(DEFAULT_THEME, data);
        _cachedTheme = merged;
        applyCSSVariables(merged.branding);
        applyDocumentMeta(merged.platform);
    })
        .catch(() => {
        _cachedTheme = DEFAULT_THEME;
        applyCSSVariables(DEFAULT_THEME.branding);
        applyDocumentMeta(DEFAULT_THEME.platform);
    });
    return _fetchPromise;
}
// ── useTheme hook — used by individual components ────────────────────────────
export function useTheme() {
    const [theme, setTheme] = useState(_cachedTheme ?? DEFAULT_THEME);
    const [loading, setLoading] = useState(!_cachedTheme);
    useEffect(() => {
        if (_cachedTheme) {
            setTheme(_cachedTheme);
            setLoading(false);
            return;
        }
        initTheme().then(() => {
            setTheme(_cachedTheme);
            setLoading(false);
        });
    }, []);
    return { theme, loading };
}
// ── Context-based hook (after ThemeContext.Provider is set up) ────────────────
export function useThemeContext() {
    return useContext(ThemeContext);
}
