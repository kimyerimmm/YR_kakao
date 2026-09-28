import json, html
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE/"data/processed/financials.csv"
OUT = BASE/"dashboard/index.html"
df = pd.read_csv(DATA) if DATA.exists() else pd.DataFrame()
if not df.empty:
    df = df.sort_values(["year","period"])
meta = json.load(open(BASE/"data/processed/meta.json",encoding="utf-8")) if (BASE/"data/processed/meta.json").exists() else {}

def fmt(x):
    try:
        if pd.isna(x): return "—"
        return f"{x:,.0f}"
    except: return "—"
def pct(x):
    try:
        if pd.isna(x): return "—"
        return f"{x:.1f}%"
    except: return "—"

latest = df.iloc[-1] if not df.empty else pd.Series()
annual = df[df.period=="annual"].tail(15)
half = df[df.period=="half-year"].tail(15)
quarter = df[df.period.isin(["quarterly","third-quarter"])].tail(20)

def rows(frame):
    if frame.empty: return "<tr><td colspan='8'>데이터가 없습니다.</td></tr>"
    cols=["year","period","revenue","operating_income","net_income","cfo","assets","equity"]
    return "".join(
        f"<tr><td>{int(r.year)}</td><td>{html.escape(str(r.period))}</td>"
        f"<td>{fmt(r.revenue)}</td><td>{fmt(r.operating_income)}</td>"
        f"<td>{fmt(r.net_income)}</td><td>{fmt(r.cfo)}</td>"
        f"<td>{fmt(r.assets)}</td><td>{fmt(r.equity)}</td></tr>"
        for _,r in frame.iterrows()
    )

# Simple inline SVG charts: no external JS dependency, so GitHub Pages remains robust.
chart = ""
if len(annual)>=2:
    x=list(range(len(annual)))
    vals=pd.to_numeric(annual["revenue"],errors="coerce").fillna(0).tolist()
    mx=max(vals) or 1
    pts=" ".join(f"{40+i*600/max(1,len(vals)-1)},{220-(v/mx)*170:.1f}" for i,v in enumerate(vals))
    labels="".join(f"<text x='{40+i*600/max(1,len(vals)-1):.1f}' y='250' text-anchor='middle'>{int(y)}</text>" for i,y in enumerate(annual.year))
    chart=f"""<svg viewBox='0 0 680 280' role='img' aria-label='연도별 매출 추이'>
      <polyline points='{pts}' fill='none' stroke='#174f42' stroke-width='4'/>
      {labels}<text x='20' y='25' font-size='14'>Revenue trend</text></svg>"""
else:
    chart="<div class='empty'>연도별 데이터가 쌓이면 매출 추이 그래프가 표시됩니다.</div>"

peer_rows = [
("덴티움","145720","치과용 임플란트 및 관련 솔루션"),
("디오","039840","치과용 임플란트·디지털 치과 솔루션"),
("네오바이오텍","—","국내 치과 임플란트·치과용 솔루션"),
("메가젠임플란트","—","국내 치과 임플란트 제조·판매"),
]
peer_html="".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a,b,c in peer_rows)

OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'><title>OSSTEM Financial Dashboard</title>
<style>
:root{{--g:#174f42;--g2:#2e705e;--b:#f2e8d9;--p:#fffaf2;--ink:#20342e;--muted:#718078;--line:#d9cdbd}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--b);color:var(--ink);font-family:Inter,system-ui,'Noto Sans KR',sans-serif}}
header{{background:var(--g);color:white;padding:54px 7vw 44px}}header h1{{font-family:Georgia,serif;font-size:clamp(38px,6vw,72px);font-weight:500;margin:10px 0}}header p{{color:#d5e4dd;max-width:800px;line-height:1.7}}
main{{max-width:1250px;margin:auto;padding:35px 5vw 80px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin:0 0 25px}}
.card,section{{background:var(--p);border:1px solid var(--line);border-radius:20px;padding:22px}}.label{{font-size:11px;letter-spacing:.14em;color:var(--muted)}}.big{{font-size:30px;font-weight:800;margin-top:12px}}
.grid{{display:grid;grid-template-columns:1.3fr .7fr;gap:20px;margin:20px 0}}svg{{width:100%;height:auto}}h2{{font-family:Georgia,serif;font-weight:500;font-size:32px;margin:0 0 18px}}
.tablewrap{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:11px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}}th{{color:var(--muted);font-size:11px;letter-spacing:.06em}}
.tabs{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:15px}}.pill{{background:#e6ddd0;border-radius:999px;padding:8px 12px;font-size:11px}}.note{{color:var(--muted);font-size:12px;line-height:1.7}}.empty{{padding:35px;color:var(--muted)}}
footer{{background:var(--g);color:#c7d8d0;padding:28px 7vw;font-size:12px}}a{{color:inherit}}@media(max-width:800px){{.cards,.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<header><div class='label'>OPEN DART · AUTOMATED FINANCIAL ANALYSIS</div>
<h1>OSSTEM Financial Dashboard</h1>
<p>2010년부터 사업보고서·반기보고서·분기보고서를 수집하고, 재무제표 주요 수치와 성장성·수익성·현금흐름·차입 부담·투자수익률 지표를 자동 계산하는 GitHub Pages 대시보드입니다.</p>
</header><main>
<div class='cards'>
<div class='card'><div class='label'>LATEST REVENUE</div><div class='big'>{fmt(latest.get("revenue",float("nan")))}</div></div>
<div class='card'><div class='label'>OPERATING MARGIN</div><div class='big'>{pct(latest.get("operating_margin",float("nan")))}</div></div>
<div class='card'><div class='label'>CFO</div><div class='big'>{fmt(latest.get("cfo",float("nan")))}</div></div>
<div class='card'><div class='label'>ROE</div><div class='big'>{pct(latest.get("roe",float("nan")))}</div></div>
</div>
<div class='grid'><section><h2>Revenue Trend</h2>{chart}</section>
<section><h2>Analysis Flow</h2><div class='tabs'><span class='pill'>01 매출 성장</span><span class='pill'>02 이익률</span><span class='pill'>03 현금흐름</span><span class='pill'>04 차입 부담</span><span class='pill'>05 투자수익률</span><span class='pill'>06 주가 수준</span></div><p class='note'>금액과 비율을 함께 보고, 추세와 비교 대상을 통일하는 분석 원칙을 적용합니다.</p></section></div>
<section><h2>Annual</h2><div class='tablewrap'><table><thead><tr><th>Year</th><th>Period</th><th>Revenue</th><th>Operating income</th><th>Net income</th><th>CFO</th><th>Assets</th><th>Equity</th></tr></thead><tbody>{rows(annual)}</tbody></table></div></section>
<section style='margin-top:20px'><h2>Half-year</h2><div class='tablewrap'><table><thead><tr><th>Year</th><th>Period</th><th>Revenue</th><th>Operating income</th><th>Net income</th><th>CFO</th><th>Assets</th><th>Equity</th></tr></thead><tbody>{rows(half)}</tbody></table></div></section>
<section style='margin-top:20px'><h2>Quarterly</h2><div class='tablewrap'><table><thead><tr><th>Year</th><th>Period</th><th>Revenue</th><th>Operating income</th><th>Net income</th><th>CFO</th><th>Assets</th><th>Equity</th></tr></thead><tbody>{rows(quarter)}</tbody></table></div></section>
<section style='margin-top:20px'><h2>Domestic Peer Firms</h2><p class='note'>국내 치과 임플란트·디지털 치과 솔루션 시장에서 비교 대상으로 사용할 수 있는 기업입니다. 비상장사는 종목코드를 비워 두었습니다.</p>
<div class='tablewrap'><table><thead><tr><th>기업</th><th>종목코드</th><th>주요 사업</th></tr></thead><tbody>{peer_html}</tbody></table></div></section>
</main><footer>Data source: OpenDART · Updated automatically on the 1st of every month · <a href='https://opendart.fss.or.kr/'>OpenDART</a></footer>
</body></html>""", encoding="utf-8")
