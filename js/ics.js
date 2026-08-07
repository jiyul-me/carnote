/* 차일지 — .ics(iCalendar) 생성. 순수 함수만, DOM 비의존 — jsc로 테스트 가능.
 * RFC 5545 준수 포인트: CRLF 줄바꿈, 75옥텟 라인 폴딩, 텍스트 이스케이프, 종일 일정(VALUE=DATE). */
(function (global) {
  'use strict';

  // RFC 5545 3.3.11 TEXT 이스케이프
  function icsEscape(s) {
    return String(s == null ? '' : s)
      .replace(/\\/g, '\\\\')
      .replace(/;/g, '\\;')
      .replace(/,/g, '\\,')
      .replace(/\r?\n/g, '\\n');
  }

  // UTF-8 옥텟 길이 (한글 3바이트 — 폴딩은 문자가 아니라 옥텟 기준)
  function byteLen(s) {
    return encodeURIComponent(s).replace(/%[0-9A-Fa-f]{2}/g, '_').length;
  }

  // 75옥텟 초과 라인을 접는다. 연속 줄은 공백 1칸으로 시작(그 공백도 1옥텟)
  function fold(line) {
    if (byteLen(line) <= 74) return line;
    var parts = [];
    var cur = '';
    for (var i = 0; i < line.length; i++) {
      var limit = parts.length ? 73 : 74;
      if (byteLen(cur + line[i]) > limit) {
        parts.push(cur);
        cur = line[i];
      } else {
        cur += line[i];
      }
    }
    if (cur) parts.push(cur);
    return parts.join('\r\n ');
  }

  function dateBasic(iso) { return iso.replace(/-/g, ''); } // YYYY-MM-DD → YYYYMMDD

  function nextDayISO(iso) {
    var p = iso.split('-');
    var d = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]) + 1);
    var m = String(d.getMonth() + 1);
    var day = String(d.getDate());
    return d.getFullYear() + '-' + (m.length < 2 ? '0' + m : m) + '-' + (day.length < 2 ? '0' + day : day);
  }

  /* event: { uid, date: 'YYYY-MM-DD'(종일), summary, description?, url?, yearlyRepeat? } */
  function veventLines(ev, stamp) {
    var lines = [
      'BEGIN:VEVENT',
      'UID:' + ev.uid,
      'DTSTAMP:' + stamp,
      'DTSTART;VALUE=DATE:' + dateBasic(ev.date),
      'DTEND;VALUE=DATE:' + dateBasic(nextDayISO(ev.date)),
      'SUMMARY:' + icsEscape(ev.summary)
    ];
    if (ev.description) lines.push('DESCRIPTION:' + icsEscape(ev.description));
    if (ev.url) lines.push('URL:' + ev.url);
    if (ev.yearlyRepeat) lines.push('RRULE:FREQ=YEARLY');
    // 알림 2개: 7일 전 자정, 당일 오전 9시(종일 시작 + 9시간)
    lines.push(
      'BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:' + icsEscape(ev.summary), 'TRIGGER:-P7D', 'END:VALARM',
      'BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:' + icsEscape(ev.summary), 'TRIGGER;RELATED=START:PT9H', 'END:VALARM'
    );
    lines.push('END:VEVENT');
    return lines;
  }

  /* events 배열 → .ics 문자열. opts: { stamp: 'YYYYMMDDTHHMMSSZ'(필수 — 호출자가 현재 시각), calName } */
  function buildCalendar(events, opts) {
    var stamp = opts.stamp;
    var lines = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//chailji//ics//KO',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
      'X-WR-CALNAME:' + icsEscape(opts.calName || '차일지')
    ];
    events.forEach(function (ev) {
      lines = lines.concat(veventLines(ev, stamp));
    });
    lines.push('END:VCALENDAR');
    return lines.map(fold).join('\r\n') + '\r\n';
  }

  global.ChailjiIcs = {
    icsEscape: icsEscape,
    byteLen: byteLen,
    fold: fold,
    nextDayISO: nextDayISO,
    buildCalendar: buildCalendar
  };
})(typeof window !== 'undefined' ? window : globalThis);
