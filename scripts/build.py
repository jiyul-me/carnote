#!/usr/bin/env python3
"""차일지 — 차종별 자동차세 정적 페이지 + sitemap 생성기.

이 머신에는 node가 없으므로 정적 생성은 Python으로 한다 (CLAUDE.md 기술 방향).
세율·차종 등 모든 수치는 data/*.json에서 읽는다 — 여기 하드코딩 금지.

사용법:  python3 scripts/build.py   (프로젝트 루트 기준 상대 경로로 동작)
출력:    tax/<slug>.html, tax/index.html, sitemap.xml(site.json에 baseUrl 있을 때만)
"""
import json
import html
import re
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "tax"

FUEL_LABELS = {"gasoline": "가솔린", "diesel": "디젤", "lpg": "LPG", "hybrid": "하이브리드", "ev": "전기"}


def load(name):
    with open(ROOT / "data" / name, encoding="utf-8") as f:
        return json.load(f)


def floor10(x):
    """지방세 단수 처리 관례에 맞춰 10원 미만 절사 (위택스 대조로 최종 확인)."""
    return int(x // 10 * 10)


def tax_for(cc, age, rates):
    """비영업용 승용 자동차세. age = 차령(1 = 신차 첫해). data/tax-rates.json 규칙 그대로."""
    d = rates["displacement"]
    per_cc = next(b["wonPerCc"] for b in d["brackets"] if b["maxCc"] is None or cc <= b["maxCc"])
    base = cc * per_cc
    aging = d["agingDiscount"]
    discount_rate = 0.0
    if age >= aging["startCarAge"]:
        discount_rate = min(aging["maxRate"], (age - aging["startCarAge"] + 1) * aging["ratePerYear"])
    base_after = floor10(base * (1 - discount_rate))
    edu = floor10(base_after * d["educationTaxRate"])
    annual = base_after + edu
    return {"perCc": per_cc, "discountRate": discount_rate, "base": base_after, "edu": edu, "annual": annual}


def prepay(annual, rates):
    """1월 연납 시 공제액·납부액. 공제율은 rateByYear의 가장 최근 연도."""
    p = rates["prepayDiscount"]
    year = max(p["rateByYear"].keys())
    rate = p["rateByYear"][year]
    pr = p["januaryProration"]
    discount = floor10(annual * pr["coveredMonths"] / pr["totalMonths"] * rate)
    return {"year": year, "rate": rate, "discount": discount, "pay": annual - discount}


def won(n):
    return f"{n:,}원"


def esc(s):
    return html.escape(str(s), quote=True)


def page_canonical(site, path):
    base = site.get("baseUrl", "").rstrip("/")
    return f"{base}/{path}" if base else None


def page(site, title, description, body, css_prefix="../", canonical=None):
    canonical_tag = ""
    if canonical:
        canonical_tag = (
            f'<link rel="canonical" href="{esc(canonical)}">\n  '
            f'<meta property="og:type" content="website">\n  '
            f'<meta property="og:site_name" content="{esc(site["siteName"])}">\n  '
            f'<meta property="og:title" content="{esc(title)}">\n  '
            f'<meta property="og:description" content="{esc(description)}">\n  '
            f'<meta property="og:url" content="{esc(canonical)}">\n  '
        )
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{esc(description)}">
  <meta name="theme-color" content="#FFFFFF">
  {canonical_tag}<title>{esc(title)}</title>
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%231A56DB'/%3E%3Ctext x='50' y='67' font-size='52' font-weight='700' text-anchor='middle' fill='%23FFFFFF' font-family='sans-serif'%3E차%3C/text%3E%3C/svg%3E">
  <link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
  <link rel="stylesheet" href="{css_prefix}css/style.css">
  <link rel="stylesheet" href="{css_prefix}css/content.css">
  <script src="{css_prefix}js/analytics.js" defer></script>
</head>
<body>
  <header class="topbar">
    <a class="topbar-title" href="{css_prefix}index.html">{esc(site["siteName"])}</a>
    <nav class="topbar-right topbar-nav">
      <a href="{css_prefix}tax/index.html">자동차세</a>
      <a href="{css_prefix}tco.html">유지비 비교</a>
    </nav>
  </header>
  <main class="content">
{body}
  </main>
  <footer class="foot">
    <p>{esc(site["siteName"])} (베타) — 계산 결과는 참고용이며, 실제 고지 세액은 위택스에서 확인하세요.</p>
    <p><a href="{css_prefix}privacy.html">개인정보처리방침</a> · <a href="{css_prefix}terms.html">이용약관</a></p>
  </footer>
</body>
</html>
"""


def jsonld_block(v, rates, site, this_year):
    """FAQPage + BreadcrumbList 구조화 데이터 (TASKS #9)."""
    base = site.get("baseUrl", "").rstrip("/")
    page_url = f"{base}/tax/{v['slug']}.html" if base else ""
    name = v["name"]
    if v["fuelType"] == "ev":
        ev = rates["displacement"]["ev"]
        annual = ev["annualTotalKrw"]
        faqs = [
            (f"{name} 자동차세는 얼마인가요?",
             f"전기차(비영업용 승용)는 배기량이 없어 연 {annual:,}원 정액입니다 (본세 {ev['baseKrw']:,}원 + 지방교육세 {ev['educationTaxKrw']:,}원). 연식과 무관하게 같습니다."),
            ("1월에 연납하면 얼마나 할인되나요?",
             f"1월에 연납 신청하면 2~12월분 세액의 {list(rates['prepayDiscount']['rateByYear'].values())[-1]*100:.0f}%를 공제받습니다. 연 {annual:,}원 기준 {prepay(annual, rates)['pay']:,}원을 냅니다."),
            ("전기차도 차령 경감이 되나요?",
             "아니요. 차령 경감은 배기량 기준 승용차에 적용되며, 전기차는 정액이라 연식이 지나도 세액이 같습니다."),
        ]
    else:
        t1 = tax_for(v["displacementCc"], 1, rates)
        t13 = tax_for(v["displacementCc"], 13, rates)
        p1 = prepay(t1["annual"], rates)
        faqs = [
            (f"{name} 자동차세는 얼마인가요?",
             f"배기량 {v['displacementCc']:,}cc 기준 신차는 연 {t1['annual']:,}원(본세+지방교육세)입니다. 3년차부터 차령 경감이 적용되어 12년 이상이면 연 {t13['annual']:,}원까지 줄어듭니다."),
            ("1월에 연납하면 얼마나 할인되나요?",
             f"1월 연납 시 2~12월분 세액의 {p1['rate']*100:.0f}%를 공제받습니다. 신차 기준 연 {t1['annual']:,}원에서 {p1['discount']:,}원을 공제받아 {p1['pay']:,}원을 냅니다."),
            ("차령 경감은 언제부터 적용되나요?",
             "최초 등록 후 3년차부터 (차령 − 2) × 5%씩 경감되고, 12년 이상이면 최대 50%가 경감됩니다."),
        ]
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faqs
        ],
    }
    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": site["siteName"], "item": f"{base}/" if base else "/"},
            {"@type": "ListItem", "position": 2, "name": "자동차세", "item": f"{base}/tax/index.html" if base else "/tax/index.html"},
            {"@type": "ListItem", "position": 3, "name": name, "item": page_url or f"/tax/{v['slug']}.html"},
        ],
    }
    return (
        '<script type="application/ld+json">' + json.dumps(faq, ensure_ascii=False) + "</script>\n"
        '<script type="application/ld+json">' + json.dumps(crumbs, ensure_ascii=False) + "</script>"
    )


