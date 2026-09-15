"""Shared headline-metrics computation. Both fleo_under30.ipynb (the full analysis)
and fleo_under30_onepager.ipynb (the short summary) import compute_headline() from
here, so the two notebooks' numbers can never drift out of sync with each other.

External citation constants (BJS_TOTAL, GAO_*) live here too -- they're facts read
off a report, not computed by this pipeline, so they can't be "generated," but
centralizing them means every place that cites one reads the same value. Each is
backed by a source-page screenshot in ../sources/ -- see fleo_under30.ipynb Sec. 1b.

2026 is only a partial calendar year. Earlier drafts of this handled that by
annualizing (flat 12/7, later a seasonally-bounded range) -- both required explaining
an assumption. Trailing-twelve-months (TTM) sidesteps that: the 12 months ending at
the latest month are real, already-happened data, not a projection, so no assumption
needs stating at all. Everything here works at monthly grain plus TTM roll-ups.
"""
import pandas as pd

from fleo_defs import METHODS, where_clause

EMP = "data/emp_fleo.parquet"
HIST_ACC, HIST_SEP, HIST_EMP = "data/acc_history.parquet", "data/sep_history.parquet", "data/emp_history.parquet"
HIST_START, HIST_END = "202101", "202607"  # 2021 through the latest month on HF
PROVISIONAL_MONTH = "202607"  # newest file; late-arriving corrections not in yet
PROVISIONAL_MONTH_FMT = f"{PROVISIONAL_MONTH[:4]}-{PROVISIONAL_MONTH[4:]}"
U30 = "age_bracket IN ('LESS THAN 20','20-24','25-29')"
NEW_HIRE = "accession_category LIKE 'NEW HIRE%'"
NOT_TRANSFER_OUT = "separation_category NOT LIKE 'TRANSFER OUT%'"
VALIDATED_METHOD = "narrow_series"  # see fleo_under30.ipynb Sec. 1b for why

# sources/bjs_2023_total.png -- BJS, Federal Law Enforcement Officers, 2023 (p.1)
BJS_TOTAL = 133_798
# sources/gao_0083_total.png -- GAO-25-107099 (p.13)
GAO_0083_TOTAL = 12_600  # ~11,004 standard + 1,612 enhanced retirement, FY2023
# sources/gao_fig4_age.png -- GAO-25-107099, Figure 4 (p.16)
GAO_0083_AGE_STD_PCT = 10   # GS-0083, standard FERS retirement, age 29-and-under
GAO_0083_AGE_ENH_PCT = 20   # GS-0083, enhanced retirement, age 29-and-under
# sources/gao_fig12_attrition.png -- GAO-25-107099, Figure 12 (p.42)
GAO_ATTR_WITHOUT = (12.1, 13.9)  # GS-0083 voluntary attrition FY2019-2023, without enhanced retirement
GAO_ATTR_WITH = (6.9, 10.6)      # GS-0083 voluntary attrition FY2019-2023, with enhanced retirement


def scalar(con, sql):
    """Run a single-value query without the con.execute(sql).fetchone()[0] noise at call sites."""
    return con.execute(sql).fetchone()[0]


def monthly_series(con, table, date_col, extra_where):
    """Raw monthly SUM(count) -- real data, no calendar-year bucketing, no projection."""
    return con.execute(f"""
        SELECT {date_col} AS ym, SUM(count) AS n
        FROM '{table}' WHERE {date_col} BETWEEN '{HIST_START}' AND '{HIST_END}' AND ({extra_where})
        GROUP BY 1 ORDER BY 1
    """).df().set_index("ym")["n"]


def monthly_headcount(con, table, extra_where="1=1"):
    return con.execute(f"""
        SELECT snapshot_ym AS ym, SUM(count) AS n
        FROM '{table}' WHERE ({extra_where})
        GROUP BY 1 ORDER BY 1
    """).df().set_index("ym")["n"]


def as_dt_index(series):
    """YYYYMM string index -> real datetime index, for proper chart tick formatting."""
    out = series.copy()
    out.index = pd.to_datetime(out.index, format="%Y%m")
    return out


def ttm_sum(monthly):
    """Trailing-12-month sum at each point (needs 12 real months of history first)."""
    return monthly.rolling(12).sum().dropna()


def ttm_mean(monthly):
    """Trailing-12-month average at each point (used as the TTM headcount denominator)."""
    return monthly.rolling(12).mean().dropna()


