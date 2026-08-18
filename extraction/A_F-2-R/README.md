# A_F-2-R — 지역특화 우수인재(F-2-R) 원천 근거표

이 폴더는 F-2-R 공고문과 안내·참고자료에서 직접 추출한 **비자별 원천 근거표**를 보존한다. 여러 비자유형을 합친 서비스용 공통 마스터는 `extraction/D_visa_requirements/`에서 별도 PR로 관리한다.

## 식별자

- `visa_id`: `78dca2d7-f771-553a-b788-46c9ff56d633`
- 위 `visa_id`는 F-2-R 비자 코드·트랙 자체를 식별하며 공고 차수나 지역이 달라져도 재사용한다.
- 공고 차수와 적용기간은 `announcement_round`, `valid_from`, `valid_to`, 변경 이력으로 구분한다.
- 원천 `group_id`는 이 폴더의 중첩 AND/OR 구조를 표현하는 UUID다. 공통 마스터의 `condition_group=G1` 같은 로컬 라벨과 동일한 식별자가 아니다.
- 공통 마스터로 정규화하는 각 criteria 행에는 원천 `criteria_id`를 복사하지 않고 새 `criteria_id` UUID를 발급한다.

## 원천 논리그룹 해석

`visa_criterion_groups.csv`는 `parent_group_id`로 중첩 그룹을 구성한다. 각 그룹은 직접 연결된 criteria와 하위 그룹의 결과를 `boolean_operator`로 결합한다.

### 신청 대상 경로

```text
applicant_status (OR)
├─ e74_path (AND)
│  ├─ E-7-4 체류기간
│  └─ e74_status_options (OR)
│     ├─ 현 근무처 계속 근무
│     ├─ 계약 종료 또는 3개월 이내 종료 예정
│     └─ E-7-4 체류 후 D-10
└─ e74r_path (AND)
   ├─ E-7-4R 체류기간
   └─ 인구감소지역 거주
```

### 학력 또는 소득 경로

```text
education_or_income (OR)
├─ education_path (AND)
│  ├─ 국내 교육과정 2년 이상 체류·이수
│  └─ education_degree_status (OR)
│     ├─ 국내 전문학사 이상 학위 취득
│     └─ education_expected_path (AND)
│        ├─ 국내 전문대학 이상 졸업 예정
│        └─ 신청일부터 6개월 이내 학위 취득 예정
└─ income_path (AND)
   ├─ 연간 생활임금 이상
   ├─ 신청인 본인 소득
   ├─ 소득 산정기간
   └─ 인정 소득 종류
```

상위 OR 그룹에 세부 조건을 직접 평탄화하여 연결하지 않는다. 평탄화하면 경로별 필수조건이 누락된 것으로 해석될 수 있다.

## 공통 마스터 매핑 규칙

`extraction/D_visa_requirements/visa_requirement_criteria.csv`로 이관할 때 다음 규칙을 적용한다.

1. 원천 `group_id` UUID를 공통 `condition_group`에 복사하지 않는다.
2. 공통 `condition_group`은 실제로 서로 대체 가능한 OR 조건에만 `G1`, `G2`처럼 새로 부여한다.
3. `G1`, `G2`는 전역 ID가 아니라 비자별 로컬 라벨이다. 그룹 식별·조인에는 `(visa_id, condition_group)`을 사용한다.
4. AND 조건은 공통 테이블에서 기본적으로 그룹 없이 표현한다.
5. `A AND (B OR C)`는 A를 그룹 없이 두고 B와 C에만 같은 `condition_group`과 `condition_operator=OR`을 부여한다.
6. `(A AND B) OR (C AND D)`처럼 공통 스키마가 손실 없이 표현하지 못하는 중첩식은 임의로 평탄화하지 않는다. `special_case_note`에 원식을 남기고 `extraction_review_queue.csv`의 수동 매핑 대상으로 유지한다.
7. 하위 설명·예외·보충문은 논리그룹으로 만들지 않고 `value_text` 또는 `special_case_note`에 보존한다.

## 출처 위치 변환

- 원천 계층에서는 HWPX의 `source_section`, `source_block_index`, `source_table_index`, `source_text`를 근거 위치로 사용한다.
- 공통 마스터에는 `source_page`가 필요하므로, 이관 전에 블록·표 위치를 PDF 또는 팀이 합의한 공식 문서 페이지와 대조한다.
- 페이지를 확정하지 못한 행은 공통 마스터에 넣지 않고 `extraction_review_queue.csv`의 `common_source_page_mapping` 항목으로 관리한다.
- 공통 이관 전 `visa_id`, 새 `criteria_id`, `condition_group`, `condition_operator`, `source_page`, `valid_from`, `valid_to`를 함께 검수한다.

## 점수표 상태

`visa_scoring_models.csv`와 `visa_scoring_items.csv`는 최신 17차 공고에 완전한 배점표가 없어 9차 자료에서 보완한 잠정 데이터다.

- `fill_strategy=backfilled`
- `review_status=needs_review`

수동 검수로 17차에도 같은 점수표가 유효하다고 확인되기 전에는 공통 마스터나 scoring engine에 반영하지 않는다. 검수 항목은 `extraction_review_queue.csv`의 `scoring_model` 행으로 관리한다.

## 작업·PR 경계

- 이 폴더의 PR: F-2-R 원문 추출, 정규화, 중첩 논리 보존, 검수 상태 관리
- 공통 마스터 PR: 검수 완료된 원천 행만 `extraction/D_visa_requirements/` 스키마로 별도 매핑
- 여러 담당자가 D 공통 마스터를 동시에 수정하지 않도록 통합 PR은 순차적으로 진행한다.

## 검수 체크

- [ ] 모든 `parent_group_id`가 같은 `visa_id`의 존재하는 그룹을 참조한다.
- [ ] OR 그룹에는 실제 대체조건이 두 개 이상 있다.
- [ ] 경로별 필수 AND 조건이 상위 OR 그룹에 직접 평탄화되지 않았다.
- [ ] 원천 `group_id`를 공통 `condition_group`으로 복사하지 않았다.
- [ ] 공통 이관 대상 행의 `source_page`와 유효기간을 원문으로 확인했다.
- [ ] 9차 보완 점수표의 현행성을 수동 검수했다.