def spec_box(v, site):
    """'한눈에' 미니 박스 (TASKS 개편 B). 연비·주행거리는 null이면 해당 줄 미노출 — 추정 금지."""
    rows = []
    if v["displacementCc"]:
        rows.append(("배기량", f"{v['displacementCc']:,}cc"))
    rows.append(("연료", FUEL_LABELS.get(v["fuelType"], v["fuelType"])))
    fe = v.get("fuelEconomy")
    is_ev = v["fuelType"] == "ev"
    if fe:
        rows.append(("공인연비", f"{fe}km/{'kWh' if is_ev else 'L'} (복합)"))
    if is_ev and v.get("rangeKm"):
        rows.append(("인증 주행거리", f"{v['rangeKm']:,}km (상온 복합)"))
    body = "".join(
        f'<div class="spec-row"><span class="spec-label">{a}</span><span>{b}</span></div>'
        for a, b in rows
    )
    fuel_line = ""
    prices = site.get("fuelPrices", {})
    basis_km = site.get("fuelCostBasisKm", 15000)
    price = prices.get("gasoline" if v["fuelType"] == "hybrid" else v["fuelType"])
    if fe and price:
        annual_cost = round(basis_km / fe * price)
        unit = "원/kWh" if is_ev else "원/L"
        fuel_line = (
            f'<div class="spec-fuel">공인연비 기준 연 {basis_km:,}km 주행 시 연료비 약 '
            f'<strong>{annual_cost:,}원</strong> <span>({price:,}{unit} 기준)</span></div>'
        )
    return f'<div class="card spec-box">{body}{fuel_line}</div>'


