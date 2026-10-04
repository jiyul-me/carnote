/* 차일지 — JS 테스트 러너 (node). tests/*.test.js를 전부 실행한다.
 *   node tests/run.js            전체
 *   node tests/run.js tax-calc   파일 이름에 'tax-calc'가 들어간 테스트만
 * 무엇을 로드할지는 각 테스트 파일 첫 줄 주석 'jsc 실행: jsc a.js b.js'에서 읽는다 (단일 출처).
 * 같은 테스트를 macOS jsc로도 그대로 돌릴 수 있어야 하므로, 테스트 파일에는 node 전용 기능(require 등)을 쓰지 않는다.
 * 파일마다 새 vm 컨텍스트(전역 오염 없음) + jsc 전역 print()를 console.log로 흉내 낸다.
 * 하나라도 예외로 끝나면 exit 1 → CI 실패. */
'use strict';

var fs = require('fs');
var path = require('path');
var vm = require('vm');

var ROOT = path.resolve(__dirname, '..');
var TEST_DIR = path.join(ROOT, 'tests');
var HEADER = /jsc 실행:\s*jsc\s+(.*)/; // scripts/checklib.py JSC_HEADER와 같은 규칙
var TIMEOUT_MS = 10000; // 무한 루프 방지

// 첫 줄 주석에서 로드 목록 추출. .js로 끝나지 않는 토큰(설명 괄호 등)에서 멈춘다
function loadList(testPath) {
  var first = fs.readFileSync(testPath, 'utf8').split('\n')[0];
  var m = HEADER.exec(first);
  if (!m) return null;
  var files = [];
  var toks = m[1].trim().split(/\s+/);
  for (var i = 0; i < toks.length; i++) {
    if (!/\.js$/.test(toks[i])) break;
    files.push(toks[i]);
  }
  return files.length ? files : null;
}

// 예외가 난 위치 ' (tests/x.test.js:52)' — 스택에서 저장소 파일을 가리키는 첫 줄
function errorLocation(e) {
  var lines = String((e && e.stack) || '').split('\n');
  for (var i = 0; i < lines.length; i++) {
    var m = /((?:js|tests)\/[\w.-]+\.js:\d+)/.exec(lines[i]);
    if (m) return ' (' + m[1] + ')';
  }
  return '';
}

// 반환: null(통과) 또는 실패 사유 문자열
function runOne(relTest) {
  var files = loadList(path.join(ROOT, relTest));
  if (!files) {
    return '첫 줄에 실행 방법 주석이 없어요.\n' +
      '  고치는 법: 파일 맨 첫 줄을 다음 형식으로 쓰세요 → /* jsc 실행: jsc js/대상.js ' + relTest + ' */';
  }
  if (files.indexOf(relTest) === -1) {
    return '첫 줄 로드 목록에 테스트 파일 자신(' + relTest + ')이 빠졌어요.\n' +
      '  고치는 법: 첫 줄 끝에 ' + relTest + '를 추가하세요 (jsc는 나열된 파일만 실행해요).';
  }
  var ctx = vm.createContext({
    print: function () { // 테스트 출력은 파일 이름 아래로 들여 쓴다
      console.log('  ' + Array.prototype.join.call(arguments, ' ').replace(/\n/g, '\n  '));
    },
    console: console
  });
  for (var i = 0; i < files.length; i++) {
    var f = files[i];
    var abs = path.join(ROOT, f);
    if (!fs.existsSync(abs)) {
      return '첫 줄이 가리키는 ' + f + ' 파일이 없어요.\n' +
        '  고치는 법: 파일 이름이 바뀌었다면 ' + relTest + ' 첫 줄 주석의 경로도 같이 고치세요.';
    }
    try {
      vm.runInContext(fs.readFileSync(abs, 'utf8'), ctx, { filename: f, timeout: TIMEOUT_MS });
    } catch (e) {
      var where = f === relTest ? '테스트가' : f + ' 로드 중';
      return where + ' 예외로 끝났어요: ' + String(e) + errorLocation(e);
    }
  }
  return null;
}

function main() {
  var filter = process.argv[2] || '';
  var tests = fs.readdirSync(TEST_DIR)
    .filter(function (n) { return /\.test\.js$/.test(n) && n.indexOf(filter) !== -1; })
    .sort()
    .map(function (n) { return 'tests/' + n; });
  if (!tests.length) {
    console.log('실행할 테스트가 없어요' + (filter ? " (이름에 '" + filter + "'가 들어간 파일 없음)" : '') + '.');
    process.exit(1);
  }

  var failed = [];
  tests.forEach(function (t) {
    console.log('· ' + t);
    var err = runOne(t);
    if (err) {
      failed.push(t);
      console.log('  실패 — ' + err);
    }
  });

  console.log('');
  if (!failed.length) {
    console.log('JS 테스트 ' + tests.length + '개 파일 모두 통과');
    return;
  }
  console.log('JS 테스트 실패: ' + failed.length + '/' + tests.length + '개 파일 — ' + failed.join(', '));
  console.log('고치는 법:');
  console.log("  - 위의 'FAIL' 줄에 '기대'와 '실제' 값이 나와요. js/ 계산 코드를 고쳤다면 그 결과가 의도한 것인지 확인하세요.");
  console.log('  - 세율·규칙이 실제로 바뀐 거라면 테스트의 기대값도 같이 고치세요 (data/*.json 값과 맞게).');
  console.log('  - 다시 확인: node tests/run.js ' + failed[0].replace(/^tests\//, '').replace(/\.test\.js$/, ''));
  process.exit(1);
}

main();
