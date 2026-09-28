import io
import json
import os
import re
import zipfile
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)

API = "https://opendart.fss.or.kr/api"
CORP_NAME = "오스템임플란트"
STOCK_CODE = "048260"
START_YEAR = 2010
END_YEAR = datetime.now().year

# OpenDART periodic report codes.
REPORT_CODES = {
    "annual": "11011",
    "half-year": "11012",
    "quarterly": "11013",
    "third-quarter": "11014",
}
REPORT_NAMES = {
    "annual": ["사업보고서"],
    "half-year": ["반기보고서"],
    "quarterly": ["1분기보고서"],
    "third-quarter": ["3분기보고서"],
}

# Account aliases are deliberately broad because DART account names/taxonomies
# have changed over time.
ALIASES = {
    "revenue": ["매출액", "수익(매출액)", "영업수익"],
    "gross_profit": ["매출총이익", "매출총손익"],
    "operating_income": ["영업이익", "영업이익(손실)"],
    "net_income": ["당기순이익", "당기순이익(손실)", "분기순이익", "반기순이익"],
    "assets": ["자산총계"],
    "liabilities": ["부채총계"],
    "equity": ["자본총계"],
    "cash": ["현금및현금성자산", "현금 및 현금성자산"],
    "receivables": ["매출채권", "매출채권및기타채권", "매출채권 및 기타채권"],
    "inventory": ["재고자산"],
    "ppe": ["유형자산"],
    "borrowings": ["차입금", "단기차입금", "장기차입금"],
    "cfo": ["영업활동현금흐름", "영업활동으로 인한 현금흐름"],
    "capex": ["유형자산의 취득", "유형자산 취득"],
    "interest_expense": ["이자비용", "금융비용"],
    "ebitda": ["EBITDA"],
}

def key():
    v = os.getenv("DART_API_KEY", "").strip()
    if not v:
        raise RuntimeError("DART_API_KEY is not set. Add it as a GitHub Actions secret.")
    return v

def get_json(endpoint, params):
    p = dict(params)
    p["crtfc_key"] = key()
    r = requests.get(f"{API}/{endpoint}", params=p, timeout=40)
    r.raise_for_status()
    data = r.json()
    if str(data.get("status")) not in ("000", "013"):
        raise RuntimeError(f"OpenDART {endpoint}: {data.get('status')} {data.get('message')}")
    return data

