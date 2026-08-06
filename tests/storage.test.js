/* jsc 실행: jsc js/storage.js tests/storage.test.js (localStorage 없음 → 인메모리 폴백) */
(function () {
  'use strict';
  var S = globalThis.CarnoteStorage;
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

  print(failures === 0 ? '통과: ' + total + '/' + total : '실패: ' + failures + '/' + total);
  if (failures > 0) throw new Error(failures + '개 실패');
})();
