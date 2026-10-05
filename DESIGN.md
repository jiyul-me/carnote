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
  --accent:        #1A56DB;  /* 유일한 포인트색 — CTA, 강조 숫자, 내 차 행, 본문 링크 */
  --accent-bg:     #EBF2FE;  /* 하이라이트 행·배지 배경 */
  --warning:       #B45309;  /* D-day 임박 텍스트 */
  --warning-bg:    #FEF3C7;
  --danger:        #DC2626;  /* D-day 초과·삭제 */
  --danger-bg:     #FEE2E2;
}
```

- `<meta name="theme-color">`는 `#FFFFFF`로 변경.
- accent 사용처는 화면당 소수로 제한: primary 버튼 1개, 강조 숫자, 내 차 행. 그 외에는 잉크와 회색만.
  **예외: 본문 링크**(아래 '본문 링크'). 텍스트 버튼과 같은 계열로 보고 accent를 쓴다.
- 링크·버튼에 브라우저 기본 파랑(`rgb(0,0,238)`)·방문 보라(`rgb(85,26,139)`)가 보이면 안 된다.

### 크기 토큰

| 토큰 | 값 | 선언 위치 | 쓰임 |
|---|---|---|---|
| `--ad-slot-min-h` | 280px | `css/content.css`의 `:root` | 광고 자리 최소 높이 — 광고가 늦게 떠도 본문이 밀리지 않게(CLS). 광고가 들어가는 페이지는 모두 content.css를 읽는다 |

## 타이포그래피

- Pretendard Variable을 jsdelivr CDN woff2로 로드, `font-display: swap` (Core Web Vitals 유지).
- `font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, system-ui, sans-serif;`
- 모든 숫자 표기(금액, D-day, 주행거리, %)에 `font-variant-numeric: tabular-nums`.
- **줄바꿈**: `body`에 `word-break: keep-all; overflow-wrap: break-word;` — 한글은 어절 단위로 끊고('브라/우저' 방지),
  공백 없는 긴 영문·URL은 break-word로 넘치지 않게 한다. 사용자 메모처럼 긴 입력을 보이는 곳
  (`.history-main`·`.history-sub`·`.msg-toast`·`.car-name`)은 `overflow-wrap: anywhere`를 유지한다.

| 역할 | 크기/굵기 | 비고 |
|---|---|---|
| 히어로 금액 | 30px / 700 | `letter-spacing: -0.02em`, 페이지당 1개 |
| 페이지 제목 | 20px / 700 | |
| 카드·항목명 | 15px / 500 | 자주 묻는 질문의 질문(`.faq-q`), CTA 카드 제목(`.cta-title`)도 |
| 본문 | 15px / 400 | `line-height: 1.6`. 자주 묻는 질문의 답(`.faq-a`)도 |
| 표 본문 | 14px / 400 | 숫자 우측 정렬 |
| 섹션 라벨 | 12px / 500 | `--ink-muted`, 자간 그대로 |
| 캡션·기준일 | 12px / 400 | `--ink-muted`. 연식표 차령 꼬리(`.age-sub`)·연식 캡션(`.hub-years`)도 |

## 레이아웃

- 8px 그리드: 간격은 4 / 8 / 12 / 16 / 20 / 24px만 사용.
- 콘텐츠 최대폭 640px 중앙 정렬, 좌우 패딩 20px. 모바일(375px) 퍼스트.
- radius: 컨트롤 8px, 카드 12px, 배지 6px.
- `box-shadow`는 input focus ring(`0 0 0 3px var(--accent-bg)`) 한 곳에만 허용.
- transition은 `0.15s ease` 색·배경 변화만. 그 외 애니메이션 금지.
- **탭 타깃 최소 44px**: 누를 수 있는 것(버튼·내비 링크·칩·목록 행·푸터 링크·'닫기'·'취소')은 높이 44px 이상.
  `.topbar-nav a`·`.topbar-btn`·워드마크는 `inline-flex` + `min-height: 44px`, `.back-btn`은 padding 10px 0 + 44px,
  `.quick-btn`·`.btn.small`은 44px·14px/500, `.history-del`은 44×44, 칩(`.chip`, `.chip-radio span`)·텍스트 버튼(`.text-btn`) 44px,
  `.foot a`는 세로 padding 8px + 44px. 예외는 산문 안 인라인 링크뿐이다.
