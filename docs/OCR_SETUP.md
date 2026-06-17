# Optional OCR Setup

The Gauntlet does not require OCR for the normal local checker. OCR is only
useful when a PDF is made of scanned page images and the extraction preview
shows little or no readable text.

## What V27 Does

V27 detects OCR readiness only. It does not run OCR yet.

The `System Check` page reports:

- whether `tesseract` is available on your `PATH`
- whether optional Python OCR packages are importable
- whether OCR readiness is `available`, `partial`, or `not_installed`

The upload `Extraction Preview` uses that status to explain what to do when a
PDF looks scanned or broken.

## Windows Notes

1. Install Tesseract OCR from a trusted Windows installer or package manager.
2. Add the Tesseract install folder to your `PATH`.
3. Restart the terminal or relaunch `Start-Gauntlet.bat`.
4. Open `System Check` and confirm OCR readiness changed.

Optional Python OCR packages are not part of `requirements.txt`, because the
default GitHub ZIP flow should stay lightweight and non-AI/local-first.

## Current Best Workaround

Until optional OCR processing is added, use one of these paths for scanned PDFs:

- run OCR outside The Gauntlet, then upload the OCR/selectable-text PDF
- export the paper as `.txt`, `.md`, or `.docx`
- copy text from a browser or PDF viewer and use `Paste Text Instead`
