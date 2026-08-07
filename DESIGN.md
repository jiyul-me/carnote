# DESIGN.md — 차일지 디자인 시스템

방향: **문서처럼 정확하고, 금융앱처럼 여백 있는 화면. 숫자가 주인공이다.**
CLAUDE.md·TASKS.md와 함께 읽는다. 아래에 정의된 토큰 외의 색·크기 값을 새로 만들지 않는다.

## 원칙 5개

1. 색은 셋: 흰 배경, 잉크 텍스트, 블루 포인트. 상태 표시(D-day 임박·초과)에만 amber/red 예외.
2. 장식은 0.5px 헤어라인뿐. 그림자·그라데이션 금지.
3. 금액·D-day 등 숫자는 페이지에서 가장 크게, 전부 tabular-nums.
4. 폰트는 Pretendard 하나.
5. 이모지 금지. 로고는 "차일지" 텍스트 워드마크(🚗 제거).

## 색 토큰

전역 CSS 변수로 정의하고, 기존 색 값은 전부 이 변수로 치환한다. 라이트 단일 모드로 확정(다크모드는 범위 밖).

```css
:root {
  --bg:            #FFFFFF;  /* 페이지 배경 */
  --surface:       #F6F7F9;  /* 프로그레스 트랙, 은은한 구획 */
  --ink:           #191F28;  /* 본문·제목 */
  --ink-secondary: #4E5968;  /* 보조 텍스트 */
  --ink-muted:     #8B95A1;  /* 라벨·캡션·플레이스홀더 */
  --border:        #E5E8EB;  /* 헤어라인 */
  --accent:        #1A56DB;  /* 유일한 포인트색 — CTA, 강조 숫자, 내 차 행 */
  --accent-bg:     #EBF2FE;  /* 하이라이트 행·배지 배경 */
  --warning:       #B45309;  /* D-day 임박 텍스트 */
  --warning-bg:    #FEF3C7;
  --danger:        #DC2626;  /* D-day 초과·삭제 */
  --danger-bg:     #FEE2E2;
}
```

- `<meta name="theme-color">`는 `#FFFFFF`로 변경.
- accent 사용처는 화면당 소수로 제한: primary 버튼 1개, 강조 숫자, 내 차 행. 그 외에는 잉크와 회색만.

## 타이포그래피

- Pretendard Variable을 jsdelivr CDN woff2로 로드, `font-display: swap` (Core Web Vitals 유지).
- `font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, system-ui, sans-serif;`
- 모든 숫자 표기(금액, D-day, 주행거리, %)에 `font-variant-numeric: tabular-nums`.

| 역할 | 크기/굵기 | 비고 |
|---|---|---|
| 히어로 금액 | 30px / 700 | `letter-spacing: -0.02em`, 페이지당 1개 |
| 페이지 제목 | 20px / 700 | |
| 카드·항목명 | 15px / 500 | |
| 본문 | 15px / 400 | `line-height: 1.6` |
| 표 본문 | 14px / 400 | 숫자 우측 정렬 |
| 섹션 라벨 | 12px / 500 | `--ink-muted`, 자간 그대로 |
| 캡션·기준일 | 12px / 400 | `--ink-muted` |

## 레이아웃

- 8px 그리드: 간격은 4 / 8 / 12 / 16 / 20 / 24px만 사용.
- 콘텐츠 최대폭 640px 중앙 정렬, 좌우 패딩 20px. 모바일(375px) 퍼스트.
- radius: 컨트롤 8px, 카드 12px, 배지 6px.
- `box-shadow`는 input focus ring(`0 0 0 3px var(--accent-bg)`) 한 곳에만 허용.
- transition은 `0.15s ease` 색·배경 변화만. 그 외 애니메이션 금지.

## 컴포넌트

### 버튼
- primary: `--accent` 배경 + 흰 글자, 높이 48px, radius 8px, 15px/600. **화면당 1개만** (세금 페이지에선 "이 차로 수첩 시작하기").
- secondary: 흰 배경 + `--border` 테두리 + `--ink` 글자. 나머지 전부 이것.
- 텍스트 버튼: `--accent` 글자만, 배경·테두리 없음.

### D-day 배지
- 임박(D-14 이하): `--warning-bg` 배경 + `--warning` 글자, 12px/500, padding 3px 8px, radius 6px.
- 여유(D-15 이상): 배경 없이 `--ink-secondary` 텍스트만.
- 초과(D+): `--danger-bg` + `--danger`.

### 표 (연식별 세액표)
- 헤더: 12px `--ink-muted`, 하단 1px `--border` 굵은 느낌은 색으로만.
- 행: 0.5px `--border` 구분, padding 상하 10px, 숫자 우측 정렬.
- "내 차" 행: `--accent-bg` 배경 + `--accent` 글자 + radius 6px — 연식 선택 시 해당 행만 하이라이트.

### 카드
- 흰 배경 + 0.5px `--border` + radius 12px + padding 16~20px. 그림자 없음.

### 프로그레스 바 (소모품 상태)
- 높이 4px, 트랙 `--surface`, 채움 `--accent`, radius 2px.

### 입력·셀렉트
- 높이 48px, 0.5px `--border`, radius 8px, focus 시 ring.

### 아이콘
- 꼭 필요한 자리만 단색 라인 SVG(스트로크 1.5px, 16~20px, `currentColor`). 장식용 아이콘·이모지 금지.

## 페이지별 적용

- **세금 페이지**: 브레드크럼(12px muted) → 제목 → 히어로 금액 → 연납 한 줄(할인액만 accent 강조) → 연식 select → 연식별 표(내 차 행 하이라이트) → primary CTA → 기준일 캡션. 이 순서 고정.
- **수첩 홈**: 내 차 카드 → "다가오는 일정" 리스트(배지 규칙 적용) → 캘린더에 추가(secondary) → 소모품 상태(프로그레스).
- **허브(차종 목록)**: 현재 불릿 나열을 브랜드별 섹션 라벨(12px muted) + 헤어라인 구분 리스트로 교체. 각 행은 차종명 좌측, 신차 기준 세액 우측(tabular) 노출 권장.
- **TCO 비교**: 두 열 카드, 결론 숫자(월 유지비)를 히어로 크기로.

## 마이그레이션 순서

1. 전역: Pretendard 로드 + 색 변수 정의 + 기존 색 전면 치환 + theme-color 변경 + 🚗 워드마크 교체
2. 공용 컴포넌트 클래스화: 버튼·배지·표·카드·프로그레스 (한 CSS 파일로)
3. 페이지 적용: 세금 템플릿 → 수첩 → 허브 → TCO → 법적 페이지
4. 확인: 375px 폭에서 가로 스크롤 없음, 히어로 금액 줄바꿈 없음, Lighthouse 성능 저하 없음(폰트 swap 확인)

## 금지 목록

- 이모지, 그림자, 그라데이션, 정의 외 색 추가, 페이지당 primary 버튼 2개 이상, 장식 애니메이션, 다크모드 임의 구현