- `#앵커`로 이동하는 대상은 sticky 상단바 밑에 가리지 않게 `scroll-margin-top: 64px`(`.content [id]`).

## 컴포넌트

### 상단바·내비 (공통 크롬 — 모든 페이지가 같은 마크업)
- 항목은 3개 고정: **수첩 · 자동차세 · 유지비 비교**. '설정'은 내비에 두지 않는다 — 내 차 카드의 텍스트 버튼 '설정·백업'과
  수첩 푸터 1번째 줄의 '설정·백업'(`#settings`, muted)으로 들어간다.
- 마크업 계약(`scripts/build.py` `topbar_nav()`와 손 페이지가 같은 문자열, tax/ 안에서는 경로 앞에 `../`):
  `<nav class="topbar-right topbar-nav" aria-label="주 메뉴"><a href="index.html">수첩</a><a href="tax/index.html">자동차세</a><a href="tco.html">유지비 비교</a></nav>`
- 현재 위치는 해당 링크에 `aria-current="page"` + `--ink`·600(`.topbar-nav a[aria-current="page"]`). accent는 쓰지 않는다.
  수첩 화면=수첩, 세금·허브·계산기(tax/)=자동차세, tco.html=유지비 비교. privacy·terms·about에는 없다.
- 워드마크는 `<a class="topbar-title" href="index.html">차일지</a>`(17px/700, 한 줄).
- 상단바 안쪽은 본문 640px 열에 맞춘다: `.topbar { padding-inline: max(20px, calc((100% - 640px)/2 + 20px)); }`
  — 넓은 화면에서 워드마크와 내비가 양 끝으로 갈라지지 않게.

### 푸터
- `<footer class="foot">` 두 줄, 12px muted, 가운데 정렬.
- 1번째 줄: 페이지별 한 문장(예: 세금 페이지 '차일지 (베타) — 계산 결과는 참고용이며, 실제 고지 세액은 위택스에서 확인하세요.').
  수첩은 끝에 '설정·백업' 링크.
- 2번째 줄(계약, 순서 고정): `<p><a href="about.html">소개·문의</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="terms.html">이용약관</a></p>`
- 내비·푸터 계약과 손 페이지의 광고 마커는 `python3 scripts/check_links.py`가 전 페이지에서 검사한다.

### 본문 링크
- 산문 속 링크(클래스 없는 `a`): `--accent` 글자 + 1px 밑줄, `text-underline-offset: 3px`. 방문 후에도 같은 색.
- 선택자는 `.content :where(a:not([class]))` — `:where()`로 감싸 명시도를 `.content` 하나(0,1,0)로 낮춘다.
  그래서 브레드크럼(`.crumb a`)·출처(`.sources a`, 12px muted)·목록형 링크(`.hub-row` 등)는 각자 규칙을 따른다.
  같은 이유로 `.content :where(h2)`·`.content :where(p)`도 `:where()`로 쓴다(`h2.brand-title` 12px/500 같은 컴포넌트 스타일을 덮지 않게).
- 원칙 1 'accent 소수 사용'의 예외다(텍스트 버튼과 같은 계열).

### 버튼
- primary: `--accent` 배경 + 흰 글자, 높이 48px, radius 8px, 15px/600. **화면당 1개만**
  (세금 페이지 "이 차로 수첩 시작하기", 데모 대시보드 "내 차 등록하기").
- secondary: 흰 배경 + `--border` 테두리 + `--ink` 글자. 나머지 전부 이것.
- 텍스트 버튼: `--accent` 글자만, 배경·테두리 없음.
- **위험 버튼**(전체 데이터 삭제 등): 다른 버튼 묶음과 24px 띄우고 위에 0.5px 헤어라인으로 나눈다(`.danger-zone`:
  `margin-top: 24px; padding-top: 16px; border-top: 0.5px solid var(--border)`). 버튼 자체는 `--danger` 테두리·글자.

