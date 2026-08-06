# 로컬 저장 스키마 (수첩 MVP)

MVP는 로그인 없이 브라우저 로컬 저장. 데이터량이 작으므로(텍스트 기록뿐) **localStorage에 단일 JSON 문서**로 저장한다. 사진 첨부·대용량 기능이 생기면 그때 IndexedDB로 이전한다.

- 저장 키: `carnote:v1`
- 최상위에 `schemaVersion`을 두고, 구조가 바뀌면 로드 시점에 마이그레이션 함수를 순차 적용한다 (`v1 → v2 → …`)
- 쓰기는 항상 문서 전체를 직렬화해서 저장 (부분 쓰기 없음 — 단순함 우선)
- **내보내기/가져오기(JSON 파일)를 MVP에 포함한다.** 로컬 저장은 브라우저 데이터 삭제로 유실되므로 백업 수단이 리텐션 보험이다. 추후 계정 동기화가 생기면 이 내보내기 포맷이 그대로 이관 포맷이 된다.

## 타입 정의

```typescript
interface CarnoteDocument {
  schemaVersion: 1;
  cars: Car[];
  records: MaintenanceRecord[];
  fuelLogs: FuelLog[];
  settings: Settings;
}

interface Car {
  id: string;                    // crypto.randomUUID()
  nickname: string | null;       // "우리 아반떼" — 없으면 modelName 표시
  modelName: string;             // 자유 입력. 등록 폼에 vehicles.json 기반 datalist 자동완성 제공
  vehicleId: string | null;      // 저장 시 modelName이 vehicles.json의 name/aliases와 일치하면 해당 id, 아니면 null
  fuelType: "gasoline" | "diesel" | "lpg" | "hybrid" | "ev";
  displacementCc: number | null; // 전기차는 null. 자동차세 추정에 사용
  firstRegisteredOn: string;     // "YYYY-MM-DD" 최초 등록일 — 검사 D-day·차령(자동차세 경감)·감가 계산 기준
  purchasePriceKrw: number | null; // 감가 추정용. 신차가가 아니라 "실제 지불액" (중고 구입가 포함). 미입력 시 감가 기능만 비활성
  purchasedOn: string | null;    // 중고 구입이면 최초 등록일과 다름. null이면 신차 구입으로 간주
  odometerLog: OdometerEntry[];  // 날짜 오름차순 append-only. 등록 시점 주행거리가 첫 원소. 기록·주유 입력 시마다 append
                                 // 최신 주행거리·월평균 주행거리는 여기서 파생 (이력이 있어야 "약 N월경" 예측 가능)
                                 // 예외 둘: ① 같은 날짜 재입력은 그 날짜 항목을 대체 ② 자기가 만든 항목의 롤백
                                 //   (기록 삭제 시 그 기록이 append한 항목 제거)은 허용. 과거 날짜는 append하지 않는다
  insuranceExpiresOn: string | null; // 보험 만기 알림용 (날짜만 저장 — 보험 정보는 그 이상 다루지 않음)
  lastInspectionOn: string | null;   // 최근 자동차 검사일. null이면 firstRegisteredOn + 4년 규칙으로 첫 검사일 추정
  enabledPartIds: string[];      // 이 차에서 추적하는 소모품 (parts.json의 defaultEnabled + appliesTo(fuelType)로 초기화, 사용자가 조정)
  createdAt: string;             // ISO 8601
  updatedAt: string;
}

interface OdometerEntry {
  date: string;                  // "YYYY-MM-DD"
  km: number;
}

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
  odometerKm: number;
  amount: number;                // 주유·충전량
  unit: "L" | "kWh";             // 입력 시 차량 fuelType으로 기본값. 레코드가 자기완결적이어야 fuelType 정정·PHEV 확장 시 마이그레이션이 없다
  unitPriceKrw: number | null;   // 단위당 단가
  totalKrw: number | null;       // 총액 — 단가·총액 중 하나만 입력해도 됨
  isFullTank: boolean;           // 실연비는 가득 주유(full-to-full) 구간에서만 계산
  createdAt: string;
}

interface Settings {
  reminderLeadDays: number;      // 날짜 기반 알림 며칠 전부터 표시 (기본 30)
  reminderLeadKm: number;        // 주행거리 기반 알림 몇 km 전부터 표시 (기본 1000)
  lastExportAt: string | null;   // 마지막 JSON 백업 시각 (ISO) — 30일 지나면 대시보드에 백업 유도 배너
}
```

## 파생 데이터 (저장하지 않고 계산)

저장소에는 사실만 두고, 알림·통계는 로드 시 계산한다. 규칙이 바뀌어도 저장 데이터 마이그레이션이 필요 없다.

- **최신 주행거리**: `odometerLog`의 마지막 원소
- **소모품 D-day**: 항목별 마지막 `MaintenanceRecord` + `parts.json`의 `intervalKm`/`intervalMonths` → 도래 시점. 기록이 없는 항목은 "기록 없음"으로 표시하고 첫 기록을 유도 (등록 시점 주행거리를 소모품 기준으로 삼지 않는다 — 중고차는 이전 이력을 모름)
- **월평균 주행거리**: `odometerLog`와 주유·정비 기록의 (주행거리, 날짜) 쌍에서 추정 → km 기반 주기를 날짜로 환산해 "약 N월경" 예측. 관측이 등록 시점 1개뿐이면 예측 대신 "주행거리를 한 번 더 입력하면 예측이 시작돼요" 안내
- **검사 D-day**: `lastInspectionOn`(없으면 `firstRegisteredOn` + `inspection.json` 규칙) → 다음 유효기간 만료일. 수검 가능 기간은 `windowBeforeDays`/`windowAfterDays`로 계산
- **실연비**: `isFullTank`인 주유 사이 구간 = (주행거리 차) ÷ (구간 주유량 합)
- **현재 추정 가치**: `purchasePriceKrw` × retention(현재 차령) ÷ retention(구입 시점 차령) — UI에 `disclaimerText` 필수 표기
  - 구입 시점 차령 = `purchasedOn` − `firstRegisteredOn` (`purchasedOn`이 null이면 차령 0 = 신차, retention(0) = 1.0이라 기존 식으로 수렴)
  - 구입가는 이미 감가된 가격이므로 구입 시점 잔존율로 나눠 신차가 기준으로 환원해야 이중 감가가 없다
  - 분모·분자 모두 동일한 규칙(연 중간 선형 보간, 곡선 범위 초과 시 `afterCurveYearlyDrop`·`minRetention`) 적용

## 마이그레이션 정책

1. 로드 시 `schemaVersion` 확인 → 현재 버전보다 낮으면 마이그레이션 체인 적용 → 저장
2. 마이그레이션 직전 원본을 `carnote:backup:v<version>` 키에 1회 백업
3. 파싱 실패(손상) 시: 손상 원본을 `carnote:v1:corrupt`에 보존 → 백업 키 복구 시도(최신 버전부터) → 모두 실패하면 빈 문서로 시작

## 외부 입력 정규화 (보안)

가져온 백업 파일은 신뢰하지 않는다. `load()`와 `importJson()`은 필드 단위로 타입을 강제한다
(숫자 필드 `Number` + 유한성 검사, 날짜 `YYYY-MM-DD` 정규식, id 문자 화이트리스트 — 불일치 시 null 또는 재발급).
innerHTML 렌더 경로에 사용자 파일의 문자열이 원문으로 흘러가는 저장형 XSS를 저장 층에서 차단하고,
렌더 층의 `esc()`와 이중 방어를 이룬다.
