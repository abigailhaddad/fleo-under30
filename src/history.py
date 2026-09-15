"""Pull a longer (multi-year) FLEO extract, restricted to the validated `narrow_series`
definition only (Sec. 1b of the notebook) -- narrower than extract.py in *series* (7
codes, no pay_plan/broad_series union) but wider in *time* (~5.5 years vs. 13 months),
so the total pull stays small even with column pruning turned off. Feeds the notebook's
year-over-year hiring/attrition comparison.
"""
import json
import re
from pathlib import Path

import duckdb
from huggingface_hub import list_repo_files

from fleo_defs import NARROW_SERIES

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://huggingface.co/datasets/impactproject/opm-ehri-data/resolve/main"
HF_REPO = "impactproject/opm-ehri-data"

HIST_START, HIST_END = "202101", "202607"  # 2021 through the latest month on HF


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
    return [f"{BASE}/{m[ym]}" for ym in sorted(m) if HIST_START <= ym <= HIST_END]


def url_list(us):
    return "[" + ",".join(f"'{u}'" for u in us) + "]"


def series_filter():
    codes = "','".join(sorted(NARROW_SERIES))
    return f"occupational_series_code IN ('{codes}')"


def run():
    file_map = build_file_map()
    json.dump(file_map, open(ROOT / "data" / "hf_file_map_history.json", "w"), indent=1)

    con = duckdb.connect()
    con.execute("SET enable_progress_bar=false;")

    us = urls_in_window(file_map, "accessions")
    print(f"accessions: reading {len(us)} remote files ({HIST_START}-{HIST_END}) ...", flush=True)
    con.execute(f"""
        COPY (
          SELECT personnel_action_effective_date_yyyymm AS event_ym,
                 accession_category, age_bracket,
                 SUM(TRY_CAST(count AS INT)) AS count
          FROM read_parquet({url_list(us)}, union_by_name=true)
          WHERE {series_filter()}
          GROUP BY 1,2,3
        ) TO '{ROOT/'data'/'acc_history.parquet'}' (FORMAT parquet);
    """)

    us = urls_in_window(file_map, "separations")
    print(f"separations: reading {len(us)} remote files ({HIST_START}-{HIST_END}) ...", flush=True)
    con.execute(f"""
        COPY (
          SELECT personnel_action_effective_date_yyyymm AS event_ym,
                 separation_category, drp_indicator, age_bracket,
                 SUM(TRY_CAST(count AS INT)) AS count
          FROM read_parquet({url_list(us)}, union_by_name=true)
          WHERE {series_filter()}
          GROUP BY 1,2,3,4
        ) TO '{ROOT/'data'/'sep_history.parquet'}' (FORMAT parquet);
    """)

    us = urls_in_window(file_map, "employment")
    print(f"employment: reading {len(us)} remote files ({HIST_START}-{HIST_END}) ...", flush=True)
    con.execute(f"""
        COPY (
          SELECT snapshot_yyyymm AS snapshot_ym, age_bracket,
                 SUM(TRY_CAST(count AS INT)) AS count
          FROM read_parquet({url_list(us)}, union_by_name=true)
          WHERE {series_filter()}
          GROUP BY 1,2
        ) TO '{ROOT/'data'/'emp_history.parquet'}' (FORMAT parquet);
    """)

    for f in ("acc_history", "sep_history", "emp_history"):
        n = con.execute(f"SELECT COUNT(*) FROM '{ROOT/'data'/(f+'.parquet')}'").fetchone()[0]
        print(f"  {f}: {n:,} rows")


if __name__ == "__main__":
    run()
