/**
 * Crossmap — Neomnix Healthcare Edition (Chunk 5).
 *
 * The N×N multi-framework overlap matrix was a feature of the
 * pre-refactor cross-mapping engine. After Chunk 2 the engine
 * operates exclusively on the two healthcare frameworks:
 *   - HIPAA-2026
 *   - WA-MHMDA (RCW 19.373.030)
 *
 * SOC2, NIST-800-53, CCM-4.0, SEC-2023 have been removed from the
 * rule engine, the cross-mapping analyzer, the gap analyzer, the
 * PDF report allowlist, and the PDF tier model. As a result there
 * is no longer a meaningful "framework overlap" to visualize —
 * there is exactly one framework pair, and it is identity.
 *
 * This component is kept as a stub so that any old internal links
 * to `/crossmap` still resolve to a clean explanation page rather
 * than a 404. Customer-facing dashboard surfaces do not link here.
 */

import { useTheme } from '@/lib/useTheme';

export default function Crossmap() {
  useTheme();
  return (
    <div
      style={{
        padding: '2rem',
        maxWidth: 720,
        margin: '0 auto',
        fontFamily: 'system-ui, sans-serif',
        color: '#1f2937',
      }}
    >
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
        Framework Cross-Map
      </h1>
      <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
        Bu ozellik kaldirildi. / This feature has been removed.
      </p>

      <section style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '0.5rem' }}>
          Why it was removed
        </h2>
        <p style={{ lineHeight: 1.5 }}>
          The Neomnix platform is now focused exclusively on healthcare
          compliance. The cross-mapping engine no longer produces an
          N x N matrix because there is exactly one framework pair
          in scope, and the overlap is identity.
        </p>
      </section>

      <section style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '0.5rem' }}>
          Supported frameworks
        </h2>
        <ul style={{ listStyle: 'disc', paddingLeft: '1.5rem', lineHeight: 1.7 }}>
          <li>
            <strong>HIPAA-2026</strong> - Health Insurance Portability
            and Accountability Act, current edition.
          </li>
          <li>
            <strong>WA-MHMDA</strong> - Washington My Health My Data
            Act (RCW 19.373.030).
          </li>
        </ul>
      </section>

      <section>
        <h2 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '0.5rem' }}>
          Where to find this information now
        </h2>
        <p style={{ lineHeight: 1.5 }}>
          The compliance posture for each framework is shown directly
          on the Dashboard (Grant Loss Risk Indicator for WA-MHMDA;
          HIPAA Violation Summary for HIPAA-2026). The
          <code style={{ background: '#f3f4f6', padding: '0 0.25rem' }}>
            GET /scans
          </code>
          {' '}endpoint returns the per-scan findings that feed the
          dashboard. Detailed controls are visible inside each
          scan's report.
        </p>
      </section>
    </div>
  );
}