### D-day 배지
- 임박(D-14 이하): `--warning-bg` 배경 + `--warning` 글자, 12px/500, padding 3px 8px, radius 6px.
- 여유(D-15 이상): 배경 없이 `--ink-secondary` 텍스트만.
- 초과(D+): `--danger-bg` + `--danger`.

### 표 (연식별 세액표)
- 헤더: 12px `--ink-muted`, 하단 1px `--border` 굵은 느낌은 색으로만. 첫 열 헤더는 '등록 연도'.
- 첫 열: `{등록 연도}년` + 12px muted 꼬리 `<span class="age-sub"> · {차령}년차</span>`. 1행은 ` · 신차`, 마지막(13)행은
  ` · 13년차+`('이전'은 붙이지 않는다 — 360·375px에서 두 줄이 된다). 계산기 표·표 이미지 저장(캔버스)도 같은 형식.
- 줄바꿈: `table.data th, table.data td:not(:first-child) { white-space: nowrap; }` — 금액·헤더는 한 줄, 첫 열만 줄바꿈 허용
  (320px에서도 표가 넘치지 않게).
- 행: 0.5px `--border` 구분, padding 상하 10px, 숫자 우측 정렬.
- "내 차" 행(`tr.hl`): `--accent-bg` 배경 + `--accent` 글자 + radius 6px — 배경만 바꾸고 padding은 그대로(선택할 때 열 폭이 흔들리지 않게).

### 카드
- 흰 배경 + 0.5px `--border` + radius 12px + padding 16~20px. 그림자 없음.
- 마지막 요소의 아래 여백은 0(`.card > :last-child { margin-bottom: 0; }`).

### 목록 행 (허브·관련 차종·도구 목록·가이드 목록·접힌 소모품)
- `.hub-list` / `.hub-row`(헤어라인 구분) + 오른쪽 셰브론 SVG(16px, stroke 1.5, `currentColor`). 접는 묶음은 `<details class="hub-group">`
  + `summary.hub-row` — JS 없이 열고 닫힌다.
- 금액(`.hub-price`): 14px `--ink-secondary`, `white-space: nowrap; flex-shrink: 0`. 셰브론이 없는 단일 행도 셰브론 자리(16px + gap 8px)를
  비워 금액 열을 맞춘다.
- 지금 보고 있는 차(관련 차종): 링크 없이 `aria-current="page"` + 600.

### 프로그레스 바 (소모품 상태)
- 높이 4px, 트랙 `--surface`, 채움 `--accent`, radius 2px.

### 입력·셀렉트
- 높이 48px, 0.5px `--border`, radius 8px, focus 시 ring.

### 광고 슬롯 (`.ad-slot`)
- 마크업은 `scripts/build.py`만 만든다(`data/site.json` `adsense`의 publisherId와 그 자리 슬롯 ID가 모두 있을 때만). 손 페이지는
  `<!-- adsense:slot 이름 --><!-- /adsense:slot -->` 마커로 자리만 둔다(README '손 페이지 마커 규칙').
- 모양: 위 0.5px 헤어라인(`border-top`), `padding-top: 12px`, `margin: 24px 0`, `min-height: var(--ad-slot-min-h)`.
  맨 위에 라벨 '광고'(`.ad-label`, 12px `--ink-muted`) — 라벨 문구는 '광고' 또는 '스폰서 링크'만 허용된다.
- 반응형 단위, `data-full-width-responsive="false"`(화면 폭 확장으로 좌우 여백을 깨지 않게).
- 게재되지 않은 단위는 숨긴다: `.ad-slot:has(ins[data-ad-status="unfilled"]) { display: none; }`.
- **페이지당 1개.** 위아래로 가장 가까운 상호작용 요소(a·button·select·input·summary)와 60px 이상 떨어뜨린다.
- 금지 구역: 첫 화면(375×667 기준 슬롯 top이 667px 안), 히어로 직후, primary CTA·입력·select·표·버튼 근처,
  입력과 결과 사이, 아코디언 행 사이, **수첩 화면 전체**(`index.html` — `#app`과 소개 섹션 모두).
