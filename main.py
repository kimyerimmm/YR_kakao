import os
import json
import zipfile
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

API_KEY = os.getenv("OPENDART_API_KEY", "").strip()
CORP_NAME = "카카오"
CORP_CODE = os.getenv("DART_CORP_CODE", "").strip()  # Optional; Kakao corp code is discovered automatically.
YEARS = [2023, 2024, 2025]
REPORT_CODE = "11011"  # Annual report
BASE = "https://opendart.fss.or.kr/api"
DATA_DIR = Path("docs")
DATA_DIR.mkdir(exist_ok=True)

def get_json(url, params):
    response = requests.get(url, params=params, timeout=40)
    response.raise_for_status()
    return response.json()

def get_corp_code():
    if CORP_CODE:
        return CORP_CODE
    url = f"{BASE}/corpCode.xml"
    response = requests.get(url, params={"crtfc_key": API_KEY}, timeout=60)
    response.raise_for_status()
    if response.content[:2] != b"PK":
        raise RuntimeError("법인코드 파일을 받지 못했습니다. OpenDART 인증키와 API 상태를 확인해 주세요.")
    with zipfile.ZipFile(__import__("io").BytesIO(response.content)) as zf:
        xml_data = zf.read("CORPCODE.xml")
    root = ET.fromstring(xml_data)
    for item in root.findall("list"):
        name = (item.findtext("corp_name") or "").strip()
        stock_code = (item.findtext("stock_code") or "").strip()
        if name == CORP_NAME and stock_code:
            return (item.findtext("corp_code") or "").strip()
    raise RuntimeError("법인코드 목록에서 카카오를 찾지 못했습니다.")

def fetch_year(corp_code, year, fs_div):
    data = get_json(
        f"{BASE}/fnlttSinglAcntAll.json",
        {
            "crtfc_key": API_KEY,
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": REPORT_CODE,
            "fs_div": fs_div,
        },
    )
    if data.get("status") != "000":
        return None, data.get("message", "자료 없음")
    return data.get("list", []), None

def as_number(value):
    if value is None:
        return None
    value = str(value).replace(",", "").strip()
    if value in ("", "-", "－"):
        return None
    try:
        return float(value)
    except ValueError:
        return None

def find_amount(rows, names, period="thstrm_amount"):
    # Match Korean account names returned by OpenDART. Use exact names first, then normalized inclusion.
    normalized = [n.replace(" ", "") for n in names]
    for row in rows:
        account = (row.get("account_nm") or "").replace(" ", "")
        if account in normalized:
            return as_number(row.get(period))
    for row in rows:
        account = (row.get("account_nm") or "").replace(" ", "")
        if any(n in account for n in normalized):
            val = as_number(row.get(period))
            if val is not None:
                return val
    return None

def extract_metrics(rows, year):
    revenue = find_amount(rows, ["영업수익", "매출액", "수익(매출액)", "매출"])
    operating_profit = find_amount(rows, ["영업이익", "영업이익(손실)"])
    net_income = find_amount(rows, ["당기순이익", "당기순이익(손실)", "분기순이익"])
    assets = find_amount(rows, ["자산총계"])
    liabilities = find_amount(rows, ["부채총계"])
    equity = find_amount(rows, ["자본총계"])
    operating_cf = find_amount(rows, ["영업활동현금흐름"])
    investing_cf = find_amount(rows, ["투자활동현금흐름"])
    financing_cf = find_amount(rows, ["재무활동현금흐름"])
    cash = find_amount(rows, ["현금및현금성자산", "현금및현금성자산(현금성자산 포함)"])
    return {
        "year": year,
        "revenue": revenue,
        "operating_profit": operating_profit,
        "net_income": net_income,
        "total_assets": assets,
        "total_liabilities": liabilities,
        "total_equity": equity,
        "operating_cash_flow": operating_cf,
        "investing_cash_flow": investing_cf,
        "financing_cash_flow": financing_cf,
        "cash_and_equivalents": cash,
    }

def ratio(a, b):
    if a is None or b in (None, 0):
        return None
    return round(a / b * 100, 2)

def main():
    if not API_KEY:
        raise RuntimeError("OPENDART_API_KEY가 설정되지 않았습니다. GitHub Secrets에 등록해 주세요.")
    corp_code = get_corp_code()
    output = []
    source_used = {}
    for year in YEARS:
        rows, error = fetch_year(corp_code, year, "CFS")
        fs_div = "CFS"
        if not rows:
            rows, error = fetch_year(corp_code, year, "OFS")
            fs_div = "OFS"
        if not rows:
            print(f"[경고] {year}년 자료를 가져오지 못했습니다: {error}")
            continue
        item = extract_metrics(rows, year)
        item["fs_div"] = fs_div
        output.append(item)
        source_used[str(year)] = fs_div

    output.sort(key=lambda x: x["year"])
    for i, item in enumerate(output):
        item["operating_margin_pct"] = ratio(item["operating_profit"], item["revenue"])
        item["net_margin_pct"] = ratio(item["net_income"], item["revenue"])
        item["debt_ratio_pct"] = ratio(item["total_liabilities"], item["total_equity"])
        avg_equity = None
        if i > 0 and item["total_equity"] is not None and output[i-1]["total_equity"] is not None:
            avg_equity = (item["total_equity"] + output[i-1]["total_equity"]) / 2
        item["roe_pct"] = ratio(item["net_income"], avg_equity)

    payload = {
        "company": CORP_NAME,
        "corp_code": corp_code,
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "unit": "KRW",
        "report_code": REPORT_CODE,
        "financial_statement_basis_by_year": source_used,
        "data": output,
        "notes": [
            "CFS(연결재무제표)를 우선 수집하며, 해당 연도 자료가 없으면 OFS(별도재무제표)를 사용합니다.",
            "연도별 fs_div를 확인해 서로 다른 재무제표 기준이 섞였는지 확인하세요.",
            "ROE는 당기순이익을 기초·기말 평균 자본으로 나눈 값이며, 첫 수집 연도에는 전년도 자본이 없어 계산하지 않습니다.",
            "OpenDART 계정명 차이로 일부 항목이 누락될 수 있습니다. 원문 공시와 대조하세요."
        ]
    }
    (DATA_DIR / "data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"완료: {len(output)}개 연도 데이터를 docs/data.json에 저장했습니다.")

if __name__ == "__main__":
    main()