def notebook_cta(v):
    """세금 페이지 → 수첩 프리필 등록 CTA (TASKS #2). 연식 선택 시 JS가 &year= 추가."""
    params = f"model={v['slug']}&fuel={v['fuelType']}"
    if v["displacementCc"]:
        params += f"&cc={v['displacementCc']}"
    return f"""<div class="card" style="border-color:var(--accent);margin:18px 0;">
  <h2 style="margin-top:0;">이 차를 타고 계신가요?</h2>
  <p style="margin:6px 0 12px;">소모품 교체 주기·검사 D-day까지 수첩이 챙겨드려요. 차종·배기량은 미리 채워둘게요.</p>
  <a id="start-notebook" class="btn" style="display:block;text-align:center;text-decoration:none;" href="../index.html?{params}">이 차로 수첩 시작하기</a>
</div>
<a class="btn secondary" style="display:block;text-align:center;text-decoration:none;margin:0 0 12px;" href="../tco.html?car={v["slug"]}">이 차와 다른 차 유지비 비교하기</a>"""


def sources_block(rates):
    links = " · ".join(
        f'<a href="{esc(s["url"])}" rel="noopener" target="_blank">{esc(s["label"])}</a>'
        for s in rates["sources"]
    )
    this_year = datetime.date.today().year
    return (
        '<div class="sources"><p>근거 법령·출처: ' + links + "</p>"
        f"<p>{this_year}년 세율 기준 · 최종 확인 {rates['lastVerified']}. "
        "세액은 10원 미만 절사 기준으로 계산한 참고값입니다. 실제 고지서와 단수 차이가 있을 수 있어요.</p></div>"
    )


def table_img_script(v, site, this_year):
    base = site.get("baseUrl", "").rstrip("/")
    watermark = base.replace("https://", "").replace("http://", "") if base else site["siteName"]
    return (
        TABLE_IMG_SCRIPT
        .replace("__TITLE__", f"{v['name']} 자동차세")
        .replace("__META__", f"{v['displacementCc']:,}cc · {this_year}년 세율 기준 · 연납은 1월 신청 기준")
        .replace("__WATERMARK__", watermark)
        .replace("__SLUG__", v["slug"])
    )


