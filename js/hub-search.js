/* 차일지 — 차종 허브(tax/index.html) 검색.
 * 색인(data-q)은 scripts/build.py search_index()가 만든다: 정규화한 이름·브랜드·모델·세대·별칭·가족 공통 별칭을 '|'로 이은 문자열.
 * 정규화·매칭 순수 함수는 globalThis.ChailjiHubSearch로 노출한다(tests/hub-search.test.js — jsc·node vm).
 * DOM 코드는 document가 있을 때만 돈다. JS가 꺼지면 검색창은 hidden 그대로이고 목록은 모두 보인다. */
(function (root) {
  'use strict';

  // 소문자 + 공백·'|' 제거 (build.py search_norm과 같은 규칙). 질의에 '|'가 남지 않으므로 토큰 경계를 넘는 일치가 없다
  function normalize(s) {
    return String(s == null ? '' : s).toLowerCase().replace(/[\s|]+/g, '');
  }

  // index: '|'로 이은 정규화 토큰, q: normalize된 질의. 빈 질의는 모두 일치
  function matches(index, q) {
    if (!q) return true;
    return String(index == null ? '' : index).indexOf(q) !== -1;
  }

  // 색인 목록에서 질의와 일치하는 위치 — 테스트·디버깅용
  function filter(indexes, query) {
    var q = normalize(query), out = [];
    for (var i = 0; i < indexes.length; i++) if (matches(indexes[i], q)) out.push(i);
    return out;
  }

  // '#brand-gia'·'index.html#model-k5' → 'brand-gia'·'model-k5' (퍼센트 인코딩 해제). #가 없거나 깨진 인코딩이면 ''
  function hashId(href) {
    var s = String(href == null ? '' : href), i = s.indexOf('#');
    if (i === -1) return '';
    try { return decodeURIComponent(s.slice(i + 1)); } catch (e) { return ''; }
  }

  root.ChailjiHubSearch = { normalize: normalize, matches: matches, filter: filter, hashId: hashId };

  if (typeof document === 'undefined') return;

  function each(list, fn) { Array.prototype.forEach.call(list, fn); }

  // 주소의 #id가 접힌 details 안(또는 details 자신)이면 연다 — 브레드크럼·칩 링크(Safari 폴백, Chromium은 자동으로도 열림)
  function openHashTarget() {
    var id = hashId(location.hash);
    if (!id) return;
    var el = document.getElementById(id);
    if (!el || !el.closest) return;
    var opened = false, d = el.closest('details');
    while (d) {
      if (!d.open) { d.open = true; opened = true; }
      d = d.parentElement ? d.parentElement.closest('details') : null;
    }
    if (opened && el.scrollIntoView) el.scrollIntoView();
  }

  function init() {
    var box = document.querySelector('.hub-search');
    var input = document.getElementById('hub-q');
    if (!box || !input) return;
    var status = document.getElementById('hub-status');
    var empty = document.getElementById('hub-empty');
    var brands = document.querySelectorAll('.hub-brand');
    // 브랜드 칩 — 검색 중에는 결과가 있는 브랜드의 칩만 남긴다(숨은 구획을 가리키는 칩은 눌러도 아무 일이 없다)
    var chipBox = document.querySelector('.brand-chips');
    var chips = [];
    if (chipBox) {
      each(chipBox.querySelectorAll('a[href*="#"]'), function (a) {
        var target = document.getElementById(hashId(a.getAttribute('href')));
        var sec = target && target.closest ? target.closest('.hub-brand') : null;
        if (sec) chips.push([a, sec]);
      });
    }
    var saved = null; // 검색 시작 전 details 열림 상태 — 입력을 비우면 되돌린다
    box.hidden = false;

    function restore() {
      each(document.querySelectorAll('.hub-brand[hidden], .hub-brand li[hidden], .brand-chips [hidden]'),
        function (el) { el.hidden = false; });
      if (chipBox) chipBox.hidden = false;
      if (saved) saved.forEach(function (s) { s[0].open = s[1]; });
      saved = null;
      if (status) status.textContent = '';
      if (empty) empty.hidden = true;
    }

    function run() {
      var q = normalize(input.value);
      if (!q) { restore(); return; }
      if (!saved) {
        saved = [];
        each(document.querySelectorAll('.hub-brand details'), function (d) { saved.push([d, d.open]); });
      }
      var total = 0;
      each(brands, function (sec) {
        var shown = 0;
        each(sec.querySelectorAll('[data-q]'), function (a) {
          var ok = matches(a.getAttribute('data-q'), q);
          a.parentNode.hidden = !ok;
          if (ok) shown++;
        });
        each(sec.querySelectorAll('.hub-gen'), function (li) { li.hidden = true; }); // 세대 라벨은 검색 중 숨김
        each(sec.querySelectorAll('details'), function (d) {
          var hit = false;
          each(d.querySelectorAll('[data-q]'), function (a) { if (!a.parentNode.hidden) hit = true; });
          d.parentNode.hidden = !hit;
          if (hit) d.open = true;
        });
        sec.hidden = shown === 0;
        total += shown;
      });
      chips.forEach(function (c) { c[0].hidden = c[1].hidden; });
      if (chipBox) chipBox.hidden = total === 0; // 결과 0건이면 칩 줄 자체를 접는다
      if (status) status.textContent = total ? '검색 결과 ' + total + '개' : '검색 결과가 없어요';
      if (empty) empty.hidden = total > 0;
    }

    input.addEventListener('input', run);
    if (input.value) run(); // 뒤로가기로 돌아와 입력값이 복원된 경우
  }

  init();
  openHashTarget();
  window.addEventListener('hashchange', openHashTarget);
})(typeof globalThis !== 'undefined' ? globalThis : this);
