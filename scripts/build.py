#!/usr/bin/env python3
"""카노트 — 차종별 자동차세 정적 페이지 + sitemap 생성기.

이 머신에는 node가 없으므로 정적 생성은 Python으로 한다 (CLAUDE.md 기술 방향).
세율·차종 등 모든 수치는 data/*.json에서 읽는다 — 여기 하드코딩 금지.

사용법:  python3 scripts/build.py   (프로젝트 루트 기준 상대 경로로 동작)
출력:    tax/<slug>.html, tax/index.html, sitemap.xml(site.json에 baseUrl 있을 때만)
"""
import json
import html
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


def page(site, title, description, body, css_prefix="../", canonical=None):
    canonical_tag = f'<link rel="canonical" href="{esc(canonical)}">\n  ' if canonical else ""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{esc(description)}">
  <meta name="theme-color" content="#1a56db">
  {canonical_tag}<title>{esc(title)}</title>
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E🚗%3C/text%3E%3C/svg%3E">
  <link rel="stylesheet" href="{css_prefix}css/style.css">
  <link rel="stylesheet" href="{css_prefix}css/content.css">
</head>
<body>
  <header class="topbar">
    <a class="topbar-title" href="{css_prefix}index.html">🚗 {esc(site["siteName"])}</a>
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


def notebook_cta(v):
    """세금 페이지 → 수첩 프리필 등록 CTA (TASKS #2). 연식 선택 시 JS가 &year= 추가."""
    params = f"model={v['slug']}&fuel={v['fuelType']}"
    if v["displacementCc"]:
        params += f"&cc={v['displacementCc']}"
    return f"""<div class="card" style="border-color:var(--brand);margin:18px 0;">
  <h2 style="margin-top:0;">이 차를 타고 계신가요?</h2>
  <p style="margin:6px 0 12px;">소모품 교체 주기·검사 D-day까지 수첩이 챙겨드려요. 차종·배기량은 미리 채워둘게요.</p>
  <a id="start-notebook" class="btn" style="display:block;text-align:center;text-decoration:none;" href="../index.html?{params}">이 차로 수첩 시작하기</a>
</div>"""


