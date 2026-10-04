/* 차일지 — 자동차세 계산 (비영업용 승용). 순수 함수, DOM 비의존 — jsc 테스트 가능.
 * scripts/build.py의 tax_for/prepay와 동일 규칙이어야 한다 (절사 포함).
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

  // 1월 연납 공제. year = 기준 연도(계산기는 브라우저의 올해). 반환 year = 실제로 쓴 공제율의 연도(문자열)
  function prepay(rates, annual, year) {
    var r = rateFor(rates, year);
    var pr = rates.prepayDiscount.januaryProration;
    var discount = floor10(annual * pr.coveredMonths / pr.totalMonths * r.rate);
    return { year: r.year, rate: r.rate, fallback: r.fallback, discount: discount, pay: annual - discount };
  }

  global.ChailjiTax = { floor10: floor10, taxFor: taxFor, evTax: evTax, rateFor: rateFor, prepay: prepay };
})(typeof window !== 'undefined' ? window : globalThis);
