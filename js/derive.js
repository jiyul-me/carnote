/* 차일지 — 파생 계산 (순수 함수만, DOM·localStorage 사용 금지)
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

  /* 이 차에 inspection.json의 검사 주기(비사업용 승용: 최초 4년, 이후 2년)를 적용해도 되는지.
   * vehicle = car.vehicleId로 찾은 vehicles.json 항목. 없으면(차종 미매칭) 지금까지처럼 승용으로 본다.
   * vehicleClass가 없거나 'passenger'면 승용. 화물('truck')·승합('van') 등은 검사 주기가 차종·용도마다 달라
   * 승용 규칙으로 날짜를 만들지 않는다(D-day·캘린더 일정 없음) — 화면은 등록증·검사 안내문을 확인하라고 안내한다 */
  function passengerInspectionApplies(vehicle) {
    if (!vehicle) return true;
    var cls = vehicle.vehicleClass;
    return cls == null || cls === 'passenger';
  }

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

  // ---------- 지출 (정비 비용 + 주유·충전 + 기타 지출) ----------
  // 월은 'YYYY-MM' 문자열 키. 날짜는 전부 로컬 날짜 문자열이라 시간대 변환이 끼지 않는다

  function monthKey(iso) { return iso ? iso.slice(0, 7) : null; }

  // 'YYYY-MM' ± n개월
  function addMonthKey(month, n) { return addMonths(month + '-01', n).slice(0, 7); }

  // 주유 1건의 금액: 총액 우선, 없으면 주유량 × 단가 (스키마: 둘 중 하나만 입력해도 됨). 둘 다 없으면 null
  function fuelLogCost(l) {
    if (l.totalKrw != null) return l.totalKrw;
    if (l.amount != null && l.unitPriceKrw != null) return Math.round(l.amount * l.unitPriceKrw);
    return null;
  }

  // 주유량: 입력값 우선, 없으면 총액 ÷ 단가 ('5만원어치'처럼 금액만 적은 주유도 실연비 구간에 합산되게)
  function fuelLogAmount(l) {
    if (l.amount != null) return l.amount;
    if (l.totalKrw != null && l.unitPriceKrw) return l.totalKrw / l.unitPriceKrw;
    return null;
  }

  function byDateDesc(a, b) {
    if (a.date !== b.date) return a.date < b.date ? 1 : -1;
    return a.createdAt < b.createdAt ? 1 : (a.createdAt > b.createdAt ? -1 : 0);
  }

  /* 차 한 대의 지출을 한 목록으로: 정비(비용 입력분만) + 주유·충전 + 기타 지출.
   * kind: 'maintenance' | 'fuel' | 'expense' (원본 배열 구분 — 삭제 경로가 다르다)
   * category: 정비='maintenance', 주유='fuel', 그 외는 Expense.category (data/expense-categories.json의 id)
   * amountKrw: 금액을 모르는 주유는 null (건수에는 들어가고 합계에서는 빠진다)
   * 최근순: 날짜 내림차순, 같은 날은 나중에 입력한 것 먼저 */
  function spendEntries(carId, records, fuelLogs, expenses) {
    var out = [];
    (records || []).forEach(function (r) {
      if (r.carId !== carId || !r.doneOn || r.costKrw == null) return;
      out.push({ kind: 'maintenance', category: 'maintenance', id: r.id, date: r.doneOn,
        amountKrw: r.costKrw, createdAt: r.createdAt || '', source: r });
    });
    (fuelLogs || []).forEach(function (l) {
      if (l.carId !== carId || !l.filledOn) return;
      out.push({ kind: 'fuel', category: 'fuel', id: l.id, date: l.filledOn,
        amountKrw: fuelLogCost(l), createdAt: l.createdAt || '', source: l });
    });
    (expenses || []).forEach(function (e) {
      if (e.carId !== carId || !e.spentOn) return;
      out.push({ kind: 'expense', category: e.category, id: e.id, date: e.spentOn,
        amountKrw: e.amountKrw, createdAt: e.createdAt || '', source: e });
    });
    return out.sort(byDateDesc);
  }

  // 한 달 합계: {totalKrw, count, byCategory: [{category, totalKrw, count}] — 금액 큰 순}
  function monthSpend(entries, month) {
    var total = 0;
    var count = 0;
    var cats = Object.create(null); // 분류 id가 '__proto__'여도 안전하게
    var order = [];
    (entries || []).forEach(function (e) {
      if (monthKey(e.date) !== month) return;
      count += 1;
      var k = e.category == null ? '' : String(e.category);
      if (!(k in cats)) {
        cats[k] = { category: e.category, totalKrw: 0, count: 0 };
        order.push(k);
      }
      cats[k].count += 1;
      if (e.amountKrw != null) {
        cats[k].totalKrw += e.amountKrw;
        total += e.amountKrw;
      }
    });
    var byCategory = order.map(function (k) { return cats[k]; });
    byCategory.sort(function (a, b) { return b.totalKrw - a.totalKrw; });
    return { totalKrw: total, count: count, byCategory: byCategory };
  }

  // 최근 n개월 시계열 (오래된 달 → endMonth 순): [{month, totalKrw, count}]
  function spendSeries(entries, endMonth, n) {
    var out = [];
    for (var k = n - 1; k >= 0; k--) {
      var m = addMonthKey(endMonth, -k);
      var s = monthSpend(entries, m);
      out.push({ month: m, totalKrw: s.totalKrw, count: s.count });
    }
    return out;
  }

  /* 월평균: endMonth(진행 중인 이번 달)는 빼고 직전 n개월의 완결된 달만 평균.
   * 기록을 시작하기 전 달(첫 기록 달 이전)은 0원으로 치지 않고 제외한다 — 막 시작한 사용자의 평균이 낮게 나오지 않게.
   * 첫 기록 달 이후 기록이 없는 달은 0원으로 포함. 완결된 달이 하나도 없으면 null */
  function monthlyAverageSpend(entries, endMonth, n) {
    var first = null;
    (entries || []).forEach(function (e) {
      var m = monthKey(e.date);
      if (m && (first == null || m < first)) first = m;
    });
    if (first == null) return null;
    var sum = 0;
    var months = 0;
    for (var k = 1; k <= n; k++) {
      var m = addMonthKey(endMonth, -k);
      if (m < first) break;
      sum += monthSpend(entries, m).totalKrw;
      months += 1;
    }
    return months ? Math.round(sum / months) : null;
  }

  // ---------- 에너지원 (주유·충전 단위) ----------
  // 과세 구분(fuelType)과 실제 넣는 에너지는 다를 수 있다 — 수소차(넥쏘)는 세법상 'ev'지만 수소를 kg 단위로 충전한다.
  // vehicles.json 항목의 energySource가 있으면 그것, 없으면 fuelType에서 유도
  var ENERGY_BY_FUEL = { gasoline: 'gasoline', diesel: 'diesel', lpg: 'lpg', hybrid: 'gasoline', ev: 'electricity' };
  var UNIT_BY_ENERGY = { electricity: 'kWh', hydrogen: 'kg' }; // 그 외(휘발유·경유·LPG)는 L

  function energySource(vehicle, fuelType) {
    if (vehicle && typeof vehicle.energySource === 'string' && vehicle.energySource) return vehicle.energySource;
    return ENERGY_BY_FUEL[fuelType] || 'gasoline';
  }

  function energyUnit(source) { return UNIT_BY_ENERGY[source] || 'L'; }

  // 같은 날짜는 입력 순서(createdAt)대로
  function sortedFuelLogs(fuelLogs, carId) {
    var logs = (fuelLogs || []).filter(function (l) { return l.carId === carId && l.filledOn; });
    logs.sort(function (a, b) {
      if (a.filledOn !== b.filledOn) return a.filledOn < b.filledOn ? -1 : 1;
      var ac = a.createdAt || '';
      var bc = b.createdAt || '';
      return ac < bc ? -1 : (ac > bc ? 1 : 0);
    });
    return logs;
  }

  // 구간 주유량 누적: 단위가 하나로 모이고 양을 다 알 때만 유효
  function newAcc() { return { amount: 0, ok: true, unit: null }; }
  function addToAcc(acc, l) {
    var a = fuelLogAmount(l);
    if (a == null) acc.ok = false;
    else acc.amount += a;
    if (acc.unit == null) acc.unit = l.unit;
    else if (acc.unit !== l.unit) acc.ok = false;
  }
  function joinAcc(a, b) {
    return {
      amount: a.amount + b.amount,
      ok: a.ok && b.ok && (a.unit == null || b.unit == null || a.unit === b.unit),
      unit: a.unit != null ? a.unit : b.unit
    };
  }

  /* 실연비 (가득 주유 full-to-full, docs/storage-schema.md 파생 규칙)
   * - 끝점: 주행거리가 있는 가득 주유. 연속한 두 끝점 사이 구간의 실연비 =
   *   (뒤 끝점 km − 앞 끝점 km) ÷ (앞 끝점 다음 주유부터 뒤 끝점까지 넣은 양의 합)
   * - 구간 안의 부분 주유·주행거리 없는 가득 주유는 끝점이 못 될 뿐 양은 합산된다
   * - 양을 알 수 없는 주유(주유량·단가 모두 없음)나 단위(L·kWh·kg)가 다른 주유가 낀 구간은 제외
   * - 주행거리가 기준점보다 줄어든 가득 주유(자릿수 오타 등)는 구간도 기준점도 되지 못한다. 양은 다음 구간에 합산.
   *   · 다음 끝점이 기준점보다 크면 그 줄어든 값은 오타 — 기준점에서 다음 끝점까지 한 구간으로 잰다
   *   · 다음 끝점도 기준점보다 작지만 줄어든 값보다는 크면 계기판 교체 등 새 출발 — 줄어든 값부터 잰다
   *   · 다음 끝점이 기준점보다 작아도 그 앞 기준점보다 크면 기준점 쪽이 튄 값(자릿수가 붙은 오타 등) —
   *     앞 기준점→기준점 구간을 버리고 앞 기준점부터 다음 끝점까지 한 구간으로 다시 잰다
   * - 같은 주행거리로 다시 기록한 가득 주유(중복 저장·추가 주유)는 구간 없이 기준점만 옮긴다
   * - 합산 실연비 = 유효 구간 거리 합 ÷ 양 합. 단위가 섞였으면 가장 최근 유효 구간의 단위로만 집계
   * 반환: null(유효 구간 없음) | {kmPerUnit, unit, distanceKm, amount, intervals, latestKmPerUnit} */
  function fuelEconomy(fuelLogs, carId) {
    var segs = [];        // 잰 구간 {dist, amount, unit} — null이면 양·단위 문제로 무효(자리만 차지)
    var anchor = null;    // 지금 기준 끝점
    var acc = null;       // anchor 다음 주유부터 지금까지의 양
    var back = null;      // anchor 직전 기준점과 그 구간 {anchor, acc, seg(segs 안의 위치)} — 튄 값 판정용
    var low = null;       // anchor보다 작은 끝점 {log, acc(그 다음부터의 양)} — 오타·계기판 교체 판정용

    function measure(from, to, a) {
      var dist = to.odometerKm - from.odometerKm;
      var ok = a.ok && a.amount > 0 && a.unit === from.unit && dist > 0;
      segs.push(ok ? { dist: dist, amount: a.amount, unit: a.unit } : null);
      return segs.length - 1;
    }
    function moveTo(l, prevAnchor, prevAcc, segIdx) {
      back = prevAnchor ? { anchor: prevAnchor, acc: prevAcc, seg: segIdx } : null;
      anchor = l;
      acc = newAcc();
      low = null;
    }

    sortedFuelLogs(fuelLogs, carId).forEach(function (l) {
      if (anchor) addToAcc(acc, l);
      if (low) addToAcc(low.acc, l);
      if (!l.isFullTank || l.odometerKm == null) return;
      if (!anchor) { moveTo(l, null); return; }
      var km = l.odometerKm;
      if (km > anchor.odometerKm) {
        moveTo(l, anchor, acc, measure(anchor, l, acc));
      } else if (km === anchor.odometerKm) {
        anchor = l; // 같은 주행거리 — 기준점만 옮긴다 (그 사이 양은 버림)
        acc = newAcc();
        low = null;
      } else if (back && km > back.anchor.odometerKm) {
        segs[back.seg] = null; // anchor가 튄 값 — 그 구간 무효, 앞 기준점부터 다시
        var merged = joinAcc(back.acc, acc);
        var from = back.anchor;
        moveTo(l, from, merged, measure(from, l, merged));
      } else if (low && km > low.log.odometerKm) {
        var lowLog = low.log;
        var lowAcc = low.acc;
        moveTo(l, lowLog, lowAcc, measure(lowLog, l, lowAcc)); // 줄어든 값이 이어짐 — 새 출발
      } else {
        low = { log: l, acc: newAcc() }; // 판정 보류 (양은 anchor 구간에 계속 합산)
      }
    });

    var per = {};
    var latest = null;
    segs.forEach(function (s) {
      if (!s) return;
      var u = per[s.unit] || (per[s.unit] = { distanceKm: 0, amount: 0, intervals: 0 });
      u.distanceKm += s.dist;
      u.amount += s.amount;
      u.intervals += 1;
      latest = { unit: s.unit, kmPerUnit: s.dist / s.amount };
    });
    if (!latest) return null;
    var t = per[latest.unit];
    return {
      kmPerUnit: t.distanceKm / t.amount,
      unit: latest.unit,
      distanceKm: t.distanceKm,
      amount: t.amount,
      intervals: t.intervals,
      latestKmPerUnit: latest.kmPerUnit
    };
  }

  /* 실연비가 없을 때(fuelEconomy가 null) 무엇이 모자란지 — 안내 문구를 실제 조건에 맞추기 위함
   *  'endpoints' 주행거리를 적은 가득 주유가 2번 미만
   *  'amount'    끝점은 2번 이상인데 그 사이 주유 중 양을 알 수 없는 것(금액만 적음)이 있음
   *  'other'     그 밖(단위가 섞임, 주행거리가 늘지 않음 등) */
  function fuelEconomyGap(fuelLogs, carId) {
    var logs = sortedFuelLogs(fuelLogs, carId);
    var first = -1;
    var last = -1;
    logs.forEach(function (l, i) {
      if (l.isFullTank && l.odometerKm != null) {
        if (first === -1) first = i;
        last = i;
      }
    });
    if (first === last) return 'endpoints'; // 끝점 0~1개
    // 첫 끝점 다음부터 마지막 끝점까지(구간에 들어가는 주유) 중 양을 모르는 것
    for (var i = first + 1; i <= last; i++) {
      if (fuelLogAmount(logs[i]) == null) return 'amount';
    }
    return 'other';
  }

  // ---------- 입력 정규화 ----------
  // 금액: '50,000' · '50000원' · '5만' · '5.5만' 허용. 'abc'·'1e3'·음수는 null (parseInt의 '1e3'→1 오파싱 방지)
  function parseKrwInput(v) {
    var s = String(v == null ? '' : v).replace(/[\s,]/g, '').replace(/원$/, '');
    var m = /^(\d+(?:\.\d+)?)(만)?$/.exec(s);
    if (!m) return null;
    return Math.round(Number(m[1]) * (m[2] ? 10000 : 1));
  }

  // 소수 허용 수치(주유량 L·kWh, 전기 단가 347.2원 등): 소수 둘째 자리까지. 쉼표는 천 단위 구분으로 보고 제거
  function parseDecimalInput(v) {
    var s = String(v == null ? '' : v).replace(/[\s,]/g, '');
    if (!/^\d+(\.\d+)?$/.test(s)) return null;
    return Math.round(Number(s) * 100) / 100;
  }

  // ---------- 포맷 ----------

  // 좁은 자리(막대 그래프 라벨)용 짧은 금액: 9,800 / 12.3만 / 123만 / 1.2억
  function formatKrwShort(n) {
    if (n == null) return '';
    if (n < 10000) return n.toLocaleString('ko-KR');
    var man = n / 10000;
    if (man < 100) return String(Math.round(man * 10) / 10) + '만';
    if (Math.round(man) < 10000) return Math.round(man).toLocaleString('ko-KR') + '만'; // 9,999.5만은 아래 억으로
    return String(Math.round(n / 10000000) / 10) + '억';
  }

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

  global.ChailjiDerive = {
    parseDate: parseDate, toISO: toISO,
    addDays: addDays, addMonths: addMonths, addYears: addYears,
    diffDays: diffDays, yearsBetween: yearsBetween,
    retentionAt: retentionAt, estimateValue: estimateValue,
    latestOdometer: latestOdometer, monthlyKmEstimate: monthlyKmEstimate,
    lastRecordFor: lastRecordFor, partStatus: partStatus,
    defaultEnabledPartIds: defaultEnabledPartIds, applicableParts: applicableParts,
    passengerInspectionApplies: passengerInspectionApplies,
    inspectionStatus: inspectionStatus, insuranceStatus: insuranceStatus,
    yearlySpend: yearlySpend,
    monthKey: monthKey, addMonthKey: addMonthKey,
    fuelLogCost: fuelLogCost, fuelLogAmount: fuelLogAmount,
    spendEntries: spendEntries, monthSpend: monthSpend, spendSeries: spendSeries,
    monthlyAverageSpend: monthlyAverageSpend, fuelEconomy: fuelEconomy, fuelEconomyGap: fuelEconomyGap,
    energySource: energySource, energyUnit: energyUnit,
    parseKrwInput: parseKrwInput, parseDecimalInput: parseDecimalInput,
    formatKrw: formatKrw, formatKrwShort: formatKrwShort, formatDday: formatDday
  };
})(typeof window !== 'undefined' ? window : globalThis);
