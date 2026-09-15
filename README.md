# Under-30 federal law enforcement: hiring & attrition (OPM/EHRI)

## Bottom line
**As of 2026-07, we estimate ~16,000 federal law enforcement officers are under 30
(12.8% of ~125,000 total)** — using a job-series definition (Police, US Marshal,
Criminal Investigator, General Investigator, Border Patrol, CBP Officer, Correctional
Officer; any pay plan) that lands within **7% of BJS's independent census total**
(133,798, FY2023) and within **2% of GAO's independently audited Police-series count**
alone. Two other candidate definitions — a LEO-specific pay plan, and OPM's full
"Investigation Group" job family — were tested and **rejected**: they missed the same
external benchmarks by 73% and 78%. **Year over year (2021–2026):** in the 12 months
ending 2026-07 — real trailing data, not a projection — under-30 hiring (~7,112) is up
49% from the same window a year earlier and already 40% above the best full calendar
year on record (5,086, in 2025). Under-30 attrition (8.5%) is *not* elevated relative to
history — it sits well inside its historical range, not at a new high. What *is* stable
every month checked: under-30 officers leave at roughly 1.19–1.62x the all-ages rate, a
structural gap, not a new development.

Are federal law enforcement agencies hiring and losing officers under 30 differently
than the rest of the force? And what does "under-30 federal law enforcement officer"
even mean in OPM's data — there's no FLEO flag, so three candidate definitions were
tested and validated against outside sources before trusting any of them. Built from
OPM/EHRI accessions, separations, and employment records
(`impactproject/opm-ehri-data` on HuggingFace), read directly with DuckDB.

## Deliverables
- **`fleo_under30.ipynb`** — the full analysis, start to finish (charts + tables inline).
- **`fleo_under30_onepager.ipynb`** / **`fleo_under30_onepager.pdf`** — just the Bottom
  Line + the year-over-year chart, for handing to someone who wants the answer, not
  the methodology. The PDF is a one-page, code-hidden export of the notebook — dated,
  not a static document, so re-exporting after a data refresh updates the numbers.

## Reproduce
```bash
pip install duckdb pandas matplotlib nbformat nbconvert jupyter huggingface_hub
python src/extract.py          # 13-month FLEO-candidate slice (2025-07→2026-07), all 3 methods -> data/*_fleo.parquet
python src/history.py          # 2021-2026 slice, validated narrow_series only -> data/*_history.parquet
jupyter nbconvert --to notebook --execute --inplace fleo_under30.ipynb
jupyter nbconvert --to notebook --execute --inplace fleo_under30_onepager.ipynb

# PDF export needs Playwright's Chromium (one-time: `playwright install chromium`)
# and, on some installs, JUPYTER_PATH pointed at nbconvert's bundled templates:
JUPYTER_PATH=/opt/homebrew/share/jupyter jupyter nbconvert --to webpdf --no-input \\
  fleo_under30_onepager.ipynb --output fleo_under30_onepager.pdf
```

## Layout
- `src/fleo_defs.py` — the three FLEO definitions (pay plan, narrow job series, broad
  job series), documented with what each catches and misses.
- `src/headline.py` — the external citation constants (`BJS_TOTAL`, `GAO_0083_TOTAL`,
  etc. — each backed by a screenshot in `sources/`) and `compute_headline()`, the
  single function both notebooks call for the Bottom Line numbers, so they can't
  report two different answers to the same question.
- `src/extract.py` — 13-month pull (2025-07→2026-07), the union of all three
  definitions, used to pick a definition (notebook §1/§1b).
- `src/history.py` — 2021→2026-07 pull, `narrow_series` only (the validated
  definition), used for the year-over-year comparison (notebook §5).
- `data/hf_file_map*.json` — deduped max-version HuggingFace file lists each extract reads from.
- `sources/` — screenshots of the exact report pages the cited numbers come from
  (BJS's total, GAO's GS-0083 count, and GAO's Figures 4 and 12) — see notebook §1b.

The notebook's opening data note covers the load-bearing assumptions in one paragraph
— OPM's monthly files are incremental (the newest month is undercounted and shown
dashed), transfers aren't hires or losses, and DRP buyout departures aren't ordinary
attrition.

## Nothing here is hand-typed
Every number in both notebooks is interpolated from a computed value (`display(Markdown(f"..."))`
cells), not written as a literal — rerun the extracts against next month's HF data and
every number updates, Bottom Line included. The only exceptions are the BJS/GAO/CRS
citation numbers themselves (`src/headline.py`), which can't be "generated" since
they're read off a report rather than computed by this pipeline — those are centralized
as named constants and backed by the `sources/` screenshots above, rather than being
retyped at each mention.

## Defining FLEO
No column in OPM's public EHRI extract flags "law enforcement officer" directly, so
the notebook uses three proxies (full rationale in `src/fleo_defs.py`):