def annual_sum(con, table, date_col, extra_where):
    """Per-calendar-year SUM(count) -- context only (e.g. 'here's what past full years
    looked like'), never used to project 2026; see ttm_sum() for the current pace."""
    return con.execute(f"""
        SELECT LEFT({date_col},4) AS yr, SUM(count) AS n
        FROM '{table}' WHERE {date_col} BETWEEN '{HIST_START}' AND '{HIST_END}' AND ({extra_where})
        GROUP BY 1 ORDER BY 1
    """).df().set_index("yr")["n"]


def compute_headline(con):
    """All numbers behind the Bottom Line: method validation (latest month) + monthly
    and trailing-twelve-month (TTM) series (2021-2026-07), under the validated
    `narrow_series` method except where all three methods are compared."""
    hc_latest, u30_latest = {}, {}
    for name in METHODS:
        w = where_clause(name)
        hc_latest[name] = scalar(con, f"SELECT SUM(count) FROM '{EMP}' WHERE snapshot_ym='{PROVISIONAL_MONTH}' AND ({w})")
        u30_latest[name] = scalar(con, f"SELECT SUM(count) FROM '{EMP}' WHERE snapshot_ym='{PROVISIONAL_MONTH}' AND {U30} AND ({w})")
    vs_bjs = {name: 100 * (hc_latest[name] - BJS_TOTAL) / BJS_TOTAL for name in METHODS}

    series_0083_latest = scalar(
        con, f"SELECT SUM(count) FROM '{EMP}' WHERE snapshot_ym='{PROVISIONAL_MONTH}' AND occupational_series_code='0083'"
    )
    vs_gao_0083 = 100 * (series_0083_latest - GAO_0083_TOTAL) / GAO_0083_TOTAL

    w30 = where_clause(VALIDATED_METHOD)
    hires_m = monthly_series(con, HIST_ACC, "event_ym", f"{NEW_HIRE} AND {U30}")
    seps_m = monthly_series(con, HIST_SEP, "event_ym", f"{NOT_TRANSFER_OUT} AND drp_indicator='N' AND {U30}")
    hc_m = monthly_headcount(con, HIST_EMP, U30)
    allage_seps_m = monthly_series(con, HIST_SEP, "event_ym", f"{NOT_TRANSFER_OUT} AND drp_indicator='N'")
    allage_hc_m = monthly_headcount(con, HIST_EMP)

    # Calendar-year totals, for "here's what a normal full year looked like" context.
    hires_yr = annual_sum(con, HIST_ACC, "event_ym", f"{NEW_HIRE} AND {U30}")
    seps_yr = annual_sum(con, HIST_SEP, "event_ym", f"{NOT_TRANSFER_OUT} AND drp_indicator='N' AND {U30}")

    # Trailing twelve months ending at the latest month -- real data, not a projection.
    hires_ttm = ttm_sum(hires_m)
    seps_ttm = ttm_sum(seps_m)
    hc_ttm_avg = ttm_mean(hc_m)
    allage_seps_ttm = ttm_sum(allage_seps_m)
    allage_hc_ttm_avg = ttm_mean(allage_hc_m)

    attr_rate_ttm = 100 * seps_ttm / hc_ttm_avg
    allage_attr_rate_ttm = 100 * allage_seps_ttm / allage_hc_ttm_avg
    attr_ratio_ttm = attr_rate_ttm / allage_attr_rate_ttm  # monthly-cadence, ~55 points

    return dict(
        hc_latest=hc_latest, u30_latest=u30_latest, vs_bjs=vs_bjs,
        series_0083_latest=series_0083_latest, vs_gao_0083=vs_gao_0083,
        hires_m=hires_m, seps_m=seps_m, hc_m=hc_m,
        allage_seps_m=allage_seps_m, allage_hc_m=allage_hc_m,
        hires_yr=hires_yr, seps_yr=seps_yr,
        hires_ttm=hires_ttm, seps_ttm=seps_ttm, hc_ttm_avg=hc_ttm_avg,
        allage_seps_ttm=allage_seps_ttm, allage_hc_ttm_avg=allage_hc_ttm_avg,
        attr_rate_ttm=attr_rate_ttm, allage_attr_rate_ttm=allage_attr_rate_ttm,
        attr_ratio_ttm=attr_ratio_ttm,
    )