- 자리: 차종 페이지 '계산 방법' 뒤·자주 묻는 질문 앞(`taxArticle`), 가이드 글 자주 묻는 질문 뒤·'다른 가이드' 앞(같은 `taxArticle`
  단위를 함께 쓴다 — 바로 아래 안내 문단 한 줄이 목록 행과의 거리를 만든다), 허브·계산기 출처(`.sources`) 뒤(`hubEnd`·`calcEnd`),
  유지비 비교 본문 끝(`tcoEnd` 마커, `</main>` 바로 앞). 가이드 목록(`tax/guide.html`)은 글 목록뿐이라 광고를 두지 않는다.
- 광고 크리에이티브 내부(광고 네트워크가 그리는 iframe 안)는 이 문서의 토큰 규칙 대상이 아니다. 슬롯 테두리·라벨·여백만 규칙을 따른다.

### 아이콘
- 꼭 필요한 자리만 단색 라인 SVG(스트로크 1.5px, 16~20px, `currentColor`). 장식용 아이콘·이모지 금지.

## 페이지별 적용

- **세금 페이지**(승용·전기·화물·승합 모두 이 순서):
  브레드크럼(12px muted, '자동차세 › {브랜드} {모델} › {차종}', 가족이 1개면 '자동차세 › {브랜드} › {차종}', 중간 단계는 허브 앵커
  `index.html#{id}`) → 제목 → 캡션 → 히어로 금액 → 연납 한 줄(할인액만 accent 강조) → 한눈에 카드 →
  (해당 차만) 비교 한 줄(`.compare-line` — 단종 세대는 세대 요약, 화물·승합은 같은 배기량 승용차와 비교) →
  h2 '{차종} 연식별 자동차세' → 연식 select(아래 12px 캡션 '자동차등록증의 최초 등록 연도로 고르세요') → 연식별 표(내 차 행 하이라이트)
  → 표 이미지 저장 → 일괄부과 안내(해당 차만) → **primary CTA 카드** → h2 계산 방법(산문) → **[광고 슬롯 taxArticle]** →
  h2 자주 묻는 질문 → h2 관련 차종(끝에 계산기 안내 한 줄과 '가이드: … · 전체 보기' 한 줄) → 출처·기준일 캡션(`.sources`, 맨 끝).
  화물·승합도 CTA 뒤에 h2 '계산 방법'을 두어 광고가 CTA에 붙지 않게 한다. '계산 방법' 산문에는 링크를 두지 않는다(바로 뒤가 광고 자리).
- **가이드 글**(`tax/guide-*.html`, 내용은 `scripts/guides.py`): 브레드크럼('자동차세 › 가이드 › {글}') → h1 → 작성일·기준 캡션
  (`.guide-meta`, 12px muted) → 소개(`.lede`) → 한눈에 상자(`.guide-summary`, `--surface` 배경·radius 8px·14px) → 본문(h2 산문·표·목록)
  → h2 자주 묻는 질문 → **[광고 슬롯 taxArticle]** → h2 다른 가이드(안내 한 줄 + 목록 행) → 계산 도구 안내 → 출처·기준일(`.sources`, 맨 끝).
  가이드 목록(`tax/guide.html`)은 브레드크럼 → h1 → 소개 → 목록 행 → 계산 도구 안내, 광고 없음.
- **단종 세대 기본 연식**: 판매가 끝나 차령 경감 대상이 된 세대(승용 내연기관, modelYearTo 있음, 올해−modelYearTo+1 ≥ 경감 시작 차령)는
  '신차 기준' 대신 기본 등록 연도 `modelYearTo`(차령 = 올해−modelYearTo+1, 실제 값)로 캡션·히어로·연납 줄·title·FAQ·썸네일·허브 금액을
  만든다. 연식표는 13행까지라 하이라이트 행은 `min(차령, 13)`('13년차+')으로 따로 둔다 — 캡션·FAQ·썸네일에는 표 행의 연도가 아니라 실제 연도·차령을 쓴다.
  연식 select는 아무것도 고르지 않은 상태(빈 옵션 '등록 연도 선택', `selected` 없음)가 곧 기본 연식이고, 그 행(`tr#age-N`)이 하이라이트된다.
  select 옵션은 표보다 오래된 세대면 그 세대 첫 연식까지 내려간다.
  골랐다가 다시 비우면 기본 연식으로 돌아간다(신차 금액이 다시 나오면 안 된다). 판매 중 모델은 신차 기준 그대로.
