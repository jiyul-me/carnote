/* jsc 실행: jsc js/ics.js tests/ics.test.js */
(function () {
  'use strict';
  var I = globalThis.CarnoteIcs;
  var failures = 0, total = 0;
  function ok(cond, label) {
    total++;
    if (!cond) { failures++; print('FAIL ' + label); }
  }
  function eq(a, b, label) { ok(a === b, label + (a === b ? '' : '\n  기대: ' + JSON.stringify(b) + '\n  실제: ' + JSON.stringify(a))); }

  // 이스케이프
  eq(I.icsEscape('a;b,c\nd\\e'), 'a\\;b\\,c\\nd\\\\e', 'TEXT 이스케이프');

  // 옥텟 길이 (한글 3바이트)
  eq(I.byteLen('abc'), 3, 'ASCII 옥텟');
  eq(I.byteLen('가'), 3, '한글 1자 = 3옥텟');

  // 폴딩: 접힌 각 물리 줄이 75옥텟 이하, 펼치면 원문 복원
  var long = 'SUMMARY:카노트 — 엔진오일·오일필터 교체 시기 알림입니다 아주 길게 만든 제목으로 폴딩을 검증합니다';
  var folded = I.fold(long);
  var physical = folded.split('\r\n');
  ok(physical.length > 1, '장문 폴딩 발생');
  ok(physical.every(function (l) { return I.byteLen(l) <= 75; }), '모든 물리 줄 75옥텟 이하');
  eq(physical[0].charAt(0) === ' ', false, '첫 줄은 공백 없음');
  ok(physical.slice(1).every(function (l) { return l.charAt(0) === ' '; }), '연속 줄은 공백 선행');
  eq(folded.replace(/\r\n /g, ''), long, '펼치면 원문 복원');

  // 날짜
  eq(I.nextDayISO('2026-12-31'), '2027-01-01', '연말 다음날');
  eq(I.nextDayISO('2026-02-28'), '2026-03-01', '평년 2월');

  // 캘린더 구조
  var ics = I.buildCalendar([
    { uid: 'a@carnote', date: '2026-09-01', summary: '카노트 — 엔진오일 교체 시기', description: '카노트에서 확인: https://example.test', url: 'https://example.test' },
    { uid: 'b@carnote', date: '2027-01-16', summary: '자동차세 연납 신청 시작', yearlyRepeat: true }
  ], { stamp: '20260807T000000Z', calName: '카노트' });

  ok(ics.indexOf('BEGIN:VCALENDAR') === 0, 'VCALENDAR 시작');
  ok(/\r\nEND:VCALENDAR\r\n$/.test(ics), 'CRLF + VCALENDAR 종료');
  eq((ics.match(/BEGIN:VEVENT/g) || []).length, 2, 'VEVENT 2개');
  eq((ics.match(/BEGIN:VALARM/g) || []).length, 4, '이벤트당 VALARM 2개');
  ok(ics.indexOf('DTSTART;VALUE=DATE:20260901') !== -1, '종일 DTSTART');
  ok(ics.indexOf('DTEND;VALUE=DATE:20260902') !== -1, 'DTEND 다음날');
  ok(ics.indexOf('RRULE:FREQ=YEARLY') !== -1, '연납 매년 반복');
  ok(ics.indexOf('TRIGGER:-P7D') !== -1, '7일 전 알림');
  ok(ics.indexOf('TRIGGER;RELATED=START:PT9H') !== -1, '당일 9시 알림');
  ok(ics.split('\r\n').every(function (l) { return I.byteLen(l) <= 75; }), '전체 출력 75옥텟 준수');

  print(failures === 0 ? '통과: ' + total + '/' + total : '실패: ' + failures + '/' + total);
  if (failures > 0) throw new Error(failures + '개 실패');
})();
