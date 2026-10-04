# 로컬 저장 스키마 (수첩 MVP)

MVP는 로그인 없이 브라우저 로컬 저장. 데이터량이 작으므로(텍스트 기록뿐) **localStorage에 단일 JSON 문서**로 저장한다. 사진 첨부·대용량 기능이 생기면 그때 IndexedDB로 이전한다.

- 저장 키: `chailji:v1` (키 이름의 v1은 키 자체의 버전 — 문서 스키마 버전과 별개로 유지한다)
- 이 앱이 localStorage에 쓰는 키는 모두 `chailji:` 접두사 — 본 문서 `chailji:v1`, 마이그레이션 백업 `chailji:backup:v<n>`, 손상 원본 `chailji:v1:corrupt`.
  설정의 **'전체 데이터 삭제'는 이 접두사의 키를 전부 지운다** (`ChailjiStorage.wipeAll`, 개인정보처리방침 4항 '즉시·완전 삭제')
- 최상위에 `schemaVersion`을 두고, 구조가 바뀌면 로드 시점에 마이그레이션 함수를 순차 적용한다 (`v1 → v2 → …`)
- 현재 스키마: **v2** (아래 "버전 이력" 참고)
- 쓰기는 항상 문서 전체를 직렬화해서 저장 (부분 쓰기 없음 — 단순함 우선)
- **내보내기/가져오기(JSON 파일)를 MVP에 포함한다.** 로컬 저장은 브라우저 데이터 삭제로 유실되므로 백업 수단이 리텐션 보험이다. 추후 계정 동기화가 생기면 이 내보내기 포맷이 그대로 이관 포맷이 된다.

## 타입 정의

```typescript
interface ChailjiDocument {
  schemaVersion: 2;
  cars: Car[];
  records: MaintenanceRecord[];
  fuelLogs: FuelLog[];
  expenses: Expense[];           // v2 — 주유·정비 외 지출
  settings: Settings;
}

interface Car {
  id: string;                    // crypto.randomUUID()
  nickname: string | null;       // "우리 아반떼" — 없으면 modelName 표시
  modelName: string;             // 자유 입력. 등록 폼에 vehicles.json 기반 datalist 자동완성 제공
  vehicleId: string | null;      // 저장 시 modelName이 vehicles.json의 name/aliases와 일치하면 해당 id, 아니면 null
  fuelType: "gasoline" | "diesel" | "lpg" | "hybrid" | "ev"; // 과세 구분. 수소차(넥쏘)는 세법상 정액 과세라 "ev"
                                 // 실제 넣는 에너지(주유·충전 단위)는 vehicleId로 찾은 vehicles.json 항목의 energySource
                                 // ("hydrogen" 등), 없으면 fuelType에서 유도(ev→electricity, hybrid→gasoline …) — derive.energySource
  displacementCc: number | null; // 전기차는 null. 자동차세 추정에 사용
  firstRegisteredOn: string;     // "YYYY-MM-DD" 최초 등록일 — 검사 D-day·차령(자동차세 경감)·감가 계산 기준
  purchasePriceKrw: number | null; // 감가 추정용. 신차가가 아니라 "실제 지불액" (중고 구입가 포함). 미입력 시 감가 기능만 비활성
  purchasedOn: string | null;    // 중고 구입이면 최초 등록일과 다름. null이면 신차 구입으로 간주
  odometerLog: OdometerEntry[];  // 날짜 오름차순 append-only. 등록 시점 주행거리가 첫 원소. 기록·주유 입력 시마다 append
                                 // 최신 주행거리·월평균 주행거리는 여기서 파생 (이력이 있어야 "약 N월경" 예측 가능)
                                 // 예외 둘: ① 같은 날짜 재입력은 그 날짜 항목을 대체(대체 전 값은 prev에 보관)
                                 //   ② 기록 삭제 시 그 기록이 한 일만 되돌림(아래 OdometerEntry). 과거·미래 날짜는 append하지 않는다
  insuranceExpiresOn: string | null; // 보험 만기 알림용 (날짜만 저장 — 보험 정보는 그 이상 다루지 않음)
  lastInspectionOn: string | null;   // 최근 자동차 검사일. null이면 firstRegisteredOn + 4년 규칙으로 첫 검사일 추정
  enabledPartIds: string[];      // 이 차에서 추적하는 소모품 (parts.json의 defaultEnabled + appliesTo(fuelType)로 초기화, 사용자가 조정)
  createdAt: string;             // ISO 8601
  updatedAt: string;
}

interface OdometerEntry {
  date: string;                  // "YYYY-MM-DD"
  km: number;
  by?: string;                   // 이 값을 쓴 출처: 정비 기록·주유 기록의 id, 또는 "manual"(차 등록·대시보드 '갱신' — 직접 입력)
                                 // 없으면 출처 미상(이 필드 이전에 저장된 관측). "manual"은 예약어라 객체 id로 쓰이면 정규화가 재발급
  prev?: { km: number; by?: string }[]; // 같은 날 이 값에 덮어써진 이전 값들 (오래된 것 → 최근, 최근 10개까지)
}
```

