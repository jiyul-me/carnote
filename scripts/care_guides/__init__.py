"""차일지 — 차 관리 가이드 (care/index.html 목록 + care/{slug}.html). scripts/build.py가 부른다.

글 하나 = 이 폴더의 모듈 하나. 파일 이름은 slug의 '-'를 '_'로 바꾼 것(engine-oil → engine_oil.py).
모듈은 두 가지를 둔다.
  GUIDE = {"slug", "short", "published", "updated", "og_title", "og_lede", "summary"}  (scripts/guides.py GUIDES와 같은 모양)
  def build(c): -> {"h1", "title", "description", "lede", "summary", "body", "faqs", "sources"}
ORDER 순서가 목록·'다른 가이드' 순서다. 새 글은 모듈을 만들고 ORDER에 slug를 더한다.

규칙 (자동차세 가이드와 같다)
- 교체 주기처럼 data/*.json에 있는 숫자는 문장에 직접 쓰지 않고 c.part()·c.interval_text()로 만든다.
  수첩(index.html)이 같은 data/parts.json으로 교체 시기를 계산하므로, 글과 수첩이 서로 다른 숫자를 말하면 안 된다.
- parts.json의 priceKrw(공임 포함 대략 가격)는 수첩 내부 참고용이라 글에 쓰지 않는다(parts.json conventions.priceKrw —
  콘텐츠 페이지 노출 금지). 소모품·정비 비용 금액을 글에 적지 않는다.
- 법령·공공기관 수치(검사 주기·과태료·마모한계 등)는 출처로 확인한 것만 쓰고, sources에 그 출처를 넣는다.
  확인하지 못한 것·차종마다 다른 것은 단정하지 말고 '차량 설명서(매뉴얼)·정비소에서 확인'으로 안내한다.
- 글 문장(사실)을 고치면 GUIDE["updated"]를 고친다 — 화면의 '수정'일과 Article 구조화 데이터에 쓰인다.
- 링크는 care/ 기준 상대 경로: 다른 차 관리 글 '{slug}.html', 수첩 '../index.html', 자동차세 '../tax/…',
  유지비 비교 '../tco.html' — 헬퍼(c.link_*)를 쓰면 틀릴 일이 없다.
- 운영자 개인 정보(이름·나이 등)는 어디에도 쓰지 않는다.
"""
import importlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import guides as _g  # noqa: E402  — table·num·ext·date_ko·short_name 재사용 (table은 글자 표로 감싼다)

ORDER = ("replacement-schedule", "inspection", "warning-lights", "engine-oil", "tire", "brake", "battery", "filters",
         "fluids", "engine-parts", "winter", "summer", "ev-care", "diesel-care", "fuel-economy", "used-car-check",
         "recall-warranty")
INDEX_SLUG = "index"  # 목록 페이지 care/index.html

num, ext, date_ko, short_name = _g.num, _g.ext, _g.date_ko, _g.short_name


def _wbr(cell):
    """가운뎃점 뒤에 줄바꿈 자리(<wbr>) — 태그 밖 글자만. '가솔린·LPG·디젤·하이브리드'가 한 낱말로 묶여 좁은 칸을 넘치지 않게."""
    return re.sub(r"·(?![^<]*>)", "·<wbr>", str(cell))


def table(head, rows):
    """글자 표 — 자동차세 가이드 표(guides.table)와 같은 모양에 'text' 클래스.
    차 관리 글의 표 칸에는 설명 문장이 들어가서, 숫자 표처럼 한 줄 고정·오른쪽 정렬이면 표가 옆으로 넘친다(css/content.css)."""
    return _g.table([_wbr(h) for h in head], [[_wbr(x) for x in r] for r in rows], "data text")


def module_name(slug):
    return slug.replace("-", "_")


def load(slug):
    """slug의 글 모듈. GUIDE의 slug가 파일과 맞는지 확인한다."""
    m = importlib.import_module(f"care_guides.{module_name(slug)}")
    if m.GUIDE.get("slug") != slug:
        raise ValueError(f"care_guides/{module_name(slug)}.py의 GUIDE['slug']가 '{slug}'가 아니에요")
    return m


def guides():
    """[GUIDE] — ORDER 순서."""
    return [load(s).GUIDE for s in ORDER]


class Ctx:
    """글 공통 재료 — build.py 모듈(B), 세율·사이트·차종 데이터, 소모품(parts.json)·검사(inspection.json) 데이터."""

    def __init__(self, B, rates, site, cat, this_year):
        self.B, self.rates, self.site, self.cat, self.y = B, rates, site, cat, this_year
        parts = B.load("parts.json")
        self.parts_updated = parts.get("updatedAt")
        self.parts = {p["id"]: p for p in parts["parts"]}
        self.part_categories = parts.get("categories")
        self.inspection = B.load("inspection.json")
        self.fuel_prices = site.get("fuelPrices") or {}
        self.fuel_km = site.get("fuelCostBasisKm")
        self.by_slug = {v["slug"]: v for v in cat.vehicles}

    # ---- 소모품 (data/parts.json — 수첩과 같은 값)
    def part(self, pid):
        if pid not in self.parts:
            raise ValueError(f"data/parts.json에 '{pid}'가 없어요 — scripts/care_guides의 글을 고치세요")
        return self.parts[pid]

    def interval_text(self, pid):
        """'10,000km 또는 12개월 중 먼저 오는 때' · '40,000km마다' · '24개월마다' · '정해진 주기 없이 상태를 보고'."""
        p = self.part(pid)
        km, mo = p.get("intervalKm"), p.get("intervalMonths")
        if km and mo:
            return f"{km:,}km 또는 {mo}개월 중 먼저 오는 때"
        if km:
            return f"{km:,}km마다"
        if mo:
            return f"{mo}개월마다"
        return "정해진 주기 없이 상태를 보고"

    # ---- 링크 (care/ 기준 상대 경로)
    def link_care(self, slug, label):
        return f'<a href="{self.B.esc(slug)}.html">{self.B.esc(label)}</a>'

    def link_notebook(self, label="내 차 수첩"):
        return f'<a href="../index.html">{self.B.esc(label)}</a>'

    def link_tax(self, path, label):
        """자동차세 쪽 페이지 — path는 tax/ 기준 ('guide-prepay.html', 'calculator.html')."""
        return f'<a href="../tax/{self.B.esc(path)}">{self.B.esc(label)}</a>'

    def link_tco(self, label="유지비 비교"):
        return f'<a href="../tco.html">{self.B.esc(label)}</a>'

    def link_car(self, slug, label=None):
        """차종 페이지 — 빌드 대상에 없으면 빌드를 멈춘다."""
        if slug not in self.by_slug:
            raise ValueError(f"예시 차종 '{slug}'가 data/vehicles.json(빌드 대상)에 없어요")
        v = self.by_slug[slug]
        return f'<a href="../tax/{self.B.esc(slug)}.html">{self.B.esc(label or v["name"])}</a>'


def build_all(B, rates, site, cat, this_year):
    """[(GUIDE, 글)] — ORDER 순서."""
    c = Ctx(B, rates, site, cat, this_year)
    return [(load(s).GUIDE, load(s).build(c)) for s in ORDER]
