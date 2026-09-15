"""Pull a small, aggregated FLEO extract from impactproject/opm-ehri-data on HuggingFace.

Self-contained: queries HF parquet directly over HTTP with DuckDB (no local HF clone),
filters server-side to the union of all three FLEO definitions (src/fleo_defs.py) so one
pass covers every method the notebook compares, and aggregates by count so the cached
files stay tiny. Window is the last ~13 months of data on HF (2025-07 through 2026-07,
the latest file as of this pull) -- deliberately short; see README for why.
"""
import json
import re
from pathlib import Path

import duckdb
from huggingface_hub import list_repo_files

from fleo_defs import ALL_SERIES_FOR_EXTRACT, ALL_PAY_PLANS_FOR_EXTRACT

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://huggingface.co/datasets/impactproject/opm-ehri-data/resolve/main"
HF_REPO = "impactproject/opm-ehri-data"

WINDOW_START = "202507"  # inclusive
WINDOW_END = "202607"    # inclusive; latest month on HF as of this extract


def build_file_map():
    files = list_repo_files(HF_REPO, repo_type="dataset")
    out = {}
    for kind in ("accessions", "separations", "employment"):
        pat = re.compile(rf"^{kind}/{kind}_(\d{{6}})_v(\d+)\.parquet$")
        best = {}
        for f in files:
            m = pat.match(f)
            if m:
                ym, v = m.group(1), int(m.group(2))
                if ym not in best or v > best[ym][0]:
                    best[ym] = (v, f)
        out[kind] = {ym: fn for ym, (v, fn) in best.items()}
    return out


def urls_in_window(file_map, kind):
    m = file_map[kind]
    return [f"{BASE}/{m[ym]}" for ym in sorted(m) if WINDOW_START <= ym <= WINDOW_END]


def url_list(us):
    return "[" + ",".join(f"'{u}'" for u in us) + "]"


def fleo_filter():
    series = "','".join(sorted(ALL_SERIES_FOR_EXTRACT))
    plans = "','".join(sorted(ALL_PAY_PLANS_FOR_EXTRACT))
    return f"(occupational_series_code IN ('{series}') OR pay_plan_code IN ('{plans}'))"


def run():
    file_map = build_file_map()
    json.dump(file_map, open(ROOT / "data" / "hf_file_map.json", "w"), indent=1)

    con = duckdb.connect()
    con.execute("SET enable_progress_bar=false;")

    # ---- Accessions: new hires + transfers, FLEO-candidate rows, 2025-07..2026-07 ----
    us = urls_in_window(file_map, "accessions")
    print(f"accessions: reading {len(us)} remote files ...", flush=True)
    con.execute(f"""
        COPY (
          SELECT personnel_action_effective_date_yyyymm AS event_ym,
                 agency, agency_code, agency_subelement, agency_subelement_code,
                 accession_category, accession_category_code,
                 pay_plan_code, occupational_series, occupational_series_code,
                 grade, age_bracket, work_schedule,
                 regexp_extract(filename, '_(\\d{{6}})_v', 1) AS file_ym,
                 SUM(TRY_CAST(count AS INT)) AS count
          FROM read_parquet({url_list(us)}, union_by_name=true, filename=true)
          WHERE {fleo_filter()}
          GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12,13,14
        ) TO '{ROOT/'data'/'acc_fleo.parquet'}' (FORMAT parquet);
    """)

    # ---- Separations: departures, FLEO-candidate rows, 2025-07..2026-07 ----
    us = urls_in_window(file_map, "separations")
    print(f"separations: reading {len(us)} remote files ...", flush=True)
    con.execute(f"""
        COPY (
          SELECT personnel_action_effective_date_yyyymm AS event_ym,
                 agency, agency_code, agency_subelement, agency_subelement_code,
                 separation_category, separation_category_code, drp_indicator,
                 pay_plan_code, occupational_series, occupational_series_code,
                 grade, age_bracket, work_schedule,
                 regexp_extract(filename, '_(\\d{{6}})_v', 1) AS file_ym,
                 SUM(TRY_CAST(count AS INT)) AS count
          FROM read_parquet({url_list(us)}, union_by_name=true, filename=true)
          WHERE {fleo_filter()}
          GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
        ) TO '{ROOT/'data'/'sep_fleo.parquet'}' (FORMAT parquet);
    """)

    # ---- Employment: point-in-time headcount, FLEO-candidate rows, 2025-07..2026-07 ----
    us = urls_in_window(file_map, "employment")
    print(f"employment: reading {len(us)} remote files ...", flush=True)
    con.execute(f"""
        COPY (
          SELECT snapshot_yyyymm AS snapshot_ym,
                 agency, agency_code, agency_subelement, agency_subelement_code,
                 pay_plan_code, occupational_series, occupational_series_code,
                 age_bracket, work_schedule,
                 SUM(TRY_CAST(count AS INT)) AS count
          FROM read_parquet({url_list(us)}, union_by_name=true)
          WHERE {fleo_filter()}
          GROUP BY 1,2,3,4,5,6,7,8,9,10
        ) TO '{ROOT/'data'/'emp_fleo.parquet'}' (FORMAT parquet);
    """)

    for f in ("acc_fleo", "sep_fleo", "emp_fleo"):
        n = con.execute(f"SELECT COUNT(*) FROM '{ROOT/'data'/(f+'.parquet')}'").fetchone()[0]
        print(f"  {f}: {n:,} rows")


if __name__ == "__main__":
    run()
