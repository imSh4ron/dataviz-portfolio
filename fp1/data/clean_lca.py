"""
Clean DOL LCA disclosure data down to data-analyst / data-scientist jobs.

Usage:
    pip install pandas openpyxl
    python clean_lca.py LCA_Disclosure_Data_FY2026_Q1.xlsx LCA_Disclosure_Data_FY2026_Q2.xlsx ...

Outputs (same folder):
    lca_data_jobs_clean.csv   one row per certified data job
    summary_by_employer.csv   top employers
    summary_by_city.csv       median salary by city
"""
import re
import sys

import pandas as pd

COLS = [
    "CASE_STATUS", "VISA_CLASS", "JOB_TITLE", "SOC_CODE", "SOC_TITLE",
    "FULL_TIME_POSITION", "EMPLOYER_NAME", "NAICS_CODE",
    "WORKSITE_CITY", "WORKSITE_STATE",
    "WAGE_RATE_OF_PAY_FROM", "WAGE_RATE_OF_PAY_TO", "WAGE_UNIT_OF_PAY",
    "PREVAILING_WAGE", "PW_UNIT_OF_PAY", "PW_WAGE_LEVEL",
]

# Converts each pay unit to a yearly amount
TO_YEAR = {"Year": 1, "Month": 12, "Bi-Weekly": 26, "Week": 52, "Hour": 2080}


def load(paths):
    frames = []
    for p in paths:
        print(f"Reading {p} (this can take a minute)...")
        df = pd.read_excel(p, usecols=lambda c: c in COLS, dtype=str)
        print(f"  {len(df):,} rows")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def role_of(title, soc=None):
    # Roles are defined by job title only. The SOC code is not used, because many
    # filings use the Data Scientist code (15-2051) for data engineer / ML jobs.
    t = str(title).lower()
    if "data analyst" in t or "business intelligence" in t or "bi analyst" in t:
        return "Data Analyst"
    if "data scientist" in t or "data science" in t:
        return "Data Scientist"
    return None


SUFFIX = re.compile(r"[,\.]|\b(inc|llc|l\.l\.c|corp|corporation|co|ltd|lp|llp|pllc|services|usa|us|na)\b", re.I)


def clean_employer(name):
    n = SUFFIX.sub(" ", str(name).lower())
    n = re.sub(r"\s+", " ", n).strip()
    # Merge common big-company variants
    for key in ["amazon", "google", "meta platforms", "microsoft", "apple", "deloitte", "jpmorgan", "capital one", "wal-mart", "walmart", "tiktok", "bytedance"]:
        if n.startswith(key):
            return key.title()
    return n.title()


def to_yearly(amount, unit):
    try:
        return float(str(amount).replace(",", "").replace("$", "")) * TO_YEAR.get(unit, float("nan"))
    except ValueError:
        return float("nan")


def main(paths):
    df = load(paths)
    start = len(df)

    df = df[(df["CASE_STATUS"] == "Certified") & (df["VISA_CLASS"] == "H-1B")]
    df = df[df["FULL_TIME_POSITION"] == "Y"]
    print(f"Certified, H-1B, full-time: {len(df):,}")

    df["ROLE"] = [role_of(t, s) for t, s in zip(df["JOB_TITLE"], df["SOC_CODE"])]
    df = df[df["ROLE"].notna()].copy()
    print(f"Data analyst / scientist jobs: {len(df):,}")

    df["SALARY"] = [to_yearly(a, u) for a, u in zip(df["WAGE_RATE_OF_PAY_FROM"], df["WAGE_UNIT_OF_PAY"])]
    df["PREVAILING_SALARY"] = [to_yearly(a, u) for a, u in zip(df["PREVAILING_WAGE"], df["PW_UNIT_OF_PAY"])]
    # Drop typos and impossible salaries
    df = df[df["SALARY"].between(30_000, 500_000)]

    df["EMPLOYER"] = df["EMPLOYER_NAME"].map(clean_employer)
    df["CITY"] = df["WORKSITE_CITY"].str.strip().str.title() + ", " + df["WORKSITE_STATE"].str.strip()
    df["ABOVE_PREVAILING_PCT"] = (df["SALARY"] / df["PREVAILING_SALARY"] - 1) * 100

    out = df[["ROLE", "JOB_TITLE", "EMPLOYER", "NAICS_CODE", "CITY", "WORKSITE_STATE",
              "SALARY", "PREVAILING_SALARY", "ABOVE_PREVAILING_PCT", "PW_WAGE_LEVEL"]]
    out.to_csv("lca_data_jobs_clean.csv", index=False)

    by_emp = (out.groupby("EMPLOYER")
                 .agg(jobs=("SALARY", "size"), median_salary=("SALARY", "median"))
                 .sort_values("jobs", ascending=False).head(50))
    by_emp.to_csv("summary_by_employer.csv")

    by_city = (out.groupby(["CITY", "ROLE"])
                  .agg(jobs=("SALARY", "size"), median_salary=("SALARY", "median"))
                  .query("jobs >= 20")
                  .sort_values("median_salary", ascending=False))
    by_city.to_csv("summary_by_city.csv")

    print(f"\nDone: {start:,} raw rows -> {len(out):,} clean rows")
    print(f"Median salary: Analyst ${out[out.ROLE == 'Data Analyst'].SALARY.median():,.0f}, "
          f"Scientist ${out[out.ROLE == 'Data Scientist'].SALARY.median():,.0f}")
    print("\nTop 10 employers:")
    print(by_emp.head(10).to_string())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Give one or more LCA .xlsx files, e.g. python clean_lca.py LCA_Disclosure_Data_FY2026_Q1.xlsx")
    main(sys.argv[1:])
