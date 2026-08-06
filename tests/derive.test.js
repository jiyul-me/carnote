/* jsc 실행: jsc js/derive.js tests/derive.test.js
 * (DOM 없음 — derive.js는 globalThis.CarnoteDerive로 노출됨) */
(function () {
  'use strict';
  var D = globalThis.CarnoteDerive;
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

  // ---------- 포맷 ----------
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
