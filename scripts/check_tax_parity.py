#!/usr/bin/env python3
"""차일지 — 세액 계산 일치(패리티) 검사.

차종 페이지 표는 scripts/build.py(파이썬)가, 계산기·유지비 비교는 js/tax-calc.js(자바스크립트)가 계산한다.
둘 중 한쪽만 고치면 같은 차인데 페이지마다 세액이 달라진다 — 과거 '세액 오류' 수정이 여러 번 있었던 지점.
실제 data/tax-rates.json으로 양쪽을 돌려 결과가 한 원 단위까지 같은지 본다.

대상: vehicles.json의 모든 배기량 + 구간 경계값(999·1000·1001·1599·1600·1601·1998·1999·2000 …) × 차령 1~15,
      연납 공제(위 세액 전부 + 전기차 정액 + 승합·화물 정액).

사용법:  python3 scripts/check_tax_parity.py
JS 실행: node가 있으면 node, 없으면 macOS 기본 jsc. 둘 다 없으면 안내 후 건너뜀(CI에서는 실패).
build.py는 수정하지 않고 import만 한다 (main()은 __main__ 가드 안이라 import해도 빌드가 돌지 않는다).
Python 3.9 호환.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
from checklib import ROOT, NO_JS_RUNTIME_HELP, annotate, find_js_runtime, in_ci  # noqa: E402

AGES = list(range(1, 16))  # 페이지 표는 1~13, 경감 상한(50%) 이후도 같은지 넉넉히
FIXED_CC = [600, 799, 800, 998, 999, 1000, 1001, 1199, 1353, 1497, 1499, 1500, 1501, 1591, 1598, 1599, 1600,
            1601, 1995, 1998, 1999, 2000, 2001, 2497, 2999, 3000, 3470, 4999, 5000, 8000]
SHOW_MAX = 10

TAX_FIELDS = (("annual", "연세액"), ("base", "본세"), ("edu", "지방교육세"),
              ("perCc", "cc당 세율"), ("discountRate", "차령 경감률"))
PREPAY_FIELDS = (("pay", "연납 납부액"), ("discount", "연납 공제액"), ("rate", "공제율"), ("year", "공제율 기준 연도"),
                 ("fallback", "공제율 폴백 여부"))

JS_DRIVER = """
var T = globalThis.ChailjiTax;
var out = { ev: T.evTax(RATES), tax: [], prepay: [] };
for (var i = 0; i < CASES.length; i++) out.tax.push(T.taxFor(RATES, CASES[i][0], CASES[i][1]));
for (var y = 0; y < YEARS.length; y++)
  for (var j = 0; j < ANNUALS.length; j++) out.prepay.push(T.prepay(RATES, ANNUALS[j], YEARS[y]));
