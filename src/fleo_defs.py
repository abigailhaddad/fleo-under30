"""Three ways to define "Federal Law Enforcement Officer" (FLEO) in OPM/EHRI data.

There is no single FLEO flag in the data (no retirement-plan-code or LEO-indicator
column) -- and per the authoritative sources below, there isn't a clean one anywhere:
statutory LEO status is a *position-duties* determination made case by case, explicitly
independent of job series or pay plan. See notebook Sec. 1b for the full citations and
how each method below maps onto (and diverges from) those authoritative definitions.
This file documents three defensible, non-overlapping-in-method proxies, and the
notebook runs the whole analysis under all three to check whether the headline story
changes.

1. PAY_PLAN -- pay_plan_code == 'GL'. OPM's own label for this plan is "... PAID A LAW
   ENFORCEMENT OFFICER SPECIAL BASE RATE UNDER SECTION 403 OF THE FEDERAL LAW ENFORCEMENT
   PAY REFORM ACT OF 1990." GAO-25-107099 (2025) confirms GL correlates with (but is not
   identical to) the "enhanced retirement benefits" (statutory LEO / 6(c)) cohort. Caveat:
   GL only covers GS-3-10 uniformed positions (Border Patrol, CBP Officers, Police). GS-11+
   criminal investigators/special agents (FBI, DEA, Secret Service, IRS-CI, etc.) keep
   pay_plan_code 'GS' under Law Enforcement Availability Pay, and other enhanced-retirement
   uniformed forces sit on their own plans (LE = Secret Service Uniformed Division, SP =
   Park Police, TR = Mint/BEP Police, PQ = GPO Police) -- all invisible to this method. It
   also picks up some apparent non-LEO GL-coded support staff (see Sec. 1 in the notebook).

2. NARROW_SERIES -- sworn/uniformed occupational series, any pay plan:
     0083 Police              0082 United States Marshal
     1811 Criminal Investigation   1810 General Investigation
     1896 Border Patrol Enforcement   1895 Customs and Border Protection
     0007 Correctional Officer
   Catches GS-11+ special agents (pay_plan GS) and non-GL uniformed forces (LE/SP/TR/PQ)
   that PAY_PLAN misses. IMPORTANT DIVERGENCE FROM THE STATUTORY DEFINITION: CRS R42631
   states plainly that OPM's administrative LEO determination "does not depend ... on the
   classification of a position within an occupational series," and that this "has
   excluded police officers, guards, and inspectors from the definition of LEO for federal
   retirement purposes" -- i.e., 0083 Police is generally NOT a statutory LEO series (GAO
   -25-107099 is a whole report about this gap). 0007 (BOP) and 1895 (CBP Officers) *are*
   covered, but via separate direct legislation, not the general 6(c) test. So this method
   is better read as "sworn/arrest-authority job families" than "statutory LEO."

3. BROAD_SERIES -- NARROW_SERIES plus the rest of OPM's "Investigation Group" (job family
   1800): general inspectors, compliance/import staff, equal-opportunity investigators,
   mine-safety and aviation-safety inspectors, etc. Closer in spirit to BJS's Census of
   Federal Law Enforcement Officers (functional test: authorized to make arrests and/or
   carry firearms) than to the statutory retirement definition, though it still both
   overshoots BJS (unarmed compliance inspectors) and undershoots it (BJS-counted forces
   like Capitol Police / Supreme Court Police / Park Police / Secret Service Uniformed
   Division sit outside both this series list and the GL pay plan).

Pick the method by name; see notebook Sec. 1 for row/headcount counts per method and the
pairwise overlap between them, and Sec. 1b for how each compares to CRS/GAO/BJS numbers.
"""

PAY_PLAN_CODES = {"GL"}

NARROW_SERIES = {
    "0083",  # Police
    "0082",  # United States Marshal
    "1811",  # Criminal Investigation
    "1810",  # General Investigation
    "1896",  # Border Patrol Enforcement
    "1895",  # Customs and Border Protection
    "0007",  # Correctional Officer
}

_INVESTIGATION_GROUP_REST = {
    "1801",  # General Inspection, Investigation, Enforcement, and Compliance
    "1802",  # Compliance Inspection and Support
    "1805",  # Investigative Analysis
    "1822",  # Mine Safety and Health Inspection
    "1825",  # Aviation Safety
    "1860",  # Equal Opportunity Investigation
    "1862",  # Consumer Safety Inspection
    "1881",  # Customs and Border Protection Interdiction
    "1889",  # Import Compliance
    "1894",  # Customs Entry and Liquidating
}

BROAD_SERIES = NARROW_SERIES | _INVESTIGATION_GROUP_REST

METHODS = {
    "pay_plan": {
        "label": "Pay plan (GL = LEO special base rate; correlates with, not identical to, statutory LEO)",
        "series": None,
        "pay_plan": PAY_PLAN_CODES,
    },
    "narrow_series": {
        "label": "Narrow job series (sworn / arrest authority)",
        "series": NARROW_SERIES,
        "pay_plan": None,
    },
    "broad_series": {
        "label": "Broad job series (full Investigation Group 1800)",
        "series": BROAD_SERIES,
        "pay_plan": None,
    },
}


def where_clause(method):
    """SQL WHERE fragment (no leading WHERE/AND) selecting FLEO rows for a method."""
    m = METHODS[method]
    if m["pay_plan"] is not None:
        codes = "','".join(sorted(m["pay_plan"]))
        return f"pay_plan_code IN ('{codes}')"
    codes = "','".join(sorted(m["series"]))
    return f"occupational_series_code IN ('{codes}')"


ALL_SERIES_FOR_EXTRACT = BROAD_SERIES  # widest set worth pulling from HF
ALL_PAY_PLANS_FOR_EXTRACT = PAY_PLAN_CODES