def sources_block(rates):
    links = " · ".join(
        f'<a href="{esc(s["url"])}" rel="noopener" target="_blank">{esc(s["label"])}</a>'
        for s in rates["sources"]
    )
    return (
        '<div class="sources"><p>근거 법령·출처: ' + links + "</p>"
        "<p>세액은 10원 미만 절사 기준으로 계산한 참고값입니다. 실제 고지서와 단수 차이가 있을 수 있어요.</p></div>"
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
<p class="lede">전기차(비영업용 승용)는 배기량이 없어 자동차세가 <strong>연 {won(annual)} 고정</strong>입니다 (본세 {won(ev["baseKrw"])} + 지방교육세 {won(ev["educationTaxKrw"])}). 연식과 무관하게 같아요.</p>
<div class="tax-summary">
  <div class="card"><div class="label">연세액</div><div class="amount">{won(annual)}</div></div>
  <div class="card"><div class="label">1월 연납 시 ({esc(pp["year"])}년 공제율 {pp["rate"]*100:.0f}%)</div><div class="amount">{won(pp["pay"])}</div><div class="label">{won(pp["discount"])} 할인</div></div>
</div>
<h2>계산 방법</h2>
<p>전기차는 지방세법상 "그 밖의 승용자동차"로 분류되어 배기량 기준 대신 정액이 적용됩니다. 차령 경감도 적용되지 않습니다.</p>
{notebook_cta(v)}
<p>내연기관차와 유지비를 나란히 비교하려면 <a href="../tco.html">유지비 비교</a>를 써보세요.</p>
{sources_block(rates)}"""
        title = f"{name} 자동차세 — 연 {annual:,}원 고정 | {site['siteName']}"
        desc = f"{name} 자동차세는 연 {annual:,}원 고정(전기차 정액). 연납 할인과 계산 근거까지 정리했습니다."
        return page(site, title, desc, body)

    new_tax = tax_for(cc, 1, rates)
    new_prepay = prepay(new_tax["annual"], rates)

    rows = []
    for age in range(1, 14):
        t = tax_for(cc, age, rates)
        p = prepay(t["annual"], rates)
        label = f"{age}년차" + (" (신차)" if age == 1 else "") + (" 이상" if age == 13 else "")
        reg_year = this_year - age + 1
        rows.append(
            f'<tr id="age-{age}"><td>{label}<span style="color:var(--text-dim);font-size:12px;"> · {reg_year}년 등록</span></td>'
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
    picker = f"""<div class="year-picker">
  <label for="reg-year">우리 차 등록 연도:</label>
  <select id="reg-year"><option value="">선택</option>{year_options}</select>
</div>
<div class="card year-result-card" id="year-result-card" hidden>
  <div class="label" id="yr-label"></div>
  <div class="amount" id="yr-amount"></div>
  <div class="label" id="yr-prepay"></div>
</div>
<script>
(function () {{
  var rows = {json.dumps({str(a): {"annual": tax_for(cc, a, rates)["annual"], "pay": prepay(tax_for(cc, a, rates)["annual"], rates)["pay"]} for a in range(1, 14)}, ensure_ascii=False)};
  var sel = document.getElementById('reg-year');
  sel.addEventListener('change', function () {{
    var card = document.getElementById('year-result-card');
    document.querySelectorAll('tr.hl').forEach(function (r) {{ r.classList.remove('hl'); }});
    if (!sel.value) {{ card.hidden = true; return; }}
    var age = Math.min(13, Math.max(1, {this_year} - Number(sel.value) + 1));
    var d = rows[String(age)];
    document.getElementById('yr-label').textContent = sel.value + '년 등록 · ' + age + '년차' + (age === 13 ? ' 이상' : '');
    document.getElementById('yr-amount').textContent = '연 ' + d.annual.toLocaleString('ko-KR') + '원';
    document.getElementById('yr-prepay').textContent = '1월 연납 시 ' + d.pay.toLocaleString('ko-KR') + '원';
    card.hidden = false;
    var row = document.getElementById('age-' + age);
    if (row) {{
      row.classList.add('hl');
      row.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
    }}
    var cta = document.getElementById('start-notebook');
    if (cta) {{
      var base = cta.getAttribute('href').split('&year=')[0];
      cta.setAttribute('href', sel.value ? base + '&year=' + sel.value : base);
    }}
  }});
}})();
</script>"""

    aging = rates["displacement"]["agingDiscount"]
    body = f"""{crumb}
<h1>{esc(name)} 자동차세</h1>
<p class="lede">{esc(name)}({esc(fuel)}, 배기량 {cc:,}cc)의 자동차세를 연식별로 계산했습니다. 비영업용 승용 기준이며, 3년차부터 차령 경감이 적용돼 해마다 줄어들어요.</p>
<div class="tax-summary">
  <div class="card"><div class="label">신차 기준 연세액</div><div class="amount">{won(new_tax["annual"])}</div><div class="label">본세 {won(new_tax["base"])} + 교육세 {won(new_tax["edu"])}</div></div>
  <div class="card"><div class="label">1월 연납 시 ({esc(new_prepay["year"])}년 공제율 {new_prepay["rate"]*100:.0f}%)</div><div class="amount">{won(new_prepay["pay"])}</div><div class="label">{won(new_prepay["discount"])} 할인</div></div>
</div>
{picker}
{table}
{notebook_cta(v)}
<h2>계산 방법</h2>
<p>본세 = 배기량 × cc당 세액({new_tax["perCc"]}원/cc 구간) → 차령 {aging["startCarAge"]}년차부터 (차령 − 2) × {aging["ratePerYear"]*100:.0f}% 경감(최대 {aging["maxRate"]*100:.0f}%) → 지방교육세 {rates["displacement"]["educationTaxRate"]*100:.0f}% 가산. 6월·12월에 절반씩 부과되며, 1월에 연납 신청하면 2~12월분의 {new_prepay["rate"]*100:.0f}%를 공제받아요.</p>
<p>차령은 대략 <em>올해 − 등록 연도 + 1</em>로 계산합니다.</p>
<p>차값·연료비·보험까지 묶어 보려면 <a href="../tco.html">유지비 비교</a>, 소모품·검사 일정 관리는 <a href="../index.html">내 차 수첩</a>에서.</p>
{sources_block(rates)}"""

    title = f"{name} 자동차세 — 연 {new_tax['annual']:,}원부터, 연식별 계산표 | {site['siteName']}"
    desc = (
        f"{name}({cc:,}cc) 자동차세는 신차 기준 연 {new_tax['annual']:,}원. "
        f"연식(차령)별 경감·1월 연납 할인까지 표로 정리했습니다."
    )
    return page(site, title, desc, body)


def index_page(vehicles, rates, site):
    by_brand = {}
    for v in vehicles:
        by_brand.setdefault(v["brand"], []).append(v)

    sections = []
    for brand, items in by_brand.items():
        links = "".join(
            f'<li><a href="{esc(v["slug"])}.html">{esc(v["name"])} 자동차세</a></li>' for v in items
        )
        sections.append(f'<p class="brand-title">{esc(brand)}</p><ul class="model-list">{links}</ul>')

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
{"".join(sections)}
<p style="margin-top:24px;">찾는 차종이 없나요? <a href="../tco.html">유지비 비교</a>에서 배기량을 직접 입력해 계산할 수 있어요.</p>
{sources_block(rates)}"""
    title = f"차종별 자동차세 계산 — 연식별 세액·연납 할인 | {site['siteName']}"
    desc = "아반떼·그랜저·쏘렌토 등 인기 차종의 자동차세를 연식별로 계산. cc당 세율, 차령 경감, 연납 할인까지."
    return page(site, title, desc, body)


def build_sitemap(site, slugs):
    base = site.get("baseUrl", "").rstrip("/")
    if not base:
        print("· site.json baseUrl이 비어 있어 sitemap.xml 생성을 건너뜁니다 (도메인 확정 후 재실행)")
        return
    today = datetime.date.today().isoformat()
    urls = [f"{base}/", f"{base}/tco.html", f"{base}/tax/index.html"] + [
        f"{base}/tax/{s}.html" for s in slugs
    ]
    items = "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>\n'
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"· sitemap.xml ({len(urls)}개 URL)")


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
    print(f"· tax/ 페이지 {len(slugs)}개 + index 생성")
    build_sitemap(site, slugs)


if __name__ == "__main__":
    main()