**주행거리 관측 되돌리기 규칙** — 기록(정비·주유)을 지우면 그 기록이 로그에 한 일만 정확히 되돌린다.
같은 날 직접 입력한 값이나 다른 기록이 쓴 값을 지우지 않기 위함이다.

| 지운 기록과 그 날짜 항목의 관계 | 처리 |
|---|---|
| 항목의 `by`가 그 기록 (지금 보이는 값을 쓴 쪽) · `prev` 있음 | `prev`의 마지막 값(과 출처)으로 복원 — 덮어쓰기 전 값으로 |
| 〃 · `prev` 없음 | 그 기록이 새로 추가한 항목이므로 제거 (로그의 유일한 항목이면 남김) |
| 그 기록이 `prev` 안에 있음 (이미 다른 값에 덮어써짐) | 보이는 값은 그대로, `prev`에서 그 기록 몫만 제거 |
| 항목에 `by`도 `prev`도 없음 (출처 미상 옛 관측) | 예전 규칙: 날짜·km가 같고 같은 (날짜, km)의 다른 정비·주유 기록이 남아 있지 않을 때만 제거 |
| 그 밖 | 아무것도 하지 않음 |

- 직접 입력을 같은 날 직접 입력으로 고치면 `prev`에 쌓지 않는다(직접 입력은 지우는 기록이 없다)
- 되돌리기(삭제 토스트)는 삭제 직전 항목으로 복원하되, 그사이 그 날짜 항목이 바뀌었으면 새 값을 존중해 그대로 둔다
- 미래 날짜 관측은 받지 않는다 — 날짜 입력은 오늘(로컬 날짜)까지, 저장 단계에서도 거부. 끝에 붙으면 그날까지 '갱신'이 전부 막힌다
- 선택 필드라 스키마 버전은 그대로(v2). 이 필드를 모르는 옛 앱이 저장하면 빠지고, 그 관측은 출처 미상 규칙을 따른다

