from __future__ import annotations

from zipfile import ZipFile

from gauntlet_core.share import build_demo_share_pack, build_demo_share_summary, build_share_card_svg, build_x_post


def test_demo_share_pack_contains_public_demo_assets(tmp_path):
    pack_path = tmp_path / "share-pack.zip"
    pack_path.write_bytes(build_demo_share_pack())

    with ZipFile(pack_path) as archive:
        names = set(archive.namelist())
        assert "README.md" in names
        assert "x-post.txt" in names
        assert "x-thread.md" in names
        assert "share-card.html" in names
        assert "share-card.svg" in names
        assert "demo-batch-index.html" in names
        assert "demo-batch-summary.csv" in names
        assert "demo-share-summary.json" in names
        assert "gauntlet-demo-batch-bundle.zip" in names

        x_post = archive.read("x-post.txt").decode("utf-8")
        assert "Start-Gauntlet.bat" in x_post
        assert "https://github.com/Martin123132/The-Gauntlet-" in x_post
        assert len(x_post) <= 280

        readme = archive.read("README.md").decode("utf-8")
        assert "synthetic benchmark papers" in readme
        assert "private uploaded documents" in readme


def test_demo_share_summary_and_card_are_deterministic():
    summary = build_demo_share_summary()
    svg = build_share_card_svg(summary)

    assert summary.paper_count >= 8
    assert summary.analyzed_count == summary.paper_count
    assert summary.high_risk_count > 0
    assert "Local Non-AI" in svg
    assert str(summary.paper_count) in svg
    assert "The Gauntlet is now a local non-AI paper checker demo" in build_x_post()
