# OSSTEM DART Financial Analysis Agent

[![Dashboard](https://fonts.gstatic.com/s/e/notoemoji/17.0/1f517/32.png)](https://kimyerimmm.github.io/YR_osstem/)

## 🔗 대시보드 바로가기
[![Dashboard 바로가기](https://fonts.gstatic.com/s/e/notoemoji/17.0/1f517/32.png)](https://kimyerimmm.github.io/YR_osstem/)

오스템임플란트의 DART 정기보고서를 자동 수집하고, 주요 재무수치와 재무비율을 계산하여 GitHub Pages 대시보드로 보여주는 프로젝트입니다.

## 대상
- 기업: 오스템임플란트
- 종목코드: 048260
- 수집 시작: 2010년
- 보고서: 사업보고서 / 반기보고서 / 1분기보고서 / 3분기보고서
- 자동 실행: 매월 1일 09:00 (Asia/Seoul)

## 분석 지표
첨부된 「재무제표 및 재무비율 실무 가이드」의 구조를 반영했습니다.

1. 매출 성장: 매출증가율
2. 이익률: 매출총이익률, 영업이익률, 순이익률
3. 현금흐름: CFO, CFO/순이익, FCF, CCC 관련 원천자료
4. 차입 부담: 순차입금, 순차입금/EBITDA, 이자보상배율
5. 투자수익률: ROIC, ROE, ROA
6. 주가 수준: PER, PBR, EV/EBITDA 등 확장 가능한 구조

금액과 비율을 함께 보고 추세와 비교 대상을 통일한다는 원칙을 사용합니다.

## 2010~2014 데이터
OpenDART의 구조화된 단일회사 재무제표 API는 2015년 이후 사업연도부터 제공되므로, 2010~2014년은 OpenDART `document.xml` 원문 API로 정기보고서를 내려받아 주요 계정명을 탐색하는 레거시 경로를 사용합니다. 과거 보고서는 회계기준·표현이 달라 일부 항목이 비어 있을 수 있으므로 `data/processed/financials.csv`에서 결측 여부를 확인하세요.

## API 키 설정
1. OpenDART에서 인증키를 발급합니다: https://opendart.fss.or.kr/
2. GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret
3. Name: `DART_API_KEY`
4. Value: 발급받은 40자리 인증키
5. 저장 후 Actions → `Monthly DART update and GitHub Pages` → `Run workflow`로 최초 실행

API 키는 코드나 README에 절대 입력하지 않습니다.

## GitHub Pages
Repository Settings → Pages에서 Source를 `GitHub Actions`로 설정합니다.
워크플로는 매월 1일에 데이터를 갱신하고 dashboard를 다시 빌드합니다.

## Peer Firms
| 기업 | 종목코드 | 비교 범위 |
|---|---:|---|
| 덴티움 | 145720 | 치과용 임플란트 및 관련 솔루션 |
| 디오 | 039840 | 치과용 임플란트·디지털 치과 솔루션 |
| 네오바이오텍 | - | 국내 치과 임플란트·치과용 솔루션 |
| 메가젠임플란트 | - | 국내 치과 임플란트 제조·판매 |

## 로컬 실행
```bash
pip install -r requirements.txt
# Windows PowerShell
$env:DART_API_KEY="발급받은키"
python src/dart_agent.py
python src/build_dashboard.py
```

생성물:
- `data/processed/financials.csv`
- `data/processed/financials.json`
- `data/processed/meta.json`
- `dashboard/index.html`