```typescript
interface MaintenanceRecord {
  id: string;
  carId: string;
  partId: string | null;         // data/parts.json 참조. 커스텀 항목이면 null + customLabel
  customLabel: string | null;
  doneOn: string;                // "YYYY-MM-DD"
  odometerKm: number | null;     // 교체 시점 주행거리 (다음 알림 계산 기준 — 미입력 허용)
  costKrw: number | null;
  shop: string | null;           // "OO카센터" 자유 입력
  memo: string | null;
  createdAt: string;
}

interface FuelLog {
  id: string;
  carId: string;
  filledOn: string;              // "YYYY-MM-DD"
  odometerKm: number | null;     // 선택 — 주유소에서 계기판을 못 봤을 수 있다. 없으면 실연비 구간의 끝점이 못 될 뿐
                                 // (v1 시절에도 정규화가 null을 허용했으므로 스키마 버전 변경 없이 문서만 정정)
                                 // 입력되면 정비 기록과 같은 규칙으로 odometerLog에 append (같은 날짜 대체, 과거 날짜·더 작은 값 미반영, 삭제 시 이 기록이 한 일만 되돌림). 날짜는 오늘까지
  amount: number | null;         // 주유·충전량(소수 둘째 자리까지). '5만원어치'처럼 금액만 아는 주유는 null
  unit: "L" | "kWh" | "kg";      // 입력 시 차의 에너지원으로 기본값(전기 kWh, 수소 kg, 그 외 L — 수소차는 kg만).
                                 // 레코드가 자기완결적이어야 fuelType 정정·PHEV 확장 시 마이그레이션이 없다. 모르는 값은 정규화가 "L"로
  unitPriceKrw: number | null;   // 단위당 단가(소수 허용 — 전기 347.2원/kWh 등)
  totalKrw: number | null;       // 총액 — 총액, 또는 주유량+단가 중 하나는 있어야 입력 가능(폼 검증)
  isFullTank: boolean;           // 실연비는 가득 주유(full-to-full) 구간에서만 계산
  createdAt: string;
}

interface Expense {              // v2. 주유·충전(FuelLog)·정비(MaintenanceRecord) 외의 지출
  id: string;
  carId: string;
  spentOn: string;               // "YYYY-MM-DD"
  category: string | null;       // data/expense-categories.json의 id (wash, parking, tax, other …)
                                 // 저장 층은 형식(id 문자 화이트리스트)만 검사 — 모르는 id·null은 화면에서 fallbackId(기타)로 표시
                                 // 보험료 분류는 두지 않는다(보험은 만기일 외에는 다루지 않음) — 사용자는 '기타'로 기록
  amountKrw: number;             // 원, 0 이상 정수. 없거나 숫자가 아니면 정규화에서 항목 제거
  memo: string | null;
  createdAt: string;
}

interface Settings {
  reminderLeadDays: number;      // 날짜 기반 알림 며칠 전부터 표시 (기본 30)
  reminderLeadKm: number;        // 주행거리 기반 알림 몇 km 전부터 표시 (기본 1000)
  lastExportAt: string | null;   // 마지막 JSON 백업 시각 (ISO) — 정비·주유·지출 기록이 합쳐 5건 이상이고
                                 // 마지막 백업 후 30일 지나면(또는 백업한 적 없으면) 대시보드에 백업 유도 배너
}
```

## 파생 데이터 (저장하지 않고 계산)

저장소에는 사실만 두고, 알림·통계는 로드 시 계산한다. 규칙이 바뀌어도 저장 데이터 마이그레이션이 필요 없다.

- **최신 주행거리**: `odometerLog`의 마지막 원소
- **소모품 D-day**: 항목별 마지막 `MaintenanceRecord` + `parts.json`의 `intervalKm`/`intervalMonths` → 도래 시점. 기록이 없는 항목은 "기록 없음"으로 표시하고 첫 기록을 유도 (등록 시점 주행거리를 소모품 기준으로 삼지 않는다 — 중고차는 이전 이력을 모름)
- **월평균 주행거리**: `odometerLog`와 주유·정비 기록의 (주행거리, 날짜) 쌍에서 추정 → km 기반 주기를 날짜로 환산해 "약 N월경" 예측. 관측이 등록 시점 1개뿐이면 예측 대신 "주행거리를 한 번 더 입력하면 예측이 시작돼요" 안내
- **검사 D-day**: `lastInspectionOn`(없으면 `firstRegisteredOn` + `inspection.json` 규칙) → 다음 유효기간 만료일. 수검 가능 기간은 `windowBeforeDays`/`windowAfterDays`로 계산
- **실연비** (`fuelEconomy`): `isFullTank`인 주유 사이 구간 = (주행거리 차) ÷ (구간 주유량 합). 단위는 기록의 `unit` 그대로(km/L·km/kWh·km/kg)
  - 끝점은 **주행거리가 있는** 가득 주유. 주유량 합은 앞 끝점 *다음* 주유부터 뒤 끝점까지(앞 끝점의 양은 그 전 구간 몫)
  - 구간 안의 부분 주유와 주행거리 없는 가득 주유는 끝점이 못 될 뿐 양은 합산
  - 주유량이 없으면 `totalKrw ÷ unitPriceKrw`로 추정. 그것도 안 되는 주유가 끼거나(금액만 적은 주유), 단위가 섞인 구간은 제외
  - **주행거리가 기준 끝점보다 줄어든 가득 주유**(자릿수 누락 오타 등)는 구간도 다음 기준점도 되지 못한다(양은 다음 구간에 합산). 다음 끝점으로 판정:
    - 다음 끝점 > 기준 끝점 → 줄어든 값은 오타. 기준 끝점부터 다음 끝점까지 한 구간
    - 기준 끝점 > 다음 끝점 > 줄어든 값 → 계기판 교체 등 새 출발. 줄어든 값부터 다음 끝점까지
    - 다음 끝점이 기준 끝점보다 작지만 그 앞 기준 끝점보다 크면 → 기준 끝점이 튄 값(자릿수가 붙은 오타). 앞 구간을 버리고 앞 기준 끝점부터 다음 끝점까지 다시 잰다
  - 같은 주행거리로 다시 기록한 가득 주유(중복 저장·추가 주유)는 구간 없이 기준점만 옮긴다(양이 이중으로 잡히지 않게)
  - 합산 실연비 = 유효 구간 거리 합 ÷ 양 합 (단위가 섞인 이력이면 가장 최근 유효 구간의 단위로만). 유효 구간이 없으면 표시하지 않음
  - 실연비가 없을 때 안내는 이유별(`fuelEconomyGap`): 주행거리 있는 가득 주유가 2번 미만 / 끝점 사이에 양을 모르는 주유가 있음 / 그 밖(단위 섞임 등)
  - 공인연비(vehicles.json `fuelEconomy`)는 그 차종 에너지원의 단위와 실연비 단위가 같을 때만 나란히 표시