| Method | Definition | Headcount (2026-07) | Under-30 share |
|---|---|---|---|
| `pay_plan` | `pay_plan_code = 'GL'` — OPM's own label: *"...PAID A LAW ENFORCEMENT OFFICER SPECIAL BASE RATE UNDER SECTION 403 OF THE FEDERAL LAW ENFORCEMENT PAY REFORM ACT OF 1990"* | ~35.6k | 29.2% |
| `narrow_series` | Sworn/arrest-authority job series: Police, US Marshal, Criminal Investigator, General Investigator, Border Patrol, CBP Officer, Correctional Officer | ~124.9k | 12.8% |
| `broad_series` | `narrow_series` + the rest of OPM's Investigation Group (general inspectors, compliance staff, EEO investigators, safety inspectors) | ~238.3k | 12.5% |

`age_bracket` is exact 5-year bands in this data, so "under 30" itself is clean
(`LESS THAN 20` + `20-24` + `25-29`) — the ambiguity is entirely in what counts as FLEO,
not in the age cut.

## How this compares to authoritative definitions (Notebook Sec. 1b)
None of the three proxies above is reproducing a single ground-truth field — there
isn't one, even outside this dataset. Per **CRS Report R42631** (*Retirement Benefits
for Federal Law Enforcement Personnel*, Aug. 8, 2024), the statutory "law enforcement
officer" test for retirement purposes (5 U.S.C. §8331(20)/§8401(17)) turns on a
position's *primary duties*, and explicitly "does not depend ... on the classification
of a position within an occupational series" — which the report says "has excluded
police officers, guards, and inspectors from the definition of LEO." **GAO-25-107099**
(*Federal Police Officers: Considerations on Retirement and Pay*, Apr. 2025) documents
this gap empirically: ~12,600 federal police officers (GS-0083) spread across nine
different pay plans, mostly without statutory LEO retirement coverage — so our
`narrow_series`'s inclusion of Police (0083) is a sworn/arrest-authority proxy, not a
literal match to the statutory definition. GAO also reports GS-0083 age and attrition
splits that bracket our own numbers: 10% of standard-retirement 0083 officers vs. 20%
of enhanced-retirement (GL-correlated) 0083 officers were age 29-and-under in FY2023,
and voluntary attrition ran 6.9%–13.9%/year FY2019–2023 — both in the same direction
and rough range as our `pay_plan` vs. `narrow_series` gap and our own attrition rates.
The **Bureau of Justice Statistics'** Census of Federal Law Enforcement Officers uses a
functional test instead ("authorized to make arrests, carry firearms, or both") and
counted 133,798 full-time officers across 88 agencies in FY2023 (*Federal Law
Enforcement Officers, 2023 – Statistical Tables*, May 2026) — landing almost exactly
between our `narrow_series` (~125k) and `broad_series` (~238k) headcounts, but with no
age breakdown published, which is the gap this notebook fills.

**References:** 5 U.S.C. §8331(20), §8401(17); 5 C.F.R. §831.802, §831.920, §842.802,
§3307(e) • CRS R42631 (Aug. 8, 2024) • GAO-25-107099 (Apr. 2025) • BJS, *Federal Law
Enforcement Officers, 2023 – Statistical Tables* (May 2026) • OPM, *Federal Law
Enforcement Pay and Benefits, Report to the Congress* (July 2004).

## Headline findings
Under `narrow_series` (the validated definition — see Bottom Line above), under-30
officers are ~12.8% of the FLEO workforce as of 2026-07, and attrition in this slice
is almost entirely voluntary quits rather than retirement (unsurprising under 30).

**Year over year (2021–2026, notebook §5):** rather than bucketing by calendar year —
which would need guessing the rest of a still-partial 2026 — §5 works at monthly grain
plus **trailing-twelve-months (TTM)**: the 12 real months ending at each point, never a
projection. Trailing-12-month headcount rose from ~12,060 (ending 2021-12) to ~14,400
(ending 2026-07), ~20%. Hiring in the last 12 months (~7,112) is up 49% year-over-year
and already 40% above the best *full calendar year* on record (5,086, in 2025) — no
seasonal assumption needed, since it's 12 months that already happened. Sec. 3 shows
DHS accounts for ~70% of recent under-30 hires, so this reads as a continuation of
DHS's broader hiring push rather than a separate signal. Attrition is *not* elevated
relative to history despite the hiring surge: the trailing-12-month under-30 rate has
moved in a ~7.1–11.5% band throughout 2021–2026, and today's 8.5% sits well inside it,
not at a new high. The one constant throughout: under-30 attrition runs ~1.19–1.62x the
all-ages rate every month checked — a structural feature of this workforce, not a
2025–2026 development.

**Still open:** this is a headcount/flow read, not cohort survival — "attrition rate"
here is separations-over-headcount for a given year, not "what share of people hired
under 30 in 2021 are still there." That needs individual-level tenure data this
public extract doesn't carry.
