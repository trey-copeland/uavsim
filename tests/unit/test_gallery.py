"""Gallery export + base-case document shape."""

from __future__ import annotations

import json
from pathlib import Path

from uavsim.studies import run_nominal_study
from uavsim.viz.gallery import (
    build_gallery_document,
    run_to_gallery_entry,
    write_gallery,
)

ROOT = Path(__file__).resolve().parents[2]


def test_run_to_gallery_and_write(tmp_path: Path) -> None:
    result = run_nominal_study(
        ROOT / "configs" / "studies" / "hover_nominal.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    entry = run_to_gallery_entry(result.run_dir, gallery_id="hover", role="demo")
    assert entry["id"] == "hover"
    assert entry["timeseries"] is not None
    assert len(entry["timeseries"]["t"]) >= 2
    assert "pos_plot" in entry["timeseries"]

    doc = build_gallery_document([entry], title="test")
    out = tmp_path / "gallery"
    # template from repo
    write_gallery(doc, out, copy_app=True, template_dir=ROOT / "docs" / "showcase")
    data = json.loads((out / "data" / "showcase.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["runs"][0]["id"] == "hover"
    assert (out / "index.html").is_file()
    assert (out / "app.js").is_file()
