/* 차일지 — localStorage 단일 문서 저장 (docs/storage-schema.md 구현)
 * DOM 비의존. localStorage가 없는 환경(jsc)에서는 인메모리로 동작한다. */
(function (global) {
  'use strict';

  var NS = 'chailji:';                   // 이 앱이 localStorage에 쓰는 키의 공통 접두사 (전체 삭제 범위)
  var KEY = 'chailji:v1';
  var CORRUPT_KEY = KEY + ':corrupt';    // 형태 검증에 실패한 원본 보존 (수동 복구용)
  var BACKUP_PREFIX = 'chailji:backup:v'; // 마이그레이션 직전 1회 백업 (docs/storage-schema.md)
  // 마이그레이션 백업 보존 기간. 새 버전의 마이그레이션 결함은 며칠 안에 드러나므로 그동안만 손상 복구에 쓰고,
  // 지난 뒤에는 로드 때 지운다 — 몇 달 묵은 스냅샷을 조용히 되살리는 것도 데이터 손실이다
  var BACKUP_KEEP_DAYS = 30;
  var CURRENT_VERSION = 2;
  // 주행거리 관측의 출처 중 '사용자가 직접 입력'(차 등록·갱신 버튼). 기록 id와 겹치지 않게 id로는 쓰지 못하게 한다
  var ODO_MANUAL = 'manual';
  var ODO_PREV_MAX = 10; // 같은 날 덮어쓴 이전 값은 최근 이만큼만 보관

  // v(n) → v(n+1) 마이그레이션 함수를 버전 키로 등록. 로드 시 순차 적용.
  // 마이그레이션은 원본(정규화 전) 구조에 적용되므로 필드가 없거나 타입이 틀려도 죽지 않게 쓴다
  var migrations = {
    // v1 → v2: 주유 외 지출(세차·주차·통행료·자동차세·기타) 기록 배열 추가
    1: function (doc) {
      if (!Array.isArray(doc.expenses)) doc.expenses = [];
      return doc;
    }
  };

  var memoryStore = {}; // localStorage 부재 시(테스트) 폴백
  var memoryBackend = {
    getItem: function (k) { return Object.prototype.hasOwnProperty.call(memoryStore, k) ? memoryStore[k] : null; },
    setItem: function (k, v) { memoryStore[k] = String(v); },
    removeItem: function (k) { delete memoryStore[k]; }
  };
  function backend() {
    try {
      if (typeof localStorage !== 'undefined') return localStorage;
    } catch (e) { /* 접근 차단(시크릿 모드 등) */ }
    return memoryBackend;
  }

  // 이 앱의 키 목록 (NS 접두사). 지우는 동안 목록이 바뀌지 않게 먼저 모은다
  function ownKeys(prefix) {
    var b = backend();
    var all = [];
    if (b === memoryBackend) {
      all = Object.keys(memoryStore);
    } else {
      for (var i = 0; i < b.length; i++) {
        var k = b.key(i);
        if (k != null) all.push(k);
      }
    }
    return all.filter(function (k) { return k.indexOf(prefix || NS) === 0; });
  }

  function uuid() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
    return 'id-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
  }

  function emptyDoc() {
    return {
      schemaVersion: CURRENT_VERSION,
      cars: [],
      records: [],
      fuelLogs: [],
      expenses: [],
      settings: { reminderLeadDays: 30, reminderLeadKm: 1000, lastExportAt: null }
    };
  }

  // ----- 외부 입력 정규화 -----
  // 가져온 백업 파일은 신뢰할 수 없다. 숫자·날짜·id 필드의 타입을 강제해
  // innerHTML 경로의 저장형 XSS와 계산 오염을 차단한다.

  var DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
  var ID_RE = /^[A-Za-z0-9_.:-]+$/;
  var FUELS = ['gasoline', 'diesel', 'lpg', 'hybrid', 'ev'];
  // 주유·충전량 단위: L(휘발유·경유·LPG), kWh(전기), kg(수소). 차의 에너지원으로 기본값을 정하지만
  // 기록마다 저장해 자기완결적으로 둔다 (docs/storage-schema.md FuelLog.unit)
  var UNITS = ['L', 'kWh', 'kg'];

  // 숫자·숫자 문자열만 받는다 (Number([])=0, Number(' ')=0 같은 암묵 변환 차단)
  function nonNeg(v) {
    var ok = typeof v === 'number' || (typeof v === 'string' && v.trim() !== '');
    var n = ok ? Number(v) : NaN;
    return isFinite(n) && n >= 0 ? n : null;
  }
  function posInt(v) {
    var n = nonNeg(v);
    return n == null ? null : Math.round(n);
  }
  // 소수 허용 (주유량 L·kWh, 전기 단가 347.2원/kWh 등) — 소수 둘째 자리까지
  function posNum(v) {
    var n = nonNeg(v);
    return n == null ? null : Math.round(n * 100) / 100;
  }
  function dateStr(v) { return typeof v === 'string' && DATE_RE.test(v) ? v : null; }
  // ODO_MANUAL은 주행거리 관측 출처의 예약어라 객체 id로 쓰지 않는다 (겹치면 그 기록 삭제가 수동 관측을 지운다)
  function idStr(v) { return typeof v === 'string' && v && ID_RE.test(v) && v !== ODO_MANUAL ? v : uuid(); }
  function odoBy(v) { return typeof v === 'string' && v && ID_RE.test(v) ? v : null; }
  function obj(v) { return !!v && typeof v === 'object'; }
  // 주행거리 관측 한 개: {date, km} + 선택 필드 by(이 값을 쓴 출처) · prev(같은 날 이 값에 덮어써진 이전 값들, 오래된 것부터)
  function odoEntry(e) {
    var out = { date: dateStr(e.date), km: posInt(e.km) };
    var by = odoBy(e.by);
    if (by) out.by = by;
    var prev = arr(e.prev).filter(obj).map(function (p) {
      var q = { km: posInt(p.km) };
      var pb = odoBy(p.by);
      if (pb) q.by = pb;
      return q;
    }).filter(function (p) { return p.km != null; }).slice(-ODO_PREV_MAX);
    if (prev.length) out.prev = prev;
    return out;
  }
  // 다른 객체를 가리키는 id(carId): 형식이 틀리면 재발급하지 않고 비운다 (어느 차에도 붙지 않음)
  function refStr(v) { return typeof v === 'string' && ID_RE.test(v) ? v : ''; }
  function str(v) { return v == null ? null : String(v); }
  function arr(v) { return Array.isArray(v) ? v : []; }
  // 같은 id가 둘이면 삭제 한 번에 둘 다 지워진다 — 뒤의 것을 재발급
  function uniqueIds(list) {
    var seen = Object.create(null);
    list.forEach(function (x) {
      if (x.id in seen) x.id = uuid();
      seen[x.id] = true;
    });
    return list;
  }

  function sanitizeDoc(doc) {
    // 차도 중복 id 재발급 — 남겨 두면 차 전환 칩이 같은 차만 가리키고, '이 차 삭제'가 두 대와 그 기록을 함께 지운다.
    // 기록의 carId는 그대로이므로 겹치던 id의 기록은 앞의 차에 남는다
    doc.cars = uniqueIds(arr(doc.cars).filter(Boolean).map(function (c) {
      return {
        id: idStr(c.id),
        nickname: str(c.nickname),
        modelName: str(c.modelName) || '',
        vehicleId: str(c.vehicleId),
        fuelType: FUELS.indexOf(c.fuelType) !== -1 ? c.fuelType : 'gasoline',
        displacementCc: posInt(c.displacementCc),
        firstRegisteredOn: dateStr(c.firstRegisteredOn),
        purchasePriceKrw: posInt(c.purchasePriceKrw),
        purchasedOn: dateStr(c.purchasedOn),
        insuranceExpiresOn: dateStr(c.insuranceExpiresOn),
        lastInspectionOn: dateStr(c.lastInspectionOn),
        odometerLog: arr(c.odometerLog).filter(obj).map(odoEntry)
          .filter(function (e) { return e.date && e.km != null; }),
        enabledPartIds: arr(c.enabledPartIds).filter(function (id) {
          return typeof id === 'string' && ID_RE.test(id);
        }),
        createdAt: str(c.createdAt),
        updatedAt: str(c.updatedAt)
      };
    }));
    doc.records = uniqueIds(arr(doc.records).filter(Boolean).map(function (r) {
      return {
        id: idStr(r.id),
        carId: refStr(r.carId),
        partId: r.partId == null ? null : String(r.partId),
        customLabel: str(r.customLabel),
        doneOn: dateStr(r.doneOn),
        odometerKm: posInt(r.odometerKm),
        costKrw: posInt(r.costKrw),
        shop: str(r.shop),
        memo: str(r.memo),
        createdAt: str(r.createdAt)
      };
    }).filter(function (r) { return r.doneOn; }));
    doc.fuelLogs = uniqueIds(arr(doc.fuelLogs).filter(Boolean).map(function (l) {
      return {
        id: idStr(l.id),
        carId: refStr(l.carId),
        filledOn: dateStr(l.filledOn),
        odometerKm: posInt(l.odometerKm),     // 선택 — 주유소에서 계기판을 못 봤을 수 있다
        amount: posNum(l.amount),             // 선택 — 금액만 아는 주유('5만원어치')
        unit: UNITS.indexOf(l.unit) !== -1 ? l.unit : 'L',
        unitPriceKrw: posNum(l.unitPriceKrw),
        totalKrw: posInt(l.totalKrw),
        isFullTank: l.isFullTank === true,
        createdAt: str(l.createdAt)
      };
    }).filter(function (l) { return l.filledOn; }));
    doc.expenses = uniqueIds(arr(doc.expenses).filter(function (e) {
      return e && typeof e === 'object';
    }).map(function (e) {
      return {
        id: idStr(e.id),
        carId: refStr(e.carId),
        spentOn: dateStr(e.spentOn),
        // 분류 목록은 data/expense-categories.json(화면 층)에 있다 — 저장 층은 형식만 검사,
        // 모르는 id는 화면에서 '기타'로 표시된다
        category: typeof e.category === 'string' && ID_RE.test(e.category) ? e.category : null,
        amountKrw: posInt(e.amountKrw),
        memo: str(e.memo),
        createdAt: str(e.createdAt)
      };
    }).filter(function (e) { return e.spentOn && e.amountKrw != null; }));
    var settings = doc.settings && typeof doc.settings === 'object' ? doc.settings : {};
    doc.settings = {
      reminderLeadDays: posInt(settings.reminderLeadDays) || 30,
      reminderLeadKm: posInt(settings.reminderLeadKm) || 1000,
      lastExportAt: str(settings.lastExportAt)
    };
    return doc;
  }

  // 최소 형태 검증 — 가져오기(import)와 로드 공용.
  // v1부터 있던 필드만 요구한다: v2의 expenses는 구버전 백업에 없으므로 마이그레이션·정규화가 채운다
  function isValidDoc(doc) {
    return !!doc && typeof doc === 'object' &&
      typeof doc.schemaVersion === 'number' &&
      doc.schemaVersion % 1 === 0 && doc.schemaVersion >= 1 && // 0·1.5·Infinity는 마이그레이션 체인에 없다
      Array.isArray(doc.cars) && Array.isArray(doc.records) &&
      Array.isArray(doc.fuelLogs) &&
      !!doc.settings && typeof doc.settings === 'object';
  }

  // skipBackup: 가져오기 미리보기처럼 아직 확정되지 않은 문서는 백업 키를 덮어쓰지 않는다.
  // 백업은 {backupAt, doc} — 보존 기간(BACKUP_KEEP_DAYS) 판단용 시각을 함께 둔다
  function migrate(doc, skipBackup) {
    while (doc.schemaVersion < CURRENT_VERSION) {
      var fn = migrations[doc.schemaVersion];
      if (!fn) throw new Error('마이그레이션 없음: v' + doc.schemaVersion);
      if (!skipBackup) {
        backend().setItem(BACKUP_PREFIX + doc.schemaVersion,
          JSON.stringify({ backupAt: new Date().toISOString(), doc: doc }));
      }
      doc = fn(doc);
      doc.schemaVersion += 1;
    }
    return doc;
  }

  // 마이그레이션(원본 구조) → 정규화(현재 구조) 순서. 거꾸로 하면 정규화가 옛 필드를 지운 뒤라
  // 이름이 바뀌는 류의 마이그레이션이 옮길 값을 잃는다
  function upgrade(doc, skipBackup) {
    return sanitizeDoc(migrate(doc, skipBackup));
  }

  // 백업 키 값 해석: {backupAt, doc} 또는 시각 없이 문서만 쓰던 형식(초기 v2 빌드). 못 읽으면 null
  function readBackup(raw) {
    var parsed = null;
    try { parsed = JSON.parse(raw); } catch (e) { return null; }
    if (obj(parsed) && typeof parsed.backupAt === 'string' && obj(parsed.doc)) {
      return { backupAt: parsed.backupAt, doc: parsed.doc };
    }
    return obj(parsed) ? { backupAt: null, doc: parsed } : null;
  }

  // 손상 시 마이그레이션 백업 키에서 복구 시도 (최신 버전부터)
  function restoreFromBackups() {
    for (var v = CURRENT_VERSION; v >= 1; v--) {
      var raw = backend().getItem(BACKUP_PREFIX + v);
      if (raw == null) continue;
      var b = readBackup(raw);
      try {
        if (b && isValidDoc(b.doc)) return upgrade(b.doc, true);
      } catch (e) { /* 다음 백업 시도 */ }
    }
    return null;
  }

  // 보존 기간이 지난 마이그레이션 백업 삭제. 시각 없는 옛 형식은 지금부터 기간을 센다(지금 시각으로 다시 감싼다).
  // 본 문서가 정상으로 읽힌 로드에서만 부른다 — 손상 복구에 쓸 수 있는 동안은 지우지 않는다
  function pruneBackups(nowMs) {
    var now = nowMs == null ? Date.now() : nowMs;
    ownKeys(BACKUP_PREFIX).forEach(function (k) {
      var b = readBackup(backend().getItem(k));
      if (!b) { backend().removeItem(k); return; }
      if (b.backupAt == null) {
        backend().setItem(k, JSON.stringify({ backupAt: new Date(now).toISOString(), doc: b.doc }));
        return;
      }
      var at = Date.parse(b.backupAt);
      if (!isFinite(at) || now - at > BACKUP_KEEP_DAYS * 86400000) backend().removeItem(k);
    });
  }

  // 마이그레이션 백업과 손상 원본 보존 키 삭제 (본 문서는 그대로).
  // 차 삭제·가져오기처럼 데이터를 지우거나 통째로 바꾼 뒤 옛 스냅샷이 남아 되살아나지 않게
  function clearBackups() {
    ownKeys(BACKUP_PREFIX).forEach(function (k) { backend().removeItem(k); });
    backend().removeItem(CORRUPT_KEY);
  }

  // '전체 데이터 삭제' — 본 문서·마이그레이션 백업·손상 원본 등 이 앱의 키(NS 접두사)를 전부 지운다
  function wipeAll() {
    ownKeys(NS).forEach(function (k) { backend().removeItem(k); });
  }

  function load() {
    var raw = backend().getItem(KEY);
    if (raw == null) return emptyDoc();
    var doc = null;
    try {
      doc = JSON.parse(raw);
    } catch (e) { doc = null; }
    if (!isValidDoc(doc)) {
      // 손상 원본 보존 → 백업 복구 시도 → 실패 시 빈 문서 (schema 문서의 복구 정책)
      backend().setItem(CORRUPT_KEY, raw);
      return restoreFromBackups() || emptyDoc();
    }
    if (doc.schemaVersion > CURRENT_VERSION) {
      // 미래 버전(새 버전 앱이 같은 브라우저에 저장한 뒤 캐시된 옛 앱이 열린 경우 등) —
      // 버전 번호는 그대로 두고 아는 필드만 정규화해 사용한다(모르는 최상위 필드는 보존).
      // 원문 그대로 쓰면 저장형 XSS 방어와 화면이 기대하는 배열 보장이 빠진다.
      // 백업 정리는 새 버전 앱의 정책에 맡긴다
      return sanitizeDoc(doc);
    }
    var fromVersion = doc.schemaVersion;
    try {
      doc = upgrade(doc, false);
    } catch (e) {
      backend().setItem(CORRUPT_KEY, raw);
      return restoreFromBackups() || emptyDoc();
    }
    if (doc.schemaVersion !== fromVersion) save(doc); // 마이그레이션 결과 즉시 반영
    try { pruneBackups(); } catch (e) { /* 정리 실패(저장 공간 부족 등)는 다음 로드에 다시 */ }
    return doc;
  }

  function save(doc) {
    backend().setItem(KEY, JSON.stringify(doc));
  }

  function exportJson(doc) {
    return JSON.stringify(doc, null, 2);
  }

  // 성공 시 {doc}, 실패 시 {error: 메시지}
  function importJson(text) {
    var doc = null;
    try {
      doc = JSON.parse(text);
    } catch (e) {
      return { error: 'JSON 형식이 아닙니다' };
    }
    if (!isValidDoc(doc)) return { error: '차일지 백업 파일이 아닙니다' };
    if (doc.schemaVersion > CURRENT_VERSION) return { error: '더 새로운 버전의 백업입니다. 앱을 업데이트한 뒤 가져와 주세요' };
    try {
      // 구버전 백업은 현재 버전으로 올려서 돌려준다. 사용자가 덮어쓰기를 확정하기 전이라 백업 키는 건드리지 않음
      return { doc: upgrade(doc, true) };
    } catch (e) {
      return { error: '백업 파일을 변환할 수 없습니다' };
    }
  }

  global.ChailjiStorage = {
    KEY: KEY,
    CURRENT_VERSION: CURRENT_VERSION,
    BACKUP_KEEP_DAYS: BACKUP_KEEP_DAYS,
    ODO_MANUAL: ODO_MANUAL,
    ODO_PREV_MAX: ODO_PREV_MAX,
    UNITS: UNITS,
    uuid: uuid,
    emptyDoc: emptyDoc,
    isValidDoc: isValidDoc,
    sanitizeDoc: sanitizeDoc,
    load: load,
    save: save,
    clearBackups: clearBackups,
    wipeAll: wipeAll,
    pruneBackups: pruneBackups,
    exportJson: exportJson,
    importJson: importJson,
    _keys: function () { return ownKeys(NS); },
    _backend: backend,
    _migrations: migrations
  };
})(typeof window !== 'undefined' ? window : globalThis);
