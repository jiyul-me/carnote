/* 카노트 — 파생 계산 (순수 함수만, DOM·localStorage 사용 금지)
 * docs/storage-schema.md의 "파생 데이터" 절 구현.
 * jsc로 단독 실행 가능해야 한다: tests/derive.test.js 참고 */
(function (global) {
  'use strict';

  var MS_PER_DAY = 24 * 60 * 60 * 1000;
  var DAYS_PER_MONTH = 30.44;

  // ---------- 날짜 ----------

  function parseDate(iso) {
    if (!iso) return null;
    var p = iso.split('-');
    return new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
  }

  function toISO(date) {
    var m = String(date.getMonth() + 1);
    var d = String(date.getDate());
    return date.getFullYear() + '-' + (m.length < 2 ? '0' + m : m) + '-' + (d.length < 2 ? '0' + d : d);
  }

  function addDays(iso, days) {
    var d = parseDate(iso);
    d.setDate(d.getDate() + days);
    return toISO(d);
  }

  // 말일 넘침 방지: 1/31 + 1개월 → 2/28
  function addMonths(iso, months) {
    var d = parseDate(iso);
    var day = d.getDate();
    d.setDate(1);
    d.setMonth(d.getMonth() + months);
    var lastDay = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
    d.setDate(Math.min(day, lastDay));
    return toISO(d);
  }

  function addYears(iso, years) {
    return addMonths(iso, years * 12);
  }

  // diffDays(a, b) = b − a (일)
  function diffDays(fromIso, toIso) {
    return Math.round((parseDate(toIso) - parseDate(fromIso)) / MS_PER_DAY);
  }

  function yearsBetween(fromIso, toIso) {
    return diffDays(fromIso, toIso) / 365.25;
  }

  // ---------- 감가 (data/depreciation.json) ----------

  function retentionAt(dep, ageYears) {
    var curve = dep.retentionByAge;
    var last = curve.length - 1;
    if (ageYears <= 0) return curve[0];
    if (ageYears >= last) {
      return Math.max(dep.minRetention, curve[last] - dep.afterCurveYearlyDrop * (ageYears - last));
    }
    var i = Math.floor(ageYears);
    return curve[i] + (curve[i + 1] - curve[i]) * (ageYears - i);
  }

  // 이중 감가 방지: 구입가 ÷ retention(구입 시점 차령)으로 신차가 기준 환원 후 현재 잔존율 적용
  function estimateValue(dep, car, todayIso) {
    if (!car.purchasePriceKrw || !car.firstRegisteredOn) return null;
    var nowAge = Math.max(0, yearsBetween(car.firstRegisteredOn, todayIso));
    var buyAge = car.purchasedOn ? Math.max(0, yearsBetween(car.firstRegisteredOn, car.purchasedOn)) : 0;
    var ratio = retentionAt(dep, nowAge) / retentionAt(dep, buyAge);
    return Math.round(car.purchasePriceKrw * Math.min(1, ratio));
  }

  // ---------- 주행거리 ----------

  function latestOdometer(car) {
    var log = car.odometerLog || [];
    return log.length ? log[log.length - 1] : null;
  }

  // (날짜, km) 관측점: odometerLog + km이 있는 정비·주유 기록. 최초·최신 두 점으로 월평균 추정
  function monthlyKmEstimate(car, records, fuelLogs) {
    var points = (car.odometerLog || []).map(function (e) { return { date: e.date, km: e.km }; });
    (records || []).forEach(function (r) {
      if (r.carId === car.id && r.odometerKm != null && r.doneOn) {
        points.push({ date: r.doneOn, km: r.odometerKm });
      }
    });
    (fuelLogs || []).forEach(function (l) {
      if (l.carId === car.id && l.odometerKm != null && l.filledOn) {
        points.push({ date: l.filledOn, km: l.odometerKm });
      }
    });
    if (points.length < 2) return null;
    points.sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; });
    var first = points[0];
    var last = points[points.length - 1];
    var days = diffDays(first.date, last.date);
    var km = last.km - first.km;
    if (days < 14 || km <= 0) return null; // 관측 구간이 짧으면 예측하지 않음
    return km / (days / DAYS_PER_MONTH);
  }

  // ---------- 소모품 상태 ----------

  function lastRecordFor(records, carId, partId) {
    var best = null;
    (records || []).forEach(function (r) {
      if (r.carId !== carId || r.partId !== partId) return;
      if (!best || r.doneOn > best.doneOn || (r.doneOn === best.doneOn && r.createdAt > best.createdAt)) {
        best = r;
      }
    });
    return best;
  }

  /* 반환 state:
   *  'manual'    주기 없는 항목(보충·고장 시) — D-day 없음, 기록만
   *  'no-record' 주기 항목인데 기록 없음 — 첫 기록 유도
   *  'overdue' | 'soon' | 'ok'
   * 부가: dueDate, dueKm, remainingDays, remainingKm, predictedDate(km 주기의 날짜 예측), lastRecord */
  function partStatus(part, car, records, settings, todayIso, monthlyKm) {
    var last = lastRecordFor(records, car.id, part.id);
    var hasInterval = part.intervalKm != null || part.intervalMonths != null;
    if (!hasInterval) return { state: 'manual', lastRecord: last };
    if (!last) return { state: 'no-record', lastRecord: null };

    var out = {
      lastRecord: last, dueDate: null, dueKm: null,
      remainingDays: null, remainingKm: null, predictedDate: null
    };

    if (part.intervalMonths != null) {
      out.dueDate = addMonths(last.doneOn, part.intervalMonths);
      out.remainingDays = diffDays(todayIso, out.dueDate);
    }
    if (part.intervalKm != null && last.odometerKm != null) {
      var current = latestOdometer(car);
      if (current) {
        out.dueKm = last.odometerKm + part.intervalKm;
        out.remainingKm = out.dueKm - current.km;
        if (monthlyKm && out.remainingKm > 0) {
          out.predictedDate = addDays(todayIso, Math.round(out.remainingKm / monthlyKm * DAYS_PER_MONTH));
        }
      }
    }

    if (out.remainingDays == null && out.remainingKm == null) {
      // 주기는 있는데 판단 근거가 전혀 없음(기록에 km 없음 등) — 'ok'로 안심시키면 안 된다
      out.state = 'no-data';
      return out;
    }

    var overdue = (out.remainingDays != null && out.remainingDays < 0) ||
                  (out.remainingKm != null && out.remainingKm < 0);
    var soon = (out.remainingDays != null && out.remainingDays <= settings.reminderLeadDays) ||
               (out.remainingKm != null && out.remainingKm <= settings.reminderLeadKm);
    out.state = overdue ? 'overdue' : (soon ? 'soon' : 'ok');
    return out;
  }

  // 이 차에서 기본으로 추적할 항목 (parts.json의 defaultEnabled + appliesTo)
  function defaultEnabledPartIds(parts, fuelType) {
    return parts.filter(function (p) {
      return p.defaultEnabled && p.appliesTo.indexOf(fuelType) !== -1;
    }).map(function (p) { return p.id; });
  }

  function applicableParts(parts, fuelType) {
    return parts.filter(function (p) { return p.appliesTo.indexOf(fuelType) !== -1; });
  }

  // ---------- 검사 D-day (data/inspection.json) ----------

  /* 만료일 추정: 최근 검사일이 있으면 +intervalYears, 없으면 최초등록일 +firstInspectionAfterYears.
   * 과거로 밀린 만료일은 intervalYears씩 굴려 현재에 가장 가까운 회차를 잡는다
   * (기록이 없어도 과거 검사는 받았다고 가정 — UI에 '최근 검사일을 입력하면 정확해져요' 안내).
   * 유예(만료 후 windowAfterDays 이내)는 굴리지 않고 '지남'으로 보여준다. */
  function inspectionStatus(car, rules, todayIso) {
    if (!car.firstRegisteredOn) return null;
    var estimated = !car.lastInspectionOn;
    var expiry = estimated
      ? addYears(car.firstRegisteredOn, rules.firstInspectionAfterYears)
      : addYears(car.lastInspectionOn, rules.intervalYears);
    if (estimated) {
      // 기록이 없을 때만 과거 회차를 굴린다. 실제 검사일이 입력돼 있으면
      // 연체(D+N)를 그대로 보여줘야 과태료 상태를 숨기지 않는다
      while (diffDays(expiry, todayIso) > rules.windowAfterDays) {
        expiry = addYears(expiry, rules.intervalYears);
      }
    }
    var dDay = diffDays(todayIso, expiry);
    var windowStart = addDays(expiry, -rules.windowBeforeDays);
    var windowEnd = addDays(expiry, rules.windowAfterDays);
    return {
      expiryOn: expiry,
      dDay: dDay,
      windowStart: windowStart,
      windowEnd: windowEnd,
      inWindow: diffDays(windowStart, todayIso) >= 0 && diffDays(todayIso, windowEnd) >= 0,
      estimated: estimated
    };
  }

  // ---------- 보험 만기 ----------

  function insuranceStatus(car, todayIso) {
    if (!car.insuranceExpiresOn) return null;
    return { expiresOn: car.insuranceExpiresOn, dDay: diffDays(todayIso, car.insuranceExpiresOn) };
  }

  // ---------- 연간 정비 요약 ----------

  // 해당 연도의 정비 건수·비용 합계 (costKrw 없는 기록은 건수만)
  function yearlySpend(records, carId, year) {
    var count = 0;
    var cost = 0;
    (records || []).forEach(function (r) {
      if (r.carId === carId && r.doneOn && r.doneOn.slice(0, 4) === String(year)) {
        count += 1;
        if (r.costKrw != null) cost += r.costKrw;
      }
    });
    return { count: count, costKrw: cost };
  }

  // ---------- 포맷 ----------

  function formatKrw(n) {
    if (n == null) return '';
    if (n >= 10000000) {
      var eok = Math.floor(n / 100000000);
      var man = Math.round((n % 100000000) / 10000);
      if (man === 10000) { eok += 1; man = 0; } // 반올림 자리올림 (9,999.5만 → 1억)
      if (eok > 0) return man > 0 ? eok + '억 ' + man.toLocaleString('ko-KR') + '만원' : eok + '억원';
      return man.toLocaleString('ko-KR') + '만원';
    }
    return n.toLocaleString('ko-KR') + '원';
  }

  function formatDday(d) {
    if (d === 0) return 'D-day';
    return d > 0 ? 'D-' + d : 'D+' + (-d);
  }

  global.CarnoteDerive = {
    parseDate: parseDate, toISO: toISO,
    addDays: addDays, addMonths: addMonths, addYears: addYears,
    diffDays: diffDays, yearsBetween: yearsBetween,
    retentionAt: retentionAt, estimateValue: estimateValue,
    latestOdometer: latestOdometer, monthlyKmEstimate: monthlyKmEstimate,
    lastRecordFor: lastRecordFor, partStatus: partStatus,
    defaultEnabledPartIds: defaultEnabledPartIds, applicableParts: applicableParts,
    inspectionStatus: inspectionStatus, insuranceStatus: insuranceStatus,
    yearlySpend: yearlySpend,
    formatKrw: formatKrw, formatDday: formatDday
  };
})(typeof window !== 'undefined' ? window : globalThis);
