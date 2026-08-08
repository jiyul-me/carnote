/* 차일지 — TCO(총소유비용) 비교기.
 * 세율·차종·감가는 전부 data/*.json에서 읽는다 (하드코딩 금지).
 * 차값은 사용자 입력(제조사 견적기 금액), 보험료도 사용자 입력 — 산출하지 않는다(규제 영역). */
(function () {
  'use strict';

  var FUEL_LABELS = { gasoline: '가솔린', diesel: '디젤', lpg: 'LPG', hybrid: '하이브리드', ev: '전기' };
  var FUEL_UNIT = { gasoline: 'L', diesel: 'L', lpg: 'L', hybrid: 'L', ev: 'kWh' };

  // 기본 연료 단가는 data/site.json(fuelPrices)이 단일 출처 — 사용자가 화면에서 수정 가능
  var data = { vehicles: null, rates: null, dep: null, site: null };
  function sitePrices() { return (data.site && data.site.fuelPrices) || {}; }

  function $(id) { return document.getElementById(id); }
  function num(v) {
    var n = Number(v);
    return v !== '' && v != null && isFinite(n) && n >= 0 ? n : null;
  }
  function won(n) { return Math.round(n).toLocaleString('ko-KR') + '원'; }

  // 자동차세 (비영업용 승용, 신차 첫해 기준) — js/tax-calc.js 공용 모듈 사용
  function annualTax(fuelType, cc) {
    if (fuelType === 'ev') return window.ChailjiTax.evTax(data.rates);
    if (cc == null) return null;
    return window.ChailjiTax.taxFor(data.rates, cc, 1).annual;
  }

  function retentionAt(ageYears) {
    var dep = data.dep;
    var curve = dep.retentionByAge;
    var last = curve.length - 1;
    if (ageYears <= 0) return curve[0];
    if (ageYears >= last) return Math.max(dep.minRetention, curve[last] - dep.afterCurveYearlyDrop * (ageYears - last));
    var i = Math.floor(ageYears);
    return curve[i] + (curve[i + 1] - curve[i]) * (ageYears - i);
  }

  // ---------- 차 패널 ----------

  function carPanel(side) {
    var options = '<option value="">차종 선택</option><option value="custom">직접 입력</option>';
    var byBrand = {};
    data.vehicles.forEach(function (v) {
      (byBrand[v.brand] = byBrand[v.brand] || []).push(v);
    });
    Object.keys(byBrand).forEach(function (brand) {
      options += '<optgroup label="' + brand + '">' + byBrand[brand].map(function (v) {
        return '<option value="' + v.id + '">' + v.name + '</option>';
      }).join('') + '</optgroup>';
    });

    return '<div class="card" data-side="' + side + '">' +
      '<h2>' + (side === 'a' ? '차 A' : '차 B') + '</h2>' +
      '<div class="field"><label for="model-' + side + '">차종</label>' +
        '<select id="model-' + side + '" data-role="model">' + options + '</select></div>' +
      '<div class="field-row" data-role="custom-fields" style="display:none;">' +
        '<div class="field"><label for="fuel-' + side + '">연료</label><select id="fuel-' + side + '" data-role="fuel">' +
          Object.keys(FUEL_LABELS).map(function (k) { return '<option value="' + k + '">' + FUEL_LABELS[k] + '</option>'; }).join('') +
        '</select></div>' +
        '<div class="field"><label for="cc-' + side + '">배기량(cc)</label>' +
          '<input id="cc-' + side + '" data-role="cc" type="number" min="0" inputmode="numeric" placeholder="예: 1598"></div>' +
      '</div>' +
      '<div class="field"><label for="price-' + side + '">차값(만원) — 제조사 견적기 금액</label>' +
        '<input id="price-' + side + '" data-role="price" type="number" min="0" inputmode="numeric" placeholder="예: 3200"></div>' +
      '<div class="field-row">' +
        '<div class="field"><label for="eff-' + side + '">공인연비(km/<span data-role="unit">L</span>)</label>' +
          '<input id="eff-' + side + '" data-role="eff" type="number" min="0" step="0.1" inputmode="decimal" placeholder="예: 14.5"></div>' +
        '<div class="field"><label for="ins-' + side + '">연 보험료(만원)</label>' +
          '<input id="ins-' + side + '" data-role="ins" type="number" min="0" inputmode="numeric" placeholder="견적 금액"></div>' +
      '</div></div>';
  }

  function readCar(side) {
    var panel = document.querySelector('[data-side="' + side + '"]');
    var modelSel = panel.querySelector('[data-role="model"]');
    var fuelType = null, cc = null, name = null;
    if (modelSel.value === 'custom') {
      fuelType = panel.querySelector('[data-role="fuel"]').value;
      cc = num(panel.querySelector('[data-role="cc"]').value);
      name = '직접 입력';
    } else if (modelSel.value) {
      var v = data.vehicles.filter(function (x) { return x.id === modelSel.value; })[0];
      if (v) { fuelType = v.fuelType; cc = v.displacementCc; name = v.name; }
    }
    if (!fuelType) return null;
    if (fuelType !== 'ev' && cc == null) return null;
    return {
      name: name,
      fuelType: fuelType,
      cc: cc,
      priceKrw: (num(panel.querySelector('[data-role="price"]').value) || 0) * 10000,
      eff: num(panel.querySelector('[data-role="eff"]').value),
      insuranceKrw: (num(panel.querySelector('[data-role="ins"]').value) || 0) * 10000
    };
  }

  // ---------- 계산 ----------

  function monthly(car, kmPerYear, holdYears, fuelPrices) {
    var tax = annualTax(car.fuelType, car.cc);
    var fuelKey = car.fuelType === 'hybrid' ? 'gasoline' : car.fuelType;
    var fuel = null;
    if (car.eff && car.eff > 0) {
      fuel = kmPerYear / car.eff * fuelPrices[fuelKey] / 12;
    }
    var depMonthly = null;
    if (car.priceKrw > 0) {
      depMonthly = car.priceKrw * (1 - retentionAt(holdYears)) / (holdYears * 12);
    }
    return {
      tax: tax != null ? tax / 12 : null,
      fuel: fuel,
      insurance: car.insuranceKrw > 0 ? car.insuranceKrw / 12 : null,
      dep: depMonthly
    };
  }

  function render() {
    var a = readCar('a');
    var b = readCar('b');
    var table = $('tco-result');
    var note = $('tco-note');
    var headline = $('tco-headline');
    var barsEl = $('tco-bars');
    if (!a || !b) {
      table.innerHTML = '';
      barsEl.innerHTML = '';
      headline.style.display = 'none';
      note.style.display = '';
      return;
    }
    note.style.display = 'none';

    var kmPerYear = num($('common-km').value) || 12000;
    var holdYears = Math.min(15, Math.max(1, num($('common-years').value) || 5));
    var fuelPrices = {};
    Object.keys(sitePrices()).forEach(function (k) {
      var el = $('fp-' + k);
      fuelPrices[k] = (el && num(el.value)) || sitePrices()[k];
    });

    var ma = monthly(a, kmPerYear, holdYears, fuelPrices);
    var mb = monthly(b, kmPerYear, holdYears, fuelPrices);

    function cell(v, other) {
      if (v == null) return '<td style="color:var(--ink-muted);">입력 필요</td>';
      var win = other != null && v < other;
      return '<td' + (win ? ' class="win"' : '') + '>' + won(v) + '</td>';
    }
    function row(label, va, vb, noteTxt) {
      return '<tr><td>' + label + (noteTxt ? '<div style="font-size:11.5px;color:var(--ink-muted);">' + noteTxt + '</div>' : '') + '</td>' +
        cell(va, vb) + cell(vb, va) + '</tr>';
    }
    var totalA = (ma.tax || 0) + (ma.fuel || 0) + (ma.insurance || 0) + (ma.dep || 0);
    var totalB = (mb.tax || 0) + (mb.fuel || 0) + (mb.insurance || 0) + (mb.dep || 0);

    // 결론부터 — 월 유지비 숫자를 히어로 크기로 (DESIGN.md)
    if (totalA > 0 && totalB > 0 && Math.round(totalA) !== Math.round(totalB)) {
      var cheaper = totalA < totalB ? a : b;
      var diff = Math.abs(totalA - totalB);
      headline.innerHTML = '<div class="tax-hero">월 ' + won(Math.min(totalA, totalB)) + '</div>' +
        '<div class="sub"><strong>' + cheaper.name + '</strong> 기준 — 상대보다 월 ' + won(diff) +
        ' 저렴해요 (' + holdYears + '년 보유 시 약 ' + won(diff * 12 * holdYears) + ' 차이)</div>';
      headline.style.display = '';
    } else {
      headline.style.display = 'none';
    }

    // 항목별 가로 막대 (두 차 최대값 기준 비율)
    var cats = [
      { label: '자동차세', a: ma.tax, b: mb.tax },
      { label: '연료비', a: ma.fuel, b: mb.fuel },
      { label: '보험료', a: ma.insurance, b: mb.insurance },
      { label: '감가', a: ma.dep, b: mb.dep },
      { label: '합계', a: totalA, b: totalB }
    ];
    var maxV = 0;
    cats.forEach(function (c) { maxV = Math.max(maxV, c.a || 0, c.b || 0); });
    if (maxV > 0) {
      barsEl.innerHTML = '<div class="tco-bars">' + cats.map(function (c) {
        function bar(cls, v) {
          var w = v ? Math.max(2, v / maxV * 100) : 0;
          return '<div class="tco-bar ' + cls + '" style="width:' + w.toFixed(1) + '%;"></div>';
        }
        return '<div class="tco-bar-row"><div class="tco-bar-label">' + c.label + '</div>' +
          '<div class="tco-bar-track">' + bar('a', c.a) + bar('b', c.b) + '</div></div>';
      }).join('') +
      '<div class="tco-legend"><span class="dot a"></span>' + a.name +
      ' <span class="dot b"></span>' + b.name + '</div></div>';
    } else {
      barsEl.innerHTML = '';
    }

    table.innerHTML = '<thead><tr><th>월 기준</th><th>' + a.name + '</th><th>' + b.name + '</th></tr></thead><tbody>' +
      row('자동차세', ma.tax, mb.tax, '신차 첫해 기준 — 3년차부터 매년 줄어요') +
      row('연료비', ma.fuel, mb.fuel, '연 ' + kmPerYear.toLocaleString('ko-KR') + 'km ÷ 공인연비 × 단가') +
      row('보험료', ma.insurance, mb.insurance, '입력한 견적 금액') +
      row('감가', ma.dep, mb.dep, holdYears + '년 보유 가정, 자체 추정 곡선') +
      row('<strong>합계</strong>', totalA, totalB, null) +
      '</tbody>';
  }

  // ---------- 초기화 ----------

  function init() {
    Promise.all(['data/vehicles.json', 'data/tax-rates.json', 'data/depreciation.json', 'data/site.json'].map(function (u) {
      return fetch(u).then(function (r) {
        if (!r.ok) throw new Error(u + ' 로드 실패');
        return r.json();
      });
    })).then(function (res) {
      // 배기량 미확정 스켈레톤 제외 (전기차는 정액이라 포함)
      data.vehicles = res[0].vehicles.filter(function (v) {
        return v.status === 'active' && (v.fuelType === 'ev' || v.displacementCc != null);
      });
      data.rates = res[1];
      data.dep = res[2];
      data.site = res[3];

      $('tco-cars').innerHTML = carPanel('a') + carPanel('b');
      $('fuel-prices').innerHTML = Object.keys(sitePrices()).map(function (k) {
        var unit = k === 'ev' ? 'kWh' : 'L';
        return '<div class="field"><label for="fp-' + k + '">' + FUEL_LABELS[k] + '(원/' + unit + ')</label>' +
          '<input id="fp-' + k + '" type="number" min="0" inputmode="numeric" value="' + sitePrices()[k] + '"></div>';
      }).join('');

      // 차종 페이지에서 온 프리필 (?car=slug) — 수첩 프리필과 같은 패턴
      var carSlug = new URLSearchParams(location.search).get('car');
      if (carSlug) {
        var pv = data.vehicles.filter(function (v) { return v.slug === carSlug; })[0];
        if (pv) {
          var selA = $('model-a');
          selA.value = pv.id;
          var opt = selA.querySelector('option[value="' + pv.id + '"]');
          if (opt) opt.setAttribute('selected', '');
          var panelA = selA.closest('[data-side]');
          panelA.querySelector('[data-role="unit"]').textContent = FUEL_UNIT[pv.fuelType];
          render();
        }
        try { history.replaceState(null, '', location.pathname); } catch (e) { /* 무시 */ }
      }

      document.addEventListener('input', render);
      document.addEventListener('change', function (e) {
        // 차종 선택 변경: 직접 입력 필드 표시 + 연비 단위(L/kWh) 갱신
        var panel = e.target.closest('[data-side]');
        if (panel && e.target.getAttribute('data-role') === 'model') {
          panel.querySelector('[data-role="custom-fields"]').style.display =
            e.target.value === 'custom' ? '' : 'none';
        }
        if (panel) {
          var side = panel.getAttribute('data-side');
          var car = readCar(side);
          panel.querySelector('[data-role="unit"]').textContent = car ? FUEL_UNIT[car.fuelType] : 'L';
        }
        render();
      });
    }).catch(function (err) {
      $('tco-note').textContent = '데이터를 불러오지 못했어요: ' + err.message;
    });
  }

  init();
})();