def load_corp_code():
    path = RAW / "corpCode.json"
    if not path.exists():
        p = {"crtfc_key": key()}
        r = requests.get(f"{API}/corpCode.xml", params=p, timeout=40)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        xml = z.read(z.namelist()[0])
        soup = BeautifulSoup(xml, "xml")
        rows = []
        for x in soup.find_all("list"):
            rows.append({
                "corp_code": x.findtext("corp_code", ""),
                "corp_name": x.findtext("corp_name", ""),
                "stock_code": x.findtext("stock_code", ""),
            })
        json.dump(rows, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    rows = json.load(open(path, encoding="utf-8"))
    for row in rows:
        if row.get("stock_code") == STOCK_CODE or row.get("corp_name") == CORP_NAME:
            return row["corp_code"]
    raise RuntimeError("Osstem corporate code was not found.")

def get_filings(corp_code):
    rows = []
    # Query by year so 2010-2014 legacy reports are also discovered.
    for year in range(START_YEAR, END_YEAR + 1):
        bgn = f"{year}0101"
        end = f"{year}1231"
        page = 1
        while True:
            data = get_json("list.json", {
                "corp_code": corp_code,
                "bgn_de": bgn,
                "end_de": end,
                "last_reprt_at": "Y",
                "page_no": page,
                "page_count": 100,
            })
            batch = data.get("list", [])
            rows.extend(batch)
            total_page = int(data.get("total_page", 1) or 1)
            if page >= total_page:
                break
            page += 1

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df[df["report_nm"].fillna("").str.contains("사업보고서|반기보고서|분기보고서", regex=True)]
    df = df.drop_duplicates("rcept_no").sort_values("rcept_dt")
    df.to_csv(PROC / "filings.csv", index=False, encoding="utf-8-sig")
    return df

def download_document(rcept_no):
    out = RAW / f"{rcept_no}.zip"
    if out.exists():
        return out
    r = requests.get(f"{API}/document.xml",
                     params={"crtfc_key": key(), "rcept_no": rcept_no},
                     timeout=60)
    r.raise_for_status()
    # DART returns XML error bodies for failed requests.
    if not r.content[:2] == b"PK":
        try:
            msg = r.text[:500]
        except Exception:
            msg = "unknown response"
        raise RuntimeError(f"document.xml did not return ZIP for {rcept_no}: {msg}")
    out.write_bytes(r.content)
    return out

def normalize_num(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    s = str(x).strip().replace(",", "").replace(" ", "")
    if s in ("", "-", "—", "nan", "None"):
        return np.nan
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    s = re.sub(r"[^0-9.\-]", "", s)
    if not s or s in ("-", "."):
        return np.nan
    try:
        v = float(s)
        return -v if neg else v
    except ValueError:
        return np.nan

def extract_api_accounts(corp_code, year, reprt_code):
    data = get_json("fnlttSinglAcntAll.json", {
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": reprt_code,
        "fs_div": "CFS",
    })
    if str(data.get("status")) == "013":
        data = get_json("fnlttSinglAcntAll.json", {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": reprt_code,
            "fs_div": "OFS",
        })
    return data.get("list", [])

def find_alias(rows, aliases, field):
    for alias in aliases:
        candidates = [r for r in rows if str(r.get("account_nm", "")).strip() == alias]
        if candidates:
            # Prefer consolidated statement rows where available.
            for r in candidates:
                val = normalize_num(r.get(field))
                if not np.isnan(val):
                    return val
    return np.nan

def api_record(corp_code, year, period, reprt_code):
    rows = extract_api_accounts(corp_code, year, reprt_code)
    if not rows:
        return None
    # For income/cash flow, use the accumulated value for half/quarter reports.
    # Annual uses the ordinary term amount.
    accumulated = period in ("half-year", "quarterly", "third-quarter")
    value_field = "thstrm_add_amount" if accumulated else "thstrm_amount"
    r = {"year": year, "period": period, "source": "OpenDART financial API"}
    for metric, aliases in ALIASES.items():
        r[metric] = find_alias(rows, aliases, value_field)
    # Balance sheet figures are point-in-time, so thstrm_amount is preferred.
    for metric in ("assets", "liabilities", "equity", "cash", "receivables",
                   "inventory", "ppe", "borrowings"):
        r[metric] = find_alias(rows, ALIASES[metric], "thstrm_amount")
    return r

def legacy_extract_from_zip(zip_path, filing):
    # 2010-2014: OpenDART structured financial API is not available.
    # Download the original filing and scan tables for account labels.
    z = zipfile.ZipFile(zip_path)
    texts = []
    for name in z.namelist():
        if not re.search(r"\.(xml|xhtml|html|htm)$", name, re.I):
            continue
        raw = z.read(name)
        for enc in ("utf-8", "cp949", "euc-kr"):
            try:
                txt = raw.decode(enc)
                break
            except UnicodeDecodeError:
                txt = ""
        if not txt:
            continue
        soup = BeautifulSoup(txt, "lxml")
        texts.append(soup.get_text(" ", strip=True))
    blob = " ".join(texts)
    blob = re.sub(r"\s+", " ", blob)

    def scan(metric):
        for alias in ALIASES[metric]:
            # Look within 180 chars after the account name.
            m = re.search(re.escape(alias) + r".{0,180}", blob)
            if not m:
                continue
            nums = re.findall(r"[\(\-]?\d[\d,]{2,}(?:\.\d+)?\)?", m.group(0))
            if nums:
                return normalize_num(nums[0])
        return np.nan

    return {
        "year": int(filing["bsns_year"]),
        "period": period_from_report_name(filing["report_nm"]),
        "source": "OpenDART original filing document",
        **{metric: scan(metric) for metric in ALIASES},
    }

def period_from_report_name(name):
    name = str(name)
    if "사업보고서" in name:
        return "annual"
    if "반기보고서" in name:
        return "half-year"
    if "3분기" in name:
        return "third-quarter"
    return "quarterly"

def derive(df):
    if df.empty:
        return df
    df = df.copy()
    for c in ["revenue","gross_profit","operating_income","net_income","assets",
              "liabilities","equity","cash","receivables","inventory","ppe",
              "borrowings","cfo","capex","interest_expense","ebitda"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["gross_margin"] = df["gross_profit"] / df["revenue"] * 100
    df["operating_margin"] = df["operating_income"] / df["revenue"] * 100
    df["net_margin"] = df["net_income"] / df["revenue"] * 100
    df["debt_ratio"] = df["liabilities"] / df["equity"] * 100
    df["current_net_debt"] = df["borrowings"] - df["cash"]
    df["cfo_to_net_income"] = df["cfo"] / df["net_income"]
    df["fcf"] = df["cfo"] - df["capex"].abs()
    df["roe"] = df["net_income"] / df["equity"] * 100
    df["roa"] = df["net_income"] / df["assets"] * 100
    df["roic"] = df["operating_income"] / (df["equity"] + df["current_net_debt"]) * 100
    df["interest_coverage"] = df["operating_income"] / df["interest_expense"].abs()
    df["net_debt_to_ebitda"] = df["current_net_debt"] / df["ebitda"]
    df["revenue_growth"] = df.groupby("period")["revenue"].pct_change() * 100
    return df

def main():
    corp_code = load_corp_code()
    filings = get_filings(corp_code)
    if filings.empty:
        raise RuntimeError("No periodic reports found.")

    records = []
    for _, filing in filings.iterrows():
        name = str(filing.get("report_nm", ""))
        period = period_from_report_name(name)
        year = int(str(filing["bsns_year"]))
        # API financial data is documented from 2015 onward.
        if year >= 2015:
            code = REPORT_CODES[period]
            try:
                rec = api_record(corp_code, year, period, code)
                if rec:
                    rec.update({"rcept_no": filing["rcept_no"], "rcept_dt": filing["rcept_dt"],
                                "report_nm": name, "corp_code": corp_code})
                    records.append(rec)
            except Exception as exc:
                print(f"[WARN] structured API failed {year} {name}: {exc}")
        else:
            try:
                z = download_document(filing["rcept_no"])
                rec = legacy_extract_from_zip(z, filing)
                rec.update({"rcept_no": filing["rcept_no"], "rcept_dt": filing["rcept_dt"],
                            "report_nm": name, "corp_code": corp_code})
                records.append(rec)
            except Exception as exc:
                print(f"[WARN] legacy parse failed {year} {name}: {exc}")

    df = derive(pd.DataFrame(records))
    df = df.sort_values(["year","period","rcept_dt"])
    df.to_csv(PROC / "financials.csv", index=False, encoding="utf-8-sig")
    df.to_json(PROC / "financials.json", orient="records", force_ascii=False, indent=2)
    meta = {
        "company": CORP_NAME,
        "stock_code": STOCK_CODE,
        "corp_code": corp_code,
        "start_year": START_YEAR,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "reports": ["사업보고서","반기보고서","1분기보고서","3분기보고서"],
        "source": "OpenDART",
    }
    json.dump(meta, open(PROC / "meta.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Saved {len(df)} financial rows.")

if __name__ == "__main__":
    main()
