# 카카오 재무분석 에이전트

OpenDART API에서 카카오의 연간 재무 데이터를 가져와 재무비율을 계산하고 GitHub Pages 대시보드에 표시합니다.

## 1. GitHub Secret 등록
저장소 `Settings → Secrets and variables → Actions → New repository secret`에서 다음 값을 등록합니다.

- Name: `OPENDART_API_KEY`
- Secret: OpenDART에서 발급받은 인증키

인증키를 코드에 직접 입력하거나 공개 저장소에 올리지 마세요.

## 2. 자동 실행
`.github/workflows/update.yml`은 매월 정기 실행되며, Actions 탭에서 `Update Kakao financial data`를 선택해 `Run workflow`로 수동 실행할 수도 있습니다.

## 3. 대시보드 공개
저장소 `Settings → Pages`에서:
- Build and deployment: `Deploy from a branch`
- Branch: `main`
- Folder: `/docs`
를 선택하고 Save를 누릅니다.

잠시 후 `https://<GitHub 사용자명>.github.io/VR_kakao/`에서 대시보드를 확인할 수 있습니다.

## 4. 데이터 기준과 주의사항
- 연간 사업보고서(`reprt_code=11011`)의 2023~2025년 데이터를 수집합니다.
- 연결재무제표(CFS)를 먼저 요청하고, 해당 연도 데이터가 없을 때 별도재무제표(OFS)를 대체로 사용합니다.
- `docs/data.json`의 `financial_statement_basis_by_year`에서 각 연도 기준을 확인하세요. CFS와 OFS가 섞이면 직접 비교하지 않는 것이 좋습니다.
- OpenDART의 계정명이나 공시 형식에 따라 일부 항목이 비어 있을 수 있습니다. 원문 사업보고서와 대조하세요.
- ROE는 당기순이익 ÷ 평균 자기자본 × 100으로 계산합니다. 첫 수집 연도는 전년도 자본이 없어 표시되지 않습니다.
- 대시보드의 그래프 라이브러리는 Chart.js CDN을 사용합니다.

## 5. 로컬 실행
```bash
pip install -r requirements.txt
# macOS/Linux
export OPENDART_API_KEY="발급받은_인증키"
python main.py
```
Windows PowerShell:
```powershell
$env:OPENDART_API_KEY="발급받은_인증키"
python main.py
```
