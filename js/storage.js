/* 차일지 — localStorage 단일 문서 저장 (docs/storage-schema.md 구현)
 * DOM 비의존. localStorage가 없는 환경(jsc)에서는 인메모리로 동작한다. */
(function (global) {
  'use strict';

  var KEY = 'chailji:v1';
  var BACKUP_PREFIX = 'chailji:backup:v'; // 마이그레이션 직전 1회 백업 (docs/storage-schema.md)
  var CURRENT_VERSION = 1;

  // v(n) → v(n+1) 마이그레이션 함수를 버전 키로 등록. 로드 시 순차 적용
  var migrations = {};

  var memoryStore = {}; // localStorage 부재 시(테스트) 폴백
  function backend() {
    try {
      if (typeof localStorage !== 'undefined') return localStorage;
    } catch (e) { /* 접근 차단(시크릿 모드 등) */ }
    return {
      getItem: function (k) { return Object.prototype.hasOwnProperty.call(memoryStore, k) ? memoryStore[k] : null; },
      setItem: function (k, v) { memoryStore[k] = String(v); },
      removeItem: function (k) { delete memoryStore[k]; }
    };
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
      settings: { reminderLeadDays: 30, reminderLeadKm: 1000, lastExportAt: null }
    };
  }

  // ----- 외부 입력 정규화 -----
  // 가져온 백업 파일은 신뢰할 수 없다. 숫자·날짜·id 필드의 타입을 강제해
  // innerHTML 경로의 저장형 XSS와 계산 오염을 차단한다.

  var DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
  var ID_RE = /^[A-Za-z0-9_.:-]+$/;
  var FUELS = ['gasoline', 'diesel', 'lpg', 'hybrid', 'ev'];

  function posInt(v) {
    var n = Number(v);
    return typeof v !== 'boolean' && v !== '' && v != null && isFinite(n) && n >= 0 ? Math.round(n) : null;
  }
  function dateStr(v) { return typeof v === 'string' && DATE_RE.test(v) ? v : null; }
  function idStr(v) { return typeof v === 'string' && v && ID_RE.test(v) ? v : uuid(); }
  function str(v) { return v == null ? null : String(v); }
  function arr(v) { return Array.isArray(v) ? v : []; }

  function sanitizeDoc(doc) {
    doc.cars = arr(doc.cars).filter(Boolean).map(function (c) {
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
        odometerLog: arr(c.odometerLog).filter(Boolean).map(function (e) {
          return { date: dateStr(e.date), km: posInt(e.km) };
        }).filter(function (e) { return e.date && e.km != null; }),
        enabledPartIds: arr(c.enabledPartIds).filter(function (id) {
          return typeof id === 'string' && ID_RE.test(id);
        }),
        createdAt: str(c.createdAt),
        updatedAt: str(c.updatedAt)
      };
    });
    doc.records = arr(doc.records).filter(Boolean).map(function (r) {
      return {
        id: idStr(r.id),
        carId: str(r.carId) || '',
        partId: r.partId == null ? null : String(r.partId),
        customLabel: str(r.customLabel),
        doneOn: dateStr(r.doneOn),
        odometerKm: posInt(r.odometerKm),
        costKrw: posInt(r.costKrw),
        shop: str(r.shop),
        memo: str(r.memo),
        createdAt: str(r.createdAt)
      };
    }).filter(function (r) { return r.doneOn; });
    doc.fuelLogs = arr(doc.fuelLogs).filter(Boolean).map(function (l) {
      return {
        id: idStr(l.id),
        carId: str(l.carId) || '',
        filledOn: dateStr(l.filledOn),
        odometerKm: posInt(l.odometerKm),
        amount: posInt(l.amount),
        unit: l.unit === 'kWh' ? 'kWh' : 'L',
        unitPriceKrw: posInt(l.unitPriceKrw),
        totalKrw: posInt(l.totalKrw),
        isFullTank: !!l.isFullTank,
        createdAt: str(l.createdAt)
      };
    }).filter(function (l) { return l.filledOn; });
    doc.settings = {
      reminderLeadDays: posInt(doc.settings.reminderLeadDays) || 30,
      reminderLeadKm: posInt(doc.settings.reminderLeadKm) || 1000,
      lastExportAt: str(doc.settings.lastExportAt)
    };
    return doc;
  }

  // 최소 형태 검증 — 가져오기(import)와 로드 공용
  function isValidDoc(doc) {
    return !!doc && typeof doc === 'object' &&
      typeof doc.schemaVersion === 'number' &&
      Array.isArray(doc.cars) && Array.isArray(doc.records) &&
      Array.isArray(doc.fuelLogs) &&
      !!doc.settings && typeof doc.settings === 'object';
  }

  function migrate(doc) {
    while (doc.schemaVersion < CURRENT_VERSION) {
      var fn = migrations[doc.schemaVersion];
      if (!fn) throw new Error('마이그레이션 없음: v' + doc.schemaVersion);
      backend().setItem(BACKUP_PREFIX + doc.schemaVersion, JSON.stringify(doc));
      doc = fn(doc);
      doc.schemaVersion += 1;
    }
    return doc;
  }

  // 손상 시 마이그레이션 백업 키에서 복구 시도 (최신 버전부터)
  function restoreFromBackups() {
    for (var v = CURRENT_VERSION; v >= 1; v--) {
      var raw = backend().getItem(BACKUP_PREFIX + v);
      if (raw == null) continue;
      try {
        var doc = JSON.parse(raw);
        if (isValidDoc(doc)) return migrate(sanitizeDoc(doc));
      } catch (e) { /* 다음 백업 시도 */ }
    }
    return null;
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
      backend().setItem(KEY + ':corrupt', raw);
      return restoreFromBackups() || emptyDoc();
    }
    if (doc.schemaVersion > CURRENT_VERSION) {
      // 미래 버전(다른 기기에서 만든 백업 가져오기 등) — 버전은 건드리지 않고 사용 시도
      return doc;
    }
    var fromVersion = doc.schemaVersion;
    doc = migrate(sanitizeDoc(doc));
    if (doc.schemaVersion !== fromVersion) save(doc); // 마이그레이션 결과 즉시 반영
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
    return { doc: migrate(sanitizeDoc(doc)) };
  }

  global.ChailjiStorage = {
    KEY: KEY,
    CURRENT_VERSION: CURRENT_VERSION,
    uuid: uuid,
    emptyDoc: emptyDoc,
    isValidDoc: isValidDoc,
    sanitizeDoc: sanitizeDoc,
    load: load,
    save: save,
    exportJson: exportJson,
    importJson: importJson,
    _migrations: migrations
  };
})(typeof window !== 'undefined' ? window : globalThis);