print(JSON.stringify(out));
"""


def collect_cases(rates):
    vehicles = build.load("vehicles.json")["vehicles"]
    ccs = set(FIXED_CC)
    for v in vehicles:
        cc = v.get("displacementCc")
        if isinstance(cc, int) and not isinstance(cc, bool) and cc > 0:
            ccs.add(cc)
    for b in rates["displacement"]["brackets"]:  # 세율표가 바뀌어도 새 경계를 따라간다
        if b.get("maxCc"):
            ccs.update((b["maxCc"] - 1, b["maxCc"], b["maxCc"] + 1))
    cases = [[cc, age] for cc in sorted(ccs) for age in AGES]

    annuals = {rates["displacement"]["ev"]["annualTotalKrw"], 0, 10, 100000, 100010}
    for s in rates.get("van", {}).get("sizes", []):
        annuals.update((s["nonBusinessKrw"], s["businessKrw"]))
    for b in rates.get("truck", {}).get("brackets", []):
        annuals.update((b["nonBusinessKrw"], b["businessKrw"]))
    for v in vehicles:  # 1만kg 초과 화물 가산분 등 실제 차종 정액
        if v.get("vehicleClass", "passenger") != "passenger":
            t = build.nonpassenger_tax(v, rates)
            if t:
                annuals.update((t["nonBusiness"], t["business"]))
    return cases, annuals, len(ccs)


def run_js(kind, exe, rates, cases, annuals, years):
    src = (
        "if (typeof print === 'undefined') { globalThis.print = function (s) { console.log(s); }; }\n"
        + (ROOT / "js" / "tax-calc.js").read_text(encoding="utf-8")
        + "\nvar RATES = " + json.dumps(rates, ensure_ascii=False) + ";\n"
        + "var CASES = " + json.dumps(cases) + ";\n"
        + "var ANNUALS = " + json.dumps(annuals) + ";\n"
        + "var YEARS = " + json.dumps(years) + ";\n"
        + JS_DRIVER
    )
    with tempfile.TemporaryDirectory(prefix="chailji-parity-") as tmp:
        path = Path(tmp) / "parity.js"
        path.write_text(src, encoding="utf-8")
        proc = subprocess.run([exe, str(path)], cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              encoding="utf-8")
    if proc.returncode != 0:
        print("js/tax-calc.js 실행 중 오류가 났어요 ({}):".format(kind))
        print((proc.stderr or proc.stdout).strip()[:2000])
        print("고치는 법: js/tax-calc.js에 문법 오류가 없는지 보세요. node tests/run.js tax-calc 로도 확인할 수 있어요.")
        return None
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    try:
        return json.loads(lines[-1])
    except (IndexError, ValueError):
        print("js/tax-calc.js 결과를 읽지 못했어요. 출력:\n" + proc.stdout[:1000])
        return None


def fmt(field, val):
    if field in ("annual", "base", "edu", "pay", "discount") and isinstance(val, (int, float)):
        return "{:,}원".format(val)
    return json.dumps(val, ensure_ascii=False)


def prepay_years(rates):
    """공제율이 있는 연도 전부 + 그 앞뒤(데이터에 없는 해 → 폴백 규칙)까지 비교한다."""
    keys = sorted(int(y) for y in rates["prepayDiscount"]["rateByYear"])
    return sorted(set(keys) | {keys[0] - 1, keys[-1] + 1})


def diff_fields(py, js, fields):
    out = []
    for key, label in fields:
        a, b = py.get(key), (js or {}).get(key)
        if a != b:
            out.append("{}: build.py {} / tax-calc.js {}".format(label, fmt(key, a), fmt(key, b)))
    return out


def main():
    rates = build.load("tax-rates.json")
    kind, exe = find_js_runtime()
    if not kind:
        print("세액 일치 검사를 건너뛰었어요 — 자바스크립트 실행기가 없어요.")
        print(NO_JS_RUNTIME_HELP)
        if in_ci():
            print("CI에서는 이 검사를 건너뛸 수 없어요 → 워크플로에 actions/setup-node 단계가 있는지 확인하세요.")
            return 1
        return 0

    cases, annual_set, n_cc = collect_cases(rates)
    py_tax = [build.tax_for(cc, age, rates) for cc, age in cases]
    annual_set.update(t["annual"] for t in py_tax)
    annuals = sorted(annual_set)

    years = prepay_years(rates)
    js = run_js(kind, exe, rates, cases, annuals, years)
    if js is None:
        return 1

    problems = []
    for (cc, age), py, jt in zip(cases, py_tax, js["tax"]):
        d = diff_fields(py, jt, TAX_FIELDS)
        if d:
            problems.append("배기량 {:,}cc · 차령 {}년차 — {}".format(cc, age, " · ".join(d)))
    py_prepay = [(y, a, build.prepay(a, rates, y)) for y in years for a in annuals]
    for (y, a, pp), jp in zip(py_prepay, js["prepay"]):
        d = diff_fields(pp, jp, PREPAY_FIELDS)
        if d:
            problems.append("{}년 기준 연세액 {:,}원의 1월 연납 — {}".format(y, a, " · ".join(d)))
    py_ev = rates["displacement"]["ev"]["annualTotalKrw"]  # build.py는 전기차 정액을 이 값 그대로 쓴다
    if js["ev"] != py_ev:
        problems.append("전기차 정액 — build.py {} / tax-calc.js {}".format(fmt("annual", py_ev), fmt("annual", js["ev"])))

    total = len(cases) + len(py_prepay) + 1
    print("비교: 배기량 {}종 × 차령 {}~{}년 = {}건, 연납 {}건(연도 {}), 전기차 정액 1건 ({} 사용)".format(
        n_cc, AGES[0], AGES[-1], len(cases), len(py_prepay), "·".join(map(str, years)), kind))
    if not problems:
        print("결과: {:,}건 모두 build.py와 js/tax-calc.js가 같은 값을 내요 — 통과".format(total))
        return 0

    print("")
    print("결과: {:,}건 중 {:,}건이 달라요 — 실패. 처음 {}건:".format(total, len(problems), min(SHOW_MAX, len(problems))))
    for p in problems[:SHOW_MAX]:
        print("  [불일치] " + p)
    annotate("error", "build.py와 js/tax-calc.js의 세액 계산이 {}건 달라요. 예: {}".format(len(problems), problems[0]),
             file="js/tax-calc.js", title="세액 계산 불일치")
    print("")
    print("고치는 법:")
    print("  - scripts/build.py의 tax_for·prepay와 js/tax-calc.js의 taxFor·prepay 중 한쪽만 바뀐 상태예요.")
    print("    두 파일의 계산 순서와 10원 미만 절사(floor10) 위치를 똑같이 맞추세요.")
    print("  - 세율 숫자를 바꾸려던 거라면 코드가 아니라 data/tax-rates.json만 고치세요 (양쪽이 같이 읽어요).")
    print("  - 다시 확인: python3 scripts/check_tax_parity.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
