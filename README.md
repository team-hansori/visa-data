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
│   └── C_D-2-common/
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

### 새 분석을 시작할 때

1. GitHub Issue를 만들고 목표, 데이터, 성공 기준을 적습니다.
2. 브랜치를 만듭니다.

```bash
git checkout -b experiment/short-description
```

3. 원본 데이터는 `data/raw/`에 둡니다.
4. 탐색 분석은 `notebooks/`에서 진행합니다.
5. 재사용할 코드는 `src/` 아래로 옮깁니다.
6. 중요한 로직에는 `tests/`에 테스트를 추가합니다.
7. PR을 열고 체크리스트를 확인합니다.

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

## 분석 원칙

### 재현성

- random seed를 명시합니다.
- 데이터 분할 기준을 코드나 문서에 남깁니다.
- 원본 데이터는 수정하지 않고, 처리 결과는 `data/interim/` 또는 `data/processed/`에 둡니다.

### 데이터 누수 방지

- train/validation/test 분리 후 전처리 기준을 학습 데이터에서만 계산합니다.
- 시계열 rolling/lag 피처는 미래 값을 참조하지 않도록 `shift(1)` 이후 계산합니다.
- 인코더, 스케일러, imputing 파라미터는 학습 데이터에만 fit합니다.

### 설명 가능한 결과

- 모델 성능뿐 아니라 데이터 가정, 한계, 실패 사례를 함께 기록합니다.
- 복잡한 모델을 쓰기 전에 단순한 baseline을 먼저 만듭니다.
- 중요한 판단은 노트북, 이슈, PR 설명 중 한 곳에 남깁니다.

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
