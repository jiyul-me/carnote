/* 차일지 — 화면·이벤트 (derive.js, storage.js에 의존) */
(function () {
  'use strict';

  var D = window.ChailjiDerive;
  var S = window.ChailjiStorage;

  var FUEL_LABELS = { gasoline: '가솔린', diesel: '디젤', lpg: 'LPG', hybrid: '하이브리드', ev: '전기' };
  var STATE_LABELS = { overdue: '지남', soon: '임박', ok: '여유', 'no-record': '기록 없음', 'no-data': '주행거리 필요', manual: '—' };

  var data = { parts: null, inspection: null, depreciation: null, vehicles: null, site: null, affiliate: null }; // /data/*.json
  var doc = null;              // 저장 문서
  var demoMode = false;        // ?demo=1 — 저장하지 않는 시연용
  // carId = 대시보드에서 보고 있는 차, editingCarId = 차 폼이 편집 중인 차(null = 신규).
  // 분리해 두어야 '+ 차 추가' 후 취소해도 보던 차로 돌아온다.
  // prefill = 세금 페이지에서 넘어온 차종·배기량·연식 (TASKS #2)
  var state = { view: 'dashboard', carId: null, partId: null, editingCarId: null, prefill: null };
  var $app = document.getElementById('app');

  // ---------- 유틸 ----------

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function todayISO() { return D.toISO(new Date()); }
  function nowISO() { return new Date().toISOString(); }
  // parseInt는 '1e3'을 1로 오파싱한다 — 숫자 입력은 전부 이 함수로
  function numOrNull(v) {
    var n = Number(v);
    return v !== '' && v != null && isFinite(n) && n >= 0 ? Math.round(n) : null;
  }
  function fmtKm(n) { return n == null ? '' : n.toLocaleString('ko-KR') + 'km'; }
  function fmtDate(iso) { return iso ? iso.replace(/-/g, '.') : ''; }
  function persist() { if (!demoMode) S.save(doc); }
  function partById(id) {
    for (var i = 0; i < data.parts.parts.length; i++) if (data.parts.parts[i].id === id) return data.parts.parts[i];
    return null;
  }
  function carById(id) {
    for (var i = 0; i < doc.cars.length; i++) if (doc.cars[i].id === id) return doc.cars[i];
    return null;
  }
  // 차종명 입력을 vehicles.json과 매칭 (이름·별칭 완전 일치, 대소문자·공백 무시)
  function matchVehicle(text) {
    if (!text || !data.vehicles) return null;
    var t = text.trim().toLowerCase();
    for (var i = 0; i < data.vehicles.length; i++) {
      var v = data.vehicles[i];
      if (v.name.toLowerCase() === t) return v;
      for (var j = 0; j < v.aliases.length; j++) {
        if (v.aliases[j].toLowerCase() === t) return v;
      }
    }
    return null;
  }
  function activeCar() {
    return carById(state.carId) || doc.cars[0] || null;
  }

  var toastTimer = null;
  // action: {label, fn} — 실행 취소 등. 액션이 있으면 더 오래 떠 있는다
  function toast(msg, action) {
    var el = document.querySelector('.msg-toast');
    if (el) el.remove();
    el = document.createElement('div');
    el.className = 'msg-toast';
    el.textContent = msg;
    if (action) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'msg-toast-action';
      btn.textContent = action.label;
      btn.addEventListener('click', function () {
        clearTimeout(toastTimer);
        el.remove();
        action.fn();
      });
      el.appendChild(btn);
    }
    document.body.appendChild(el);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.remove(); }, action ? 5000 : 2200);
  }

  // ---------- 쿠팡파트너스 슬롯 (TASKS #12) ----------
  // data/affiliate.json의 links에 URL이 있을 때만 렌더. 링크 값은 가입 후 사용자가 채운다

  function affiliateSlot(part) {
    var aff = data.affiliate;
    var url = aff && aff.links && aff.links[part.id];
    if (!url) return '';
    var label = part.shopKeyword || part.name;
    return '<div class="card">' +
      '<a class="btn secondary" style="display:block;text-align:center;text-decoration:none;" href="' + esc(url) + '" target="_blank" rel="sponsored noopener">' +
      esc(label) + ' 쿠팡에서 보기</a>' +
      '<p class="notice">' + esc(aff.disclosure) + '</p>' +
    '</div>';
  }

  // ---------- 인앱 브라우저 안내 (TASKS #11) ----------
  // 카톡·네이버앱 등의 인앱 브라우저는 localStorage가 격리돼 기록이 사라져 보인다

  function inAppBrowser() {
    return /KAKAOTALK|NAVER\(inApp|Instagram|FBAV|FBAN|Line\//i.test(navigator.userAgent || '');
  }

  function inAppBanner() {
    if (!inAppBrowser()) return '';
    try { if (sessionStorage.getItem('chailji:inapp-dismissed')) return ''; } catch (e) { /* 무시 */ }
    var openLink = '';
    if (/Android/i.test(navigator.userAgent)) {
      var url = location.href.replace(/^https?:\/\//, '');
      openLink = ' <a class="linklike" href="intent://' + url + '#Intent;scheme=https;package=com.android.chrome;end">Chrome으로 열기</a>';
    }
    return '<div class="card" style="border-color:var(--warning);"><p class="notice" style="margin:0;color:var(--warning);">' +
      '메신저 안 브라우저에서는 기록이 따로 저장돼요. Chrome/Safari로 열면 기록이 유지됩니다.' + openLink +
      ' <button type="button" class="linklike" data-action="dismiss-inapp" style="color:var(--ink-muted);">닫기</button></p></div>';
  }

  // ---------- .ics 캘린더 내보내기 (TASKS #1) ----------
  // 웹 푸시가 없는 구조라 "알림"은 사용자 폰 캘린더에 심는다

  function calendarEvents(car) {
    var today = todayISO();
    var monthlyKm = D.monthlyKmEstimate(car, doc.records, doc.fuelLogs);
    var siteUrl = (data.site && data.site.baseUrl) || '';
    var desc = '차일지에서 확인: ' + siteUrl;
    var events = [];
    car.enabledPartIds.map(partById).filter(Boolean).forEach(function (p) {
      var st = D.partStatus(p, car, doc.records, doc.settings, today, monthlyKm);
      var due = st.dueDate || st.predictedDate;
      if (!due || due < today) return; // 이미 지난 일정은 제외 (지남 항목은 앱에서 표시)
      events.push({
        uid: car.id + '-' + p.id + '@chailji',
        date: due,
        summary: '차일지 — ' + p.name + ' 교체 시기',
        description: desc,
        url: siteUrl || undefined
      });
    });
    var insp = D.inspectionStatus(car, data.inspection.regularInspection, today);
    if (insp && insp.expiryOn >= today) {
      events.push({
        uid: car.id + '-inspection@chailji',
        date: insp.expiryOn,
        summary: '차일지 — 자동차 검사 만료일',
        description: desc,
        url: siteUrl || undefined
      });
    }
    // 자동차세 연납 신청 시작(매년 1/16 경) — 매년 반복
    var year = Number(today.slice(0, 4));
    var jan16 = year + '-01-16';
    if (jan16 < today) jan16 = (year + 1) + '-01-16';
    events.push({
      uid: 'tax-prepay@chailji',
      date: jan16,
      summary: '차일지 — 자동차세 연납 신청 시작',
      description: desc,
      url: siteUrl || undefined,
      yearlyRepeat: true
    });
    return events;
  }

  function downloadIcs(events, filename) {
    if (!events.length) { toast('내보낼 일정이 없어요 — 먼저 기록을 추가해 주세요'); return; }
    var stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
    var text = window.ChailjiIcs.buildCalendar(events, { stamp: stamp, calName: '차일지' });
    var blob = new Blob([text], { type: 'text/calendar;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    toast('캘린더 파일을 받았어요 — 열면 일정·알림이 등록돼요');
  }

  // 기록이 append했던 주행거리 관측 롤백 (기록 삭제·실행 취소 공용)
  function rollbackOdometerEntry(rec) {
    if (!rec || rec.odometerKm == null) return;
    var c = carById(rec.carId);
    if (!c || c.odometerLog.length <= 1) return;
    for (var i = c.odometerLog.length - 1; i >= 0; i--) {
      if (c.odometerLog[i].date === rec.doneOn && c.odometerLog[i].km === rec.odometerKm) {
        c.odometerLog.splice(i, 1);
        break;
      }
    }
  }

  // ---------- 렌더 ----------

  function render() {
    var views = {
      dashboard: renderDashboard,
      'car-form': renderCarForm,
      part: renderPartView,
      settings: renderSettings
    };
    $app.innerHTML = (views[state.view] || renderDashboard)();
    bindViewEvents();
    window.scrollTo(0, 0);
  }

  function go(view, extra) {
    state.view = view;
    state.partId = extra && extra.partId !== undefined ? extra.partId : null;
    state.editingCarId = extra && extra.editingCarId !== undefined ? extra.editingCarId : null;
    if (view !== 'car-form') state.prefill = null; // 프리필은 등록 폼을 떠나면 소멸
    if (extra && extra.carId !== undefined) state.carId = extra.carId;
    render();
  }

  // ----- 대시보드 -----

  function renderDashboard() {
    if (!doc.cars.length) {
      return '<div class="hero">' +
        '<h1>내 차 수첩을 시작해요</h1>' +
        '<p>소모품 교체 주기와 자동차 검사 일정을<br>한눈에 챙겨 드릴게요.</p>' +
        '<button type="button" class="btn" data-action="new-car" style="width:auto;padding:0 28px;">내 차 등록하기</button>' +
        '<p style="margin-top:14px;"><a class="linklike" href="?demo=1">등록 없이 둘러보기</a></p>' +
        '</div>';
    }

    var car = activeCar();
    var today = todayISO();
    var monthlyKm = D.monthlyKmEstimate(car, doc.records, doc.fuelLogs);
    var odo = D.latestOdometer(car);
    var html = inAppBanner();

    // 백업 유도: 기록이 쌓였는데 마지막 백업 후 30일 넘음 (iOS Safari 등 자동 삭제 대비)
    if (!demoMode && doc.records.length >= 5 &&
        (!doc.settings.lastExportAt || D.diffDays(doc.settings.lastExportAt.slice(0, 10), today) > 30)) {
      html += '<div class="card" style="border-color:var(--warning);"><p class="notice" style="margin:0;color:var(--warning);">' +
        '기록이 쌓이고 있어요 — 브라우저 데이터가 지워지면 복구할 수 없으니 ' +
        '<button type="button" class="linklike" data-action="go-settings">JSON 백업</button>을 받아두세요.</p></div>';
    }

    // 차 전환 (2대 이상)
    if (doc.cars.length > 1) {
      html += '<div class="car-switch">' + doc.cars.map(function (c) {
        return '<button type="button" class="chip' + (c.id === car.id ? ' active' : '') + '" data-action="switch-car" data-id="' + c.id + '">' +
          esc(c.nickname || c.modelName) + '</button>';
      }).join('') +
      '<button type="button" class="chip" data-action="new-car">+ 차 추가</button></div>';
    }

    // 내 차 카드 — 주행거리가 이 페이지의 히어로 숫자
    var insp = D.inspectionStatus(car, data.inspection.regularInspection, today);
    var insur = D.insuranceStatus(car, today);
    html += '<div class="card">' +
      '<div class="car-head">' +
        '<div><h2 class="car-name">' + esc(car.nickname || car.modelName) + '</h2>' +
        '<p class="car-sub">' + esc(FUEL_LABELS[car.fuelType] || car.fuelType) +
          (car.displacementCc ? ' · ' + car.displacementCc.toLocaleString('ko-KR') + 'cc' : '') +
          ' · ' + fmtDate(car.firstRegisteredOn) + ' 등록</p></div>' +
        '<button type="button" class="btn small secondary" data-action="edit-car">수정</button>' +
      '</div>' +
      '<div class="odo-row">' +
        '<span class="odo-km">' + (odo ? odo.km.toLocaleString('ko-KR') : '?') + '</span><span class="odo-unit">km</span>' +
        '<button type="button" class="btn small secondary" data-action="odo-form">갱신</button>' +
      '</div>' +
      '<div id="odo-editor"></div>' +
      yearlySpendLine(car, today) +
    '</div>';

    // 다가오는 일정 — 검사·보험·임박/지남 소모품 + 캘린더 내보내기
    html += '<div class="card"><h2>다가오는 일정</h2><ul class="sched-list">' +
      scheduleRows(car, insp, insur, today, monthlyKm) +
      '</ul>' +
      inspectionNotices(insp) +
      '<button type="button" class="btn secondary" style="margin-top:12px;" data-action="export-ics">전체 일정을 폰 캘린더로 (.ics)</button>' +
      '<p class="notice">교체 예정일·검사 만료일·연납 시작일이 알림(7일 전, 당일 오전 9시)과 함께 등록돼요.</p>' +
    '</div>';

    // 감가 카드
    var value = D.estimateValue(data.depreciation, car, today);
    if (value != null) {
      html += '<div class="card"><h2>현재 추정 가치</h2>' +
        '<div class="big">약 ' + D.formatKrw(value) + '</div>' +
        '<p class="notice">구매가 ' + D.formatKrw(car.purchasePriceKrw) + ' 기준 · ' + esc(data.depreciation.disclaimerText) + '</p>' +
      '</div>';
    }

    // 소모품 리스트 (긴급한 순)
    var order = { overdue: 0, soon: 1, 'no-record': 2, 'no-data': 3, ok: 4, manual: 5 };
    var rows = car.enabledPartIds.map(partById).filter(Boolean).map(function (p) {
      return { part: p, st: D.partStatus(p, car, doc.records, doc.settings, today, monthlyKm) };
    });
    rows.sort(function (a, b) {
      var d = order[a.st.state] - order[b.st.state];
      if (d) return d;
      var ar = a.st.remainingDays != null ? a.st.remainingDays : (a.st.remainingKm != null ? a.st.remainingKm / 40 : 1e9);
      var br = b.st.remainingDays != null ? b.st.remainingDays : (b.st.remainingKm != null ? b.st.remainingKm / 40 : 1e9);
      return ar - br;
    });

    if (monthlyKm == null) {
      html += '<p class="notice">주행거리를 한 번 더 입력하면 km 주기 항목의 "약 N월경" 예측이 시작돼요.</p>';
    }

    html += '<p class="section-title">소모품 상태 (' + rows.length + ')</p>' +
      '<div class="card" style="padding:4px 20px;"><ul class="part-list">' +
      rows.map(function (r) { return partRow(r.part, r.st); }).join('') +
      '</ul></div>' +
      '<p class="notice">항목 켜고 끄기는 <button type="button" class="linklike" data-action="go-settings">설정</button>에서.</p>';

    return html;
  }

  // D-day 배지 (DESIGN: 초과=danger, D-14 이하=warning, 여유=텍스트만)
  function ddayBadge(d) {
    var cls = d < 0 ? ' b-danger' : (d <= 14 ? ' b-warn' : '');
    return '<span class="dday' + cls + '">' + D.formatDday(d) + '</span>';
  }

  // 다가오는 일정 행: 검사·보험 + 임박/지남 소모품
  function scheduleRows(car, insp, insur, today, monthlyKm) {
    var rows = [];
    if (insp) {
      rows.push('<li><button type="button" class="sched-row" data-action="edit-car">' +
        '<span class="sched-main"><span class="sched-name">자동차 검사</span>' +
        '<div class="sched-sub">' + fmtDate(insp.expiryOn) + '까지' + (insp.estimated ? ' · 추정' : '') + '</div></span>' +
        ddayBadge(insp.dDay) + '</button></li>');
    }
    if (insur) {
      rows.push('<li><button type="button" class="sched-row" data-action="edit-car">' +
        '<span class="sched-main"><span class="sched-name">보험 만기</span>' +
        '<div class="sched-sub">' + fmtDate(insur.expiresOn) + '</div></span>' +
        ddayBadge(insur.dDay) + '</button></li>');
    } else {
      rows.push('<li><button type="button" class="sched-row" data-action="edit-car">' +
        '<span class="sched-main"><span class="sched-name">보험 만기</span>' +
        '<div class="sched-sub">만기일을 등록하면 함께 챙겨드려요</div></span>' +
        '<span class="dday">등록</span></button></li>');
    }
    car.enabledPartIds.map(partById).filter(Boolean).forEach(function (p) {
      var st = D.partStatus(p, car, doc.records, doc.settings, today, monthlyKm);
      if (st.state !== 'overdue' && st.state !== 'soon') return;
      var due = st.dueDate || st.predictedDate;
      rows.push('<li><button type="button" class="sched-row" data-action="open-part" data-id="' + p.id + '">' +
        '<span class="sched-main"><span class="sched-name">' + esc(p.name) + '</span>' +
        '<div class="sched-sub">' + (st.state === 'overdue' ? '교체 시기 지남' : '교체 시기 임박') +
        (due ? ' · ' + fmtDate(due) : '') + '</div></span>' +
        '<span class="dday ' + (st.state === 'overdue' ? 'b-danger' : 'b-warn') + '">' +
        (st.state === 'overdue' ? '지남' : '임박') + '</span></button></li>');
    });
    return rows.join('');
  }

  // 기록이 쌓이는 보람이 보이게 — 올해 정비 건수·비용 합계 한 줄
  function yearlySpendLine(car, today) {
    var spend = D.yearlySpend(doc.records, car.id, today.slice(0, 4));
    if (!spend.count) return '';
    return '<p class="notice">올해 정비 <strong>' + spend.count + '건</strong>' +
      (spend.costKrw > 0 ? ' · <strong>' + D.formatKrw(spend.costKrw) + '</strong>' : '') + '</p>';
  }

  // 수검 가능·과태료 정보는 색만으로 전달하지 않고 문장으로도 알려준다
  function inspectionNotices(insp) {
    if (!insp) return '';
    var out = '';
    if (insp.dDay < 0) {
      var p = data.inspection.penalty;
      out += '<p class="notice" style="color:var(--danger);">검사 기간이 지났어요 — 과태료: 만료 후 30일 이내 ' +
        D.formatKrw(p.within30DaysKrw) + ', 이후 3일마다 ' + D.formatKrw(p.per3DaysAfterKrw) +
        ' 가산 (최대 ' + D.formatKrw(p.maxKrw) + ')</p>';
    } else if (insp.inWindow) {
      out += '<p class="notice" style="color:var(--warning);">지금 검사 받을 수 있어요 (' +
        fmtDate(insp.windowStart) + ' ~ ' + fmtDate(insp.windowEnd) + ')</p>';
    }
    if (insp.estimated) {
      out += '<p class="notice">검사일은 등록일 기준 추정이에요. <button type="button" class="linklike" data-action="edit-car">최근 검사일을 입력</button>하면 정확해져요.</p>';
    }
    return out;
  }

  // 소모품 사용 진행률 (0~1) — km·날짜 중 더 많이 지난 쪽
  function partProgress(part, st) {
    if (!st.lastRecord) return null;
    var r = null;
    if (part.intervalKm != null && st.remainingKm != null) {
      r = Math.max(r || 0, 1 - st.remainingKm / part.intervalKm);
    }
    if (part.intervalMonths != null && st.remainingDays != null) {
      r = Math.max(r || 0, 1 - st.remainingDays / (part.intervalMonths * 30.44));
    }
    return r == null ? null : Math.min(1, Math.max(0, r));
  }

  function partRow(part, st) {
    var sub;
    if (st.state === 'no-record') {
      sub = '기록을 추가하면 교체 시기를 계산해요';
    } else if (st.state === 'no-data') {
      sub = '기록에 주행거리를 입력하면 교체 시기를 계산해요';
    } else if (st.state === 'manual') {
      sub = st.lastRecord ? '마지막: ' + fmtDate(st.lastRecord.doneOn) : (part.type === 'refill' ? '떨어지면 보충 후 기록' : '필요할 때 기록');
    } else {
      var lastTxt = '마지막 ' + fmtDate(st.lastRecord.doneOn) +
        (st.lastRecord.odometerKm != null ? ' · ' + fmtKm(st.lastRecord.odometerKm) : '');
      var nextBits = [];
      if (st.dueKm != null) {
        nextBits.push(fmtKm(st.dueKm) + (st.predictedDate ? ' (약 ' + fmtDate(st.predictedDate).slice(0, 7) + '경)' : ''));
      }
      if (st.dueDate) nextBits.push(fmtDate(st.dueDate));
      sub = lastTxt + (nextBits.length ?
        ' → 다음 ' + nextBits.join(' 또는 ') + (nextBits.length > 1 ? ' 중 빠른 쪽' : '') : '');
    }
    // 임박·지남 항목은 상세로 안 가고도 오늘 날짜로 바로 기록할 수 있게 (1탭)
    var quick = (st.state === 'overdue' || st.state === 'soon')
      ? '<button type="button" class="quick-btn" data-action="quick-record" data-id="' + part.id + '">완료</button>'
      : '';
    var prog = partProgress(part, st);
    var progressBar = prog != null
      ? '<div class="progress"><div class="progress-fill" style="width:' + (prog * 100).toFixed(0) + '%;"></div></div>'
      : '';
    return '<li><div class="part-row">' +
      '<button type="button" class="part-row-main" data-action="open-part" data-id="' + part.id + '">' +
      '<span class="part-main"><span class="part-name">' + esc(part.name) + '</span>' +
      '<div class="part-sub">' + sub + '</div>' + progressBar + '</span>' +
      '<span class="badge ' + st.state + '">' + STATE_LABELS[st.state] + '</span>' +
      '</button>' + quick +
    '</div></li>';
  }

  // ----- 차 등록/수정 -----

  function renderCarForm() {
    var car = state.editingCarId ? carById(state.editingCarId) : null;
    var isNew = !car;
    var pre = (isNew && state.prefill) ? state.prefill : null;
    var c = car || (pre ? {
      modelName: pre.modelName,
      fuelType: pre.fuelType,
      displacementCc: pre.displacementCc,
      firstRegisteredOn: pre.year ? pre.year + '-01-01' : null
    } : {});
    return '<div class="form-view">' +
      (doc.cars.length ? '<button type="button" class="back-btn" data-action="go-dashboard">← 돌아가기</button>' : '') +
      '<h1>' + (isNew ? '내 차 등록' : '차 정보 수정') + '</h1>' +
      '<form id="car-form">' +
      '<div class="field"><label for="f-model">차종명 *</label>' +
        '<input id="f-model" name="modelName" required placeholder="예: 아반떼 1.6" value="' + esc(c.modelName) + '" list="model-datalist" autocomplete="off">' +
        '<datalist id="model-datalist">' +
          data.vehicles.map(function (v) { return '<option value="' + esc(v.name) + '">'; }).join('') +
        '</datalist>' +
        '<div class="hint">목록에서 고르면 배기량·연료가 자동으로 채워져요. 없는 차종은 그냥 입력하면 돼요</div></div>' +
      '<div class="field"><label for="f-nick">별칭</label>' +
        '<input id="f-nick" name="nickname" placeholder="예: 우리집 흰둥이 (선택)" value="' + esc(c.nickname) + '"></div>' +
      '<div class="field-row">' +
        '<div class="field"><label for="f-fuel">연료 *</label><select id="f-fuel" name="fuelType">' +
          Object.keys(FUEL_LABELS).map(function (k) {
            return '<option value="' + k + '"' + (c.fuelType === k ? ' selected' : '') + '>' + FUEL_LABELS[k] + '</option>';
          }).join('') + '</select></div>' +
        '<div class="field"><label for="f-cc">배기량(cc)</label>' +
          '<input id="f-cc" name="displacementCc" type="number" min="0" inputmode="numeric" placeholder="예: 1598" value="' + (c.displacementCc != null ? c.displacementCc : '') + '">' +
          '<div class="hint">전기차는 비워두세요</div></div>' +
      '</div>' +
      '<div class="field"><label for="f-reg">최초 등록일 *</label>' +
        '<input id="f-reg" name="firstRegisteredOn" type="date" required value="' + esc(c.firstRegisteredOn) + '">' +
        '<div class="hint">자동차등록증 기준. 검사 주기·감가 계산에 쓰여요' +
        (pre && pre.year ? ' · 연식 기준 1월 1일로 채워뒀어요 — 실제 등록일로 수정해 주세요' : '') + '</div></div>' +
      (isNew ?
        '<div class="field"><label for="f-odo">현재 주행거리(km) *</label>' +
        '<input id="f-odo" name="odometerKm" type="number" min="0" inputmode="numeric" required placeholder="예: 45000"></div>' : '') +
      '<div class="field-row">' +
        '<div class="field"><label for="f-price">구매가(만원)</label>' +
          '<input id="f-price" name="purchasePriceMan" type="number" min="0" inputmode="numeric" placeholder="예: 2300" value="' + (c.purchasePriceKrw ? Math.round(c.purchasePriceKrw / 10000) : '') + '">' +
          '<div class="hint">입력하면 추정 가치를 보여드려요</div></div>' +
        '<div class="field"><label for="f-bought">구매일</label>' +
          '<input id="f-bought" name="purchasedOn" type="date" value="' + esc(c.purchasedOn) + '">' +
          '<div class="hint">중고 구입이면 꼭 입력</div></div>' +
      '</div>' +
      '<div class="field-row">' +
        '<div class="field"><label for="f-insur">보험 만기일</label>' +
          '<input id="f-insur" name="insuranceExpiresOn" type="date" value="' + esc(c.insuranceExpiresOn) + '"></div>' +
        '<div class="field"><label for="f-insp">최근 검사일</label>' +
          '<input id="f-insp" name="lastInspectionOn" type="date" value="' + esc(c.lastInspectionOn) + '"></div>' +
      '</div>' +
      '<button type="submit" class="btn">' + (isNew ? '등록하기' : '저장하기') + '</button>' +
      (!isNew ? '<button type="button" class="btn danger-outline" data-action="delete-car">이 차 삭제</button>' : '') +
      '</form></div>';
  }

  function handleCarForm(form) {
    var f = new FormData(form);
    var isNew = !state.editingCarId || !carById(state.editingCarId);
    var fuel = f.get('fuelType');
    var now = nowISO();
    var priceMan = numOrNull(f.get('purchasePriceMan'));

    var model = String(f.get('modelName') || '').trim();
    if (!model) { toast('차종명을 입력해 주세요'); return; }
    var odoKm = numOrNull(f.get('odometerKm'));
    if (isNew && odoKm == null) { toast('현재 주행거리를 입력해 주세요'); return; }

    var car;
    if (isNew) {
      car = {
        id: S.uuid(),
        createdAt: now,
        odometerLog: [{ date: todayISO(), km: odoKm }],
        enabledPartIds: D.defaultEnabledPartIds(data.parts.parts, fuel)
      };
      doc.cars.push(car);
    } else {
      car = carById(state.editingCarId);
      if (car.fuelType !== fuel) {
        // 연료 변경: 새 연료에도 해당되는 항목은 사용자의 켜고 끔을 보존하고,
        // 새로 적용되는 항목만 기본값으로 추가한다
        var applicableOld = D.applicableParts(data.parts.parts, car.fuelType).map(function (p) { return p.id; });
        var applicableNew = D.applicableParts(data.parts.parts, fuel).map(function (p) { return p.id; });
        var kept = car.enabledPartIds.filter(function (pid) { return applicableNew.indexOf(pid) !== -1; });
        D.defaultEnabledPartIds(data.parts.parts, fuel).forEach(function (pid) {
          if (applicableOld.indexOf(pid) === -1 && kept.indexOf(pid) === -1) kept.push(pid);
        });
        car.enabledPartIds = kept;
      }
    }
    car.nickname = String(f.get('nickname') || '').trim() || null;
    car.modelName = model;
    var matched = matchVehicle(model);
    car.vehicleId = matched ? matched.id : null;
    car.fuelType = fuel;
    car.displacementCc = fuel === 'ev' ? null : numOrNull(f.get('displacementCc'));
    car.firstRegisteredOn = f.get('firstRegisteredOn') || null;
    car.purchasePriceKrw = priceMan ? priceMan * 10000 : null;
    car.purchasedOn = f.get('purchasedOn') || null;
    car.insuranceExpiresOn = f.get('insuranceExpiresOn') || null;
    car.lastInspectionOn = f.get('lastInspectionOn') || null;
    car.updatedAt = now;

    persist();
    if (state.prefill) {
      // 프리필 등록 완료 — 주소의 파라미터 제거 (스펙: 등록 완료 후 replaceState)
      state.prefill = null;
      try { history.replaceState(null, '', location.pathname); } catch (e) { /* file:// 등 */ }
    }
    toast(isNew ? '등록했어요' : '저장했어요');
    go('dashboard', { carId: car.id });
  }

  // ----- 소모품 상세 -----

  function renderPartView() {
    var part = partById(state.partId);
    var car = activeCar();
    if (!part || !car) return renderDashboard();
    var today = todayISO();
    var monthlyKm = D.monthlyKmEstimate(car, doc.records, doc.fuelLogs);
    var st = D.partStatus(part, car, doc.records, doc.settings, today, monthlyKm);
    var odo = D.latestOdometer(car);

    var meta = [];
    if (part.intervalKm != null) meta.push(fmtKm(part.intervalKm) + '마다');
    if (part.intervalMonths != null) meta.push(part.intervalMonths + '개월마다');
    if (!meta.length) meta.push(part.type === 'refill' ? '떨어지면 보충' : '고장 시 교체');
    var price = part.priceKrw ? '참고가 ' + D.formatKrw(part.priceKrw.min) + '~' + D.formatKrw(part.priceKrw.max) : '';

    var history = doc.records.filter(function (r) {
      return r.carId === car.id && r.partId === part.id;
    }).sort(function (a, b) { return a.doneOn < b.doneOn ? 1 : -1; });

    return '<div class="form-view">' +
      '<button type="button" class="back-btn" data-action="go-dashboard">← 돌아가기</button>' +
      '<h1>' + esc(part.name) + ' <span class="badge ' + st.state + '">' + STATE_LABELS[st.state] + '</span></h1>' +
      '<div class="card"><h2>주기</h2><div>' + meta.join(' 또는 ') + (price ? ' · ' + price : '') + '</div>' +
        (part.note ? '<p class="notice">' + esc(part.note) + '</p>' : '') +
        ((st.dueDate || st.predictedDate) ?
          '<button type="button" class="btn small secondary" style="margin-top:10px;" data-action="export-ics-part" data-id="' + part.id + '">캘린더에 추가</button>' : '') +
      '</div>' +
      affiliateSlot(part) +
      '<div class="card"><h2>기록 추가</h2>' +
      '<form id="record-form">' +
        '<div class="field-row">' +
          '<div class="field"><label for="r-date">날짜</label><input id="r-date" name="doneOn" type="date" required value="' + today + '"></div>' +
          '<div class="field"><label for="r-odo">주행거리(km)</label>' +
            '<input id="r-odo" name="odometerKm" type="number" min="0" inputmode="numeric" value="' + (odo ? odo.km : '') + '"></div>' +
        '</div>' +
        '<div class="field-row">' +
          '<div class="field"><label for="r-cost">비용(원)</label><input id="r-cost" name="costKrw" type="number" min="0" inputmode="numeric" placeholder="선택"></div>' +
          '<div class="field"><label for="r-shop">정비소</label><input id="r-shop" name="shop" placeholder="선택"></div>' +
        '</div>' +
        '<div class="field"><label for="r-memo">메모</label><input id="r-memo" name="memo" placeholder="선택"></div>' +
        '<button type="submit" class="btn">저장</button>' +
      '</form></div>' +
      '<p class="section-title">이력 (' + history.length + ')</p>' +
      '<div class="card">' +
        (history.length ? history.map(function (r) {
          return '<div class="history-item"><div>' +
            '<div class="history-main">' + fmtDate(r.doneOn) +
              (r.odometerKm != null ? ' · ' + fmtKm(r.odometerKm) : '') +
              (r.costKrw != null ? ' · ' + D.formatKrw(r.costKrw) : '') + '</div>' +
            ((r.shop || r.memo) ? '<div class="history-sub">' + esc([r.shop, r.memo].filter(Boolean).join(' · ')) + '</div>' : '') +
          '</div><button type="button" class="history-del" data-action="del-record" data-id="' + r.id + '">삭제</button></div>';
        }).join('') : '<p class="empty">아직 기록이 없어요</p>') +
      '</div></div>';
  }

  function handleRecordForm(form) {
    var f = new FormData(form);
    var car = activeCar();
    var rec = {
      id: S.uuid(),
      carId: car.id,
      partId: state.partId,
      customLabel: null,
      doneOn: f.get('doneOn'),
      odometerKm: numOrNull(f.get('odometerKm')),
      costKrw: numOrNull(f.get('costKrw')),
      shop: String(f.get('shop') || '').trim() || null,
      memo: String(f.get('memo') || '').trim() || null,
      createdAt: nowISO()
    };
    var odo = D.latestOdometer(car);
    // 오타 방어: 주행거리가 한 번에 5만km 이상 점프하면 확인
    if (rec.odometerKm != null && odo && rec.odometerKm - odo.km > 50000 &&
        !confirm('주행거리가 마지막 기록보다 ' + fmtKm(rec.odometerKm - odo.km) + ' 늘었어요. 입력이 맞나요?')) {
      return;
    }
    doc.records.push(rec);
    // 새 주행거리 관측이면 주행거리도 함께 갱신 — 과거 날짜 기록은 로그 순서를 깨므로 제외
    if (rec.odometerKm != null && (!odo || (rec.doneOn >= odo.date && rec.odometerKm >= odo.km))) {
      appendOdometer(car, rec.doneOn, rec.odometerKm);
    }
    persist();
    toast('기록했어요');
    render();
  }

  function appendOdometer(car, date, km) {
    var log = car.odometerLog;
    var last = log.length ? log[log.length - 1] : null;
    if (last && date < last.date) return; // 배열은 날짜순 유지 (과거 관측점은 records가 담당)
    if (last && last.date === date) {
      last.km = km; // 같은 날짜는 마지막 값으로 대체 (docs/storage-schema.md에 명시된 예외)
    } else {
      log.push({ date: date, km: km });
    }
    car.updatedAt = nowISO();
  }

  // ----- 설정 -----

  function renderSettings() {
    var car = activeCar();
    var html = '<div class="form-view">' +
      '<button type="button" class="back-btn" data-action="go-dashboard">← 돌아가기</button>' +
      '<h1>설정</h1>';

    if (car) {
      var applicable = D.applicableParts(data.parts.parts, car.fuelType);
      var byCat = {};
      applicable.forEach(function (p) {
        (byCat[p.category] = byCat[p.category] || []).push(p);
      });
      html += '<p class="section-title">' + esc(car.nickname || car.modelName) + ' — 추적 항목</p>';
      Object.keys(byCat).forEach(function (cat) {
        html += '<div class="card"><h2>' + esc(data.parts.categories[cat] || cat) + '</h2>' +
          byCat[cat].map(function (p) {
            var on = car.enabledPartIds.indexOf(p.id) !== -1;
            return '<label class="toggle-row"><span>' + esc(p.name) + '</span>' +
              '<input type="checkbox" data-action="toggle-part" data-id="' + p.id + '"' + (on ? ' checked' : '') + '></label>';
          }).join('') + '</div>';
      });
    }

    html += '<p class="section-title">알림 기준</p>' +
      '<div class="card"><form id="settings-form">' +
      '<div class="field-row">' +
        '<div class="field"><label for="s-days">며칠 전부터 임박 표시</label>' +
          '<input id="s-days" name="reminderLeadDays" type="number" min="1" value="' + doc.settings.reminderLeadDays + '"></div>' +
        '<div class="field"><label for="s-km">몇 km 전부터 임박 표시</label>' +
          '<input id="s-km" name="reminderLeadKm" type="number" min="1" value="' + doc.settings.reminderLeadKm + '"></div>' +
      '</div><button type="submit" class="btn secondary">알림 기준 저장</button></form></div>';

    html += '<p class="section-title">데이터</p>' +
      '<div class="card">' +
        '<button type="button" class="btn secondary" data-action="export">JSON으로 내보내기 (백업)</button>' +
        '<button type="button" class="btn secondary" data-action="import">백업 가져오기</button>' +
        '<input type="file" id="import-file" accept="application/json,.json" style="display:none">' +
        '<button type="button" class="btn danger-outline" data-action="wipe">전체 데이터 삭제</button>' +
        '<p class="notice">기록은 이 브라우저에만 저장돼요. 기기를 바꾸거나 브라우저 데이터를 지우기 전에 꼭 백업해 두세요. ' +
        '일부 브라우저(아이폰 Safari 등)는 사이트를 오래 방문하지 않으면 저장 데이터를 자동 삭제할 수 있으니 주기적인 백업이 안전해요.</p>' +
      '</div></div>';
    return html;
  }

  // ---------- 이벤트 ----------

  function bindViewEvents() {
    var carForm = document.getElementById('car-form');
    if (carForm) {
      carForm.addEventListener('submit', function (e) { e.preventDefault(); handleCarForm(carForm); });
      // 차종 자동완성: 목록과 일치하면 배기량·연료 자동 채움
      var modelInput = document.getElementById('f-model');
      modelInput.addEventListener('change', function () {
        var v = matchVehicle(modelInput.value);
        if (!v) return;
        document.getElementById('f-fuel').value = v.fuelType;
        document.getElementById('f-cc').value = v.displacementCc != null ? v.displacementCc : '';
      });
    }

    var recForm = document.getElementById('record-form');
    if (recForm) recForm.addEventListener('submit', function (e) { e.preventDefault(); handleRecordForm(recForm); });

    var setForm = document.getElementById('settings-form');
    if (setForm) setForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var f = new FormData(setForm);
      doc.settings.reminderLeadDays = Math.max(1, numOrNull(f.get('reminderLeadDays')) || 30);
      doc.settings.reminderLeadKm = Math.max(1, numOrNull(f.get('reminderLeadKm')) || 1000);
      persist();
      toast('저장했어요');
    });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-action]');
    if (!btn) return;
    if (!doc) return; // 로딩 전·로드 실패 시 헤더·푸터의 정적 버튼 클릭 방어
    var action = btn.getAttribute('data-action');
    var id = btn.getAttribute('data-id');
    var car = activeCar();

    switch (action) {
      case 'go-dashboard': go('dashboard'); break;
      case 'go-settings': go('settings'); break;
      case 'new-car': go('car-form', { editingCarId: null }); break;
      case 'edit-car': go('car-form', { editingCarId: car && car.id }); break;
      case 'switch-car': go('dashboard', { carId: id }); break;
      case 'open-part': go('part', { partId: id }); break;

      case 'odo-form': {
        var slot = document.getElementById('odo-editor');
        var odo = D.latestOdometer(car);
        slot.innerHTML = '<form id="odo-update" class="field-row" style="margin-top:10px;">' +
          '<div class="field" style="margin:0;"><input name="km" type="number" inputmode="numeric" min="0" required ' +
          'placeholder="현재 계기판 km" value="' + (odo ? odo.km : '') + '"></div>' +
          '<button type="submit" class="btn small" style="align-self:stretch;">저장</button></form>';
        var of = document.getElementById('odo-update');
        of.querySelector('input').focus();
        of.addEventListener('submit', function (ev) {
          ev.preventDefault();
          var km = numOrNull(new FormData(of).get('km'));
          if (km == null) return;
          var latest = D.latestOdometer(car);
          if (latest && km < latest.km && !confirm('지금 주행거리(' + fmtKm(km) + ')가 마지막 기록(' + fmtKm(latest.km) + ')보다 작아요. 그래도 저장할까요?')) return;
          appendOdometer(car, todayISO(), km);
          persist();
          toast('갱신했어요');
          render();
        });
        break;
      }

      case 'toggle-part': {
        var idx = car.enabledPartIds.indexOf(id);
        if (idx === -1) car.enabledPartIds.push(id);
        else car.enabledPartIds.splice(idx, 1);
        car.updatedAt = nowISO();
        persist();
        break;
      }

      case 'del-record': {
        if (!confirm('이 기록을 삭제할까요?')) return;
        var deleted = null;
        doc.records = doc.records.filter(function (r) {
          if (r.id === id) { deleted = r; return false; }
          return true;
        });
        rollbackOdometerEntry(deleted); // 이 기록이 만든 주행거리 관측도 함께 롤백
        persist();
        toast('삭제했어요');
        render();
        break;
      }

      case 'quick-record': {
        var qOdo = D.latestOdometer(car);
        var qRec = {
          id: S.uuid(), carId: car.id, partId: id, customLabel: null,
          doneOn: todayISO(),
          odometerKm: qOdo ? qOdo.km : null,
          costKrw: null, shop: null, memo: null, createdAt: nowISO()
        };
        doc.records.push(qRec);
        // odometerLog에는 추가하지 않는다 — 계기판을 새로 읽은 게 아니라 마지막 값을 재사용한 것
        persist();
        render();
        toast('오늘 날짜로 기록했어요', {
          label: '취소',
          fn: function () {
            doc.records = doc.records.filter(function (r) { return r.id !== qRec.id; });
            persist();
            render();
          }
        });
        break;
      }

      case 'delete-car': {
        if (!confirm('차와 모든 기록을 삭제할까요? 되돌릴 수 없어요.')) return;
        var cid = state.editingCarId;
        doc.cars = doc.cars.filter(function (c) { return c.id !== cid; });
        doc.records = doc.records.filter(function (r) { return r.carId !== cid; });
        doc.fuelLogs = doc.fuelLogs.filter(function (r) { return r.carId !== cid; });
        persist();
        toast('삭제했어요');
        go('dashboard', { carId: null });
        break;
      }

      case 'dismiss-inapp':
        try { sessionStorage.setItem('chailji:inapp-dismissed', '1'); } catch (e2) { /* 무시 */ }
        render();
        break;

      case 'export-ics':
        downloadIcs(calendarEvents(car), 'chailji-calendar.ics');
        break;

      case 'export-ics-part': {
        var partEvents = calendarEvents(car).filter(function (ev) {
          return ev.uid.indexOf('-' + id + '@') !== -1;
        });
        downloadIcs(partEvents, 'chailji-' + id + '.ics');
        break;
      }

      case 'export': {
        var blob = new Blob([S.exportJson(doc)], { type: 'application/json' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'chailji-backup-' + todayISO() + '.json';
        a.click();
        // 즉시 해제하면 Firefox에서 다운로드 시작 전에 URL이 사라질 수 있다
        setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
        doc.settings.lastExportAt = nowISO();
        persist();
        toast('백업 파일을 내려받았어요');
        break;
      }

      case 'import': document.getElementById('import-file').click(); break;

      case 'wipe': {
        if (!confirm('모든 차와 기록을 삭제할까요? 백업하지 않았다면 되돌릴 수 없어요.')) return;
        doc = S.emptyDoc();
        persist();
        go('dashboard', { carId: null });
        break;
      }
    }
  });

  document.addEventListener('change', function (e) {
    if (e.target.id !== 'import-file' || !e.target.files.length) return;
    var reader = new FileReader();
    reader.onload = function () {
      var res = S.importJson(String(reader.result));
      if (res.error) { toast(res.error); return; }
      if (!confirm('백업을 가져오면 지금 데이터를 덮어써요. 계속할까요?')) return;
      doc = res.doc;
      persist();
      toast('가져왔어요');
      go('dashboard', { carId: null });
    };
    reader.readAsText(e.target.files[0]);
    e.target.value = '';
  });

  // ---------- 시연 데이터 (?demo=1 — 저장 안 함) ----------

  function demoDoc() {
    var t = todayISO();
    var d = S.emptyDoc();
    var carId = 'demo-car';
    d.cars.push({
      id: carId, nickname: null, modelName: '아반떼 1.6', vehicleId: 'avante-cn7-1.6',
      fuelType: 'gasoline', displacementCc: 1598,
      firstRegisteredOn: D.addMonths(t, -40), purchasePriceKrw: 23000000,
      purchasedOn: null, insuranceExpiresOn: D.addDays(t, 21), lastInspectionOn: null,
      odometerLog: [
        { date: D.addMonths(t, -40), km: 0 },
        { date: D.addMonths(t, -2), km: 41500 },
        { date: t, km: 43800 }
      ],
      enabledPartIds: D.defaultEnabledPartIds(window.__DEMO_PARTS__.parts, 'gasoline'),
      createdAt: nowISO(), updatedAt: nowISO()
    });
    d.records.push(
      { id: 'demo-r1', carId: carId, partId: 'engine-oil', customLabel: null, doneOn: D.addMonths(t, -3), odometerKm: 39000, costKrw: 85000, shop: '집앞 카센터', memo: null, createdAt: nowISO() },
      { id: 'demo-r2', carId: carId, partId: 'cabin-filter', customLabel: null, doneOn: D.addMonths(t, -9), odometerKm: 32000, costKrw: 12000, shop: null, memo: '직접 교체', createdAt: nowISO() },
      { id: 'demo-r3', carId: carId, partId: 'wiper', customLabel: null, doneOn: D.addMonths(t, -11), odometerKm: null, costKrw: 25000, shop: null, memo: null, createdAt: nowISO() }
    );
    return d;
  }

  // ---------- 초기화 ----------

  // 다른 탭이 저장하면 다시 읽어 반영 — 전체 문서 저장 방식이라 그대로 두면
  // 이 탭의 다음 저장이 다른 탭의 변경을 통째로 덮어쓴다
  window.addEventListener('storage', function (e) {
    if (e.key === S.KEY && !demoMode && doc) {
      doc = S.load();
      render();
    }
  });

  function init() {
    Promise.all(['data/parts.json', 'data/inspection.json', 'data/depreciation.json', 'data/vehicles.json', 'data/site.json', 'data/affiliate.json'].map(function (u) {
      return fetch(u).then(function (r) {
        if (!r.ok) throw new Error(u + ' 로드 실패(' + r.status + ')');
        return r.json();
      });
    })).then(function (res) {
      data.parts = res[0];
      data.inspection = res[1];
      data.depreciation = res[2];
      data.vehicles = res[3].vehicles.filter(function (v) { return v.status === 'active'; });
      data.site = res[4];
      data.affiliate = res[5];
      demoMode = /[?&]demo=1/.test(location.search);
      if (demoMode) {
        window.__DEMO_PARTS__ = data.parts;
        doc = demoDoc();
      } else {
        doc = S.load();
        // 브라우저의 저장 데이터 자동 정리(iOS Safari 등)로부터 보호 요청 — 실패해도 무해
        if (navigator.storage && navigator.storage.persist) {
          navigator.storage.persist().catch(function () {});
        }
      }
      // 세금 페이지에서 온 프리필 파라미터 (TASKS #2)
      var qs = new URLSearchParams(location.search);
      if (!demoMode && (qs.get('model') || qs.get('cc'))) {
        var slug = qs.get('model');
        var pv = slug ? data.vehicles.filter(function (v) { return v.slug === slug; })[0] : null;
        var prefill = {
          modelName: pv ? pv.name : (slug || ''),
          fuelType: qs.get('fuel') || (pv ? pv.fuelType : null) || 'gasoline',
          displacementCc: numOrNull(qs.get('cc')) || (pv ? pv.displacementCc : null),
          year: /^\d{4}$/.test(qs.get('year') || '') ? qs.get('year') : null
        };
        if (!doc.cars.length || confirm('이미 등록된 차가 있어요. 이 차를 새로 추가 등록할까요?')) {
          state.prefill = prefill;
          state.view = 'car-form';
          state.editingCarId = null;
          render();
          return;
        }
        try { history.replaceState(null, '', location.pathname); } catch (e) { /* 무시 */ }
      }

      // 첫 방문도 대시보드(hero 온보딩)로 — 가치 제안 없이 폼에 착지시키지 않는다
      state.view = 'dashboard';
      render();
      if (/[?&]debug=1/.test(location.search)) {
        var wide = [];
        document.querySelectorAll('*').forEach(function (el) {
          if (el.scrollWidth > document.documentElement.clientWidth) {
            wide.push(el.tagName + '.' + el.className + '=' + el.scrollWidth);
          }
        });
        var dbg = document.createElement('pre');
        dbg.id = 'debug-out';
        dbg.textContent = 'viewport=' + document.documentElement.clientWidth +
          ' docScroll=' + document.documentElement.scrollWidth + '\n' + wide.join('\n');
        document.body.appendChild(dbg);
      }
    }).catch(function (err) {
      $app.innerHTML = '<div class="hero"><h1>데이터를 불러오지 못했어요</h1>' +
        '<p>' + esc(err.message) + '<br>로컬에서는 <code>python3 -m http.server</code>로 열어주세요.</p></div>';
    });
  }

  init();
})();
