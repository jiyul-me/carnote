/* 차일지 — GA4(gtag.js) 로더.
 * 측정 ID는 data/site.json의 ga4MeasurementId가 단일 출처 — 여기 하드코딩 금지.
 * 로드 실패는 조용히 무시한다 (방문 통계는 서비스 기능이 아니다). */
(function () {
  'use strict';
  fetch('/data/site.json')
    .then(function (r) { return r.json(); })
    .then(function (site) {
      // 측정 ID가 없거나 빈 값이면 태그를 아예 렌더하지 않는다
      var id = site.ga4MeasurementId && String(site.ga4MeasurementId).trim();
      if (!id) return;
      var s = document.createElement('script');
      s.async = true; // Core Web Vitals — 렌더 블로킹 없이 비동기 로드
      s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
      document.head.appendChild(s);
      window.dataLayer = window.dataLayer || [];
      function gtag() { window.dataLayer.push(arguments); }
      window.gtag = gtag;
      gtag('js', new Date());
      gtag('config', id);
    })
    .catch(function () { /* 무시 */ });
})();