- **지출 항목** (`spendEntries`): 차 한 대의 정비(`costKrw`가 있는 기록) + 주유·충전 + `expenses`를 한 목록으로. 최근순(날짜 내림차순, 같은 날은 `createdAt` 늦은 것 먼저)
  - 분류: 정비 = `maintenance`, 주유 = `fuel`(예약 id), 그 외는 `Expense.category`
  - 주유 금액 = `totalKrw`, 없으면 `amount × unitPriceKrw`(반올림). 둘 다 없으면 금액 미상 — 건수에는 포함, 합계에서는 제외
- **월별 지출** (`monthSpend`): 달 키는 날짜 문자열의 앞 7자리(`YYYY-MM`, 로컬 날짜 기준). 합계·건수·분류별 합계(금액 큰 순)
- **최근 N개월 시계열** (`spendSeries`): 이번 달 포함 N개월, 오래된 달 → 이번 달. N은 `data/expense-categories.json`의 `chartMonths`
- **월평균** (`monthlyAverageSpend`): 진행 중인 이번 달은 빼고 직전 N개월(`averageMonths`) 중 **첫 기록 달 이후**의 달만 평균. 첫 기록 이후 기록이 없는 달은 0원으로 포함. 완결된 달이 없으면 표시하지 않음
- **현재 추정 가치**: `purchasePriceKrw` × retention(현재 차령) ÷ retention(구입 시점 차령) — UI에 `disclaimerText` 필수 표기
  - 구입 시점 차령 = `purchasedOn` − `firstRegisteredOn` (`purchasedOn`이 null이면 차령 0 = 신차, retention(0) = 1.0이라 기존 식으로 수렴)
  - 구입가는 이미 감가된 가격이므로 구입 시점 잔존율로 나눠 신차가 기준으로 환원해야 이중 감가가 없다
  - 분모·분자 모두 동일한 규칙(연 중간 선형 보간, 곡선 범위 초과 시 `afterCurveYearlyDrop`·`minRetention`) 적용

## 마이그레이션 정책

1. 로드 시 `schemaVersion` 확인 → 현재 버전보다 낮으면 마이그레이션 체인 적용 → 정규화 → 저장
   - 순서는 **마이그레이션(원본 구조) → 정규화(현재 구조)**. 정규화를 먼저 하면 옛 필드가 지워져 필드 이름을 바꾸는 류의 마이그레이션이 옮길 값을 잃는다. 그래서 마이그레이션 함수는 필드가 없거나 타입이 틀린 입력에도 죽지 않게 쓴다
