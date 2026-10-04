/* jsc 실행: jsc js/derive.js tests/derive.test.js
 * (DOM 없음 — derive.js는 globalThis.ChailjiDerive로 노출됨) */
(function () {
  'use strict';
  var D = globalThis.ChailjiDerive;
  var failures = 0, total = 0;

  function eq(actual, expected, label) {
    total++;
    var ok = JSON.stringify(actual) === JSON.stringify(expected);
    if (!ok) {
      failures++;
      print('FAIL ' + label + '\n  기대: ' + JSON.stringify(expected) + '\n  실제: ' + JSON.stringify(actual));
    }
  }
  function approx(actual, expected, tol, label) {
    total++;
    if (actual == null || Math.abs(actual - expected) > tol) {
      failures++;
      print('FAIL ' + label + '\n  기대: ~' + expected + '\n  실제: ' + actual);
    }
  }

  var DEP = {
    retentionByAge: [1.0, 0.8, 0.72, 0.65, 0.58, 0.52, 0.47, 0.43, 0.39, 0.35, 0.32, 0.29, 0.27, 0.25, 0.23, 0.21],
    minRetention: 0.1,
    afterCurveYearlyDrop: 0.01
  };
  var INSPECTION = { firstInspectionAfterYears: 4, intervalYears: 2, windowBeforeDays: 90, windowAfterDays: 31 };
  var SETTINGS = { reminderLeadDays: 30, reminderLeadKm: 1000 };

  // ---------- 날짜 ----------
  eq(D.addMonths('2026-01-31', 1), '2026-02-28', 'addMonths 말일 넘침');
  eq(D.addMonths('2024-01-31', 1), '2024-02-29', 'addMonths 윤년');
  eq(D.addMonths('2026-03-15', 12), '2027-03-15', 'addMonths 12개월');
  eq(D.addYears('2022-08-04', 4), '2026-08-04', 'addYears');
  eq(D.addDays('2026-08-04', -90), '2026-05-06', 'addDays 음수');
  eq(D.diffDays('2026-08-01', '2026-08-04'), 3, 'diffDays 부호(미래=양수)');
  eq(D.diffDays('2026-08-04', '2026-08-01'), -3, 'diffDays 과거=음수');

  // ---------- 감가 ----------
  eq(D.retentionAt(DEP, 0), 1.0, 'retention 0년');
  eq(D.retentionAt(DEP, 1), 0.8, 'retention 1년');
  approx(D.retentionAt(DEP, 0.5), 0.9, 1e-9, 'retention 보간');
  eq(D.retentionAt(DEP, 15), 0.21, 'retention 곡선 끝');
  approx(D.retentionAt(DEP, 16), 0.2, 1e-9, 'retention 곡선 이후 점감');
  eq(D.retentionAt(DEP, 30), 0.1, 'retention 하한');

  // 신차 5년: 2,300만 × 0.52
  var newCar = { purchasePriceKrw: 23000000, firstRegisteredOn: '2021-08-04', purchasedOn: null };
  approx(D.estimateValue(DEP, newCar, '2026-08-04'), 23000000 * 0.52, 23000000 * 0.002, '감가 신차');
  // 중고: 3년차에 2,000만 → 5년차 = 2,000만 × 0.52/0.65 (이중 감가 방지)
  var usedCar = { purchasePriceKrw: 20000000, firstRegisteredOn: '2021-08-04', purchasedOn: '2024-08-04' };
  approx(D.estimateValue(DEP, usedCar, '2026-08-04'), 20000000 * 0.52 / 0.65, 20000000 * 0.002, '감가 중고(이중 감가 방지)');
  eq(D.estimateValue(DEP, { purchasePriceKrw: null, firstRegisteredOn: '2020-01-01' }, '2026-08-04'), null, '감가 구매가 없음');

  // ---------- 주행거리 ----------
  var car = {
    id: 'c1',
    firstRegisteredOn: '2022-08-04',
    lastInspectionOn: null,
    odometerLog: [{ date: '2026-06-05', km: 40000 }, { date: '2026-08-04', km: 44000 }]
  };
  eq(D.latestOdometer(car).km, 44000, 'latestOdometer');
  // 60일에 4,000km → 월 약 2,029km
  approx(D.monthlyKmEstimate(car, []), 4000 / (60 / 30.44), 1, '월평균 주행거리');
  eq(D.monthlyKmEstimate({ id: 'c2', odometerLog: [{ date: '2026-08-04', km: 100 }] }, []), null, '관측 1개 → null');
  eq(D.monthlyKmEstimate({ id: 'c3', odometerLog: [{ date: '2026-08-01', km: 100 }, { date: '2026-08-04', km: 200 }] }, []), null, '기간 14일 미만 → null');
  // 정비 기록의 km도 관측점으로 쓰인다
  var carNoLog = { id: 'c4', odometerLog: [{ date: '2026-05-04', km: 30000 }] };
  var recs = [{ carId: 'c4', partId: 'engine-oil', doneOn: '2026-08-04', odometerKm: 33000, createdAt: '2026-08-04T00:00:00Z' }];
  approx(D.monthlyKmEstimate(carNoLog, recs), 3000 / (92 / 30.44), 5, '기록 km 관측점 포함');

  // ---------- 소모품 상태 ----------
  function rec(partId, doneOn, km) {
    return { id: 'r-' + partId, carId: 'c1', partId: partId, doneOn: doneOn, odometerKm: km, createdAt: doneOn + 'T00:00:00Z' };
  }
  var TODAY = '2026-08-04';
  var pKm = { id: 'atf', intervalKm: 80000, intervalMonths: null };
  var pBoth = { id: 'engine-oil', intervalKm: 10000, intervalMonths: 12 };
  var pManual = { id: 'washer-fluid', intervalKm: null, intervalMonths: null };

  eq(D.partStatus(pManual, car, [], SETTINGS, TODAY, null).state, 'manual', '주기 없음 → manual');
  eq(D.partStatus(pBoth, car, [], SETTINGS, TODAY, null).state, 'no-record', '기록 없음');

  // km 초과: 33,000에서 교체, 주기 10,000, 현재 44,000 → -1,000km
  var stOver = D.partStatus(pBoth, car, [rec('engine-oil', '2026-02-01', 33000)], SETTINGS, TODAY, null);
  eq(stOver.state, 'overdue', 'km 초과 → overdue');
  eq(stOver.remainingKm, -1000, 'remainingKm 계산');
  eq(stOver.dueDate, '2027-02-01', 'dueDate 계산');

  // 임박: 43,500에서 교체 후 현재 44,000, 주기 10,000 → 남은 9,500 > 리드 1,000 → 날짜만 임박이 아니면 ok
  var stOk = D.partStatus(pBoth, car, [rec('engine-oil', '2026-07-01', 43500)], SETTINGS, TODAY, null);
  eq(stOk.state, 'ok', '여유 → ok');

  // 날짜 임박: 11.5개월 전 교체(12개월 주기) → 남은 ~15일 ≤ 30일
  var stSoon = D.partStatus(pBoth, car, [rec('engine-oil', '2025-08-19', 43900)], SETTINGS, TODAY, null);
  eq(stSoon.state, 'soon', '날짜 임박 → soon');

  // km 전용 + 월평균 있으면 날짜 예측
  var stPred = D.partStatus(pKm, car, [rec('atf', '2024-01-10', 10000)], SETTINGS, TODAY, 2000);
  eq(stPred.dueKm, 90000, 'dueKm');
  eq(stPred.state, 'ok', 'km 전용 여유');
  eq(stPred.predictedDate == null, false, 'predictedDate 존재');

  // 기록에 km이 없으면 km 기준은 건너뛰고 날짜 기준만
  var stNoKm = D.partStatus(pBoth, car, [rec('engine-oil', '2026-05-01', null)], SETTINGS, TODAY, null);
  eq(stNoKm.remainingKm, null, '기록 km 없음 → km 기준 없음');
  eq(stNoKm.state, 'ok', '날짜 기준만으로 ok');

  // km 전용 주기 + 판단 근거 전무 → 'ok'로 안심시키지 않고 no-data
  var stNoData1 = D.partStatus(pKm, car, [rec('atf', '2023-01-01', null)], SETTINGS, TODAY, null);
  eq(stNoData1.state, 'no-data', 'km 전용 + 기록 km 없음 → no-data');
  var emptyLogCar = { id: 'c1', odometerLog: [] };
  var stNoData2 = D.partStatus(pKm, emptyLogCar, [rec('atf', '2023-01-01', 10000)], SETTINGS, TODAY, null);
  eq(stNoData2.state, 'no-data', 'km 전용 + odometerLog 비어 있음 → no-data');

  // ---------- 검사 ----------
  // 2022-08-04 등록, 오늘 2026-08-04 → 첫 검사 만료일 당일
  var insp1 = D.inspectionStatus(car, INSPECTION, TODAY);
  eq(insp1.expiryOn, '2026-08-04', '첫 검사 만료일');
  eq(insp1.dDay, 0, '검사 D-day 0');
  eq(insp1.inWindow, true, '수검 기간 내');
  eq(insp1.estimated, true, '추정 표시');

  // 10년 된 차, 검사 기록 없음 → 과거 만료일을 2년씩 굴려 현재 회차로
  var oldCar = { id: 'c9', firstRegisteredOn: '2016-08-04', lastInspectionOn: null, odometerLog: [] };
  var insp2 = D.inspectionStatus(oldCar, INSPECTION, TODAY);
  eq(insp2.expiryOn, '2026-08-04', '과거 만료일 굴리기');

  // 최근 검사일 있으면 +2년
  var insp3 = D.inspectionStatus({ id: 'c10', firstRegisteredOn: '2016-08-04', lastInspectionOn: '2025-06-01', odometerLog: [] }, INSPECTION, TODAY);
  eq(insp3.expiryOn, '2027-06-01', '최근 검사일 기준');
  eq(insp3.estimated, false, '실측 표시');
  eq(insp3.inWindow, false, '기간 밖');

  // 유예 기간(만료 후 31일 이내)은 굴리지 않고 D+ 표시
  var insp4 = D.inspectionStatus({ id: 'c11', firstRegisteredOn: '2022-07-14', lastInspectionOn: null, odometerLog: [] }, INSPECTION, TODAY);
  eq(insp4.expiryOn, '2026-07-14', '유예 중 만료일 유지');
  eq(insp4.dDay, -21, '유예 중 D+21');
  eq(insp4.inWindow, true, '유예도 수검 기간');

  // 검사일이 '기록돼' 있으면 연체가 아무리 길어도 굴리지 않는다 (과태료 상태 은폐 방지)
  var insp5 = D.inspectionStatus({ id: 'c12', firstRegisteredOn: '2018-01-10', lastInspectionOn: '2024-01-10', odometerLog: [] }, INSPECTION, TODAY);
  eq(insp5.expiryOn, '2026-01-10', '기록 있음 → 만료일 굴리지 않음');
  eq(insp5.dDay, -206, '기록 있음 → D+206 그대로');
  eq(insp5.estimated, false, '기록 있음 → 추정 아님');

  // 주유 기록의 (날짜, km)도 관측점 (스키마 파생 규칙)
  var fuelCar = { id: 'c20', odometerLog: [{ date: '2026-05-04', km: 30000 }] };
  var logs = [{ carId: 'c20', filledOn: '2026-08-04', odometerKm: 33000 }];
  approx(D.monthlyKmEstimate(fuelCar, [], logs), 3000 / (92 / 30.44), 5, '주유 기록 관측점 포함');

  // ---------- 연간 정비 요약 ----------
  var spendRecs = [
    { carId: 'c1', doneOn: '2026-02-01', costKrw: 85000 },
    { carId: 'c1', doneOn: '2026-07-15', costKrw: null },
    { carId: 'c1', doneOn: '2025-12-31', costKrw: 999999 },
    { carId: 'c2', doneOn: '2026-03-01', costKrw: 50000 }
  ];
  eq(D.yearlySpend(spendRecs, 'c1', 2026), { count: 2, costKrw: 85000 }, 'yearlySpend 연도·차 필터, cost null 허용');
  eq(D.yearlySpend(spendRecs, 'c1', 2024), { count: 0, costKrw: 0 }, 'yearlySpend 기록 없는 해');

  // ---------- 지출 ----------
  eq(D.monthKey('2026-10-04'), '2026-10', 'monthKey');
  eq(D.addMonthKey('2026-01', -1), '2025-12', 'addMonthKey 연도 넘김');
  eq(D.addMonthKey('2026-03', -1), '2026-02', 'addMonthKey 말일 무관(1일 기준)');

  // 주유 금액: 총액 우선 → 없으면 양 × 단가 → 둘 다 없으면 null
  eq(D.fuelLogCost({ totalKrw: 50000, amount: 30, unitPriceKrw: 1650 }), 50000, 'fuelLogCost 총액 우선');
  eq(D.fuelLogCost({ totalKrw: null, amount: 40.5, unitPriceKrw: 1650 }), 66825, 'fuelLogCost 양×단가');
  eq(D.fuelLogCost({ totalKrw: null, amount: 30.33, unitPriceKrw: 347.2 }), 10531, 'fuelLogCost 소수 단가 반올림');
  eq(D.fuelLogCost({ totalKrw: null, amount: 40, unitPriceKrw: null }), null, 'fuelLogCost 단가 없음 → null');
  eq(D.fuelLogAmount({ amount: 40, totalKrw: 1, unitPriceKrw: 1 }), 40, 'fuelLogAmount 입력값 우선');
  approx(D.fuelLogAmount({ amount: null, totalKrw: 50000, unitPriceKrw: 1650 }), 30.303, 0.001, 'fuelLogAmount 총액÷단가');
  eq(D.fuelLogAmount({ amount: null, totalKrw: 50000, unitPriceKrw: null }), null, 'fuelLogAmount 알 수 없음');

  var SP_RECS = [
    { id: 'm1', carId: 'c1', partId: 'engine-oil', doneOn: '2026-10-02', costKrw: 85000, createdAt: '2026-10-02T01:00:00Z' },
    { id: 'm2', carId: 'c1', partId: 'wiper', doneOn: '2026-10-03', costKrw: null, createdAt: '2026-10-03T01:00:00Z' }, // 비용 없음 → 지출 아님
    { id: 'm3', carId: 'c2', partId: 'wiper', doneOn: '2026-10-03', costKrw: 30000, createdAt: '2026-10-03T01:00:00Z' }   // 다른 차
  ];
  var SP_FUEL = [
    { id: 'f1', carId: 'c1', filledOn: '2026-10-01', amount: 40, unit: 'L', unitPriceKrw: 1650, totalKrw: null, createdAt: '2026-10-01T01:00:00Z' },
    { id: 'f2', carId: 'c1', filledOn: '2026-09-15', amount: null, unit: 'L', unitPriceKrw: null, totalKrw: 50000, createdAt: '2026-09-15T01:00:00Z' },
    { id: 'f3', carId: 'c1', filledOn: '2026-09-20', amount: 10, unit: 'L', unitPriceKrw: null, totalKrw: null, createdAt: '2026-09-20T01:00:00Z' } // 금액 모름
  ];
  var SP_EXP = [
    { id: 'e1', carId: 'c1', spentOn: '2026-10-03', category: 'wash', amountKrw: 15000, createdAt: '2026-10-03T09:00:00Z' },
    { id: 'e2', carId: 'c1', spentOn: '2026-10-03', category: 'parking', amountKrw: 3000, createdAt: '2026-10-03T08:00:00Z' },
    { id: 'e3', carId: 'c1', spentOn: '2026-07-10', category: 'tax', amountKrw: 140000, createdAt: '2026-07-10T08:00:00Z' },
    { id: 'e4', carId: 'c2', spentOn: '2026-10-03', category: 'wash', amountKrw: 99999, createdAt: '2026-10-03T08:00:00Z' }
  ];
  var entries = D.spendEntries('c1', SP_RECS, SP_FUEL, SP_EXP);
  eq(entries.map(function (e) { return e.id; }), ['e1', 'e2', 'm1', 'f1', 'f3', 'f2', 'e3'],
    'spendEntries 차 필터·비용 없는 정비 제외·최근순(같은 날은 나중 입력 먼저)');
  eq(entries.map(function (e) { return e.kind + ':' + e.category; }).slice(0, 4),
    ['expense:wash', 'expense:parking', 'maintenance:maintenance', 'fuel:fuel'], 'spendEntries kind·category');
  eq(entries[3].amountKrw, 66000, 'spendEntries 주유 금액 파생');
  eq(entries[4].amountKrw, null, 'spendEntries 금액 모르는 주유는 null');

  var oct = D.monthSpend(entries, '2026-10');
  eq(oct.totalKrw, 85000 + 66000 + 15000 + 3000, '월 합계 = 정비 + 주유 + 지출');
  eq(oct.count, 4, '월 건수');
  eq(oct.byCategory, [
    { category: 'maintenance', totalKrw: 85000, count: 1 },
    { category: 'fuel', totalKrw: 66000, count: 1 },
    { category: 'wash', totalKrw: 15000, count: 1 },
    { category: 'parking', totalKrw: 3000, count: 1 }
  ], '카테고리별 합계 (금액 큰 순)');
  var sep = D.monthSpend(entries, '2026-09');
  eq([sep.totalKrw, sep.count], [50000, 2], '금액 모르는 주유: 건수엔 포함, 합계엔 제외');
  eq(D.monthSpend(entries, '2026-08'), { totalKrw: 0, count: 0, byCategory: [] }, '기록 없는 달');
  eq(D.monthSpend([{ date: '2026-10-01', category: '__proto__', amountKrw: 10 }], '2026-10').byCategory,
    [{ category: '__proto__', totalKrw: 10, count: 1 }], '분류 id __proto__도 안전');

  eq(D.spendSeries(entries, '2026-10', 6).map(function (m) { return m.month + '=' + m.totalKrw; }),
    ['2026-05=0', '2026-06=0', '2026-07=140000', '2026-08=0', '2026-09=50000', '2026-10=169000'], '최근 6개월 시계열(오래된 달 → 이번 달)');
  eq(D.spendSeries(entries, '2026-01', 2).map(function (m) { return m.month; }), ['2025-12', '2026-01'], '시계열 연도 넘김');

  // 월평균: 이번 달(10월) 제외, 첫 기록 달(7월) 이전 제외, 사이 빈 달(8월)은 0원으로 포함 → (140000+0+50000)/3
  eq(D.monthlyAverageSpend(entries, '2026-10', 6), Math.round(190000 / 3), '월평균 (완결된 달·기록 시작 이후)');
  eq(D.monthlyAverageSpend(entries, '2026-10', 1), 50000, '월평균 n=1 → 지난달');
  eq(D.monthlyAverageSpend(D.spendEntries('c1', [], [], [SP_EXP[0]]), '2026-10', 6), null, '이번 달 기록뿐 → 월평균 없음');
  eq(D.monthlyAverageSpend([], '2026-10', 6), null, '기록 없음 → 월평균 없음');

  // ---------- 실연비 (full-to-full) ----------
  function fl(id, date, odo, amount, full, extra) {
    var l = { id: id, carId: 'c1', filledOn: date, odometerKm: odo, amount: amount, unit: 'L',
      unitPriceKrw: null, totalKrw: null, isFullTank: full, createdAt: date + 'T00:00:00Z' };
    for (var k in (extra || {})) l[k] = extra[k];
    return l;
  }
  eq(D.fuelEconomy([], 'c1'), null, '실연비 기록 없음');
  eq(D.fuelEconomy([fl('a', '2026-09-01', 40000, 40, true)], 'c1'), null, '가득 주유 1번 → 구간 없음');
  // 가득 → 가득: 600km ÷ 40L = 15
  var ec1 = D.fuelEconomy([fl('a', '2026-09-01', 40000, 45, true), fl('b', '2026-09-20', 40600, 40, true)], 'c1');
  eq([ec1.kmPerUnit, ec1.unit, ec1.distanceKm, ec1.amount, ec1.intervals], [15, 'L', 600, 40, 1], '실연비 기본 구간');
  // 사이의 부분 주유(주행거리 없음)는 양만 합산: 600 ÷ (10 + 30) = 15, 첫 가득 주유 양은 제외
  var ec2 = D.fuelEconomy([
    fl('a', '2026-09-01', 40000, 45, true),
    fl('b', '2026-09-10', null, 10, false),
    fl('c', '2026-09-20', 40600, 30, true)
  ], 'c1');
  eq([ec2.kmPerUnit, ec2.amount], [15, 40], '부분 주유 합산');
  // 금액만 적은 부분 주유는 총액÷단가로 양 추정
  var ec3 = D.fuelEconomy([
    fl('a', '2026-09-01', 40000, 45, true),
    fl('b', '2026-09-10', null, null, false, { totalKrw: 16500, unitPriceKrw: 1650 }),
    fl('c', '2026-09-20', 40600, 30, true)
  ], 'c1');
  eq(ec3.kmPerUnit, 15, '금액만 적은 주유도 양 추정해 합산');
  // 양을 알 수 없는 주유가 끼면 그 구간은 제외, 다음 구간은 정상 계산
  var ec4 = D.fuelEconomy([
    fl('a', '2026-08-01', 39000, 45, true),
    fl('b', '2026-08-10', null, null, false, { totalKrw: 20000 }),
    fl('c', '2026-08-20', 39500, 30, true),
    fl('d', '2026-09-01', 40100, 40, true)
  ], 'c1');
  eq([ec4.intervals, ec4.kmPerUnit], [1, 15], '양 모르는 주유가 낀 구간 제외');
  // 주행거리 없는 가득 주유는 끝점이 아니라 양만 합산: (40600−40000) ÷ (20 + 20)
  var ec5 = D.fuelEconomy([
    fl('a', '2026-09-01', 40000, 45, true),
    fl('b', '2026-09-10', null, 20, true),
    fl('c', '2026-09-20', 40600, 20, true)
  ], 'c1');
  eq([ec5.intervals, ec5.kmPerUnit], [1, 15], '주행거리 없는 가득 주유는 끝점 아님');
  // 여러 구간: 거리 합 ÷ 양 합, 최근 구간 값 별도. 입력 순서와 무관(날짜 정렬)
  var ec6 = D.fuelEconomy([
    fl('c', '2026-10-01', 41000, 25, true),
    fl('a', '2026-09-01', 40000, 45, true),
    fl('b', '2026-09-20', 40600, 40, true),
    fl('x', '2026-10-01', 41000, 99, true, { carId: 'c2' })
  ], 'c1');
  eq([ec6.intervals, ec6.distanceKm, ec6.amount], [2, 1000, 65], '여러 구간 합산·차 필터');
  approx(ec6.kmPerUnit, 1000 / 65, 1e-9, '합산 실연비');
  eq(ec6.latestKmPerUnit, 16, '최근 구간 실연비');
  // 주행거리가 줄어든 구간(오타)·단위가 섞인 구간은 제외
  eq(D.fuelEconomy([fl('a', '2026-09-01', 40000, 45, true), fl('b', '2026-09-20', 39000, 40, true)], 'c1'), null, '거리 0 이하 구간 제외');
  var ec7 = D.fuelEconomy([
    fl('a', '2026-09-01', 40000, 45, true),
    fl('b', '2026-09-10', null, 10, false, { unit: 'kWh' }),
    fl('c', '2026-09-20', 40600, 30, true)
  ], 'c1');
  eq(ec7, null, '단위 섞인 구간 제외');
  // 전기차: kWh 단위 그대로
  var ec8 = D.fuelEconomy([
    fl('a', '2026-09-01', 10000, 60, true, { unit: 'kWh' }),
    fl('b', '2026-09-10', 10500, 100, true, { unit: 'kWh' })
  ], 'c1');
  eq([ec8.unit, ec8.kmPerUnit], ['kWh', 5], '전기차 km/kWh');
  // 수소차: kg 단위 그대로 (넥쏘 약 100km/kg)
  var ecH = D.fuelEconomy([
    fl('a', '2026-09-01', 30000, 5, true, { unit: 'kg' }),
    fl('b', '2026-09-20', 30500, 5, true, { unit: 'kg' })
  ], 'c1');
  eq([ecH.unit, ecH.kmPerUnit], ['kg', 100], '수소차 km/kg');

  // 주행거리가 줄어든 가득 주유(자릿수 누락 46200 → 4620)는 구간·기준점이 되지 못한다.
  // 다음 정상 기록까지 한 구간으로: (46800 − 45600) ÷ (40 + 40) = 15 (예전엔 기준점이 되어 534.75 · 최근 1054.5)
  var ecDrop = D.fuelEconomy([
    fl('a', '2026-09-01', 45000, 40, true),
    fl('b', '2026-09-15', 45600, 40, true),
    fl('c', '2026-09-29', 4620, 40, true),
    fl('d', '2026-10-13', 46800, 40, true)
  ], 'c1');
  eq([ecDrop.kmPerUnit, ecDrop.intervals, ecDrop.latestKmPerUnit, ecDrop.distanceKm], [15, 2, 15, 1800], '줄어든 주행거리(오타)는 기준점 아님');
  // 마지막 기록이 줄어든 값이면 판정 보류 — 앞 구간만
  var ecDropLast = D.fuelEconomy([
    fl('a', '2026-09-01', 45000, 40, true),
    fl('b', '2026-09-15', 45600, 40, true),
    fl('c', '2026-09-29', 4620, 40, true)
  ], 'c1');
  eq([ecDropLast.kmPerUnit, ecDropLast.intervals], [15, 1], '마지막이 줄어든 값 → 앞 구간만');
  // 자릿수가 붙은 오타(46200 → 462000): 다음 기록이 그보다 작고 앞 기준점보다 크면 튄 값 — 그 구간을 버리고 다시 잰다
  var ecJump = D.fuelEconomy([
    fl('a', '2026-09-01', 45000, 40, true),
    fl('b', '2026-09-15', 45600, 40, true),
    fl('c', '2026-09-29', 462000, 40, true),
    fl('d', '2026-10-13', 46800, 40, true)
  ], 'c1');
  eq([ecJump.kmPerUnit, ecJump.intervals, ecJump.latestKmPerUnit], [15, 2, 15], '튄 주행거리(오타) 구간 제외');
  // 계기판 교체 등으로 줄어든 값이 이어지면 새 기준 — 이후 구간은 정상 계산
  var ecReset = D.fuelEconomy([
    fl('a', '2026-08-01', 45000, 40, true),
    fl('b', '2026-08-15', 45600, 40, true),
    fl('c', '2026-09-01', 100, 40, true),
    fl('d', '2026-09-15', 700, 40, true),
    fl('e', '2026-09-29', 1300, 40, true)
  ], 'c1');
  eq([ecReset.kmPerUnit, ecReset.intervals, ecReset.distanceKm], [15, 3, 1800], '계기판 교체 후 새 기준');
  // 같은 주행거리로 두 번 저장(중복)한 가득 주유: 구간 없이 기준점만 옮겨 양이 이중으로 잡히지 않는다
  var ecDup = D.fuelEconomy([
    fl('a', '2026-09-01', 45000, 40, true),
    fl('b', '2026-09-15', 45600, 40, true),
    fl('b2', '2026-09-15', 45600, 40, true),
    fl('c', '2026-09-29', 46200, 40, true)
  ], 'c1');
  eq([ecDup.kmPerUnit, ecDup.intervals], [15, 2], '중복 저장한 가득 주유');

  // 실연비가 없을 때 이유 — 안내 문구가 실제 계산 조건과 맞게
  eq(D.fuelEconomyGap([fl('a', '2026-09-01', 45000, 40, true)], 'c1'), 'endpoints', '끝점 1개 → endpoints');
  eq(D.fuelEconomyGap([fl('a', '2026-09-01', null, 40, true), fl('b', '2026-09-10', null, 40, true)], 'c1'), 'endpoints', '주행거리 없는 가득 주유뿐 → endpoints');
  // 금액·주행거리·가득만 적은 주유 3건 (리뷰 재현): 양을 몰라 계산 불가 → 'amount'
  var amtOnly = [
    fl('a', '2026-09-10', 45000, null, true, { totalKrw: 60000 }),
    fl('b', '2026-09-25', 45600, null, true, { totalKrw: 55000 }),
    fl('c', '2026-10-03', 46200, null, true, { totalKrw: 58000 })
  ];
  eq(D.fuelEconomy(amtOnly, 'c1'), null, '금액만 적은 가득 주유 → 실연비 없음');
  eq(D.fuelEconomyGap(amtOnly, 'c1'), 'amount', '금액만 적은 주유 → amount');
  // 첫 끝점(기준점)의 양은 구간에 안 들어가므로 따지지 않는다
  eq(D.fuelEconomyGap([
    fl('a', '2026-09-01', 45000, null, true, { totalKrw: 60000 }),
    fl('b', '2026-09-15', 45600, 40, true, { unit: 'kWh' })
  ], 'c1'), 'other', '단위 섞임 → other');

  // ---------- 에너지원 (주유·충전 단위) ----------
  eq(D.energySource({ fuelType: 'ev', energySource: 'hydrogen' }, 'ev'), 'hydrogen', '넥쏘: 과세는 ev, 에너지원은 수소');
  eq(D.energyUnit(D.energySource({ fuelType: 'ev', energySource: 'hydrogen' }, 'ev')), 'kg', '수소 → kg');
  eq(D.energySource({ fuelType: 'ev' }, 'ev'), 'electricity', 'energySource 없으면 fuelType에서 유도(ev → 전기)');
  eq(D.energySource(null, 'ev'), 'electricity', '차종 미매칭 전기차');
  eq(D.energyUnit(D.energySource(null, 'ev')), 'kWh', '전기 → kWh');
  eq(D.energyUnit(D.energySource(null, 'hybrid')), 'L', '하이브리드 → L');
  eq(D.energyUnit(D.energySource(null, 'diesel')), 'L', '디젤 → L');
  eq(D.energyUnit(D.energySource(null, '모르는값')), 'L', '알 수 없는 연료 → L');

  // ---------- 입력 정규화 ----------
  eq(D.parseKrwInput('50,000'), 50000, 'parseKrwInput 쉼표');
  eq(D.parseKrwInput(' 50000원 '), 50000, 'parseKrwInput 원·공백');
  eq(D.parseKrwInput('5만'), 50000, 'parseKrwInput 만');
  eq(D.parseKrwInput('5.5만원'), 55000, 'parseKrwInput 소수 만');
  eq(D.parseKrwInput('1e3'), null, 'parseKrwInput 지수 표기 거부');
  eq(D.parseKrwInput('-500'), null, 'parseKrwInput 음수 거부');
  eq(D.parseKrwInput('abc'), null, 'parseKrwInput 문자 거부');
  eq(D.parseKrwInput(''), null, 'parseKrwInput 빈 값');
  eq(D.parseDecimalInput('40.567'), 40.57, 'parseDecimalInput 둘째 자리 반올림');
  eq(D.parseDecimalInput('1,650'), 1650, 'parseDecimalInput 쉼표');
  eq(D.parseDecimalInput('4O'), null, 'parseDecimalInput 오타 거부');

  // ---------- 포맷 ----------
  eq(D.formatKrwShort(9800), '9,800', 'formatKrwShort 만 미만');
  eq(D.formatKrwShort(123000), '12.3만', 'formatKrwShort 소수 만');
  eq(D.formatKrwShort(500000), '50만', 'formatKrwShort 정수 만');
  eq(D.formatKrwShort(1234567), '123만', 'formatKrwShort 100만 이상');
  eq(D.formatKrwShort(99996000), '1억', 'formatKrwShort 억 자리올림');
  eq(D.formatKrwShort(0), '0', 'formatKrwShort 0');
  eq(D.formatKrw(23000000), '2,300만원', 'formatKrw 만원');
  eq(D.formatKrw(130000), '130,000원', 'formatKrw 원');
  eq(D.formatKrw(250000000), '2억 5,000만원', 'formatKrw 억');
  eq(D.formatKrw(99995000), '1억원', 'formatKrw 자리올림 (9,999.5만 → 1억)');
  eq(D.formatKrw(199995000), '2억원', 'formatKrw 자리올림 (1억 9,999.5만 → 2억)');
  eq(D.formatDday(0), 'D-day', 'D-day 0');
  eq(D.formatDday(5), 'D-5', 'D-미래');
  eq(D.formatDday(-3), 'D+3', 'D+과거');

  print(failures === 0 ? '통과: ' + total + '/' + total : '실패: ' + failures + '/' + total);
  if (failures > 0) throw new Error(failures + '개 테스트 실패');
})();
