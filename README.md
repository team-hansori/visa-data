# visa-data

충청북도 외국인 비자·정착지원 자료를 검색·계산 가능한 구조화 데이터(스키마, 근거표, SQL)로 변환하는 프로젝트입니다. 13회 전국 ICT융합 공모전 출품작(team-hansori)의 데이터 구축 저장소이며, [`da-template`](https://github.com/JungYeoni/da-template)을 기반으로 시작했습니다.

담당자별로 비자 유형을 나눠 공고문·심사표·서식을 원문 근거와 함께 정규화하고, 검수된 결과만 공통 스키마(SQL)로 반영합니다. 원본 PDF는 이 저장소에 올리지 않고 상대 경로 또는 별도 공유 저장소로 참조합니다.

---

## 언제 사용하나요?

- 비자 유형별 공고문·심사표(K-POINT 등)를 근거표(CSV)로 구조화
- 차수별(공고 회차) 변경 이력 추적
- 검수된 근거표를 공통 스키마의 SQL seed로 변환
- 구조화 데이터 기반 EDA, 시각화, 간단한 대시보드 제작

여러 담당자가 비자 유형별로 병렬 작업하되, 공통 스키마 반영은 리뷰 후 병합하는 것을 전제로 합니다.

---

## 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/team-hansori/visa-data.git
cd visa-data
```

### 2. 개발 환경 준비

이 프로젝트는 Python 3.11 이상과 `uv` 기반 의존성 관리를 기본으로 합니다.

권장 방식:

```bash
uv sync --extra dev
uv run pytest tests/ -v
```

`pip`만 사용할 수 있는 환경에서는 아래 방식도 가능합니다.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

Windows PowerShell에서는 가상환경 활성화 명령이 다릅니다.

```powershell
.venv\Scripts\Activate.ps1
```

### 3. 아직 남은 설정

`pyproject.toml`의 `name`/`description`, `README.md` 설명, `cliff.toml`의 저장소 URL은 반영했습니다. 아래 항목은 아직 `da-template` 기준으로 남아 있어 실제 담당자 배정 시 갱신이 필요합니다.

- `configs/base.yaml`의 경로, seed, 분할 기준
- `.github/CODEOWNERS`의 실제 GitHub 사용자명 (담당자 배정 후)

---

## 의존성 관리

이 템플릿은 `uv`를 기본 패키지 매니저로 사용합니다.

- 런타임/개발 의존성은 `pyproject.toml`에 정의합니다.
- 잠금 파일은 `uv.lock`으로 관리합니다.
- 새 환경을 만들 때는 `uv sync --extra dev`를 사용합니다.
- 명령 실행은 `uv run <command>` 형식을 권장합니다.
- `requirements.txt`는 호환성이나 외부 배포가 필요한 경우를 위한 보조 파일입니다.

자주 쓰는 명령:

```bash
uv sync --extra dev
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

의존성을 추가할 때:

```bash
uv add pandas
uv add --dev pytest
```

---

## 디렉터리 구조

```text
visa-data/
├── README.md                     # 프로젝트 설명과 사용 방법
├── CHANGELOG.md                  # 변경 이력
├── CLAUDE.md                     # Claude Code용 프로젝트 지침
├── pyproject.toml                # 패키지 메타데이터와 도구 설정
├── uv.lock                       # uv 잠금 파일
├── requirements.txt              # 핵심 의존성 목록
├── cliff.toml                    # git-cliff 변경 이력 설정
│
├── extraction/                   # 비자 유형별 근거표 추출 작업 (담당자별 폴더)
│   ├── A_F-2-R/
│   ├── B_E-7-4R/                 # current_requirements/scoring_items/document_forms/change_history.csv
│   ├── C_D-2-common/
│   └── D_visa_requirements/      # 비자 요건·절차·쿼터 공유 마스터 테이블 (여러 비자유형이 공통 사용)
│
├── data/
│   ├── raw/                      # 원본 PDF·자료, git 추적 제외
│   ├── interim/                  # 중간 처리 데이터 (근거표 CSV 등)
│   └── processed/                # 검수 완료된 최종 데이터
│
├── notebooks/                    # 탐색 분석과 실험 노트북
├── reports/                      # 보고서, 그림, 표, 대시보드 산출물
│
├── src/
│   └── visualization/            # 시각화 코드 (보고서·대시보드용)
│
├── scripts/                      # 검증·SQL 변환 스크립트 (예정)
├── tests/                        # 단위 테스트
│
├── .github/
│   ├── ISSUE_TEMPLATE/           # 이슈 템플릿
│   ├── pull_request_template.md  # PR 체크리스트
│   └── workflows/                # CI, 노트북 검사, changelog 자동화
│
└── .claude/                      # Claude Code 명령, 규칙, 에이전트 설정
```

---

## 기본 작업 흐름

### 새 추출 작업을 시작할 때

1. GitHub Issue를 만듭니다. 비자유형별 근거표를 채우는 작업이면 `🚀 추출 작업` 템플릿을, 오류·불일치 신고는 `❗ 데이터 오류`, 검수 요청은 `🔍 검수 요청`, 컬럼·상태코드 등 구조 변경 논의는 `📊 설계` 템플릿을 씁니다.
2. 브랜치를 만듭니다. 이슈 생성 시 `issue-helper` 워크플로우가 브랜치명을 자동 제안합니다.

```bash
git checkout -b extraction/b-e74r-current-requirements
```

3. 원본 PDF는 `data/raw/`의 상대 경로 또는 공유 저장소로 참조합니다 (PDF 자체는 이 레포에 올리지 않습니다).
4. 근거표는 `extraction/<비자유형>/`의 대상 CSV(`current_requirements.csv`/`scoring_items.csv`/`document_forms.csv`/`change_history.csv`)를 페이지 순서대로 채웁니다. 작성 규칙은 각 담당자 폴더의 `README.md`를 따릅니다.
5. 검수가 필요하면 `🔍 검수 요청` 이슈로 담당자를 지정합니다.
6. PR을 열고 이슈를 `Closes #번호`로 연결한 뒤, 근거표 품질 체크리스트(출처·근거, `raw_text` 보존, `status` 코드, 공고문·심사표 불일치 처리)를 확인합니다.
7. 검수를 마친 근거표만 공통 스키마 SQL(`seeds/`, 예정)로 반영합니다.

### 노트북과 소스 코드의 역할

노트북은 탐색과 의사결정을 기록하는 공간입니다. 반복해서 쓰는 전처리, 피처 생성, 평가, 시각화 코드는 `src/`로 옮겨 테스트 가능한 함수로 관리하는 것을 권장합니다.

예를 들어:

- `notebooks/01_eda.ipynb`: 구조화된 근거표(CSV)의 결측치/상태값 분포 탐색
- `src/visualization/plots.py`: 보고서·대시보드에 재사용하는 시각화 함수
- `tests/test_visualization.py`: 시각화 함수 검증

---

## 품질 확인

커밋하거나 PR을 열기 전에 아래 명령을 실행하세요.

```bash
uv run --extra dev ruff check src/ tests/
uv run --extra dev ruff format --check src/ tests/
uv run --extra dev pytest tests/ -v
```

`pip` 환경에서는 가상환경을 활성화한 뒤 아래처럼 실행하면 됩니다.

```bash
ruff check src/ tests/
ruff format --check src/ tests/
pytest tests/ -v
```

---

## 데이터 구조화 원칙

### 근거 남기기

- 모든 값에는 출처 문서·페이지 근거를 남깁니다.
- `raw_text`에는 문서 원문을 그대로 보존합니다.

### 조건 분리와 상태 코드

- 한 문장에 여러 요건이 섞여 있으면(예: "최근 10년간 4년 이상 체류 + 현재 사업장 1년 이상 근무") 개별 행으로 분리합니다.
- 확인되지 않은 값은 추측하지 않고 상태 코드(`present`/`explicitly_none`/`not_mentioned`/`not_applicable`/`not_checked`/`extraction_failed`)로 표시합니다.
- `not_mentioned`와 `not_checked`는 문서를 끝까지 확인했는지 여부로 엄격히 구분합니다.

### 문서 간 불일치

- 공고문·심사표 등 문서 간 값이 다르면 임의로 하나를 선택하지 않고 두 근거를 모두 남긴 뒤 `notes`에 검토 표시를 합니다.

### 원본 보존

- 원본 PDF는 이 저장소에 올리지 않고 `data/raw/`의 상대 경로 또는 별도 공유 저장소로 참조합니다.
- 검수 전 근거표는 원본 문서 내용을 임의로 정정하지 않습니다.

---

## 모델링 단계 원칙 (아직 해당 없음)

구조화된 근거표로 EDA·모델링·추천 로직을 만드는 단계에 들어가면 아래 원칙을 적용합니다. 자세한 내용은 `CLAUDE.md`를 참고하세요.

- `random_state=42` 고정, 전처리~평가는 `sklearn.pipeline.Pipeline`으로 통합
- 피처 생성 전 train/val/test 분리를 먼저 확정하고, 인코더·스케일러는 학습 데이터에서만 fit
- 시계열 rolling/lag 계산 시 `shift(1)` 선행 필수
- 단순 성능 비교보다 통계적 가정 검증, 계수 해석, 한계점 명시를 우선

---

## GitHub 자동화

| 워크플로우 | 트리거 | 내용 |
|-----------|--------|------|
| `ci.yml` | push/PR to `main` | ruff lint, ruff format check, pytest |
| `changelog.yml` | `main` push | `CHANGELOG.md` 자동 생성 |

변경 이력은 README에 직접 삽입하지 않고, 별도 [`CHANGELOG.md`](CHANGELOG.md) 파일로 관리합니다.

---

## PR 제목 예시

PR 제목 형식은 강제하지 않지만, 아래처럼 작업 성격이 드러나게 쓰는 것을 권장합니다.

| 예시 | 사용 시점 |
|------|----------|
| `experiment: baseline 모델 비교` | 새 분석 실험 |
| `feat: 시계열 lag 피처 추가` | 기능 또는 분석 함수 추가 |
| `fix: PSI 계산의 0 나눗셈 처리` | 버그 수정 |
| `docs: 데이터 수집 절차 정리` | 문서 변경 |
| `refactor: 학습 파이프라인 함수 분리` | 동작 변경 없는 구조 개선 |
| `chore: 개발 의존성 업데이트` | 설정, 의존성, 자동화 변경 |

---

## Claude Code 연동

`CLAUDE.md`와 `.claude/` 폴더는 Claude Code에서 프로젝트 맥락을 자동으로 읽을 수 있도록 만든 설정입니다.

포함된 내용:

- 데이터 분석 프로젝트의 기본 원칙
- 역할별 서브에이전트 설정
- `/timeseries`, `/tabular`, `/gis`, `/regression`, `/ml`, `/visualization` 같은 분석용 슬래시 커맨드
- 민감 파일 접근 제한과 작업 규칙

Claude Code를 사용하지 않아도 프로젝트 실행에는 문제가 없습니다. 다른 에디터나 코딩 에이전트를 쓰는 경우에도 `CLAUDE.md`를 분석 가이드 문서로 참고할 수 있습니다.

---

## 변경 이력

변경 이력은 [`CHANGELOG.md`](CHANGELOG.md)에서 확인할 수 있습니다.

---

## 라이선스

MIT
