# 차일지 (베타)

내 차 소모품 교체 주기·자동차 검사 일정을 챙겨주는 수첩 + 차종별 자동차세 계산 + 유지비(TCO) 비교.

- **수첩**: 차 등록 → 소모품 교체 기록 → D-day 알림. 모든 기록은 브라우저(localStorage)에만 저장되며 서버로 전송되지 않습니다. JSON 내보내기/가져오기로 백업.
- **차종별 자동차세**: 인기 차종 58종의 연식별 자동차세·연납 할인 표 (지방세법 제127조 기준).
- **유지비 비교**: 두 차종의 월 유지비(자동차세+연료비+보험+감가)를 나란히 비교.

## 개발

노빌드 바닐라 HTML/CSS/JS. 차종별 페이지는 Python으로 정적 생성.

```bash
python3 -m http.server 8347        # 로컬 실행 → http://127.0.0.1:8347
python3 scripts/build.py           # data/*.json 변경 시 tax/ 페이지 재생성
```

로직 테스트 (macOS 내장 JavaScriptCore):

```bash
jsc js/derive.js tests/derive.test.js
jsc js/storage.js tests/storage.test.js
```

세율·소모품 주기 등 모든 상수는 `data/*.json`에 있습니다. 계산 결과는 참고용이며 실제 고지 세액은 위택스에서 확인하세요.
