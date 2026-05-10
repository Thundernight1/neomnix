import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils.pdf_exporter import PDFReportExporter


def test_pdf_exporter_generates_pdf_without_unicode_bullet_error(tmp_path):
    exporter = PDFReportExporter()
    exporter.output_dir = str(tmp_path)
    os.makedirs(exporter.output_dir, exist_ok=True)

    pdf_path = exporter.generate_report(
        framework="HIPAA-2026",
        findings=[
            {
                "severity": "critical",
                "description": "Open Port 23/tcp (telnet)",
                "evidence": "evidence",
                "timestamp": "2026-01-01T00:00:00Z",
            }
        ],
        status="non_compliant",
        confidence=0.95,
        job_id="job-test",
    )

    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 0
