# CLAUDE.md — visa-data

## 프로젝트 개요

충청북도 외국인 비자·정착지원 자료(공고문, 심사표, 서식)를 검색·계산 가능한 구조화 데이터(근거표 CSV → 공통 스키마 SQL)로 변환한다. 13회 전국 ICT융합 공모전(team-hansori) 출품용 데이터 구축 저장소이며, `da-template`을 기반으로 시작했다.

담당자별로 비자 유형을 나눠 작업한다(예: `B_E-7-4R` = 지역특화 숙련기능인력). 각 담당자는 `extraction/<비자유형>/` 아래에서 공고문·심사표를 원문 근거와 함께 근거표(CSV)로 옮기고, 검수 후에만 공통 스키마 SQL(`seeds/`, `output/`, 예정)로 반영한다. 근거표 컬럼·상태 코드·변경 이력 형식은 `extraction/B_E-7-4R/README.md`에 정의되어 있다.

### 데이터 구조화 핵심 원칙
- 모든 수치·조건에는 출처 문서·페이지 근거를 남긴다. `raw_text`에는 문서 원문을 그대로 보존한다.
- 한 문장에 여러 요건이 섞여 있으면(예: "최근 10년간 4년 이상 체류 + 현재 사업장 1년 이상 근무") 개별 조건으로 분리해서 기록한다.
- 확인되지 않은 값은 추측하지 않고 상태 코드(`present`/`explicitly_none`/`not_mentioned`/`not_applicable`/`not_checked`/`extraction_failed`)로 표시한다. `not_mentioned`와 `not_checked`는 문서를 끝까지 확인했는지 여부로 엄격히 구분한다.
- 공고문과 심사표 등 문서 간 값이 불일치하면 임의로 하나를 선택하지 않고 두 근거를 모두 남긴 뒤 검토 표시를 한다.
- 원본 PDF는 이 저장소에 올리지 않고 `data/raw/`의 상대 경로 또는 별도 공유 저장소로 참조한다.

## 이 프로젝트에서 Claude가 따를 원칙

### Git 작업 안전
- 사용자가 명시적으로 요청한 경우에만 커밋, 푸시, PR 생성을 진행한다.
- 코드 수정, 테스트, 검증은 수행할 수 있지만, 배포성 Git 작업은 자동으로 진행하지 않는다.
- 커밋이나 푸시가 필요해 보이는 상황에서도 먼저 변경 내용과 검증 결과를 보고하고 사용자의 요청을 기다린다.

### 역할 분리 (현재)
- 근거표 추출/정규화: `extraction/<비자유형>/` (담당자별 폴더, 예: `extraction/B_E-7-4R/`)
- 검수 완료 데이터: `seeds/` (예정)
- 검증·SQL 변환 스크립트: `scripts/`
- 시각화 산출물: `src/visualization/`

`src/features/`, `src/modeling/`, `src/evaluation/`은 현재 단계(데이터 구조화)에 쓰이지 않아 제거했다. 이후 구조화 데이터로 모델링·추천 로직을 만드는 단계에 들어가면 아래 원칙을 다시 적용하고 필요한 폴더를 새로 만든다.

### 모델링 단계 진입 시 적용할 원칙 (아직 해당 없음)
- 모든 분석에 `np.random.seed(42)` 고정, 전처리 → 모델링 → 평가는 `sklearn.pipeline.Pipeline`으로 통합
- 피처 생성 전에 train/val/test 분리를 먼저 확정하고, 인코더·스케일러는 학습 데이터에서만 fit
- 시계열 rolling/lag 계산 시 `shift(1)` 선행 필수
- 단순 성능 비교보다 통계적 가정 검증, 계수 해석, 한계점 명시를 우선
- 실험 결과 보고 시 데이터셋 버전·기간, 분할 전략, 평가 지표/CV fold 수, 핵심 가정, 한계점을 포함

### 재발명 금지
- 새 기능을 구현하기 전에 `src/` 내 기존 함수·클래스·유틸리티를 먼저 검색하고, 표준 라이브러리(pandas, scikit-learn, statsmodels 등)에 이미 구현된 기능이 있는지 확인한다.
- 기존 코드나 라이브러리로 충분한 경우 직접 재구현하지 않고 재사용한다.
- 부득이하게 새로 작성해야 한다면 그 이유(기존 구현의 한계, 라이브러리 부재 등)를 코드 주석 또는 커밋 메시지에 명시한다.

## 서브에이전트 사용 가이드

| 에이전트 | 사용 시점 |
|----------|-----------|
| `data-scientist` | 시계열 분석(ARIMA/VAR), 회귀/인과추론(OLS/DiD/패널), sklearn 정형 데이터 분류·회귀 |
| `feature-engineer` | 시계열 lag/rolling/계절성 피처, 테이블 인코딩/스케일링/교호작용, GIS 행정구역 집계·공간조인 |
| `data-visualization` | 논문·보고서용 정적 이미지(dpi=300), Plotly/Streamlit 인터랙티브 대시보드 |

에이전트 정의 파일: `.claude/agents/`

## 기술 스택

- **언어**: Python 3.11+
- **데이터**: pandas, polars
- **통계**: statsmodels, scipy
- **ML**: scikit-learn, xgboost, lightgbm
- **시각화**: matplotlib, seaborn, plotly, streamlit
- **GIS**: geopandas, folium, shapely
- **환경**: pyproject.toml 기반 의존성 관리
