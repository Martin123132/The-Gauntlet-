from __future__ import annotations

from gauntlet_core.ocr import OcrReadinessReport, collect_ocr_readiness


def test_ocr_readiness_reports_not_installed_without_tools():
    report = collect_ocr_readiness(tesseract_path="", package_specs=())

    assert report.status == "not_installed"
    assert "not found on PATH" in report.detail
    assert "normal checker works without it" in report.recovery


def test_ocr_readiness_reports_available_with_tesseract_and_bridge():
    report = collect_ocr_readiness(
        tesseract_path="fake-tesseract",
        package_specs=(("pytesseract", "json"),),
    )

    assert report.status == "available"
    assert report.tesseract_path == "fake-tesseract"
    assert report.packages[0].available
    assert report.to_dict()["status"] == "available"


def test_ocr_readiness_reports_partial_with_python_package_only():
    report = collect_ocr_readiness(
        tesseract_path="",
        package_specs=(("pytesseract", "json"),),
    )

    assert report.status == "partial"
    assert "partially installed" in report.recovery


def test_ocr_readiness_report_serializes_packages():
    report = OcrReadinessReport(status="not_installed")

    assert report.to_dict() == {
        "status": "not_installed",
        "tesseract_path": "",
        "tesseract_version": "",
        "packages": [],
    }
