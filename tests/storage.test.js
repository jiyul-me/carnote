/* jsc 실행: jsc js/storage.js tests/storage.test.js (localStorage 없음 → 인메모리 폴백) */
(function () {
  'use strict';
  var S = globalThis.ChailjiStorage;
  var failures = 0, total = 0;
  function ok(cond, label) {
    total++;
    if (!cond) { failures++; print('FAIL ' + label); }
  }

  // 빈 상태 로드
  var doc = S.load();
  ok(S.isValidDoc(doc), '빈 로드 → 유효 문서');
  ok(doc.cars.length === 0 && doc.settings.reminderLeadDays === 30, '기본값');

  // 저장 → 재로드
  doc.cars.push({ id: 'c1' });
  S.save(doc);
  ok(S.load().cars.length === 1, '저장 후 재로드');

  // 내보내기 → 가져오기 왕복
  var res = S.importJson(S.exportJson(doc));
  ok(!res.error && res.doc.cars.length === 1, '내보내기/가져오기 왕복');

  // 불량 입력
  ok(S.importJson('{{{').error != null, '깨진 JSON 거부');
  ok(S.importJson('{"foo":1}').error != null, '형태 불일치 거부');
  ok(S.importJson('{"schemaVersion":99,"cars":[],"records":[],"fuelLogs":[],"settings":{}}').error != null, '미래 버전 거부');

  // uuid 유일성
  ok(S.uuid() !== S.uuid(), 'uuid 유일');

  // 정규화: 악성·오염 백업의 필드 타입 강제 (저장형 XSS 차단)
  var dirty = S.emptyDoc();
  dirty.cars.push({
    id: '"><img src=x onerror=alert(1)>',
    modelName: '아반떼',
    fuelType: '이상한값',
    displacementCc: '<script>1</script>',
    firstRegisteredOn: '<img src=x onerror=alert(1)>',
    purchasePriceKrw: 'NaN아님',
    odometerLog: [{ date: '2026-01-01', km: '3000' }, { date: 'not-a-date', km: 100 }],
    enabledPartIds: ['engine-oil', '<bad>', 42]
  });
  dirty.records.push({ carId: 'c1', doneOn: 'javascript:alert(1)', odometerKm: 1 });
  dirty.settings.reminderLeadDays = '<b>30</b>';
  var res2 = S.importJson(JSON.stringify(dirty));
  ok(!res2.error, '정규화 대상도 가져오기 자체는 성공');
  var c = res2.doc.cars[0];
  ok(/^[A-Za-z0-9_.:-]+$/.test(c.id), '악성 id 재발급');
  ok(c.fuelType === 'gasoline', '알 수 없는 연료 → 기본값');
  ok(c.displacementCc === null, '숫자 아닌 배기량 → null');
  ok(c.firstRegisteredOn === null, '날짜 형식 아님 → null');
  ok(c.purchasePriceKrw === null, '숫자 아닌 구매가 → null');
  ok(c.odometerLog.length === 1 && c.odometerLog[0].km === 3000, '불량 로그 항목 제거·숫자 강제');
  ok(c.enabledPartIds.length === 1 && c.enabledPartIds[0] === 'engine-oil', '불량 partId 제거');
  ok(res2.doc.records.length === 0, '날짜 없는 기록 제거');
  ok(res2.doc.settings.reminderLeadDays === 30, '설정 숫자 강제');

  // ---------- v2: 지출(expenses) ----------
  ok(S.CURRENT_VERSION === 2, '현재 스키마 v2');
  ok(Array.isArray(S.emptyDoc().expenses) && S.emptyDoc().expenses.length === 0, '빈 문서에 expenses 배열');

  // v1 문서 로드 → 마이그레이션: expenses 빈 배열 추가, 버전 올림, 즉시 저장, 기존 데이터 보존
  var V1 = {
    schemaVersion: 1,
    cars: [{ id: 'car-a', modelName: '아반떼', fuelType: 'gasoline', firstRegisteredOn: '2022-01-01',
      odometerLog: [{ date: '2026-01-01', km: 30000 }], enabledPartIds: ['engine-oil'] }],
    records: [{ id: 'r1', carId: 'car-a', partId: 'engine-oil', doneOn: '2026-02-01', costKrw: 85000 }],
    fuelLogs: [{ id: 'f1', carId: 'car-a', filledOn: '2026-03-01', odometerKm: 31000, amount: 40.25, unit: 'L', unitPriceKrw: 1650, totalKrw: null, isFullTank: true }],
    settings: { reminderLeadDays: 20, reminderLeadKm: 800, lastExportAt: null }
  };
  S.save(V1);
  var mig = S.load();
  ok(mig.schemaVersion === 2, 'v1 로드 → v2로 마이그레이션');
  ok(Array.isArray(mig.expenses) && mig.expenses.length === 0, 'v1 → v2: expenses 빈 배열');
  ok(mig.cars[0].id === 'car-a' && mig.records[0].costKrw === 85000 && mig.settings.reminderLeadDays === 20, '마이그레이션 후 기존 데이터 보존');
  ok(mig.fuelLogs[0].amount === 40.25, '주유량 소수 보존');
  var reloaded = S.load();
  ok(reloaded.schemaVersion === 2 && Array.isArray(reloaded.expenses), '마이그레이션 결과가 저장돼 재로드도 v2');

  // 손상 시 마이그레이션 직전 백업(v1)에서 복구 → 다시 v2로
  S.save('깨진 문서'); // 문자열 JSON — 형태 검증 실패
  var restored = S.load();
  ok(restored.schemaVersion === 2 && restored.cars.length === 1 && restored.cars[0].id === 'car-a', '손상 → v1 백업에서 복구 후 마이그레이션');

  // 구버전 백업 가져오기 → v2 문서로 반환
  var imp = S.importJson(JSON.stringify(V1));
  ok(!imp.error && imp.doc.schemaVersion === 2 && imp.doc.expenses.length === 0, 'v1 백업 가져오기 → v2');

  // 이상한 버전 번호는 형태 불일치로 거부 (마이그레이션 체인에 없음 — 예외가 새지 않게)
  ok(S.importJson('{"schemaVersion":0,"cars":[],"records":[],"fuelLogs":[],"settings":{}}').error != null, 'v0 거부');
  ok(S.importJson('{"schemaVersion":1.5,"cars":[],"records":[],"fuelLogs":[],"settings":{}}').error != null, '소수 버전 거부');
  ok(S.importJson('{"schemaVersion":1e999,"cars":[],"records":[],"fuelLogs":[],"settings":{}}').error != null, 'Infinity 버전 거부');
  ok(S.importJson('{"schemaVersion":"2","cars":[],"records":[],"fuelLogs":[],"settings":{}}').error != null, '문자열 버전 거부');
  // v2인데 expenses가 없거나 배열이 아니어도 문서 전체를 버리지 않고 빈 배열로
  var noExp = S.importJson('{"schemaVersion":2,"cars":[],"records":[],"fuelLogs":[],"settings":{}}');
  ok(!noExp.error && noExp.doc.expenses.length === 0, 'v2 expenses 누락 → 빈 배열');
  var badExp = S.importJson('{"schemaVersion":2,"cars":[],"records":[],"fuelLogs":[],"expenses":"<img>","settings":{}}');
  ok(!badExp.error && Array.isArray(badExp.doc.expenses) && badExp.doc.expenses.length === 0, 'expenses가 배열 아님 → 빈 배열');

  // 악성·오염 expenses 정규화
  var dirtyV2 = S.emptyDoc();
  dirtyV2.expenses = [
    { id: '"><svg onload=alert(1)>', carId: 'car-a', spentOn: '2026-10-01', category: 'wash', amountKrw: '15000', memo: '<script>x</script>' },
    { id: 'e-ok', carId: '"><b>', spentOn: '2026-10-02', category: '<img src=x>', amountKrw: 3000, memo: 42 },
    { id: 'e-ok', carId: 'car-a', spentOn: '2026-10-03', category: 'parking', amountKrw: 4000 },       // 중복 id
    { id: 'e-date', carId: 'car-a', spentOn: '10/03/2026', category: 'wash', amountKrw: 1000 },        // 날짜 형식 아님 → 제거
    { id: 'e-amt', carId: 'car-a', spentOn: '2026-10-03', category: 'wash', amountKrw: '만원' },        // 금액 숫자 아님 → 제거
    { id: 'e-neg', carId: 'car-a', spentOn: '2026-10-03', category: 'wash', amountKrw: -5000 },         // 음수 → 제거
    { id: 'e-arr', carId: 'car-a', spentOn: '2026-10-03', category: 'wash', amountKrw: [] },            // Number([])=0 함정 → 제거
    null, 7, 'str'
  ];
  dirtyV2.fuelLogs = [
    { id: 'f-x', carId: 'car-a', filledOn: '2026-10-01', odometerKm: '', amount: '40.567', unit: '<b>', unitPriceKrw: '347.2', totalKrw: 'abc', isFullTank: 'false' }
  ];
  var res3 = S.importJson(JSON.stringify(dirtyV2));
  ok(!res3.error, '오염된 v2 문서도 가져오기 자체는 성공');
  var ex = res3.doc.expenses;
  ok(ex.length === 3, '날짜·금액 불량 항목과 객체 아닌 항목 제거 (' + ex.length + ')');
  ok(/^[A-Za-z0-9_.:-]+$/.test(ex[0].id), '악성 지출 id 재발급');
  ok(ex[0].amountKrw === 15000 && ex[0].category === 'wash', '숫자 문자열 금액 강제');
  ok(ex[0].memo === '<script>x</script>', '메모는 문자열로 보존(렌더 층 esc()가 처리)');
  ok(ex[1].carId === '' && ex[1].category === null && ex[1].memo === '42', '악성 carId·분류 → 비움, 메모 문자열화');
  ok(ex[1].id !== ex[2].id && ex[1].id === 'e-ok', '중복 id는 뒤의 것을 재발급');
  var fx = res3.doc.fuelLogs[0];
  ok(fx.odometerKm === null, '주행거리 빈 값 → null (선택 입력)');
  ok(fx.amount === 40.57 && fx.unitPriceKrw === 347.2, '주유량·단가 소수 허용(둘째 자리)');
  ok(fx.totalKrw === null && fx.unit === 'L', '총액 불량 → null, 단위 불량 → L');
  ok(fx.isFullTank === false, '문자열 "false"는 가득 주유 아님');

  // 미래 버전: 가져오기는 거부, 로드는 버전 유지한 채 정규화해서 사용 (모르는 최상위 필드 보존)
  S.save({ schemaVersion: 9, cars: [{ id: '"><img src=x>', modelName: 'x' }], records: [], fuelLogs: [], settings: {}, futureField: [1] });
  var fut = S.load();
  ok(fut.schemaVersion === 9, '미래 버전 번호 유지');
  ok(/^[A-Za-z0-9_.:-]+$/.test(fut.cars[0].id), '미래 버전 로드도 정규화(저장형 XSS 차단)');
  ok(Array.isArray(fut.expenses), '미래 버전 로드에도 expenses 배열 보장');
  ok(Array.isArray(fut.futureField), '미래 버전의 모르는 최상위 필드 보존');

  // ---------- 전체 삭제·백업 보존 정책 ----------
  // 지금까지의 테스트가 본 키·마이그레이션 백업·손상 원본을 모두 남겨 둔 상태
  ok(S._keys().length >= 3, '삭제 전: 본 키·백업·손상 원본 존재 (' + S._keys().join(',') + ')');
  S.wipeAll();
  ok(S._keys().length === 0, '전체 삭제 → 이 앱의 키가 하나도 남지 않음 (' + S._keys().join(',') + ')');
  ok(S.load().cars.length === 0, '전체 삭제 후 로드 → 빈 문서');
  S.save('깨진 문서');
  ok(S.load().cars.length === 0, '전체 삭제 후 손상 → 지운 데이터가 백업에서 되살아나지 않음');
  S.wipeAll();

  // 마이그레이션 백업은 시각과 함께 저장되고, 보존 기간 안에는 손상 복구에 쓰인다
  S.save(V1);
  S.load();
  var bkKeys = S._keys().filter(function (k) { return k.indexOf('chailji:backup:') === 0; });
  ok(bkKeys.length === 1 && bkKeys[0] === 'chailji:backup:v1', '마이그레이션 → 백업 키 1개');
  var DAY = 86400000;
  S.pruneBackups(Date.now() + 10 * DAY);
  S.save('깨진 문서');
  ok(S.load().cars.length === 1, '보존 기간(10일 뒤) 안 → 손상 시 백업에서 복구');
  // 보존 기간이 지나면 정상 로드 때 지운다
  S.save(S.importJson(JSON.stringify(V1)).doc);
  S.pruneBackups(Date.now() + (S.BACKUP_KEEP_DAYS + 1) * DAY);
  ok(S._keys().filter(function (k) { return k.indexOf('chailji:backup:') === 0; }).length === 0, '보존 기간 지난 백업 삭제');
  S.save('깨진 문서');
  ok(S.load().cars.length === 0, '백업 삭제 후 손상 → 옛 스냅샷을 되살리지 않음');
  S.wipeAll();

  // 시각 없이 문서만 쓰던 초기 v2 빌드의 백업: 손상 복구에 그대로 쓰이고,
  // 정상 로드 때 지금 시각으로 다시 감싸 그때부터 보존 기간을 센다
  var be = S._backend();
  be.setItem('chailji:backup:v1', JSON.stringify(V1));
  S.save('깨진 문서');
  ok(S.load().cars.length === 1, '옛 형식(시각 없음) 백업도 복구');
  S.save(S.importJson(JSON.stringify(V1)).doc);
  S.load(); // 정상 로드 → 정리: 옛 형식은 다시 감쌈
  var rewrapped = JSON.parse(be.getItem('chailji:backup:v1'));
  ok(typeof rewrapped.backupAt === 'string' && rewrapped.doc.schemaVersion === 1, '옛 형식 백업 → 시각과 함께 다시 감쌈');
  S.pruneBackups(Date.now() + (S.BACKUP_KEEP_DAYS + 1) * DAY);
  ok(be.getItem('chailji:backup:v1') == null, '다시 감싼 백업도 보존 기간 뒤 삭제');
  be.setItem('chailji:backup:v1', '{깨진');
  S.pruneBackups();
  ok(be.getItem('chailji:backup:v1') == null, '읽을 수 없는 백업은 정리 때 삭제');
  S.wipeAll();

  // clearBackups: 본 문서는 두고 백업·손상 원본만 (차 삭제·가져오기 뒤)
  S.save(V1);
  S.load();
  S.save('깨진 문서');
  S.load(); // 손상 원본 키 생성
  S.save(S.importJson(JSON.stringify(V1)).doc);
  S.clearBackups();
  ok(S._keys().length === 1 && S._keys()[0] === S.KEY, 'clearBackups → 본 키만 남음 (' + S._keys().join(',') + ')');
  ok(S.load().cars.length === 1, 'clearBackups 후 본 문서 그대로');
  S.wipeAll();

  // ---------- 차 중복 id ----------
  var dupCars = S.importJson(JSON.stringify({
    schemaVersion: 2,
    cars: [{ id: 'c1', modelName: 'A' }, { id: 'c1', modelName: 'B' }, { id: 'c2', modelName: 'C' }],
    records: [{ id: 'r1', carId: 'c1', doneOn: '2026-01-02' }, { id: 'r1', carId: 'c1', doneOn: '2026-01-03' }],
    fuelLogs: [], expenses: [], settings: {}
  }));
  var dc = dupCars.doc.cars;
  ok(!dupCars.error && dc[0].id === 'c1' && dc[1].id !== 'c1' && dc[2].id === 'c2', '중복 차 id → 뒤의 차 재발급');
  ok(dc[1].modelName === 'B' && /^[A-Za-z0-9_.:-]+$/.test(dc[1].id), '재발급된 차 데이터 보존');
  ok(dupCars.doc.records.every(function (r) { return r.carId === 'c1'; }), '겹치던 id의 기록은 앞 차에 남음');
  // 차를 하나 지워도(app의 delete-car 필터) 다른 차는 남는다
  ok(dc.filter(function (c) { return c.id !== 'c1'; }).length === 2, '차 하나 삭제 → 나머지 두 대 유지');

  // ---------- 주유 단위 kg(수소) ----------
  var units = S.importJson(JSON.stringify({
    schemaVersion: 2, cars: [], records: [], expenses: [], settings: {},
    fuelLogs: [
      { id: 'h1', carId: 'c1', filledOn: '2026-09-01', amount: 5.2, unit: 'kg', totalKrw: 52000, isFullTank: true },
      { id: 'e1', carId: 'c1', filledOn: '2026-09-01', amount: 40, unit: 'kWh', totalKrw: 14000, isFullTank: true },
      { id: 'x1', carId: 'c1', filledOn: '2026-09-01', amount: 40, unit: 'KG', totalKrw: 60000, isFullTank: true }
    ]
  })).doc.fuelLogs;
  ok(units[0].unit === 'kg' && units[0].amount === 5.2, '수소 kg 단위 보존');
  ok(units[1].unit === 'kWh', '전기 kWh 단위 보존');
  ok(units[2].unit === 'L', '모르는 단위 → L');
  ok(S.UNITS.join(',') === 'L,kWh,kg', '허용 단위 목록');

  // ---------- 주행거리 관측 출처(by·prev) 정규화 ----------
  var odo = S.importJson(JSON.stringify({
    schemaVersion: 2, records: [], fuelLogs: [], expenses: [], settings: {},
    cars: [{ id: 'c1', modelName: 'A', odometerLog: [
      { date: '2026-09-01', km: 40000, by: 'manual' },
      { date: '2026-10-01', km: '45030', by: 'f-1', prev: [{ km: 45000, by: 'manual' }, { km: '44990' }, { km: 'x', by: 'r-1' }, null, { km: 44000, by: '<img>' }] },
      { date: '2026-10-02', km: 45100, by: '"><b>' }
    ] }]
  })).doc.cars[0].odometerLog;
  ok(odo[0].by === 'manual' && odo[0].prev === undefined, '직접 입력 출처 보존, 빈 prev는 생략');
  ok(odo[1].km === 45030 && odo[1].by === 'f-1', '출처 id 보존·km 숫자 강제');
  ok(JSON.stringify(odo[1].prev) === JSON.stringify([{ km: 45000, by: 'manual' }, { km: 44990 }, { km: 44000 }]),
    '이전 값: km 불량 항목 제거, 불량 출처는 비움 (' + JSON.stringify(odo[1].prev) + ')');
  ok(odo[2].by === undefined, '악성 출처 → 출처 없음(옛 관측 취급)');
  var longPrev = [];
  for (var pi = 0; pi < 25; pi++) longPrev.push({ km: 40000 + pi, by: 'f-' + pi });
  var capped = S.importJson(JSON.stringify({
    schemaVersion: 2, records: [], fuelLogs: [], expenses: [], settings: {},
    cars: [{ id: 'c1', modelName: 'A', odometerLog: [{ date: '2026-10-01', km: 50000, by: 'f-x', prev: longPrev }] }]
  })).doc.cars[0].odometerLog[0].prev;
  ok(capped.length === S.ODO_PREV_MAX && capped[capped.length - 1].km === 40024, '이전 값은 최근 ODO_PREV_MAX개만');
  // 'manual'은 출처 예약어 — 기록·차 id로 쓰이면 재발급 (그 기록을 지울 때 직접 입력 관측이 지워지지 않게)
  var reserved = S.importJson(JSON.stringify({
    schemaVersion: 2, cars: [{ id: 'manual', modelName: 'A' }], fuelLogs: [{ id: 'manual', carId: 'c1', filledOn: '2026-10-01' }],
    records: [{ id: 'manual', carId: 'c1', doneOn: '2026-10-01' }], expenses: [], settings: {}
  })).doc;
  ok(reserved.cars[0].id !== 'manual' && reserved.records[0].id !== 'manual' && reserved.fuelLogs[0].id !== 'manual', "id 'manual' 재발급");

  print(failures === 0 ? '통과: ' + total + '/' + total : '실패: ' + failures + '/' + total);
  if (failures > 0) throw new Error(failures + '개 실패');
})();