- **수첩 홈**: 내 차 카드 → "다가오는 일정" 리스트(배지 규칙 적용) → 캘린더에 추가(secondary) → 소모품 상태(프로그레스).
  - 기록이 있는 소모품만 상태순으로 프로그레스와 함께 보이고, 기록 없는 항목은 '기록 없는 항목 N개' `<details>` 한 행으로 접는다
    (목록 행 패턴 재사용). 안내 문구는 섹션 상단 한 줄('기록을 추가하면 교체 시기를 계산해요', 기록이 0개면 '최근 교체한 것부터 기록해 보세요').
  - 데모(`?demo=1`) 대시보드 맨 위에는 안내 줄 '예시 데이터예요 — 저장되지 않아요'와 primary '내 차 등록하기'(`index.html#car/new`) 1개.
    데모의 하위 화면에는 안내 줄만 두고 primary는 두지 않는다.
  - 첫 방문(차 없음) 화면 아래 정적 소개에는 '도구' 목록 4행(차종별 자동차세·자동차세 계산기·유지비 비교·자동차세 가이드)을 목록 행으로 둔다.
  - 광고 없음(광고 슬롯 컴포넌트의 금지 구역).
- **허브(차종 목록)**: h1 → 소개 → 연납 배너 → 검색(JS가 켤 때만 보임, 48px 입력) → 브랜드 칩(한 줄 가로 스크롤 `.brand-chips`,
  끝이 잘려 보이는 것이 스크롤 단서) → 브랜드별 목록(브랜드 h2 `.brand-title` 12px muted, 모델 그룹 안 트림은 연식 내림차순, 세대가 2개 이상이면
  누를 수 없는 세대 라벨 'IG · 2016~2022', 트림마다 12px muted 연식 캡션, 금액은 판매 중=신차·단종=기본 연식) →
  '찾는 차종이 없나요? 계산기' → h2 자동차세 가이드(목록 행) → h2 자동차세 계산 원리(세율표·설명) → 출처 → **[광고 슬롯 hubEnd]**.
- **계산기**: 입력 → 결과 → 세율표 → 출처 → **[광고 슬롯 calcEnd]**. 입력과 결과 사이에는 광고를 두지 않는다.
- **TCO 비교**: 두 열 카드, 결론 숫자(월 유지비)를 히어로 크기로. '공통 조건'은 목록 행 아코디언으로 접고 summary에 현재 값을 보인다.
  본문 끝(`</main>` 앞)에 `tcoEnd` 광고 마커.

## 마이그레이션 순서

1. 전역: Pretendard 로드 + 색 변수 정의 + 기존 색 전면 치환 + theme-color 변경 + 🚗 워드마크 교체
2. 공용 컴포넌트 클래스화: 버튼·배지·표·카드·프로그레스 (한 CSS 파일로)
3. 페이지 적용: 세금 템플릿 → 수첩 → 허브 → TCO → 법적 페이지
4. 확인: 375px 폭에서 가로 스크롤 없음, 히어로 금액 줄바꿈 없음, Lighthouse 성능 저하 없음(폰트 swap 확인)

## 금지 목록

- 이모지, 그림자, 그라데이션, 정의 외 색 추가, 페이지당 primary 버튼 2개 이상, 장식 애니메이션, 다크모드 임의 구현
- 브라우저 기본 파랑·보라 링크, 44px 미만 탭 타깃(산문 속 링크 제외), 상단 내비 4번째 항목
- 수첩 화면(index.html)의 광고, 페이지당 광고 2개 이상, 금지 구역의 광고, 자동 광고(광고 인텐트·비네트 포함)
