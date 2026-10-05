# 차일지 (베타)

내 차 소모품 교체 주기·자동차 검사 일정을 챙겨주는 수첩 + 차종별 자동차세 계산 + 유지비(TCO) 비교.

- **수첩**: 차 등록 → 소모품 교체 기록 → D-day 알림. 모든 기록은 브라우저(localStorage)에만 저장되며 서버로 전송되지 않습니다. JSON 내보내기/가져오기로 백업.
- **차종별 자동차세**: 국산·수입 인기 차종(승용·화물·승합)의 연식별 자동차세·연납 할인 표 (지방세법 제127조 기준). 차종 목록은 `data/vehicles.json`.
- **유지비 비교**: 두 차종의 월 유지비(자동차세+연료비+보험+감가)를 나란히 비교.

## 개발

노빌드 바닐라 HTML/CSS/JS. 차종별 페이지는 Python으로 정적 생성.

```bash
python3 -m http.server 8347        # 로컬 실행 → http://127.0.0.1:8347
python3 scripts/build.py           # data/*.json 변경 시 tax/ 페이지·sitemap.xml 재생성
```

`tax/`는 빌드 전용 폴더예요. 빌드는 더 이상 만들지 않는 차종 페이지(차종 삭제·slug 변경·`sample` 전환·배기량 비움)를
지우고 그 이름을 출력합니다(`tax/index.html`·`tax/calculator.html`은 빼고). 손으로 만든 페이지는 `tax/`에 두지 마세요.

빌드는 공유 썸네일(`og/*.png`, 카카오톡·SNS 미리보기)과 홈 화면 아이콘(`icons/`, `favicon.ico`)도 함께 그립니다.
Pillow가 필요합니다: `pip3 install --user pillow`. 없으면 빌드는 그대로 되지만 새 이미지를 그리지 못하고,
금액이 바뀌어 낡은 썸네일은 og:image에서 빠집니다. 폰트는 `scripts/fonts/`의 Pretendard(OFL)를 씁니다.
썸네일 디자인을 바꾸면 `scripts/images.py`의 `RENDER_VERSION`을 올리세요 — 전부 다시 그려지고 URL의 `?v=`가 바뀌어 카톡 캐시도 갱신됩니다.

로직 테스트 (macOS 내장 JavaScriptCore):

```bash
jsc js/derive.js tests/derive.test.js
jsc js/storage.js tests/storage.test.js
```

node가 있으면 `node tests/run.js` 하나로 전부 돌아갑니다. 각 테스트 파일 첫 줄의 `jsc 실행: jsc …` 주석을 읽어 같은 파일을 로드하므로, 새 테스트도 첫 줄만 그 형식으로 쓰면 자동으로 포함돼요.

세율·소모품 주기 등 모든 상수는 `data/*.json`에 있습니다. 계산 결과는 참고용이며 실제 고지 세액은 위택스에서 확인하세요.

## 검사

커밋하기 전에 한 줄만 돌리면 됩니다. 깃허브에 push하거나 PR을 열면 같은 검사가 자동으로 돌아요(Actions 탭 '자동 검사').

```bash
python3 scripts/check.py          # 전부 (1~2초)
python3 scripts/check.py data     # 하나만: data · tests · parity · build · links
```

| 검사 | 잡아내는 것 |
|---|---|
| 데이터 (`scripts/validate_data.py`) | `data/*.json` 실수 — JSON 문법, slug·id 중복, 배기량·연비·연식 범위, 세율표 순서, 공제율 단위(5% → 0.05) |
| JS 테스트 (`node tests/run.js`) | `tests/*.test.js` 전부. node가 없으면 macOS jsc로 돌리고, 둘 다 없으면 건너뜀(CI에서는 돌아감) |
| 세액 일치 (`scripts/check_tax_parity.py`) | 차종 페이지(`build.py`)와 계산기(`js/tax-calc.js`)의 세액이 모든 배기량·차령에서 1원까지 같은지 |
| 빌드 최신 여부 | `data/*.json`이나 `build.py`를 바꾸고 빌드를 안 돌렸는지. 임시 폴더에서 빌드해 `tax/`·`og/`·`icons/`·`favicon.ico`·`robots.txt`·`sitemap.xml`과 비교해요(작업 중인 파일은 안 건드림). `sitemap.xml`은 날짜(`lastmod`)만 빼고 비교해 차종 추가·삭제가 빠진 낡은 sitemap을 잡고, 빌드가 더 이상 만들지 않는 `tax/` 페이지·썸네일이 남아 있으면 '지워짐'으로 알려 줘요 |
| 링크 (`scripts/check_links.py`) | 모든 페이지의 깨진 내부 링크. 대소문자까지 봐요(Mac에선 열려도 GitHub Pages에선 404) |

CI는 사용자 Mac과 같은 Python 3.9로도 `scripts/check.py`를 한 번 더 돌려, 3.10 이상 전용 문법이 섞이면 알려 줍니다.

**실패하면** 메시지의 '→' 또는 '고치는 법'대로 고친 뒤 다시 돌리세요. 자주 나오는 경우:

- 빌드 결과가 최신이 아니에요 → `python3 scripts/build.py` 실행 후 생성물을 바뀐 것·새로 생긴 것·지워진 것까지 모두 같이 커밋: `git add tax og icons favicon.ico robots.txt sitemap.xml` (지워진 파일도 담겨요). '지워짐'은 빌드가 더 이상 만들지 않는 페이지·썸네일이라 빌드를 돌리면 작업 폴더에서도 지워져요. `sitemap.xml`은 날짜만 바뀐 건 커밋하지 않아도 통과해요. 1월 1일이 지나 연도가 바뀌면 전 페이지가 바뀌는 게 정상이니 새해에 한 번 빌드해 커밋하세요.
- 세액 불일치 → `build.py`의 `tax_for`·`prepay`와 `js/tax-calc.js`의 `taxFor`·`prepay` 중 한쪽만 고친 상태. 두 곳의 계산 순서·10원 미만 절사를 똑같이 맞추세요.
- 데이터 오류 → 메시지에 파일·몇 번째 항목(id)·줄 번호·필드가 나와요. 배기량을 모르면 추정하지 말고 `null`로 두세요(경고만 뜨고 그 차종 페이지는 빠짐).
