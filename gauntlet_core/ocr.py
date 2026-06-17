from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from importlib import util
import shutil
import subprocess


OPTIONAL_OCR_PACKAGES = (
    ("pytesseract", "pytesseract"),
    ("Pillow", "PIL"),
    ("pdf2image", "pdf2image"),
)


@dataclass(frozen=True)
class OcrPackageStatus:
    package_name: str
    import_name: str
    available: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OcrReadinessReport:
    status: str
    tesseract_path: str = ""
    tesseract_version: str = ""
    packages: tuple[OcrPackageStatus, ...] = ()

    @property
    def available_package_count(self) -> int:
        return sum(1 for package in self.packages if package.available)

    @property
    def detail(self) -> str:
        package_detail = ", ".join(
            f"{package.package_name}: {'available' if package.available else 'missing'}"
            for package in self.packages
        )
        tesseract_detail = self.tesseract_path or "not found on PATH"
        return f"OCR status {self.status}. Tesseract: {tesseract_detail}. Packages: {package_detail}."

    @property
    def recovery(self) -> str:
        if self.status == "available":
            return "OCR tools are available locally. Future OCR processing can use them for scanned PDFs."
        if self.status == "partial":
            return "OCR is partially installed. Install Tesseract and optional Python OCR packages before relying on OCR for scanned PDFs."
        return "OCR is optional. Install Tesseract only if you need scanned-PDF recovery; the normal checker works without it."

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "tesseract_path": self.tesseract_path,
            "tesseract_version": self.tesseract_version,
            "packages": [package.to_dict() for package in self.packages],
        }


def collect_ocr_readiness(
    tesseract_path: str | None = None,
    package_specs: tuple[tuple[str, str], ...] = OPTIONAL_OCR_PACKAGES,
) -> OcrReadinessReport:
    resolved_tesseract = tesseract_path if tesseract_path is not None else shutil.which("tesseract")
    packages = tuple(
        OcrPackageStatus(package_name=package_name, import_name=import_name, available=util.find_spec(import_name) is not None)
        for package_name, import_name in package_specs
    )
    has_tesseract = bool(resolved_tesseract)
    has_python_bridge = any(package.package_name == "pytesseract" and package.available for package in packages)

    if has_tesseract and has_python_bridge:
        status = "available"
    elif has_tesseract or any(package.available for package in packages):
        status = "partial"
    else:
        status = "not_installed"

    return OcrReadinessReport(
        status=status,
        tesseract_path=resolved_tesseract or "",
        tesseract_version=tesseract_version(resolved_tesseract) if resolved_tesseract else "",
        packages=packages,
    )


@lru_cache(maxsize=8)
def tesseract_version(tesseract_path: str | None) -> str:
    if not tesseract_path:
        return ""
    try:
        completed = subprocess.run(
            [tesseract_path, "--version"],
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
        )
    except Exception:
        return "unknown"
    first_line = (completed.stdout or completed.stderr or "").splitlines()
    return first_line[0].strip() if first_line else "unknown"
