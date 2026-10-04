/* 차일지 — 자동차세 계산 (비영업용 승용). 순수 함수, DOM 비의존 — jsc 테스트 가능.
 * scripts/build.py의 tax_for/prepay와 동일 규칙이어야 한다 (절사·계산 순서 포함 — scripts/check_tax_parity.py가 대조).
 * 세율은 호출자가 data/tax-rates.json을 읽어 넘긴다 — 여기 하드코딩 금지. */
(function (global) {
  'use strict';

  function floor10(x) { return Math.floor(x / 10) * 10; } // 10원 미만 절사

  // age = 차령 (1 = 신차 첫해)
  function taxFor(rates, cc, age) {
    var d = rates.displacement;
    var perCc = null;
    for (var i = 0; i < d.brackets.length; i++) {
      var b = d.brackets[i];
      if (b.maxCc == null || cc <= b.maxCc) { perCc = b.wonPerCc; break; }
    }
    var aging = d.agingDiscount;
    var discountRate = 0;
    if (age >= aging.startCarAge) {
      discountRate = Math.min(aging.maxRate, (age - aging.startCarAge + 1) * aging.ratePerYear);
    }
    var base = floor10(cc * perCc * (1 - discountRate));
    var edu = floor10(base * d.educationTaxRate);
    return { perCc: perCc, discountRate: discountRate, base: base, edu: edu, annual: base + edu };
  }

  function evTax(rates) { return rates.displacement.ev.annualTotalKrw; }

  // 연납 공제율 선택 — tax-rates.json fallbackRule (build.py prepay_rate와 같은 규칙):
  // year 키가 있으면 그 해 공제율, 없으면 가장 최근 연도의 공제율 + fallback=true ('YYYY년 기준' 표기 강제).
  // year를 생략하면 가장 최근 연도 (폴백 아님 — 기존 호출 호환)
  function rateFor(rates, year) {
    var byYear = rates.prepayDiscount.rateByYear;
    if (year != null && byYear[String(year)] != null) {
      return { year: String(year), rate: byYear[String(year)], fallback: false };
    }
    var years = Object.keys(byYear).sort();
    var latest = years[years.length - 1];
    return { year: latest, rate: byYear[latest], fallback: year != null };
  }

  // 달력 날짜 → 일 번호 (UTC 기준이라 서머타임·시각과 무관하게 날짜 차이만 센다)
  function dayNum(y, m, d) { return Math.round(Date.UTC(y, m - 1, d) / 86400000); }

  // 1월 연납 공제 일수 — 지방세법 제128조 제3항 계산식의 '납부기한 다음 날부터 12월 31일까지 일수 ÷ 365(윤년 366)'.
  // 납부기한 = applicationWindows에서 month가 januaryProration.windowMonth인 기간의 endDay (build.py prepay_days와 같은 규칙)
  // 반환: {days, yearDays} — 평년 334/365, 윤년 335/366
  function prorationDays(rates, year) {
    var p = rates.prepayDiscount;
    var ws = p.applicationWindows || [];
    var w = null;
    for (var i = 0; i < ws.length; i++) {
      if (ws[i].month === p.januaryProration.windowMonth) { w = ws[i]; break; }
    }
    if (!w) throw new Error('tax-rates.json: januaryProration.windowMonth에 해당하는 applicationWindows 기간이 없어요');
    var y = Number(year);
    return { days: dayNum(y, 12, 31) - dayNum(y, w.month, w.endDay), yearDays: dayNum(y + 1, 1, 1) - dayNum(y, 1, 1) };
  }

  // 1월 연납 공제 (일할). year = 기준 연도(계산기는 브라우저의 올해) — 공제율과 일수 모두 이 해 기준.
  // 생략하면 가장 최근 공제율 연도. 반환 year = 실제로 쓴 공제율의 연도(문자열, 폴백이면 최근 연도)
  // 연세액은 지방교육세 포함 총액 그대로 곱한다 (서울시 공식 예시와 원 단위 일치 — tests/tax-calc.test.js)
  function prepay(rates, annual, year) {
    var r = rateFor(rates, year);
    var pd = prorationDays(rates, year != null ? year : r.year);
    var discount = floor10(annual * pd.days / pd.yearDays * r.rate);
    return { year: r.year, rate: r.rate, fallback: r.fallback, days: pd.days, yearDays: pd.yearDays,
      discount: discount, pay: annual - discount };
  }

  global.ChailjiTax = { floor10: floor10, taxFor: taxFor, evTax: evTax, rateFor: rateFor,
    prorationDays: prorationDays, prepay: prepay };
})(typeof window !== 'undefined' ? window : globalThis);