def vehicle_page(v, rates, site, this_year):
    cc = v["displacementCc"]
    name = v["name"]
    fuel = FUEL_LABELS.get(v["fuelType"], v["fuelType"])
    crumb = '<p class="crumb"><a href="index.html">자동차세 계산</a> › ' + esc(name) + "</p>"

    if v["fuelType"] == "ev":
        ev = rates["displacement"]["ev"]
        annual = ev["annualTotalKrw"]
        pp = prepay(annual, rates)
        body = f"""{crumb}
<h1>{esc(name)} 자동차세</h1>
<p class="tax-caption">전기 · 비영업용 승용 · 연식 무관 정액</p>
<div class="tax-hero">연 {annual:,}원</div>
<p class="prepay-line">1월 연납 시 <span class="accent">{pp["pay"]:,}원</span> · {pp["discount"]:,}원 할인</p>
{spec_box(v, site)}
{notebook_cta(v)}
{sources_block(rates)}
<h2>계산 방법</h2>
<p>전기차는 지방세법상 "그 밖의 승용자동차"로 분류되어 배기량 기준 대신 정액(본세 {won(ev["baseKrw"])} + 지방교육세 {won(ev["educationTaxKrw"])})이 적용됩니다. 차령 경감도 적용되지 않습니다.</p>
<p>내연기관차와 유지비를 나란히 비교하려면 <a href="../tco.html">유지비 비교</a>를 써보세요.</p>
{jsonld_block(v, rates, site, this_year)}"""
        title = f"{name} 자동차세 — 연 {annual:,}원 고정 | {site['siteName']}"
        desc = f"{name} 자동차세는 연 {annual:,}원 고정(전기차 정액). 연납 할인과 계산 근거까지 정리했습니다."
        return page(site, title, desc, body, canonical=page_canonical(site, f"tax/{v['slug']}.html"))

    new_tax = tax_for(cc, 1, rates)
    new_prepay = prepay(new_tax["annual"], rates)

    rows = []
    for age in range(1, 14):
        t = tax_for(cc, age, rates)
        p = prepay(t["annual"], rates)
        label = f"{age}년차" + (" (신차)" if age == 1 else "") + (" 이상" if age == 13 else "")
        reg_year = this_year - age + 1
        rows.append(
            f'<tr id="age-{age}"><td>{label}<span style="color:var(--ink-muted);font-size:12px;"> · {reg_year}년 등록</span></td>'
            f"<td>{t['discountRate']*100:.0f}%</td><td>{won(t['annual'])}</td><td>{won(p['pay'])}</td></tr>"
        )
    table = (
        '<div class="table-wrap"><table class="data"><thead><tr>'
        "<th>차령</th><th>경감률</th><th>연세액</th><th>1월 연납 시</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )

    year_options = "".join(
        f'<option value="{y}">{y}년</option>' for y in range(this_year, this_year - 14, -1)
    )
    # DESIGN.md: 히어로 금액·연납 한 줄이 연식 선택에 반응한다 (별도 결과 카드 없음)
    picker = f"""<div class="year-picker">
  <label for="reg-year">우리 차 등록 연도</label>
  <select id="reg-year"><option value="">선택 (신차 기준)</option>{year_options}</select>
</div>
<script>
(function () {{
  var rows = {json.dumps({str(a): {"annual": tax_for(cc, a, rates)["annual"], "pay": prepay(tax_for(cc, a, rates)["annual"], rates)["pay"]} for a in range(1, 14)}, ensure_ascii=False)};
  window.__TAX_ROWS__ = rows; // 표 이미지 저장(#10)에서 재사용
  var sel = document.getElementById('reg-year');
  sel.addEventListener('change', function () {{
    document.querySelectorAll('tr.hl').forEach(function (r) {{ r.classList.remove('hl'); }});
    var age = sel.value ? Math.min(13, Math.max(1, {this_year} - Number(sel.value) + 1)) : 1;
    var d = rows[String(age)];
    document.getElementById('hero-amount').textContent = '연 ' + d.annual.toLocaleString('ko-KR') + '원';
    document.getElementById('prepay-line').innerHTML = '1월 연납 시 <span class="accent">' +
      d.pay.toLocaleString('ko-KR') + '원</span> · ' + (d.annual - d.pay).toLocaleString('ko-KR') + '원 할인';
    document.getElementById('tax-caption').textContent = '__CAPTION__ · ' +
      (sel.value ? sel.value + '년 등록 (' + age + '년차) 기준' : '신차 기준');
    if (sel.value) {{
      var row = document.getElementById('age-' + age);
      if (row) {{
        row.classList.add('hl');
        row.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
      }}
    }}
    var cta = document.getElementById('start-notebook');
    if (cta) {{
      var base = cta.getAttribute('href').split('&year=')[0];
      cta.setAttribute('href', sel.value ? base + '&year=' + sel.value : base);
    }}
  }});
}})();
</script>""".replace("__CAPTION__", f"{esc(fuel)} · {cc:,}cc · 비영업용 승용")

    aging = rates["displacement"]["agingDiscount"]
    # DESIGN.md 페이지 순서 고정: 브레드크럼 → 제목 → 히어로 금액 → 연납 한 줄 → 연식 select → 표 → primary CTA → 기준일 캡션
    body = f"""{crumb}
<h1>{esc(name)} 자동차세</h1>
<p class="tax-caption" id="tax-caption">{esc(fuel)} · {cc:,}cc · 비영업용 승용 · 신차 기준</p>
<div class="tax-hero" id="hero-amount">연 {new_tax["annual"]:,}원</div>
<p class="prepay-line" id="prepay-line">1월 연납 시 <span class="accent">{new_prepay["pay"]:,}원</span> · {new_prepay["discount"]:,}원 할인</p>
{spec_box(v, site)}
{picker}
{table}
<button type="button" class="btn secondary" id="save-table-img" style="margin-top:12px;">표를 이미지로 저장 (공유용)</button>
{table_img_script(v, site, this_year)}
{notebook_cta(v)}
{sources_block(rates)}
<h2>계산 방법</h2>
<p>본세 = 배기량 × cc당 세액({new_tax["perCc"]}원/cc 구간) → 차령 {aging["startCarAge"]}년차부터 (차령 − 2) × {aging["ratePerYear"]*100:.0f}% 경감(최대 {aging["maxRate"]*100:.0f}%) → 지방교육세 {rates["displacement"]["educationTaxRate"]*100:.0f}% 가산. 6월·12월에 절반씩 부과되며, 1월에 연납 신청하면 2~12월분의 {new_prepay["rate"]*100:.0f}%를 공제받아요.</p>
<p>차령은 대략 <em>올해 − 등록 연도 + 1</em>로 계산합니다.</p>
<p>차값·연료비·보험까지 묶어 보려면 <a href="../tco.html">유지비 비교</a>, 소모품·검사 일정 관리는 <a href="../index.html">내 차 수첩</a>에서.</p>
{jsonld_block(v, rates, site, this_year)}"""

    title = f"{name} 자동차세 — 연 {new_tax['annual']:,}원부터, 연식별 계산표 | {site['siteName']}"
    desc = (
        f"{name}({cc:,}cc) 자동차세는 신차 기준 연 {new_tax['annual']:,}원. "
        f"연식(차령)별 경감·1월 연납 할인까지 표로 정리했습니다."
    )
    return page(site, title, desc, body, canonical=page_canonical(site, f"tax/{v['slug']}.html"))


TABLE_IMG_SCRIPT = """<script>
(function () {
  var btn = document.getElementById('save-table-img');
  if (!btn) return;
  btn.addEventListener('click', function () {
    var rows = window.__TAX_ROWS__ || {};
    var scale = 2, W = 720, rowH = 42, headH = 96, footH = 54;
    var ages = Object.keys(rows);
    var H = headH + rowH * (ages.length + 1) + footH;
    var cv = document.createElement('canvas');
    cv.width = W * scale; cv.height = H * scale;
    var ctx = cv.getContext('2d');
    ctx.scale(scale, scale);
    var font = '-apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif';
    function won(n) { return n.toLocaleString('ko-KR') + '원'; }
    ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#1b2430'; ctx.font = '700 26px ' + font;
    ctx.fillText('__TITLE__', 24, 42);
    ctx.fillStyle = '#66707d'; ctx.font = '14px ' + font;
    ctx.fillText('__META__', 24, 68);
    var y = headH;
    ctx.fillStyle = '#f0f3f8'; ctx.fillRect(0, y - 28, W, rowH);
    ctx.fillStyle = '#66707d'; ctx.font = '700 14px ' + font;
    ctx.fillText('차령', 24, y);
    ctx.textAlign = 'right';
    ctx.fillText('연세액', 440, y);
    ctx.fillText('1월 연납 시', 690, y);
    ctx.textAlign = 'left';
    ages.forEach(function (age, i) {
      y += rowH;
      if (i % 2 === 1) { ctx.fillStyle = '#f7f9fc'; ctx.fillRect(0, y - 28, W, rowH); }
      ctx.fillStyle = '#1b2430'; ctx.font = '15px ' + font;
      ctx.fillText(age + '년차' + (age === '13' ? ' 이상' : ''), 24, y);
      ctx.textAlign = 'right'; ctx.font = '600 15px ' + font;
      ctx.fillText(won(rows[age].annual), 440, y);
      ctx.fillText(won(rows[age].pay), 690, y);
      ctx.textAlign = 'left';
    });
    ctx.fillStyle = '#9aa4b2'; ctx.font = '13px ' + font;
    ctx.textAlign = 'right';
    ctx.fillText('__WATERMARK__', W - 24, H - 22);
    ctx.textAlign = 'left';
    var a = document.createElement('a');
    a.href = cv.toDataURL('image/png');
    a.download = '__SLUG__-tax.png';
    a.click();
  });
})();
</script>"""


CALC_SCRIPT = """<script src="../js/tax-calc.js"></script>
<script>
(function () {
  var rates = null;
  fetch('../data/tax-rates.json').then(function (r) { return r.json(); }).then(function (j) { rates = j; render(); });
  function $(id) { return document.getElementById(id); }
  function won(n) { return n.toLocaleString('ko-KR') + '원'; }
  function render() {
    if (!rates) return;
    var T = window.ChailjiTax;
    var ev = $('calc-ev').checked;
    var cc = Number($('calc-cc').value);
    var card = $('calc-result');
    var tableWrap = $('calc-table');
    $('calc-cc').disabled = ev;
    if (!ev && (!isFinite(cc) || cc <= 0)) { card.hidden = true; tableWrap.innerHTML = ''; return; }
    var yearSel = $('calc-year').value;
    var thisYear = __THIS_YEAR__;
    var age = yearSel ? Math.min(13, Math.max(1, thisYear - Number(yearSel) + 1)) : 1;
    var annual, label;
    if (ev) {
      annual = T.evTax(rates);
      label = '전기차 정액 (연식 무관)';
      tableWrap.innerHTML = '';
    } else {
      cc = Math.round(cc);
      var t = T.taxFor(rates, cc, age);
      annual = t.annual;
      label = cc.toLocaleString('ko-KR') + 'cc · ' +
        (yearSel ? yearSel + '년 등록 · ' + age + '년차' + (age === 13 ? ' 이상' : '') : '신차 기준') +
        (t.discountRate ? ' · ' + Math.round(t.discountRate * 100) + '% 경감' : '');
      var rows = '';
      for (var a = 1; a <= 13; a++) {
        var ta = T.taxFor(rates, cc, a);
        var pa = T.prepay(rates, ta.annual);
        rows += '<tr' + (yearSel && a === age ? ' class="hl"' : '') + '><td>' + a + '년차' + (a === 13 ? ' 이상' : '') +
          '</td><td>' + Math.round(ta.discountRate * 100) + '%</td><td>' + won(ta.annual) + '</td><td>' + won(pa.pay) + '</td></tr>';
      }
      tableWrap.innerHTML = '<table class="data"><thead><tr><th>차령</th><th>경감률</th><th>연세액</th><th>1월 연납 시</th></tr></thead><tbody>' + rows + '</tbody></table>';
    }
    var p = T.prepay(rates, annual);
    $('cr-label').textContent = label;
    $('cr-amount').textContent = '연 ' + won(annual);
    $('cr-prepay').textContent = '1월 연납 시 ' + won(p.pay) + ' (' + won(p.discount) + ' 할인)';
    card.hidden = false;
  }
  document.addEventListener('input', render);
  document.addEventListener('change', render);
})();
</script>"""


def calculator_page(rates, site, this_year):
    year_options = "".join(
        f'<option value="{y}">{y}년</option>' for y in range(this_year, this_year - 14, -1)
    )
    d = rates["displacement"]
    bracket_rows = "".join(
        f"<tr><td>{'~' + format(b['maxCc'], ',') + 'cc' if b['maxCc'] else format(d['brackets'][i-1]['maxCc'], ',') + 'cc 초과'}</td>"
        f"<td>{b['wonPerCc']}원/cc</td></tr>"
        for i, b in enumerate(d["brackets"])
    )
    body = f"""<p class="crumb"><a href="index.html">자동차세 계산</a> › 계산기</p>
<h1>자동차세 계산기</h1>
<p class="lede">배기량(cc)과 등록 연도만 넣으면 자동차세와 1월 연납액을 바로 계산해요. 비영업용 승용 기준.</p>
<div class="card">
  <div class="field-row">
    <div class="field"><label for="calc-cc">배기량(cc)</label>
      <input id="calc-cc" type="number" min="0" inputmode="numeric" placeholder="예: 1998"></div>
    <div class="field"><label for="calc-year">등록 연도</label>
      <select id="calc-year"><option value="">선택 안 함 (신차 기준)</option>{year_options}</select></div>
  </div>
  <label class="toggle-row" style="border:none;padding-bottom:0;"><span>전기차예요 (배기량 없음 — 정액)</span><input type="checkbox" id="calc-ev" style="width:20px;height:20px;"></label>
  <p class="notice">배기량은 자동차등록증에서 확인할 수 있어요.</p>
</div>
<div class="card year-result-card" id="calc-result" hidden>
  <div class="label" id="cr-label"></div>
  <div class="amount" id="cr-amount"></div>
  <div class="label" id="cr-prepay"></div>
</div>
<div class="table-wrap" id="calc-table"></div>
<h2>세율표</h2>
<div class="table-wrap"><table class="data"><thead><tr><th>배기량 구간</th><th>cc당 세액</th></tr></thead><tbody>{bracket_rows}
<tr><td>전기차</td><td>연 {won(d["ev"]["annualTotalKrw"])} 고정</td></tr></tbody></table></div>
<p>여기에 지방교육세 {d["educationTaxRate"]*100:.0f}%가 붙고, 3년차부터 차령 경감(연 5%p, 최대 50%)이 적용됩니다.
  내 차종의 연식별 표는 <a href="index.html">차종별 페이지</a>에서 볼 수 있어요.</p>
{sources_block(rates)}
{CALC_SCRIPT.replace("__THIS_YEAR__", str(this_year))}"""
    title = f"자동차세 계산기 — 배기량·연식으로 바로 계산 | {site['siteName']}"
    desc = "배기량(cc)과 등록 연도만 넣으면 자동차세 연세액·1월 연납 할인액을 계산합니다. 차령 경감·전기차 정액 반영."
    return page(site, title, desc, body, canonical=page_canonical(site, "tax/calculator.html"))


def index_page(vehicles, rates, site):
    by_brand = {}
    for v in vehicles:
        by_brand.setdefault(v["brand"], []).append(v)

    def new_car_annual(v):
        if v["fuelType"] == "ev":
            return rates["displacement"]["ev"]["annualTotalKrw"]
        return tax_for(v["displacementCc"], 1, rates)["annual"]

    # 펼침 표시용 단색 라인 chevron (DESIGN: stroke 1.5, currentColor)
    chevron = (
        '<svg class="chevron" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">'
        '<path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="1.5" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )

    # 브랜드 → 모델 그룹(modelFamily) → 트림. JS 없이 <details> 기본 동작만 사용 —
    # 접힌 상태에서도 모든 트림 링크가 HTML에 존재한다 (SEO 크롤링 통로)
    sections = []
    for brand, items in by_brand.items():
        groups = {}
        for v in items:
            groups.setdefault(v["modelFamily"], []).append(v)
        rows = []
        for family, trims in groups.items():
            if len(trims) == 1:
                v = trims[0]
                rows.append(
                    f'<li><a class="hub-row" href="{esc(v["slug"])}.html">'
                    f'<span>{esc(v["name"])}</span><span class="hub-price">연 {new_car_annual(v):,}원</span></a></li>'
                )
            else:
                min_tax = min(new_car_annual(v) for v in trims)
                trim_rows = "".join(
                    f'<li><a class="hub-trim" href="{esc(v["slug"])}.html">'
                    f'<span>{esc(v["name"])}</span><span class="hub-price">연 {new_car_annual(v):,}원</span></a></li>'
                    for v in trims
                )
                rows.append(
                    f'<li><details class="hub-group"><summary class="hub-row">'
                    f'<span>{esc(family)}</span>'
                    f'<span class="hub-right"><span class="hub-price">연 {min_tax:,}원부터</span>{chevron}</span>'
                    f'</summary><ul class="hub-trims">{trim_rows}</ul></details></li>'
                )
        sections.append(f'<p class="brand-title">{esc(brand)}</p><ul class="hub-list">{"".join(rows)}</ul>')

    d = rates["displacement"]
    bracket_rows = "".join(
        f"<tr><td>{'~' + format(b['maxCc'], ',') + 'cc' if b['maxCc'] else format(d['brackets'][i-1]['maxCc'], ',') + 'cc 초과'}</td>"
        f"<td>{b['wonPerCc']}원/cc</td></tr>"
        for i, b in enumerate(d["brackets"])
    )
    body = f"""<h1>차종별 자동차세 계산</h1>
<p class="lede">배기량과 연식만으로 정해지는 자동차세, 차종별로 미리 계산해 뒀습니다. 비영업용 승용 기준.</p>
<div class="table-wrap"><table class="data"><thead><tr><th>배기량 구간</th><th>cc당 세액</th></tr></thead><tbody>{bracket_rows}
<tr><td>전기차</td><td>연 {won(d["ev"]["annualTotalKrw"])} 고정</td></tr></tbody></table></div>
<p>여기에 지방교육세 {d["educationTaxRate"]*100:.0f}%가 붙고, 3년차부터 차령 경감(연 5%p, 최대 50%)이 적용됩니다.</p>
<p class="notice">차종 옆 금액은 신차 기준 연세액 — 연식이 오래될수록 줄어들어요.</p>
{"".join(sections)}
<p style="margin-top:24px;">찾는 차종이 없나요? <a href="calculator.html">자동차세 계산기</a>에서 배기량만 넣으면 바로 계산할 수 있어요.</p>
{sources_block(rates)}"""
    title = f"차종별 자동차세 계산 — 연식별 세액·연납 할인 | {site['siteName']}"
    desc = "아반떼·그랜저·쏘렌토 등 인기 차종의 자동차세를 연식별로 계산. cc당 세율, 차령 경감, 연납 할인까지."
    return page(site, title, desc, body, canonical=page_canonical(site, "tax/index.html"))


def build_sitemap(site, slugs):
    base = site.get("baseUrl", "").rstrip("/")
    if not base:
        print("· site.json baseUrl이 비어 있어 sitemap.xml 생성을 건너뜁니다 (도메인 확정 후 재실행)")
        return
    today = datetime.date.today().isoformat()
    urls = [
        f"{base}/",
        f"{base}/tco.html",
        f"{base}/privacy.html",
        f"{base}/terms.html",
        f"{base}/tax/index.html",
        f"{base}/tax/calculator.html",
    ] + [f"{base}/tax/{s}.html" for s in slugs]
    items = "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>\n'
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"· sitemap.xml ({len(urls)}개 URL)")
    # robots.txt의 Sitemap 줄을 baseUrl 기준으로 동기화 (URL 단일 출처 규칙)
    robots = ROOT / "robots.txt"
    if robots.exists():
        txt = robots.read_text(encoding="utf-8")
        new = re.sub(r"(?m)^Sitemap: .*$", f"Sitemap: {base}/sitemap.xml", txt)
        if new != txt:
            robots.write_text(new, encoding="utf-8")
            print("· robots.txt Sitemap 줄 동기화")


def main():
    site = load("site.json")
    rates = load("tax-rates.json")
    vehicles = [v for v in load("vehicles.json")["vehicles"] if v["status"] == "active"]
    this_year = datetime.date.today().year

    OUT_DIR.mkdir(exist_ok=True)
    slugs = []
    for v in vehicles:
        out = OUT_DIR / f"{v['slug']}.html"
        out.write_text(vehicle_page(v, rates, site, this_year), encoding="utf-8")
        slugs.append(v["slug"])
    (OUT_DIR / "index.html").write_text(index_page(vehicles, rates, site), encoding="utf-8")
    (OUT_DIR / "calculator.html").write_text(calculator_page(rates, site, this_year), encoding="utf-8")
    print(f"· tax/ 페이지 {len(slugs)}개 + index + calculator 생성")
    build_sitemap(site, slugs)


if __name__ == "__main__":
    main()