2. 마이그레이션 직전 원본을 `chailji:backup:v<version>` 키에 1회 백업 — 값은 `{backupAt: ISO 시각, doc: 원본}` (가져오기 미리보기·백업 복구 경로는 확정 전이므로 백업 키를 쓰지 않음)
   - **보존 기간 30일**(`BACKUP_KEEP_DAYS`): 마이그레이션 결과 저장 뒤에도 바로 지우지 않는다 — 새 버전의 마이그레이션 결함은 며칠 안에 드러나고, 그동안은 손상 복구에 쓴다
   - 본 문서가 정상으로 읽힌 로드마다 정리: 30일 지난 백업·읽을 수 없는 백업 삭제. 시각 없이 문서만 담긴 옛 형식(초기 v2 빌드)은 그때 지금 시각으로 다시 감싸 30일을 센다
   - 몇 달 묵은 스냅샷을 조용히 되살리는 것도 데이터 손실이라 기한을 둔다
   - 데이터를 지우거나 통째로 바꾸는 동작은 옛 스냅샷이 되살아나지 않게 함께 지운다: '이 차 삭제'·'백업 가져오기' → 백업·손상 원본 삭제(`clearBackups`), '전체 데이터 삭제' → `chailji:` 키 전부(`wipeAll`)
3. 파싱 실패(손상) 시: 손상 원본을 `chailji:v1:corrupt`에 보존 → 백업 키 복구 시도(최신 버전부터, 보존 기간 안의 것만 남아 있음) → 모두 실패하면 빈 문서로 시작
4. `schemaVersion`은 1 이상의 정수여야 문서로 인정한다 (0·소수·문자열은 마이그레이션 체인에 없으므로 형태 불일치로 취급)
5. 미래 버전(`schemaVersion` > 현재):
   - 가져오기: 거부하고 앱 업데이트 안내
   - 로드(새 버전 앱이 저장한 문서를 캐시된 옛 앱이 연 경우 등): 버전 번호는 그대로 두고 아는 필드만 정규화해 사용. 모르는 최상위 필드는 보존, 아는 객체 안의 모르는 필드는 정규화에서 빠진다

### 버전 이력

| 버전 | 변경 | 마이그레이션 |
|---|---|---|
| v1 | 최초 (`cars`·`records`·`fuelLogs`·`settings`) | — |
| v2 | `expenses: Expense[]` 추가 (세차·주차·통행료·자동차세·기타 지출). `FuelLog.odometerKm`·`amount` 선택 입력으로 명시 | v1 → v2: `expenses`가 배열이 아니면 빈 배열 |
| v2 (버전 유지) | 선택 필드·값 추가: `OdometerEntry.by`·`prev`(관측 출처), `FuelLog.unit`에 `"kg"`(수소) | 없음 — 없으면 출처 미상·기존 단위로 동작 |

`isValidDoc`(최소 형태 검증)은 v1부터 있던 필드만 요구한다 — 구버전 백업에는 `expenses`가 없으므로, 없거나 배열이 아니면 문서 전체를 버리지 않고 마이그레이션·정규화가 빈 배열로 채운다.

## 외부 입력 정규화 (보안)

가져온 백업 파일은 신뢰하지 않는다. `load()`와 `importJson()`은 필드 단위로 타입을 강제한다
(숫자 필드는 숫자·숫자 문자열만 받아 `Number` + 유한성 검사(`[]`·공백 문자열이 0이 되는 암묵 변환 차단),
날짜 `YYYY-MM-DD` 정규식, id 문자 화이트리스트 — 불일치 시 null 또는 재발급. 다른 객체를 가리키는 `carId`는 재발급 대신 비움,
같은 배열 안의 중복 id는 뒤의 것을 재발급(`cars` 포함 — 겹치던 id를 가리키던 기록은 앞의 차에 남는다), 예약어 `"manual"`인 id도 재발급,
`FuelLog.unit`은 `L`·`kWh`·`kg` 외에는 `L`, `OdometerEntry.by`는 id 형식만·`prev`는 숫자 km만, `isFullTank`는 `true`일 때만 참).
innerHTML 렌더 경로에 사용자 파일의 문자열이 원문으로 흘러가는 저장형 XSS를 저장 층에서 차단하고,
렌더 층의 `esc()`와 이중 방어를 이룬다.
