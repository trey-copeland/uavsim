"""Gallery export + base-case document shape."""

from __future__ import annotations

import json
from pathlib import Path

from uavsim.studies import run_nominal_study
from uavsim.viz.gallery import (
    build_gallery_document,
    generate_base_case_gallery,
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


def test_generate_base_case_gallery_smoke(tmp_path: Path) -> None:
    """Smoke: full portfolio matrix configs run; metrics honesty for AHRS vs flow."""
    path = generate_base_case_gallery(
        repo_root=ROOT,
        out_dir=tmp_path / "showcase",
        runs_tmp=tmp_path / "runs",
        max_points=40,
        n_mc_trials=2,
        skip_envelope=True,
    )
    doc = json.loads(path.read_text(encoding="utf-8"))
    ids = {r["id"] for r in doc["runs"]}
    assert "figure_eight_lqr" in ids
    assert "flow_alt_lqg" in ids
    assert "gps_imu_lqg" in ids
    assert "gps_imu_lqg_mc" in ids
    assert doc.get("estimation_matrix") is not None
    by_id = {s["id"]: s for s in doc["estimation_matrix"]["scenarios"]}
    assert by_id["flow_alt_lqg"]["metrics"]["success"] is True
    assert float(by_id["flow_alt_lqg"]["metrics"]["rmse_position_m"]) < 0.15
    # Multi-meter AHRS path must not report success after 3× bound rule
    assert by_id["ahrs_lqg"]["metrics"]["success"] is False
    assert "time_in_bounds_frac" in by_id["flow_alt_lqg"]["metrics"]
