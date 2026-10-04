/* 차일지 — TCO(총소유비용) 비교기.
 * 세율·차종·감가는 전부 data/*.json에서 읽는다 (하드코딩 금지).
 * 차값은 사용자 입력(제조사 견적기 금액), 보험료도 사용자 입력 — 산출하지 않는다(규제 영역). */
(function () {
  'use strict';

  // '직접 입력' 연료 선택지. 값은 과세 구분(fuelType)이고, 수소전기차만 과세는 ev 정액·에너지는 수소다
  var FUEL_LABELS = { gasoline: '가솔린', diesel: '디젤', lpg: 'LPG', hybrid: '하이브리드', ev: '전기', hydrogen: '수소전기' };

  // 과세 구분(fuelType)과 실제로 넣는 에너지는 다를 수 있다 — 수소전기차(넥쏘)는 세법상 ev 정액이지만 수소를 kg 단위로 넣는다.
  // vehicles.json energySource가 있으면 그것, 없으면 fuelType에서 유도 (js/derive.js·scripts/build.py와 같은 규칙)
  var ENERGY_BY_FUEL = { gasoline: 'gasoline', diesel: 'diesel', lpg: 'lpg', hybrid: 'gasoline', ev: 'electricity' };
  var ENERGY_UNIT = { electricity: 'kWh', hydrogen: 'kg' }; // 그 외(휘발유·경유·LPG)는 L
  var PRICE_KEY = { electricity: 'ev' }; // site.json fuelPrices 키 — 그 외는 에너지 이름 그대로
  // 단가 입력칸 라벨 (site.json fuelPrices 키 기준)
  var PRICE_FIELDS = {
    gasoline: { label: '가솔린', unit: 'L' }, diesel: { label: '디젤', unit: 'L' }, lpg: { label: 'LPG', unit: 'L' },
    ev: { label: '전기', unit: 'kWh' }, hydrogen: { label: '수소', unit: 'kg' }
  };
  // 공인연비 입력 예시 — 단위마다 자릿수가 달라 L 예시(14.5)를 그대로 쓰면 오해를 부른다
  var EFF_PLACEHOLDER = { L: '예: 14.5', kWh: '예: 5.2', kg: '예: 95.0' };

  function unitOf(energy) { return ENERGY_UNIT[energy] || 'L'; }
  function priceKeyOf(energy) { return PRICE_KEY[energy] || energy; }

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
          '<input id="eff-' + side + '" data-role="eff" type="number" min="0" step="0.1" inputmode="decimal" placeholder="' + EFF_PLACEHOLDER.L + '"></div>' +
        '<div class="field"><label for="ins-' + side + '">연 보험료(만원)</label>' +
          '<input id="ins-' + side + '" data-role="ins" type="number" min="0" inputmode="numeric" placeholder="견적 금액"></div>' +
      '</div></div>';
  }

  function readCar(side) {
    var panel = document.querySelector('[data-side="' + side + '"]');
    var modelSel = panel.querySelector('[data-role="model"]');
    var fuelType = null, energy = null, cc = null, name = null;
    if (modelSel.value === 'custom') {
      fuelType = panel.querySelector('[data-role="fuel"]').value;
      if (fuelType === 'hydrogen') { fuelType = 'ev'; energy = 'hydrogen'; } // 과세는 전기차와 같은 정액
      cc = num(panel.querySelector('[data-role="cc"]').value);
      name = '직접 입력';
    } else if (modelSel.value) {
      var v = data.vehicles.filter(function (x) { return x.id === modelSel.value; })[0];
      if (v) { fuelType = v.fuelType; energy = v.energySource || null; cc = v.displacementCc; name = v.name; }
    }
    if (!fuelType) return null;
    if (fuelType !== 'ev' && cc == null) return null;
    energy = energy || ENERGY_BY_FUEL[fuelType] || 'gasoline';
    return {
      name: name,
      fuelType: fuelType,
      energy: energy,
      unit: unitOf(energy),
      cc: cc,
      priceKrw: (num(panel.querySelector('[data-role="price"]').value) || 0) * 10000,
      eff: num(panel.querySelector('[data-role="eff"]').value),
      insuranceKrw: (num(panel.querySelector('[data-role="ins"]').value) || 0) * 10000
    };
  }

  // ---------- 계산 ----------

  function monthly(car, kmPerYear, holdYears, fuelPrices) {
    var tax = annualTax(car.fuelType, car.cc);
    var price = fuelPrices[priceKeyOf(car.energy)]; // 단가 미확인(null)이면 연료비를 계산하지 않는다
    var fuel = null;
    if (car.eff && car.eff > 0 && price > 0) {
      fuel = kmPerYear / car.eff * price / 12;
    }
    var depMonthly = null;
    if (car.priceKrw > 0) {
      depMonthly = car.priceKrw * (1 - retentionAt(holdYears)) / (holdYears * 12);
    }
    return {
      tax: tax != null ? tax / 12 : null,
      fuel: fuel,
      fuelNeedsPrice: !!(car.eff && car.eff > 0) && !(price > 0),
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
      fuelPrices[k] = (el && num(el.value)) || sitePrices()[k] || null;
    });

    var ma = monthly(a, kmPerYear, holdYears, fuelPrices);
    var mb = monthly(b, kmPerYear, holdYears, fuelPrices);

    function cell(v, other, missing) {
      if (v == null) return '<td style="color:var(--ink-muted);">' + (missing || '입력 필요') + '</td>';
      var win = other != null && v < other;
      return '<td' + (win ? ' class="win"' : '') + '>' + won(v) + '</td>';
    }
    function row(label, va, vb, noteTxt, missA, missB) {
      return '<tr><td>' + label + (noteTxt ? '<div style="font-size:11.5px;color:var(--ink-muted);">' + noteTxt + '</div>' : '') + '</td>' +
        cell(va, vb, missA) + cell(vb, va, missB) + '</tr>';
    }
    // 연비는 넣었는데 그 에너지의 단가가 비어 있으면(수소 단가 미확인 등) 연료비 칸에 단가 입력을 요구한다
    function priceMissing(m, car) {
      return m.fuelNeedsPrice ? PRICE_FIELDS[priceKeyOf(car.energy)].label + ' 단가 입력 필요' : null;
    }
    var missA = priceMissing(ma, a), missB = priceMissing(mb, b);
    var totalA = (ma.tax || 0) + (ma.fuel || 0) + (ma.insurance || 0) + (ma.dep || 0);
    var totalB = (mb.tax || 0) + (mb.fuel || 0) + (mb.insurance || 0) + (mb.dep || 0);
    // 단가가 없어 연료비가 빠진 쪽의 합계는 보여주지 않는다 (빠진 만큼 싸 보여 '더 저렴'으로 강조되는 것 방지)
    var shownA = missA ? null : totalA, shownB = missB ? null : totalB;

    // 결론부터 — 월 유지비 숫자를 히어로 크기로 (DESIGN.md)
    // 한쪽 연료비가 단가 없이 빠지면 그 차가 싸 보이는 잘못된 결론이 나므로 결론을 미룬다
    if (!missA && !missB && totalA > 0 && totalB > 0 && Math.round(totalA) !== Math.round(totalB)) {
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
      { label: '합계', a: shownA, b: shownB }
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
      row('연료비', ma.fuel, mb.fuel, '연 ' + kmPerYear.toLocaleString('ko-KR') + 'km ÷ 공인연비 × 단가', missA, missB) +
      row('보험료', ma.insurance, mb.insurance, '입력한 견적 금액') +
      row('감가', ma.dep, mb.dep, holdYears + '년 보유 가정, 자체 추정 곡선') +
      row('<strong>합계</strong>', shownA, shownB, null, missA && '단가 입력 필요', missB && '단가 입력 필요') +
      '</tbody>';
  }

  // 연비 단위(km/L·km/kWh·km/kg)와 입력 예시를 차의 에너지에 맞춘다
  function setUnit(panel, car) {
    var unit = car ? car.unit : 'L';
    panel.querySelector('[data-role="unit"]').textContent = unit;
    panel.querySelector('[data-role="eff"]').setAttribute('placeholder', EFF_PLACEHOLDER[unit] || EFF_PLACEHOLDER.L);
  }

  // ---------- 초기화 ----------

  function init() {
    Promise.all(['data/vehicles.json', 'data/tax-rates.json', 'data/depreciation.json', 'data/site.json'].map(function (u) {
      return fetch(u).then(function (r) {
        if (!r.ok) throw new Error(u + ' 로드 실패');
        return r.json();
      });
    })).then(function (res) {
      // 승용이 아닌 차종(화물·승합)과 배기량 미확정 스켈레톤 제외 (전기차는 정액이라 포함)
      data.vehicles = res[0].vehicles.filter(function (v) {
        return v.status === 'active' &&
          (v.vehicleClass || 'passenger') === 'passenger' &&
          (v.fuelType === 'ev' || v.displacementCc != null);
      });
      data.rates = res[1];
      data.dep = res[2];
      data.site = res[3];

      $('tco-cars').innerHTML = carPanel('a') + carPanel('b');
      // 단가가 null(미확인)이면 빈 칸 — 그 에너지 차의 연료비는 '단가 입력 필요'로 남는다
      $('fuel-prices').innerHTML = Object.keys(sitePrices()).filter(function (k) { return PRICE_FIELDS[k]; }).map(function (k) {
        var f = PRICE_FIELDS[k];
        var val = sitePrices()[k];
        return '<div class="field"><label for="fp-' + k + '">' + f.label + '(원/' + f.unit + ')</label>' +
          '<input id="fp-' + k + '" type="number" min="0" inputmode="numeric"' +
          (val != null ? ' value="' + val + '"' : ' placeholder="직접 입력"') + '></div>';
      }).join('');
      var basis = data.site.fuelPriceBasis || {};
      var basisTxt = Object.keys(basis).filter(function (k) { return PRICE_FIELDS[k] && sitePrices()[k] != null; }).map(function (k) {
        return PRICE_FIELDS[k].label + ' 단가는 ' + basis[k] + ' 기준이에요.';
      }).join(' ');
      if (basisTxt) $('fuel-price-basis').textContent = basisTxt;

      // 차종 페이지에서 온 프리필 (?car=slug) — 수첩 프리필과 같은 패턴
      var carSlug = new URLSearchParams(location.search).get('car');
      if (carSlug) {
        var pv = data.vehicles.filter(function (v) { return v.slug === carSlug; })[0];
        if (pv) {
          var selA = $('model-a');
          selA.value = pv.id;
          var opt = selA.querySelector('option[value="' + pv.id + '"]');
          if (opt) opt.setAttribute('selected', '');
          setUnit(selA.closest('[data-side]'), readCar('a'));
          render();
        }
        try { history.replaceState(null, '', location.pathname); } catch (e) { /* 무시 */ }
      }

      document.addEventListener('input', render);
      document.addEventListener('change', function (e) {
        // 차종 선택 변경: 직접 입력 필드 표시 + 연비 단위(L/kWh/kg) 갱신
        var panel = e.target.closest('[data-side]');
        if (panel && e.target.getAttribute('data-role') === 'model') {
          panel.querySelector('[data-role="custom-fields"]').style.display =
            e.target.value === 'custom' ? '' : 'none';
        }
        if (panel) setUnit(panel, readCar(panel.getAttribute('data-side')));
        render();
      });
    }).catch(function (err) {
      $('tco-note').textContent = '데이터를 불러오지 못했어요: ' + err.message;
    });
  }

  init();
})();
