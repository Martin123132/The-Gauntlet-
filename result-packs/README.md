# The Gauntlet Result Packs

Result packs are metadata-only manifests for repeatable public demos. They do
not include papers, PDFs, copied paper text, or downloaded source files.

To run a pack:

```bash
.venv\Scripts\python -m gauntlet_core.cli --result-pack result-packs\landmark-paper-starter.json --papers-dir papers --out gauntlet-reports
```

Place your own lawful local copies in `papers/` using the filenames listed in
the manifest. The generated result bundle contains Gauntlet reports, source
snippets, anchors, and summary tables. It does not contain the original uploaded
paper files or API keys.

The included starter manifest uses famous landmark papers as a seed list for
testing. Links are convenience metadata only; always check source access and
redistribution terms before sharing any paper file.

The Gauntlet license covers this software and its metadata-only manifests. It
does not grant rights to third-party papers, PDFs, datasets, or downloaded
source files. Commercial use of The Gauntlet requires a separate written
commercial license; see `../LICENSE` and `../docs/COMMERCIAL_USE.md`.
