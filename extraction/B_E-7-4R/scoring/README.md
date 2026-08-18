# scoring

E-7-4R K-POINT 점수표를 보관한다.

`scoring_items.csv`는 자격요건 충족 여부를 판단하는 criteria가 아니라, 충족자 사이의 점수 합계와 합격선 산정에 사용하는 점수 데이터다. 따라서 `requirements/`와 분리하며, 현재는 E-7-4R 원천 데이터로 유지한다. 공통 점수 스키마가 확정되기 전까지 공통 `visa_requirement_criteria`에 합치지 않는다.

점수표의 병합 셀과 구간 조건은 텍스트 추출만으로 확정하지 않고 원본 페이지 이미지와 대조한다.
