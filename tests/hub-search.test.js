/* jsc 실행: jsc js/hub-search.js tests/hub-search.test.js
 * 허브 검색의 정규화·매칭 순수 함수. JS 테스트는 vehicles.json을 읽을 수 없으므로 색인(data-q)은
 * scripts/build.py search_index()가 만드는 모양을 인라인 고정 문자열로 둔다 — 정규화 토큰을 '|'로 이은 것.
 * 실데이터 건수('그랜저 ig' 8건, '아반테' 가족 전체, '포르쉐' 0건)는 Playwright 완료 기준에서 확인한다. */
(function () {
  'use strict';
  var S = globalThis.ChailjiHubSearch;
  var failures = 0, total = 0;
  function eq(a, b, label) {
    total++;
    if (a !== b) { failures++; print('FAIL ' + label + '\n  기대: ' + b + '\n  실제: ' + a); }
  }

  // 정규화: 소문자, 공백(탭·줄바꿈 포함)과 '|' 제거
  eq(S.normalize(' 그랜저 IG '), '그랜저ig', '공백·대문자');
  eq(S.normalize('K5\t1세대\n'), 'k51세대', '탭·줄바꿈');
  eq(S.normalize('그랜저|ig'), '그랜저ig', "질의의 '|'는 지운다 (토큰 경계 흉내 방지)");
  eq(S.normalize(''), '', '빈 문자열');
  eq(S.normalize(null), '', 'null');
  eq(S.normalize(undefined), '', 'undefined');

  // build.py search_index 모양의 색인 (이름, 브랜드, 모델, 세대, 브랜드+모델, 모델+세대, 브랜드+이름, 별칭…, 가족 공통 별칭…)
  var IG = '그랜저ig2.4|현대|그랜저|ig|현대그랜저|그랜저ig|현대그랜저ig2.4|grandeur|그랜져';
  var IG_FL = '더뉴그랜저ig3.0lpi|현대|그랜저|igf/l|현대그랜저|그랜저igf/l|현대더뉴그랜저ig3.0lpi|더뉴그랜저lpg|grandeur|그랜져';
  var HG = '그랜저hg2.4|현대|그랜저|hg|현대그랜저|그랜저hg|현대그랜저hg2.4|grandeur|그랜져';
  var GN7 = '그랜저2.5가솔린|현대|그랜저|gn7|현대그랜저|그랜저gn7|현대그랜저2.5가솔린|grandeur|그랜져';
  var AVANTE = '아반떼1.6가솔린|현대|아반떼|cn7|현대아반떼|아반떼cn7|현대아반떼1.6가솔린|avante|아반테';
  var AVANTE_MD = '아반떼md1.6|현대|아반떼|md|현대아반떼|아반떼md|현대아반떼md1.6|avante|아반테';
  var AVANTE_N = '아반떼n|현대n|아반떼n|cn7|현대n아반떼n|아반떼ncn7|현대n아반떼n';
  var ALL = [IG, IG_FL, HG, GN7, AVANTE, AVANTE_MD, AVANTE_N];

  // 공백·대소문자와 무관하게 부분일치
  eq(S.matches(IG, S.normalize('그랜저 IG')), true, "'그랜저 IG' → IG 트림");
  eq(S.matches(IG, S.normalize('그랜저ig')), true, "'그랜저ig' → IG 트림");
  eq(S.matches(IG, S.normalize('GRANDEUR')), true, '영문 대문자 별칭');
  eq(S.matches(IG_FL, S.normalize('그랜저 ig')), true, "'그랜저 ig' → 더 뉴 그랜저 IG(F/L)도 포함");

  // '그랜저ig'가 HG·GN7 색인과 섞이지 않는다 — 가족 공통 별칭('그랜저')과 다음 토큰이 이어 붙어도 경계를 넘지 않음
  eq(S.matches(HG, S.normalize('그랜저 ig')), false, "'그랜저 ig'에 HG가 섞이지 않음");
  eq(S.matches(GN7, S.normalize('그랜저 ig')), false, "'그랜저 ig'에 GN7이 섞이지 않음");
  eq(S.matches('그랜저|ig', S.normalize('그랜저ig')), false, '토큰 경계를 넘는 일치 없음');
  eq(S.filter(ALL, '그랜저 ig').join(','), '0,1', "'그랜저 ig' → IG 두 줄만");
  eq(S.filter(ALL, 'hg').join(','), '2', "'hg' → HG만");

  // 가족 공통 별칭(오타 '아반테')은 가족 전 트림에, 다른 가족(아반떼 N)에는 없다
  eq(S.filter(ALL, '아반테').join(','), '4,5', "'아반테' → 아반떼 가족 전 트림");
  eq(S.filter(ALL, '아반떼').join(','), '4,5,6', "'아반떼' → 아반떼 N 포함");
  eq(S.filter(ALL, ' 현대  그랜저 ').join(','), '0,1,2,3', "'현대 그랜저' → 그랜저 전 세대");

  // 결과 없음·빈 질의
  eq(S.filter(ALL, '포르쉐').length, 0, "'포르쉐' → 0건");
  eq(S.filter(ALL, '').length, ALL.length, '빈 질의 → 전부');
  eq(S.filter(ALL, '   ').length, ALL.length, '공백만 → 전부');
  eq(S.matches(null, 'a'), false, '색인 없음');
  eq(S.matches('', ''), true, '빈 색인·빈 질의');

  // 칩·브레드크럼 href와 location.hash에서 대상 id 꺼내기 — 검색 중 칩을 결과 있는 브랜드 것만 남길 때 쓴다
  eq(S.hashId('#brand-gia'), 'brand-gia', '칩 href');
  eq(S.hashId('index.html#model-grandeur'), 'model-grandeur', '브레드크럼 href');
  eq(S.hashId('#%EA%B8%B0%EC%95%84'), '기아', '퍼센트 인코딩 해제');
  eq(S.hashId('#%E0%A4%A'), '', '깨진 인코딩 → 빈 값');
  eq(S.hashId('#'), '', '빈 해시');
  eq(S.hashId(''), '', '빈 문자열');
  eq(S.hashId('calculator.html'), '', '# 없음');
  eq(S.hashId(null), '', 'null');

  print(failures === 0 ? '통과: ' + total + '/' + total : '실패: ' + failures + '/' + total);
  if (failures > 0) throw new Error(failures + '개 실패');
})();
