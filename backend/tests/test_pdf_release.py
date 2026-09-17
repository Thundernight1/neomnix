from src.utils.pdf_exporter import PDFReportExporter


def test_unicode_capture_evidence_and_consecutive_pdfs(tmp_path):
    exporter = PDFReportExporter()
    exporter.output_dir = str(tmp_path)
    findings = [{"severity": "critical", "description": "Telnet — açık bağlantı",
                 "evidence": "192.0.2.10 → 192.0.2.20"}]
    for framework in ("HIPAA-2026", "WA-MHMDA"):
        output = exporter.generate_report(framework, findings, "non_compliant", 1, "test-unicode")
        with open(output, "rb") as pdf:
            assert pdf.read(4) == b"%PDF"
