/* 차일지 — TCO(총소유비용) 비교기.
 * 세율·차종·감가는 전부 data/*.json에서 읽는다 (하드코딩 금지).
 * 차값은 사용자 입력(제조사 견적기 금액), 보험료도 사용자 입력 — 산출하지 않는다(규제 영역). */
(function () {
  'use strict';

  // 차 A·B 입력 카드는 tco.html 정적 마크업이다(데이터가 오기 전에도 제 높이를 차지해 아래가 밀리지 않게).
  // '직접 입력' 연료 select(tco.html)의 값은 과세 구분(fuelType)이고, 수소전기차(hydrogen)만 과세는 ev 정액·에너지는 수소다

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

  // 차종 select에 붙일 브랜드별 목록 — '차종 선택'·'직접 입력'은 tco.html에 이미 있다
  function modelOptions() {
    var byBrand = {};
    data.vehicles.forEach(function (v) {
      (byBrand[v.brand] = byBrand[v.brand] || []).push(v);
    });
    return Object.keys(byBrand).map(function (brand) {
      return '<optgroup label="' + brand + '">' + byBrand[brand].map(function (v) {
        return '<option value="' + v.id + '">' + v.name + '</option>';
      }).join('') + '</optgroup>';
    }).join('');
  }

  function readCar(side) {
    var panel = document.querySelector('[data-side="' + side + '"]');
    var modelSel = panel.querySelector('[data-role="model"]');
    var fuelType = null, energy = null, cc = null, name = null, slug = null;
    if (modelSel.value === 'custom') {
      fuelType = panel.querySelector('[data-role="fuel"]').value;
      if (fuelType === 'hydrogen') { fuelType = 'ev'; energy = 'hydrogen'; } // 과세는 전기차와 같은 정액
      cc = num(panel.querySelector('[data-role="cc"]').value);
      name = '직접 입력';
    } else if (modelSel.value && data.vehicles) {
      var v = data.vehicles.filter(function (x) { return x.id === modelSel.value; })[0];
      if (v) { fuelType = v.fuelType; energy = v.energySource || null; cc = v.displacementCc; name = v.name; slug = v.slug || null; }
    }
    if (!fuelType) return null;
    if (fuelType !== 'ev' && cc == null) return null;
    energy = energy || ENERGY_BY_FUEL[fuelType] || 'gasoline';
    return {
      name: name,
      slug: slug,
      fuelType: fuelType,
      energy: energy,
      unit: unitOf(energy),
      cc: cc,
      priceKrw: (num(panel.querySelector('[data-role="price"]').value) || 0) * 10000,
      eff: num(panel.querySelector('[data-role="eff"]').value),
      insuranceKrw: (num(panel.querySelector('[data-role="ins"]').value) || 0) * 10000
    };
  }

  // ---------- 공통 조건 ----------

  // 계산에 실제로 쓰는 값 (빈 칸·0이면 기본값으로 돌아가는 규칙 그대로) — 요약 줄도 이 값을 보인다
  function readCommon() {
    var defaults = sitePrices();
    var fuelPrices = {};
    var edited = false;
    Object.keys(defaults).forEach(function (k) {
      var el = $('fp-' + k);
      fuelPrices[k] = (el && num(el.value)) || defaults[k] || null;
      if (fuelPrices[k] !== (defaults[k] || null)) edited = true;
    });
    return {
      kmPerYear: num($('common-km').value) || 12000,
      holdYears: Math.min(15, Math.max(1, num($('common-years').value) || 5)),
      fuelPrices: fuelPrices,
      pricesEdited: edited
    };
  }

  // 접힌 '공통 조건' 줄의 요약 (tco.html 정적 문구는 JS가 꺼졌을 때의 기본값).
  // 요약은 줄바꿈 없는 한 줄이라 짧게 — 360px에서 '공통 조건'과 한 줄, 320px에서도 가로 넘침 없음
  function updateSummary(common) {
    $('common-summary').textContent = '연 ' + common.kmPerYear.toLocaleString('ko-KR') + 'km · ' +
      common.holdYears + '년 보유 · ' + (common.pricesEdited ? '수정한 단가' : '기본 단가');
  }

  // 차종 세금 페이지로 가는 목록 행 (홈 '도구' 목록과 같은 모양: 이름 + 12px 꼬리 '차 A' + 오른쪽 셰브론).
  // 금액은 넣지 않는다 — 판매가 끝난 세대는 세금 페이지가 신차가 아닌 기본 연식 금액을 보여 신차 첫해 세액과 어긋난다.
  // 목록에서 고른 차만 — 직접 입력은 페이지가 없어 빠진다. 같은 차를 둘 다 고르면 한 행('차 A·B')
  var CHEVRON_RIGHT = '<svg class="chevron" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">' +
    '<path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  function taxLinks(a, b) {
    var rows = [];
    [[a, 'A'], [b, 'B']].forEach(function (x) {
      var car = x[0];
      if (!car.slug) return;
      var same = rows.filter(function (r) { return r.slug === car.slug; })[0];
      if (same) { same.tag += '·' + x[1]; return; }
      rows.push({ slug: car.slug, name: car.name, tag: '차 ' + x[1] });
    });
    if (!rows.length) return '';
    return '<h3 class="related-label">연식별 자동차세</h3><ul class="hub-list">' + rows.map(function (r) {
      return '<li><a class="hub-row" href="tax/' + r.slug + '.html"><span class="hub-name">' + r.name +
        ' <span class="hub-years">' + r.tag + '</span></span>' + CHEVRON_RIGHT + '</a></li>';
    }).join('') + '</ul>';
  }

  // 내용이 같으면 다시 그리지 않는다. 입력칸에 포커스가 남은 채 링크를 누르면 blur → change → render가 먼저 돌고,
  // 그때 링크를 innerHTML로 갈아 끼우면 누른 요소가 DOM에서 빠져 click이 사라진다(첫 탭 헛탭)
  function setHtml(el, html) {
    if (el.__html === html) return;
    el.__html = html;
    el.innerHTML = html;
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

  var missedBefore = false; // 단가 입력이 필요해진 순간 한 번만 '공통 조건'을 펼친다

  function render() {
    if (!data.rates) return; // 데이터(JSON)가 오기 전 — 도착하면 init()이 그 시점의 입력으로 한 번 그린다
    var common = readCommon();
    updateSummary(common);
    var a = readCar('a');
    var b = readCar('b');
    var table = $('tco-result');
    var note = $('tco-note');
    var headline = $('tco-headline');
    var barsEl = $('tco-bars');
    var linksEl = $('tco-links');
    if (!a || !b) {
      setHtml(table, '');
      setHtml(barsEl, '');
      setHtml(linksEl, '');
      headline.style.display = 'none';
      note.style.display = '';
      missedBefore = false;
      return;
    }
    note.style.display = 'none';

    var kmPerYear = common.kmPerYear;
    var holdYears = common.holdYears;
    var fuelPrices = common.fuelPrices;

    var ma = monthly(a, kmPerYear, holdYears, fuelPrices);
    var mb = monthly(b, kmPerYear, holdYears, fuelPrices);

    function cell(v, other, missing) {
      if (v == null) return '<td class="spec-label">' + (missing || '입력 필요') + '</td>';
      var win = other != null && v < other;
      return '<td' + (win ? ' class="win"' : '') + '>' + won(v) + '</td>';
    }
    function row(label, va, vb, noteTxt, missA, missB) {
      return '<tr><td>' + label + (noteTxt ? '<div class="spec-label">' + noteTxt + '</div>' : '') + '</td>' +
        cell(va, vb, missA) + cell(vb, va, missB) + '</tr>';
    }
    // 연비는 넣었는데 그 에너지의 단가가 비어 있으면(수소 단가 미확인 등) 연료비 칸에 단가 입력을 요구한다
    function priceMissing(m, car) {
      return m.fuelNeedsPrice ? PRICE_FIELDS[priceKeyOf(car.energy)].label + ' 단가 입력 필요' : null;
    }
    var missA = priceMissing(ma, a), missB = priceMissing(mb, b);
    if ((missA || missB) && !missedBefore) $('common').open = true;
    missedBefore = !!(missA || missB);
    var totalA = (ma.tax || 0) + (ma.fuel || 0) + (ma.insurance || 0) + (ma.dep || 0);
    var totalB = (mb.tax || 0) + (mb.fuel || 0) + (mb.insurance || 0) + (mb.dep || 0);
    // 단가가 없어 연료비가 빠진 쪽의 합계는 보여주지 않는다 (빠진 만큼 싸 보여 '더 저렴'으로 강조되는 것 방지)
    var shownA = missA ? null : totalA, shownB = missB ? null : totalB;

    // 결론부터 — 월 유지비 숫자를 히어로 크기로 (DESIGN.md)
    // 한쪽 연료비가 단가 없이 빠지면 그 차가 싸 보이는 잘못된 결론이 나므로 결론을 미룬다
    if (!missA && !missB && totalA > 0 && totalB > 0 && Math.round(totalA) !== Math.round(totalB)) {
      var cheaper = totalA < totalB ? a : b;
      var diff = Math.abs(totalA - totalB);
      setHtml(headline, '<div class="tax-hero">월 ' + won(Math.min(totalA, totalB)) + '</div>' +
        '<div class="sub"><strong>' + cheaper.name + '</strong> 기준 — 상대보다 월 ' + won(diff) +
        ' 저렴해요 (' + holdYears + '년 보유 시 약 ' + won(diff * 12 * holdYears) + ' 차이)</div>');
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
    var barsHtml = maxV > 0 ? cats.map(function (c) {
      function bar(cls, v) {
        var w = v ? Math.max(2, v / maxV * 100) : 0;
        return '<div class="tco-bar ' + cls + '" style="width:' + w.toFixed(1) + '%;"></div>';
      }
      return '<div class="tco-bar-row"><div class="tco-bar-label">' + c.label + '</div>' +
        '<div class="tco-bar-track">' + bar('a', c.a) + bar('b', c.b) + '</div></div>';
    }).join('') : '';
    // 차마다 한 줄 — 긴 차명이 줄바꿈될 때 '차 B'와 차명이 다른 줄로 갈라지지 않게.
    // 범례는 이름만(링크 없음) — 세금 페이지 링크는 표 아래 목록 행(taxLinks)
    setHtml(barsEl, '<div class="tco-bars">' + barsHtml +
      '<div class="tco-legend"><span class="dot a"></span>차 A ' + a.name +
      '<br><span class="dot b"></span>차 B ' + b.name + '</div></div>');
    setHtml(linksEl, taxLinks(a, b));

    // 헤더에 차명을 쓰면 375px에서 '가솔/린'처럼 끊기거나(긴 이름은 표가 넘침) — 짧은 '차 A/차 B'로, 차명은 바로 위 범례에
    setHtml(table, '<thead><tr><th>월 기준</th><th>차 A</th><th>차 B</th></tr></thead><tbody>' +
      row('자동차세', ma.tax, mb.tax, '신차 첫해 기준 — 3년차부터 매년 줄어요') +
      row('연료비', ma.fuel, mb.fuel, '연 ' + kmPerYear.toLocaleString('ko-KR') + 'km ÷ 공인연비 × 단가', missA, missB) +
      row('보험료', ma.insurance, mb.insurance, '입력한 견적 금액') +
      row('감가', ma.dep, mb.dep, holdYears + '년 보유 가정, 자체 추정 곡선') +
      row('<strong>합계</strong>', shownA, shownB, null, missA && '단가 입력 필요', missB && '단가 입력 필요') +
      '</tbody>');
  }

  // 연비 단위(km/L·km/kWh·km/kg)와 입력 예시를 차의 에너지에 맞춘다
  function setUnit(panel, car) {
    var unit = car ? car.unit : 'L';
    panel.querySelector('[data-role="unit"]').textContent = unit;
    panel.querySelector('[data-role="eff"]').setAttribute('placeholder', EFF_PLACEHOLDER[unit] || EFF_PLACEHOLDER.L);
  }

  // 카드 한 장을 그 차종 선택에 맞춘다: '직접 입력'이면 연료·배기량 칸을 보이고, 연비 단위(L/kWh/kg)를 바꾼다
  function syncPanel(panel) {
    var custom = panel.querySelector('[data-role="model"]').value === 'custom';
    panel.querySelector('[data-role="custom-fields"]').style.display = custom ? '' : 'none';
    setUnit(panel, readCar(panel.getAttribute('data-side')));
  }

  // ---------- 초기화 ----------

  function init() {
    // 카드는 정적 HTML이라 데이터가 오기 전에도 만질 수 있다 — '직접 입력' 칸·연비 단위는 바로 바꾸고, 계산(render)은 데이터가 온 뒤
    document.addEventListener('input', render);
    document.addEventListener('change', function (e) {
      // 차종·연료 선택 변경: 직접 입력 필드 표시 + 연비 단위(L/kWh/kg) 갱신
      var panel = e.target.closest('[data-side]');
      if (panel) syncPanel(panel);
      render();
    });
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

      // 차종 목록은 정적 select(tco.html) 끝에 붙인다 — 카드를 다시 그리지 않으므로 데이터가 오기 전에 넣은 값도 남는다
      var groups = modelOptions();
      $('model-a').insertAdjacentHTML('beforeend', groups);
      $('model-b').insertAdjacentHTML('beforeend', groups);
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
      updateSummary(readCommon()); // 브라우저가 이전 입력값을 복원했을 때도 요약을 맞춘다

      // 차종 페이지에서 온 프리필 (?car=slug) — 수첩 프리필과 같은 패턴
      var carSlug = new URLSearchParams(location.search).get('car');
      if (carSlug) {
        var pv = data.vehicles.filter(function (v) { return v.slug === carSlug; })[0];
        if (pv) {
          var selA = $('model-a');
          selA.value = pv.id;
          var opt = selA.querySelector('option[value="' + pv.id + '"]');
          if (opt) opt.setAttribute('selected', '');
        }
        try { history.replaceState(null, '', location.pathname); } catch (e) { /* 무시 */ }
      }

      // 프리필·데이터가 오기 전에 넣은 값·브라우저가 복원한 입력값에 카드와 결과를 맞춘다
      syncPanel($('model-a').closest('[data-side]'));
      syncPanel($('model-b').closest('[data-side]'));
      render();
    }).catch(function (err) {
      // 카드는 정적 HTML이라 그대로 보인다 — 계산할 수 없으니 입력을 막는다
      Array.prototype.forEach.call(document.querySelectorAll('#tco-cars select, #tco-cars input'), function (el) {
        el.disabled = true;
      });
      $('tco-note').textContent = '데이터를 불러오지 못했어요: ' + err.message;
    });
  }

  init();
})();
