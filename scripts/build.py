#!/usr/bin/env python3
"""차일지 — 차종별 자동차세 정적 페이지 + sitemap 생성기.

이 머신에는 node가 없으므로 정적 생성은 Python으로 한다 (CLAUDE.md 기술 방향).
세율·차종 등 모든 수치는 data/*.json에서 읽는다 — 여기 하드코딩 금지.

사용법:  python3 scripts/build.py   (프로젝트 루트 기준 상대 경로로 동작)
출력:    tax/<slug>.html, tax/index.html, sitemap.xml(site.json에 baseUrl 있을 때만),
         og/*.png 공유 썸네일 · icons/*.png · favicon.ico (Pillow 필요 — scripts/images.py),
         ads.txt(site.json adsense.publisherId가 있을 때만 — 비면 지운다),
         손으로 쓴 루트 *.html의 마커 구간(<!-- adsense:head -->·<!-- adsense:slot 이름 -->·<!-- site:contact -->)
"""
import sys
import json
import html
import re
import calendar
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import images  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "tax"

FUEL_LABELS = {"gasoline": "가솔린", "diesel": "디젤", "lpg": "LPG", "hybrid": "하이브리드", "ev": "전기"}

# 과세 구분(fuelType)과 실제로 넣는 에너지는 다를 수 있다 — 수소전기차(넥쏘)는 세법상 ev 정액이지만 수소(kg)를 넣는다.
# vehicles.json energySource가 있으면 그것, 없으면 fuelType에서 유도 (js/derive.js·js/tco.js와 같은 규칙)
ENERGY_BY_FUEL = {"gasoline": "gasoline", "diesel": "diesel", "lpg": "lpg", "hybrid": "gasoline", "ev": "electricity"}
ENERGY_UNIT = {"electricity": "kWh", "hydrogen": "kg"}  # 나머지(휘발유·경유·LPG)는 L
ENERGY_PRICE_KEY = {"electricity": "ev"}  # site.json fuelPrices 키 — 나머지는 에너지 이름 그대로

# 연식별 표의 행 수 (1년차 = 신차 … 마지막 행 = 그 차령 이상). 차령 경감 상한(12년차)보다 한 줄 더 보여
# '그 뒤로는 같다'를 드러낸다. 표·선택 상자·이미지 저장·단종 세대 기본 연식이 모두 이 값을 따른다
TABLE_MAX_AGE = 13


def age_row_label(age, this_year):
    """연식표 첫 열 — ('2026년', ' · 신차'). 등록 연도가 주인공이고 차령은 12px muted 꼬리(.age-sub).
    마지막 행은 '13년차+'(그 이전 등록 포함). '이전' 같은 말은 붙이지 않는다 — 360·375px에서 두 줄이 된다."""
    reg_year = this_year - age + 1
    if age == 1:
        sub = "신차"
    elif age >= TABLE_MAX_AGE:
        sub = f"{TABLE_MAX_AGE}년차+"
    else:
        sub = f"{age}년차"
    return f"{reg_year}년", f" · {sub}"


def energy_source(v):
    return v.get("energySource") or ENERGY_BY_FUEL.get(v["fuelType"], "gasoline")


def is_hydrogen(v):
    return energy_source(v) == "hydrogen"


def flat_kind(v):
    """정액 승용차의 페이지 표기 — 전기차 / 수소전기차 (과세는 둘 다 '그 밖의 승용자동차' 정액)."""
    return "수소전기차" if is_hydrogen(v) else "전기차"


def fuel_caption(v):
    """제목 아래 캡션·썸네일의 연료 표기. 수소전기차는 '전기'가 아니라 '수소전기차'."""
    return "수소전기차" if is_hydrogen(v) else FUEL_LABELS.get(v["fuelType"], v["fuelType"])


def flat_basis_text(v):
    """정액 승용차 '계산 방법'의 과세 근거 문장 (뒤에 '배기량 기준 대신 정액 … 적용돼요'가 이어진다)."""
    if is_hydrogen(v):
        return '수소전기차도 전기차와 함께 지방세법상 "그 밖의 승용자동차"로 분류되어(전기·수소 동일 세율)'
    return '전기차는 지방세법상 "그 밖의 승용자동차"로 분류되어'


def load(name):
    with open(ROOT / "data" / name, encoding="utf-8") as f:
        return json.load(f)


def floor10(x):
    """지방세 단수 처리 관례에 맞춰 10원 미만 절사 (위택스 대조로 최종 확인)."""
    return int(x // 10 * 10)


def bp(rate):
    """비율(0.05 등)을 만분율 정수(500)로. 세액은 정수로만 계산한다 — 부동소수점으로 (1 - 0.35)를 곱하면
    0.6499999…가 되어 10원 미만 절사에서 10원이 더 깎인다(1,999cc 9년차 337,830원 → 337,810원으로 틀렸던 버그).
    js/tax-calc.js의 bp()와 같은 규칙."""
    return int(round(rate * 10000))


def tax_for(cc, age, rates):
    """비영업용 승용 자동차세. age = 차령(1 = 신차 첫해). data/tax-rates.json 규칙 그대로, 정수 연산."""
    d = rates["displacement"]
    per_cc = next(b["wonPerCc"] for b in d["brackets"] if b["maxCc"] is None or cc <= b["maxCc"])
    aging = d["agingDiscount"]
    discount_bp = 0
    if age >= aging["startCarAge"]:
        discount_bp = min(bp(aging["maxRate"]), (age - aging["startCarAge"] + 1) * bp(aging["ratePerYear"]))
    base_after = cc * per_cc * (10000 - discount_bp) // 100000 * 10   # floor10(배기량 × 세율 × (1 − 경감률))
    edu = base_after * bp(d["educationTaxRate"]) // 100000 * 10       # floor10(본세 × 교육세율)
    annual = base_after + edu
    discount_rate = discount_bp / 10000
    return {"perCc": per_cc, "discountRate": discount_rate, "base": base_after, "edu": edu, "annual": annual}


def nonpassenger_tax(v, rates):
    """승합·화물 연세액. 정액이므로 차령 경감·지방교육세를 적용하지 않는다.
    반환: {kind, nonBusiness, business, basisLabel} / 계산 불가면 None"""
    cls = v.get("vehicleClass", "passenger")
    if cls == "truck":
        kg = v.get("payloadKg")
        if not kg:
            return None
        t = rates["truck"]
        for b in t["brackets"]:
            if kg <= b["maxKg"]:
                return {"kind": "truck", "nonBusiness": b["nonBusinessKrw"],
                        "business": b["businessKrw"], "basisLabel": f"적재정량 {kg:,}kg"}
        # 1만kg 초과: 마지막 구간 + 초과 1만kg마다 가산
        last = t["brackets"][-1]
        extra_tons = -(-(kg - last["maxKg"]) // 10000)  # 올림
        per = t["over10tPerTonKrw"]
        return {"kind": "truck",
                "nonBusiness": last["nonBusinessKrw"] + extra_tons * per["nonBusinessKrw"],
                "business": last["businessKrw"] + extra_tons * per["businessKrw"],
                "basisLabel": f"적재정량 {kg:,}kg"}
    if cls == "van":
        size = v.get("vanSize", "small")
        s = next((x for x in rates["van"]["sizes"] if x["key"] == size), None)
        if not s:
            return None
        return {"kind": "van", "nonBusiness": s["nonBusinessKrw"],
                "business": s["businessKrw"], "basisLabel": s["label"]}
    return None


def prepay_rate(rates, this_year):
    """연납 공제율 선택 (tax-rates.json fallbackRule — js/tax-calc.js rateFor와 같은 규칙).
    당해 연도 키가 있으면 그 해, 없으면 가장 최근 연도의 공제율 + fallback=True('YYYY년 기준' 표기 강제).
    반환: (공제율 연도 문자열, 공제율, fallback)"""
    by_year = rates["prepayDiscount"]["rateByYear"]
    key = str(this_year)
    if key in by_year:
        return key, by_year[key], False
    latest = max(by_year, key=int)
    return latest, by_year[latest], True


def prepay_days(rates, year):
    """1월 연납 공제 일수 — 지방세법 제128조 제3항 계산식의 '납부기한 다음 날부터 12월 31일까지 일수 ÷ 365(윤년 366)'.
    납부기한 = applicationWindows에서 month가 januaryProration.windowMonth인 기간의 endDay (js/tax-calc.js prorationDays와 같은 규칙).
    반환: (일수, 그 해 일수) — 평년 (334, 365), 윤년 (335, 366)"""
    p = rates["prepayDiscount"]
    month = p["januaryProration"]["windowMonth"]
    w = next((w for w in p.get("applicationWindows") or [] if w["month"] == month), None)
    if w is None:
        raise ValueError(f"tax-rates.json januaryProration.windowMonth({month})에 해당하는 applicationWindows 기간이 없습니다")
    y = int(year)
    days = (datetime.date(y, 12, 31) - datetime.date(y, w["month"], w["endDay"])).days
    year_days = (datetime.date(y + 1, 1, 1) - datetime.date(y, 1, 1)).days
    return days, year_days


def prepay_period_label(rates, year):
    """공제 일수의 기간 문구 '2월 1일~12월 31일' (납부기한 다음 날~연말 — prepay_days와 같은 기준)."""
    days, _ = prepay_days(rates, year)
    start = datetime.date(int(year), 12, 31) - datetime.timedelta(days=days - 1)
    return f"{start.month}월 {start.day}일~12월 31일"


def prepay(annual, rates, this_year):
    """1월 연납 시 공제액·납부액 (일할). this_year = 빌드 연도 — 공제율 선택과 일수(평년 334/365, 윤년 335/366) 모두 이 해 기준.
    연세액은 지방교육세 포함 총액 그대로 곱하고 10원 미만 절사 (서울시 공식 예시와 원 단위 일치 — scripts/check_tax_parity.py)."""
    year, rate, fallback = prepay_rate(rates, this_year)
    days, year_days = prepay_days(rates, this_year)
    discount = annual * days * bp(rate) // (year_days * 100000) * 10   # floor10(연세액 × 일수/연도일수 × 공제율), 정수 연산
    return {"year": year, "rate": rate, "fallback": fallback, "days": days, "yearDays": year_days,
            "discount": discount, "pay": annual - discount}


def prepay_basis(rates, this_year, sep=" · "):
    """폴백일 때 연납 금액 옆에 붙이는 '2026년 공제율 기준' 문구. 당해 연도 공제율이 있으면 빈 문자열."""
    year, _, fallback = prepay_rate(rates, this_year)
    return f"{sep}{year}년 공제율 기준" if fallback else ""


def prepay_windows(rates):
    """연납 신청 기간 (tax-rates.json applicationWindows). 값이 이상하면 빌드를 멈춘다 —
    잘못된 날짜는 잘못된 안내로 직결된다. 금액 계산(januaryProration.windowMonth)이 가리키는 기간이 있어야 한다."""
    p = rates["prepayDiscount"]
    windows = p.get("applicationWindows") or []
    for w in windows:
        last_day = calendar.monthrange(2023, w["month"])[1] if 1 <= w["month"] <= 12 else 0  # 평년 말일 (2/29 금지)
        lead = w.get("bannerLeadDays", 0)
        if not (1 <= w["startDay"] <= w["endDay"] <= last_day and 0 < w["coveredMonths"] < 12
                and isinstance(lead, int) and 0 <= lead <= 120):
            raise ValueError(f"tax-rates.json applicationWindows 값 오류: {w}")
    jp = p["januaryProration"]
    if jp.get("method") != "daily" or not any(w["month"] == jp.get("windowMonth") for w in windows):
        raise ValueError("tax-rates.json januaryProration: method는 'daily', windowMonth는 applicationWindows의 month여야 합니다")
    return windows


def lump_sum_only(base, rates):
    """본세(지방교육세 제외)가 기준 이하면 지자체가 6월에 1년치를 부과한다(지방세법 제128조 제4항) —
    이런 차는 6·9월 연납이 없다 (applicationWindows.lumpSumEligible)."""
    th = rates["prepayDiscount"].get("lumpSumThresholdKrw")
    return bool(th) and base <= th


def prepay_banner(rates, this_year, lump_sum=False, amount_note=True, age_based=False, css_prefix="../"):
    """연납 신청 기간 안내 줄 자리 (연납 한 줄 바로 아래). 날짜 판단은 js/prepay-banner.js가 오늘 날짜로 한다.
    기본 hidden — JS가 꺼져 있거나 기간 밖이면 아무것도 보이지 않는다.
    lump_sum: 6월 일괄부과 차량이면 data-lump-sum — JS가 6·9월(lumpSumEligible=false) 기간을 뺀다.
      계산기는 입력에 따라 JS(ChailjiPrepayBanner.update)가 이 표시를 켜고 끈다.
    amount_note: 페이지에 '1월 연납 시' 금액이 있는지 (문구가 그 금액을 가리킨다).
    age_based: 페이지 금액이 차령(빌드 연도 기준)에 따라 달라지는지 — 다음 해 1월 예고 때 '차령이 늘어 달라질 수 있다'고 밝힌다.
    data-build-year: 페이지 금액의 기준 연도. 안내 대상 기간의 연도가 이와 다르면 '이 금액으로 낼 수 있다'고 하지 않는다."""
    p = rates["prepayDiscount"]
    windows = prepay_windows(rates)
    if not windows:
        return ""
    keys = ("month", "startDay", "endDay", "coveredMonths", "label", "lumpSumEligible", "bannerLeadDays")
    data = [{k: w[k] for k in keys if k in w} for w in windows]
    attrs = (
        f' data-windows="{esc(json.dumps(data, ensure_ascii=False, separators=(",", ":")))}"'
        f' data-rates="{esc(json.dumps(p["rateByYear"], separators=(",", ":")))}"'
        f' data-build-year="{int(this_year)}"'
        + (" data-amount-note" if amount_note else "")
        + (" data-age-based" if age_based else "")
        + (" data-lump-sum" if lump_sum else "")
    )
    # 신청 링크는 sources의 위택스 항목을 그대로 쓴다 (URL 단일 출처)
    src = next((s for s in rates.get("sources", []) if s.get("key") == "wetax"), None)
    link = ""
    if src:
        link = (f' <a class="prepay-apply" href="{esc(src["url"])}" rel="noopener" target="_blank" hidden>'
                f'{esc(src.get("shortLabel", src["label"]))}에서 신청</a>')
    return (f'<div class="prepay-banner"{attrs} hidden>'
            f'<span class="prepay-badge"></span><span class="prepay-main"></span>{link}'
            f'<span class="prepay-note"></span></div>\n'
            f'<script src="{css_prefix}js/prepay-banner.js" defer></script>')


def won(n):
    return f"{n:,}원"


def esc(s):
    return html.escape(str(s), quote=True)


# ---------- 세대·연식 (차종 페이지·관련 차종·허브 공용) ----------

# 이름에 연식이 이미 있는 차 — '아반떼 AD 1.6 (2015~2018)'·'벤츠 S450 (W223, 2021~2023)'·'벤츠 S450 (W223, 2025년식)'
YEARS_IN_NAME = re.compile(r"\([^)]*\d{4}(?:~|년식)")


def year_range(v):
    """모델 연식 범위 '2016~2019', 한 해뿐이면 '2025', 판매 중이면 '2022~'. 연식 데이터가 없으면 ''."""
    a, b = v.get("modelYearFrom"), v.get("modelYearTo")
    if not a:
        return ""
    if not b:
        return f"{a}~"
    return f"{a}" if a == b else f"{a}~{b}"


def years_caption(v):
    """목록 행의 12px muted 연식 캡션. 이름에 연식이 이미 있으면 두 번 쓰지 않는다."""
    return "" if YEARS_IN_NAME.search(v["name"]) else year_range(v)


def is_ice_passenger(v):
    """배기량으로 과세하는 승용차(가솔린·디젤·LPG·하이브리드) — 차령 경감이 있는 차."""
    return (v.get("vehicleClass", "passenger") == "passenger" and v["fuelType"] != "ev"
            and bool(v.get("displacementCc")))


def max_discount_age(rates):
    """차령 경감이 상한(maxRate)에 닿는 차령 — 현행 3년차부터 5%씩, 최대 50%면 12. tax-rates.json agingDiscount에서 계산."""
    a = rates["displacement"]["agingDiscount"]
    steps = -(-bp(a["maxRate"]) // bp(a["ratePerYear"]))  # 올림
    return a["startCarAge"] - 1 + steps


def gen_default(v, rates, this_year):
    """단종 세대의 대표 연식. 마지막 연식도 이미 차령 경감 구간이면 '신차 기준' 금액은 이 세대에 해당하는 차가 없다
    (아반떼 MD 2010~2015년식 → 2026년엔 전부 12년차 이상). 그런 차는 페이지 대표 금액을 마지막 연식 기준으로 보인다.
    대상: 배기량 과세 승용차 + modelYearTo 있음 + (올해 − modelYearTo + 1) ≥ agingDiscount.startCarAge.
    기본 등록 연도 = modelYearTo, 차령 = 올해 − modelYearTo + 1 (실제 값 — 캡션·FAQ·썸네일 문구는 이것을 쓴다).
    연식표는 TABLE_MAX_AGE행까지라, 하이라이트·기본 선택 행은 row = min(차령, TABLE_MAX_AGE)('13년차+' 행)로 따로 둔다.
    표 행의 연도를 문구에 쓰면 2010~2011년식에 '2014년 등록(13년차)'처럼 이 세대에 없는 등록 연도가 나온다.
    모델 연식과 최초 등록 연도는 1년 다를 수 있어, 화면에는 '등록증의 최초 등록 연도로 고르세요'를 같이 둔다.
    반환: None(판매 중·최근 단종·전기·화물·승합) 또는
    {"year": 기본 등록 연도, "age": 그 차령, "row": 연식표 행 차령, "oldAge": 첫 연식의 차령}"""
    to = v.get("modelYearTo")
    if not to or not is_ice_passenger(v):
        return None
    if this_year - to + 1 < rates["displacement"]["agingDiscount"]["startCarAge"]:
        return None
    frm = v.get("modelYearFrom") or to
    age = this_year - to + 1
    return {"year": to, "age": age, "row": min(age, TABLE_MAX_AGE), "oldAge": this_year - frm + 1}


def gen_span(v, rates, this_year):
    """단종 세대 전체의 올해 세액 범위 (lo = 가장 오래된 연식, hi = 대표 연식). gen_default 대상이 아니면 None."""
    g = gen_default(v, rates, this_year)
    if not g:
        return None
    cc = v["displacementCc"]
    return {"g": g, "lo": tax_for(cc, g["oldAge"], rates), "hi": tax_for(cc, g["age"], rates)}


def amount_range_text(lo, hi):
    """'연 144,780원' 또는 '연 144,780~188,210원'."""
    return f"연 {lo:,}원" if lo == hi else f"연 {lo:,}~{hi:,}원"


def rep_annual(v, rates, this_year):
    """목록·관련 차종에 보이는 올해 대표 세액. 화물·승합 = 자가용 정액, 전기 = 정액,
    단종 세대 = 대표 연식(gen_default), 그 밖 = 신차."""
    if v.get("vehicleClass", "passenger") != "passenger":
        return nonpassenger_tax(v, rates)["nonBusiness"]
    if v["fuelType"] == "ev":
        return rates["displacement"]["ev"]["annualTotalKrw"]
    g = gen_default(v, rates, this_year)
    return tax_for(v["displacementCc"], g["age"] if g else 1, rates)["annual"]


def gen_key(v):
    """세대 묶음 키 — generation의 첫 토큰 ('IG F/L' → 'IG', 'MD 쿠페' → 'MD')."""
    parts = (v.get("generation") or "").split()
    return parts[0] if parts else ""


def trim_sort_key(v):
    """트림 정렬 (-modelYearFrom, name) — 최신 연식이 위."""
    return (-(v.get("modelYearFrom") or 0), v["name"])


def gen_groups(trims):
    """세대(gen_key)별 묶음. 세대는 가장 최근 시작 연식이 큰 순, 세대 안은 trim_sort_key 순 —
    세대 라벨을 한 번씩만 붙일 수 있게 같은 세대를 이어 놓는다.
    반환: [(key, 라벨 'IG · 2016~2022', [trims])]"""
    groups = {}
    for v in trims:
        groups.setdefault(gen_key(v), []).append(v)
    out = []
    for key, items in groups.items():
        items = sorted(items, key=trim_sort_key)
        froms = [x["modelYearFrom"] for x in items if x.get("modelYearFrom")]
        tos = [x.get("modelYearTo") for x in items]
        span = ""
        if froms:
            last = None if any(t is None for t in tos) else max(tos)
            span = str(last) if last == min(froms) else f"{min(froms)}~" + ("" if last is None else str(last))
        label = f"{key} · {span}" if key and span else (key or span)
        out.append((key, label, items))
    out.sort(key=lambda g: (-max((x.get("modelYearFrom") or 0) for x in g[2]), g[0]))
    return out


# ---------- 허브 앵커 id (브레드크럼·브랜드 칩·검색이 가리키는 곳) ----------
# 데이터 순서가 바뀌어도 변하지 않게 번호(b0, b1…)가 아니라 이름·slug에서 만든다

_RR_INITIAL = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"]
_RR_MEDIAL = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi",
              "yu", "eu", "ui", "i"]
_RR_FINAL = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p", "l", "m", "p", "p", "t", "t",
             "ng", "t", "t", "k", "t", "p", "t"]


def romanize_id(text):
    """한글 이름 → 앵커용 ASCII 토큰 (국어의 로마자 표기법 음절 단위, 음운 변화 무시). '현대 N' → 'hyeondae-n'.
    영문·숫자는 소문자로 두고 나머지 문자는 '-'로 바꾼다."""
    out = []
    for ch in text:
        code = ord(ch) - 0xAC00
        if 0 <= code < 11172:
            out.append(_RR_INITIAL[code // 588] + _RR_MEDIAL[(code % 588) // 28] + _RR_FINAL[code % 28])
        elif ch.isascii() and ch.isalnum():
            out.append(ch.lower())
        else:
            out.append("-")
    return re.sub(r"-+", "-", "".join(out)).strip("-")


def slug_common_prefix(slugs):
    """slug들의 '-' 토큰 공통 접두 ('grandeur-2.5', 'grandeur-hg-2.4' → 'grandeur')."""
    out = []
    for parts in zip(*[s.split("-") for s in slugs]):
        if any(p != parts[0] for p in parts):
            break
        out.append(parts[0])
    return "-".join(out)


def family_key(v):
    return (v["brand"], v["modelFamily"])


class Catalog:
    """차종 목록에서 한 번 계산해 두는 색인 — 가족(브랜드+모델) 묶음, 허브 앵커 id, 가족 공통 별칭.
    차종 페이지(관련 차종·브레드크럼)와 허브(목록·검색)가 같은 값을 쓴다."""

    def __init__(self, vehicles, this_year):
        self.vehicles = list(vehicles)
        self.this_year = this_year
        self.families = {}  # (brand, family) → [트림] (데이터 순서)
        self.brands = {}    # brand → [(brand, family)] (데이터 순서)
        for v in self.vehicles:
            k = family_key(v)
            if k not in self.families:
                self.brands.setdefault(v["brand"], []).append(k)
            self.families.setdefault(k, []).append(v)
        # 브랜드: 'brand-' + 로마자, 모델 그룹(2트림 이상): 'model-' + slug 공통 접두, 트림: slug 그대로
        self.brand_ids = {b: "brand-" + (romanize_id(b) or "x") for b in self.brands}
        self.family_ids = {}
        prefixes = {}
        for k, items in self.families.items():
            if len(items) >= 2:
                prefixes[k] = slug_common_prefix([v["slug"] for v in items]) or min(v["slug"] for v in items)
        counts = {}
        for p in prefixes.values():
            counts[p] = counts.get(p, 0) + 1
        for k, p in prefixes.items():  # 공통 접두가 겹치면 가족에서 가장 앞선 slug로 (그래도 데이터 순서와 무관)
            self.family_ids[k] = "model-" + (p if counts[p] == 1 else min(v["slug"] for v in self.families[k]))
        seen = {}
        for i in list(self.brand_ids.values()) + list(self.family_ids.values()) + [v["slug"] for v in self.vehicles]:
            if i in seen:
                raise ValueError(f"허브 앵커 id가 겹칩니다: {i} — vehicles.json slug·brand·modelFamily를 확인하세요")
            seen[i] = True

    def family(self, v):
        return self.families[family_key(v)]

    def crumb_anchor(self, v):
        """브레드크럼 중간 단계 (이름, 허브 앵커 id). 가족이 1트림뿐이면 브랜드 단계."""
        k = family_key(v)
        if len(self.families[k]) >= 2:
            return f"{v['brand']} {v['modelFamily']}", self.family_ids[k]
        return v["brand"], self.brand_ids[v["brand"]]


def page_canonical(site, path):
    base = site.get("baseUrl", "").rstrip("/")
    return f"{base}/{path}" if base else None


def og_image_tags(og):
    """og = {"url", "alt"} — 카카오톡·페이스북·X 미리보기 썸네일 (1200×630)."""
    if not og:
        return ""
    return (
        f'<meta property="og:image" content="{esc(og["url"])}">\n  '
        f'<meta property="og:image:width" content="{images.OG_W}">\n  '
        f'<meta property="og:image:height" content="{images.OG_H}">\n  '
        f'<meta property="og:image:alt" content="{esc(og["alt"])}">\n  '
        f'<meta name="twitter:card" content="summary_large_image">\n  '
    )


# ---------- 애드센스·문의 이메일 — data/site.json 값 하나로 켜고 끈다 ----------
# publisherId('pub-' + 16자리)가 비어 있으면 메타·스크립트·슬롯·ads.txt를 하나도 만들지 않는다.
# 슬롯 ID(승인 후 광고 단위 번호)가 있는 자리만 광고를 넣고, 그 페이지 head에만 adsbygoogle.js를 싣는다.
# 런타임 주입은 쓰지 않는다 — 소유 확인 메타는 정적 HTML에 있어야 한다. 수첩 화면(index.html)에는 광고 슬롯 금지.

ADS_TXT = "ads.txt"
ADS_TXT_LINE = "google.com, {pub}, DIRECT, f08c47fec0942fa0\n"  # 애드센스 ads.txt 형식 (pub- 접두사, 인증 ID 고정값)
ADSENSE_JS = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-{pub}"


def adsense_conf(site):
    """(publisherId, {슬롯 이름: ID}). site.json에 adsense 키가 없어도 빈 값과 같게 동작한다."""
    ad = site.get("adsense") or {}
    pub = str(ad.get("publisherId") or "").strip()
    slots = ad.get("slots") if isinstance(ad.get("slots"), dict) else {}
    return pub, {str(k): str(v or "").strip() for k, v in slots.items()}


def adsense_head(site, slot_names=()):
    """head에 넣을 태그. publisherId가 있으면 사이트 소유 확인 메타(모든 페이지),
    이 페이지의 슬롯 중 ID가 채워진 것이 있으면 광고 스크립트(async, crossorigin)."""
    pub, slots = adsense_conf(site)
    if not pub:
        return ""
    out = f'<meta name="google-adsense-account" content="ca-{esc(pub)}">'
    if any(slots.get(n) for n in slot_names):
        out += f'<script async src="{esc(ADSENSE_JS.format(pub=pub))}" crossorigin="anonymous"></script>'
    return out


def ad_slot(site, name):
    """광고 자리 1개 (페이지당 1개). publisherId와 그 슬롯 ID가 모두 있을 때만 출력한다.
    자리 규칙: 첫 화면·히어로 직후·select·표·버튼·CTA 카드 근처·입력과 결과 사이·아코디언 행 사이 금지 —
    차종 페이지는 '계산 방법' 산문 뒤·FAQ 앞, 허브·계산기는 출처(.sources) 뒤."""
    pub, slots = adsense_conf(site)
    sid = slots.get(name)
    if not pub or not sid:
        return ""
    return (f'<div class="ad-slot"><p class="ad-label">광고</p><ins class="adsbygoogle" style="display:block" '
            f'data-ad-client="ca-{esc(pub)}" data-ad-slot="{esc(sid)}" data-ad-format="auto" '
            'data-full-width-responsive="false"></ins><script>(adsbygoogle=window.adsbygoogle||[]).push({});</script></div>')


def contact_html(site):
    """site:contact 마커 내용 — contactEmail이 있을 때만 이메일 문단."""
    e = str(site.get("contactEmail") or "").strip()
    return f'<p>이메일: <a href="mailto:{esc(e)}">{esc(e)}</a></p>' if e else ""


def sync_ads_txt(site):
    """루트 ads.txt를 publisherId와 맞춘다. 비어 있으면 지우고 그 사실을 알린다(손으로 올린 파일이 소리 없이 사라지지 않게)."""
    pub, _ = adsense_conf(site)
    path = ROOT / ADS_TXT
    if pub:
        want = ADS_TXT_LINE.format(pub=pub)
        if not path.exists() or path.read_text(encoding="utf-8") != want:
            path.write_text(want, encoding="utf-8")
            print("· ads.txt 생성")
    elif path.exists():
        path.unlink()
        print("· ads.txt 삭제(publisherId 비어 있음)")


class MarkerError(ValueError):
    pass


# 손으로 쓴 루트 페이지의 마커. 값이 비었을 때의 형태는 여는·닫는 마커가 공백·줄바꿈 없이 붙은 정확한 문자열이다:
#   <!-- adsense:head --><!-- /adsense:head -->
#   <!-- adsense:slot tcoEnd --><!-- /adsense:slot -->
#   <!-- site:contact --><!-- /site:contact -->
MARKER_ANY = re.compile(r"<!--\s*/?\s*(?:adsense:|site:contact)[^>]*-->")
MARKER = re.compile(r"<!-- (/?)(adsense:head|adsense:slot|site:contact)(?: ([A-Za-z][A-Za-z0-9]*))? -->")


def fill_markers(name, text, site):
    """마커 구간 안만 채우거나 비운다 — 마커 바깥은 한 글자도 바꾸지 않는다.
    형식이 다르거나, 닫는 마커가 없거나, 중첩·중복이면 파일명과 줄을 밝히고 MarkerError."""
    def line_of(pos):
        return text.count("\n", 0, pos) + 1

    blocks = []  # (kind, arg, 내용 시작, 내용 끝)
    open_m = None
    seen = set()
    for m in MARKER_ANY.finditer(text):
        sm = MARKER.fullmatch(m.group(0))
        where = f"{name}:{line_of(m.start())}"
        if not sm:
            raise MarkerError(f"{where} 마커 형식이 달라요: {m.group(0)}")
        closing, kind, arg = sm.group(1) == "/", sm.group(2), sm.group(3)
        if (kind == "adsense:slot") != (arg is not None) and not closing:
            raise MarkerError(f"{where} adsense:slot에는 이름이 하나 있어야 하고 다른 마커에는 이름이 없어야 해요: {m.group(0)}")
        if closing:
            if arg is not None:
                raise MarkerError(f"{where} 닫는 마커에는 이름을 쓰지 않아요: {m.group(0)}")
            if not open_m or open_m[0] != kind:
                raise MarkerError(f"{where} 여는 마커 없이 닫는 마커가 있어요: {m.group(0)}")
            blocks.append((open_m[0], open_m[1], open_m[2], m.start()))
            open_m = None
            continue
        if open_m:
            raise MarkerError(f"{where} 마커가 닫히기 전에 다른 마커가 열렸어요(중첩): {m.group(0)}")
        if (kind, arg) in seen:
            raise MarkerError(f"{where} 같은 마커가 두 번 있어요(중복): {m.group(0)}")
        if kind == "adsense:slot" and name == "index.html":
            raise MarkerError(f"{where} 수첩 화면(index.html)에는 광고 슬롯을 넣을 수 없어요: {m.group(0)}")
        seen.add((kind, arg))
        open_m = (kind, arg, m.end())
    if open_m:
        raise MarkerError(f"{name}:{line_of(open_m[2])} '<!-- {open_m[0]}{' ' + open_m[1] if open_m[1] else ''} -->'의 닫는 마커가 없어요")

    slot_names = [arg for kind, arg, _, _ in blocks if kind == "adsense:slot"]
    out, last = [], 0
    for kind, arg, start, end in blocks:
        if kind == "adsense:head":
            content = adsense_head(site, slot_names)
        elif kind == "adsense:slot":
            content = ad_slot(site, arg)
        else:
            content = contact_html(site)
        out.append(text[last:start])
        out.append(content)
        last = end
    out.append(text[last:])
    return "".join(out)


def sync_hand_pages(site):
    """루트 *.html 중 마커가 있는 파일만 채운다. 내용이 바뀔 때만 쓰고, 줄바꿈 문자도 그대로 둔다."""
    for path in sorted(ROOT.glob("*.html")):
        with path.open(encoding="utf-8", newline="") as f:
            text = f.read()
        if not MARKER_ANY.search(text):
            continue
        new = fill_markers(path.name, text, site)
        if new != text:
            with path.open("w", encoding="utf-8", newline="") as f:
                f.write(new)
            print(f"· {path.name} 광고·문의 마커 갱신")


# 상단 내비 3항목 (키, 루트 기준 경로, 이름) — 손으로 쓴 페이지(index·tco·privacy·terms·about)와 같은 계약 마크업
NAV_ITEMS = (("notebook", "index.html", "수첩"), ("tax", "tax/index.html", "자동차세"), ("tco", "tco.html", "유지비 비교"))


def topbar_nav(prefix, active=None):
    """<nav class="topbar-right topbar-nav" aria-label="주 메뉴">…</nav> — 현재 섹션에 aria-current="page"."""
    links = []
    for key, href, label in NAV_ITEMS:
        cur = ' aria-current="page"' if key == active else ""
        links.append(f'<a href="{prefix}{href}"{cur}>{label}</a>')
    return f'<nav class="topbar-right topbar-nav" aria-label="주 메뉴">{"".join(links)}</nav>'


def footer_links(prefix):
    """푸터 2번째 줄 — 순서 고정: 소개·문의 · 개인정보처리방침 · 이용약관 (손으로 쓴 페이지와 같은 계약)."""
    return (f'<p><a href="{prefix}about.html">소개·문의</a> · <a href="{prefix}privacy.html">개인정보처리방침</a> · '
            f'<a href="{prefix}terms.html">이용약관</a></p>')


def page(site, title, description, body, css_prefix="../", canonical=None, og=None, active="tax", head_extra=""):
    """생성 페이지 공통 틀. active = 상단 내비에서 현재 위치('tax' — 세금·허브·계산기 페이지).
    head_extra = head 끝에 넣을 태그(애드센스 소유 확인 메타·광고 스크립트 — adsense_head)."""
    canonical_tag = ""
    if canonical:
        canonical_tag = (
            f'<link rel="canonical" href="{esc(canonical)}">\n  '
            f'<meta property="og:type" content="website">\n  '
            f'<meta property="og:site_name" content="{esc(site["siteName"])}">\n  '
            f'<meta property="og:title" content="{esc(title)}">\n  '
            f'<meta property="og:description" content="{esc(description)}">\n  '
            f'<meta property="og:url" content="{esc(canonical)}">\n  '
        ) + og_image_tags(og)
    head_extra = f"\n  {head_extra}" if head_extra else ""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{esc(description)}">
  <meta name="theme-color" content="#FFFFFF">
  {canonical_tag}<title>{esc(title)}</title>
  <link rel="icon" href="{css_prefix}favicon.ico" sizes="32x32">
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%231A56DB'/%3E%3Ctext x='50' y='67' font-size='52' font-weight='700' text-anchor='middle' fill='%23FFFFFF' font-family='sans-serif'%3E차%3C/text%3E%3C/svg%3E">
  <link rel="apple-touch-icon" href="{css_prefix}icons/apple-touch-icon.png">
  <link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
  <link rel="stylesheet" href="{css_prefix}css/style.css">
  <link rel="stylesheet" href="{css_prefix}css/content.css">
  <script src="{css_prefix}js/analytics.js" defer></script>{head_extra}
</head>
<body>
  <header class="topbar">
    <a class="topbar-title" href="{css_prefix}index.html">{esc(site["siteName"])}</a>
    {topbar_nav(css_prefix, active)}
  </header>
  <main class="content">
{body}
  </main>
  <footer class="foot">
    <p>{esc(site["siteName"])} (베타) — 계산 결과는 참고용이며, 실제 고지 세액은 위택스에서 확인하세요.</p>
    {footer_links(css_prefix)}
  </footer>
</body>
</html>
"""


def prepay_months_label(rates):
    """1월 연납으로 공제받는 달 '2~12월분' — januaryProration.windowMonth 다음 달부터 12월까지."""
    return f"{rates['prepayDiscount']['januaryProration']['windowMonth'] + 1}~12월분"


def faq_items(v, rates, this_year):
    """'자주 묻는 질문' 문답 [(질문, 답)]. 화면 섹션(faq_section)과 FAQPage JSON-LD(faq_jsonld)가 같은 목록을 쓴다 —
    구조화 데이터는 화면에 보이는 내용만 마크업해야 하고(구글 지침), 출처가 하나라 둘이 어긋나지 않는다.
    차령 경감 숫자는 tax-rates.json agingDiscount에서 만든다 (하드코딩 금지)."""
    name = v["name"]
    basis = prepay_basis(rates, this_year, sep="")
    basis = f"({basis})" if basis else ""
    months = prepay_months_label(rates)
    at = aging_terms(rates)
    if v.get("vehicleClass", "passenger") != "passenger":
        t = nonpassenger_tax(v, rates)
        pp = prepay(t["nonBusiness"], rates, this_year)
        kind = "화물자동차" if t["kind"] == "truck" else "승합자동차"
        by = "적재정량 구간" if t["kind"] == "truck" else "규모"
        return [
            (f"{name} 자동차세는 얼마인가요?",
             f"자가용(비영업용)은 연 {t['nonBusiness']:,}원, 영업용은 연 {t['business']:,}원이에요. "
             f"{kind}는 {by}별 정액이라 연식과 관계없이 같아요."),
            ("1월에 연납하면 얼마나 할인되나요?",
             f"연납 공제는 차종과 관계없이 적용돼요. 1월에 신청하면 {months} 세액의 {pp['rate']*100:.0f}%{basis}를 "
             f"공제받아, 자가용 연 {t['nonBusiness']:,}원에서 {pp['discount']:,}원을 뺀 {pp['pay']:,}원을 내요."),
            (f"{kind}도 차령 경감이 되나요?",
             f"아니요. {kind}는 정액이라 차령 경감이 없고 지방교육세도 붙지 않아요."),
        ]
    if v["fuelType"] == "ev":
        ev = rates["displacement"]["ev"]
        annual = ev["annualTotalKrw"]
        pe = prepay(annual, rates, this_year)
        kind = flat_kind(v)
        # 수소전기차는 전기차와 같은 '그 밖의 승용자동차' 정액 — 근거를 답에 밝힌다
        why = ("배기량이 없어 전기차와 같은 '그 밖의 승용자동차'로 분류되고, "
               if is_hydrogen(v) else "배기량이 없어 ")
        return [
            (f"{name} 자동차세는 얼마인가요?",
             f"{kind}(비영업용 승용)는 {why}연 {annual:,}원 정액이에요(본세 {ev['baseKrw']:,}원 + "
             f"지방교육세 {ev['educationTaxKrw']:,}원). 연식과 관계없이 같아요."),
            ("1월에 연납하면 얼마나 할인되나요?",
             f"1월에 연납 신청하면 {months} 세액의 {pe['rate']*100:.0f}%{basis}를 공제받아요. "
             f"연 {annual:,}원 기준 {pe['pay']:,}원을 내요."),
            (f"{kind}도 차령 경감이 되나요?",
             f"아니요. 차령 경감은 배기량 기준 승용차에 적용되고, {kind}는 정액이라 연식이 지나도 세액이 같아요."),
        ]
    cc = v["displacementCc"]
    t1 = tax_for(cc, 1, rates)
    t_full = tax_for(cc, at["fullAge"], rates)
    span = gen_span(v, rates, this_year)
    faqs = []
    if span:  # 단종 세대 — 올해 이 세대의 실제 범위 (페이지마다 다른 문장)
        g, lo, hi = span["g"], span["lo"], span["hi"]
        if YEARS_IN_NAME.search(name):
            q = f"{name}{josa(name, '는', '은')} {this_year}년에 자동차세가 얼마인가요?"
        else:
            q = f"{name}({year_range(v)}년식)은 {this_year}년에 자동차세가 얼마인가요?"
        # '모두 N년차 이상·최대 경감'은 마지막 연식까지 경감 상한에 닿았을 때만 — lo == hi는 한 해짜리 세대
        # (2025~2025년식)에서도 성립하므로 그것으로 가르면 3년차 5%에 '최대 경감'이라고 쓰게 된다
        if g["age"] >= at["fullAge"]:
            a = (f"{this_year}년에는 이 세대가 모두 {at['fullAge']}년차 이상이라 최대 경감 {pct(hi)}가 적용돼 "
                 f"연 {hi['annual']:,}원(본세+지방교육세)이에요. "
                 f"1월에 연납하면 {prepay(hi['annual'], rates, this_year)['pay']:,}원이에요.")
        elif lo["annual"] == hi["annual"]:  # 한 해짜리 세대 — 차령 하나
            a = (f"{g['year']}년에 등록했다면 {this_year}년에 차령 {g['age']}년차라 {pct(hi)} 경감돼 "
                 f"연 {hi['annual']:,}원(본세+지방교육세)이에요. "
                 "등록 연도가 다르면 자동차등록증의 최초 등록 연도로 연식별 표에서 확인하세요.")
        else:
            a = (f"{this_year}년 기준 차령 {g['age']}~{g['oldAge']}년차라 {hi['discountRate']*100:.0f}~{pct(lo)} 경감돼 "
                 f"연 {lo['annual']:,}~{hi['annual']:,}원(본세+지방교육세)이에요. "
                 "정확한 금액은 자동차등록증의 최초 등록 연도로 연식별 표에서 확인하세요.")
        faqs.append((q, a))
    d_age = span["g"]["age"] if span else 1
    d_annual = tax_for(cc, d_age, rates)["annual"]
    dp = prepay(d_annual, rates, this_year)
    d_label = f"{span['g']['year']}년 등록({d_age}년차) 기준" if span else "신차 기준"
    faqs += [
        (f"{name} 자동차세는 얼마인가요?",
         f"배기량 {cc:,}cc 기준 신차는 연 {t1['annual']:,}원(본세+지방교육세)이에요. "
         f"{at['start']}년차부터 차령 경감이 적용돼 {at['fullAge']}년차 이상이면 연 {t_full['annual']:,}원까지 줄어요."),
        ("1월에 연납하면 얼마나 할인되나요?",
         f"1월에 연납 신청하면 {months} 세액의 {dp['rate']*100:.0f}%{basis}를 공제받아요. "
         f"{d_label} 연 {d_annual:,}원에서 {dp['discount']:,}원을 공제받아 {dp['pay']:,}원을 내요."),
        ("차령 경감은 언제부터 적용되나요?",
         f"최초 등록 후 {at['start']}년차부터 (차령 − {at['start'] - 1}) × {at['per']}%씩 경감되고, "
         f"{at['fullAge']}년차 이상이면 최대 {at['max']}%가 경감돼요."),
    ]
    return faqs


def faq_section(faqs):
    """화면의 '자주 묻는 질문' — 질문 15px/500, 답 15px/400. 아이콘·이모지 없음."""
    items = "".join(f'<h3 class="faq-q">{esc(q)}</h3><p class="faq-a">{esc(a)}</p>' for q, a in faqs)
    return f'<h2>자주 묻는 질문</h2>\n<div class="faq">{items}</div>'


def faq_jsonld(faqs):
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                       for q, a in faqs],
    }
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"


def crumb_parts(v, cat):
    """화면 브레드크럼 [(이름, tax/ 기준 href | None)] — '자동차세 › 현대 그랜저 › 그랜저 IG 3.0'.
    가족이 1트림뿐이면 가운데가 브랜드. 가운데 단계는 허브 앵커(index.html#model-…/#brand-…)."""
    mid_name, mid_id = cat.crumb_anchor(v)
    return [("자동차세", "index.html"), (mid_name, f"index.html#{mid_id}"), (v["name"], None)]


def crumb_html(v, cat):
    return '<p class="crumb">' + " › ".join(
        f'<a href="{esc(href)}">{esc(n)}</a>' if href else esc(n) for n, href in crumb_parts(v, cat)) + "</p>"


def breadcrumb_jsonld(v, cat, site):
    """BreadcrumbList — position 1은 홈(사이트 이름), 2부터 화면 크럼과 같은 이름·URL."""
    base = site.get("baseUrl", "").rstrip("/")
    items = [{"@type": "ListItem", "position": 1, "name": site["siteName"], "item": f"{base}/" if base else "/"}]
    for i, (n, href) in enumerate(crumb_parts(v, cat), start=2):
        path = f"/tax/{href or v['slug'] + '.html'}"
        items.append({"@type": "ListItem", "position": i, "name": n, "item": f"{base}{path}"})
    data = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"


def josa(word, no_batchim, with_batchim):
    """받침 유무로 조사 선택 (와/과, 은/는 …). 숫자로 끝나면 읽는 음의 받침을 따른다. 끝의 닫는 괄호는 건너뛴다('… (2015~2018)' → 팔)."""
    if not word:
        return no_batchim
    ch = (word.strip().rstrip(")]") or word.strip())[-1]
    if "가" <= ch <= "힣":
        return with_batchim if (ord(ch) - 0xAC00) % 28 else no_batchim
    if ch.isdigit():  # 영·일·삼·육·칠·팔은 받침 있음
        return with_batchim if ch in "0136 78".replace(" ", "") else no_batchim
    return no_batchim


def class_note_line(v):
    """정원에 따라 승용/승합/화물이 갈리는 모델의 안내 (카니발·스타리아).
    이 페이지의 계산은 승용 사양 기준임을 밝혀야 11인승 소유자가 오해하지 않는다."""
    note = v.get("classNote")
    return f'<p class="compare-line">{esc(note)}</p>' if note else ""


def trim_compare_line(v, all_vehicles, rates, this_year):
    """패키지 트림(N Line 등) 페이지에 같은 모델 일반 트림과의 세액 비교 한 줄.
    중복 콘텐츠를 피하면서 '세금이 더 나오나?'라는 실제 검색 의도에 답한다.
    비교 상대의 금액은 그 차가 히어로·관련 차종 행에 보이는 금액(rep_annual)과 같은 기준이어야 한다.
    판매 중 트림은 판매 중인 일반 트림과만 신차 금액으로 비교한다 — 단종 세대(gen_default 대상)는 화면에
    대표 연식 금액이 보이므로, 그 차의 신차 금액을 쓰면 한 페이지에 같은 차 금액이 둘이 된다.
    단종 트림은 같은 세대의 일반 트림 중 배기량이 같은 차만 '같은 해에 등록했다면 동일'로 잇는다
    (등록 연도마다 금액이 달라 차이를 숫자 하나로 말할 수 없다). 상대가 없으면 줄을 넣지 않는다."""
    if not v.get("trimGroup"):
        return ""
    old = gen_default(v, rates, this_year) is not None
    peers = [
        p for p in all_vehicles
        if p["modelFamily"] == v["modelFamily"] and not p.get("trimGroup") and p["id"] != v["id"]
        and (gen_key(p) == gen_key(v) if old else gen_default(p, rates, this_year) is None)
    ]
    if not peers:
        return ""

    def annual(x):
        if x["fuelType"] == "ev":
            return rates["displacement"]["ev"]["annualTotalKrw"]
        return tax_for(x["displacementCc"], 1, rates)["annual"] if x["displacementCc"] else None

    mine = annual(v)
    if mine is None:
        return ""
    # 배기량이 같은 상대 — 연료가 같은 차 우선(투싼 하이브리드 N Line ↔ 투싼 하이브리드)
    same = sorted((p for p in peers if p.get("displacementCc") == v.get("displacementCc")),
                  key=lambda p: p["fuelType"] != v["fuelType"])
    if same:
        reason = ("전기차는 배기량과 무관하게 정액이라 트림이 달라도 세금이 같아요."
                  if v["fuelType"] == "ev" else
                  "배기량이 같아 세금 차이가 없어요.")
        when = "같은 해에 등록한 " if old else ""
        return (f'<p class="compare-line">이 트림의 자동차세는 {when}'
                f'<strong>일반 {esc(same[0]["name"])}{josa(same[0]["name"], "와", "과")} 동일</strong>해요 — {reason} '
                f"N Line은 외관·서스펜션 등의 패키지 트림이라 과세 기준이 바뀌지 않아요.</p>")
    if old:
        return ""
    priced = [(p, annual(p)) for p in peers if annual(p) is not None]
    if not priced:
        return ""
    base, base_tax = min(priced, key=lambda t: t[1])
    diff = mine - base_tax
    if diff == 0:
        return ('<p class="compare-line">이 트림의 자동차세는 '
                f'<strong>일반 {esc(base["name"])}{josa(base["name"], "와", "과")} 동일</strong>해요.</p>')
    word = "높아요" if diff > 0 else "낮아요"
    return (f'<p class="compare-line">이 트림의 자동차세는 일반 {esc(base["name"])}({base_tax:,}원)보다 '
            f"<strong>연 {abs(diff):,}원 {word}</strong> — 배기량이 달라 과세 구간·세액이 달라져요.</p>")


# 펼침 표시용 단색 라인 chevron (DESIGN: stroke 1.5, currentColor) — 허브·관련 차종 아코디언 공용
CHEVRON = (
    '<svg class="chevron" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">'
    '<path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)

RELATED_OPEN_MAX = 8      # 같은 가족이 이보다 많으면 같은 세대만 펼치고 나머지는 <details>로 접는다
RELATED_PEERS_MAX = 6     # '세금이 같은 차' 최대 개수
RELATED_NEAR_MAX = 3      # 폴백 '배기량이 비슷한 차' 개수


def row_inner(p, rates, this_year):
    """목록 행 안쪽 — 이름 + 12px muted 연식 캡션 + 올해 대표 세액 (허브·관련 차종 공용)."""
    cap = years_caption(p)
    cap_html = f' <span class="hub-years">{cap}</span>' if cap else ""
    return (f'<span class="hub-name">{esc(p["name"])}{cap_html}</span>'
            f'<span class="hub-price">연 {rep_annual(p, rates, this_year):,}원</span>')


def related_row(p, v, rates, this_year, cls="hub-row"):
    """관련 차종 행. 지금 페이지의 차는 링크 없이 aria-current (굵기만 600)."""
    if p["id"] == v["id"]:
        return f'<li><div class="{cls}" aria-current="page">{row_inner(p, rates, this_year)}</div></li>'
    return f'<li><a class="{cls}" href="{esc(p["slug"])}.html">{row_inner(p, rates, this_year)}</a></li>'


def gen_labelled_rows(trims, row_fn):
    """세대가 2개 이상이면 세대 라벨(비대화형 li, 'IG · 2016~2022')을 앞에 붙여 세대별로 나열."""
    groups = gen_groups(trims)
    if len(groups) < 2:
        return "".join(row_fn(p) for p in sorted(trims, key=trim_sort_key))
    return "".join(f'<li class="hub-gen">{esc(label)}</li>' + "".join(row_fn(p) for p in items)
                   for _, label, items in groups)


def same_tax_peers(v, cat, rates, exclude=()):
    """관련 차종 (b) — 세금이 같은 다른 가족의 차. (라벨, 보조 문구, [차])
    승용 내연기관 = 같은 배기량, 전기 = 같은 브랜드 전기차, 화물 = 같은 적재정량, 승합 = 같은 규모.
    하나도 없으면 폴백: 내연기관은 같은 cc당 세율 구간에서 배기량이 가까운 차, 전기는 다른 브랜드 전기차
    (전기·수소는 모두 같은 정액), 화물·승합은 같은 분류에서 가까운 차."""
    others = [p for p in cat.vehicles if family_key(p) != family_key(v) and p["id"] not in exclude]  # (a)에 이미 있는 차 제외
    cls = v.get("vehicleClass", "passenger")

    def order(cands):  # 같은 브랜드 우선, 최신 연식 순
        return sorted(cands, key=lambda p: (p["brand"] != v["brand"],) + trim_sort_key(p))

    if cls == "truck":
        same = [p for p in others if p.get("vehicleClass") == "truck" and p.get("payloadKg") == v.get("payloadKg")]
        if same:
            return (f"세금이 같은 화물차 (적재정량 {v['payloadKg']:,}kg)",
                    "화물차는 적재정량 구간별 정액이라 연식과 관계없이 세액이 같아요.", order(same)[:RELATED_PEERS_MAX])
        near = sorted([p for p in others if p.get("vehicleClass") == "truck" and p.get("payloadKg")],
                      key=lambda p: (abs(p["payloadKg"] - v["payloadKg"]),) + trim_sort_key(p))
        return "적재정량이 비슷한 화물차", "화물차는 적재정량 구간별 정액이에요.", near[:RELATED_NEAR_MAX]
    if cls == "van":
        sizes = {s["key"]: s["label"] for s in rates["van"]["sizes"]}
        same = [p for p in others if p.get("vehicleClass") == "van" and p.get("vanSize") == v.get("vanSize")]
        if same:
            return (f"세금이 같은 승합차 ({sizes.get(v.get('vanSize'), '')})",
                    "승합차는 규모별 정액이라 연식과 관계없이 세액이 같아요.", order(same)[:RELATED_PEERS_MAX])
        near = [p for p in others if p.get("vehicleClass") == "van"]
        return "다른 승합차", "승합차는 규모별 정액이에요.", order(near)[:RELATED_NEAR_MAX]
    if v["fuelType"] == "ev":
        evs = [p for p in others if p.get("vehicleClass", "passenger") == "passenger" and p["fuelType"] == "ev"]
        note = "전기·수소전기차는 차종·연식과 관계없이 같은 정액이에요."
        same = [p for p in evs if p["brand"] == v["brand"]]
        if same:
            return f"세금이 같은 {v['brand']} 전기차", note, order(same)[:RELATED_PEERS_MAX]
        # 다른 브랜드 전기차 — 브랜드마다 최신 1대씩 먼저, 남으면 이어서
        ranked = sorted(evs, key=trim_sort_key)
        picked, seen = [], set()
        for p in ranked:
            if p["brand"] not in seen:
                picked.append(p)
                seen.add(p["brand"])
        picked += [p for p in ranked if p not in picked]
        return "세금이 같은 전기차", note, picked[:RELATED_PEERS_MAX]
    cc = v["displacementCc"]
    same = [p for p in others if is_ice_passenger(p) and p["displacementCc"] == cc]
    if same:
        return (f"세금이 같은 차 ({cc:,}cc)", "배기량이 같아 등록 연도가 같으면 자동차세도 같아요.",
                order(same)[:RELATED_PEERS_MAX])
    per_cc = tax_for(cc, 1, rates)["perCc"]
    near = [p for p in others if is_ice_passenger(p) and tax_for(p["displacementCc"], 1, rates)["perCc"] == per_cc]
    near.sort(key=lambda p: (abs(p["displacementCc"] - cc), p["brand"] != v["brand"]) + trim_sort_key(p))
    return ("배기량이 비슷한 차", f"같은 cc당 세율({per_cc}원/cc) 구간이라 배기량 차이만큼만 세액이 달라요.",
            near[:RELATED_NEAR_MAX])


def related_family(v, cat):
    """같은 가족 + 고성능 N 가족을 한 목록으로 — '아반떼'(현대) ↔ '아반떼 N'(현대 N)처럼 브랜드가 갈려
    허브에서 멀리 떨어진 모델을 서로 잇는다. 반환: (기본 모델 이름, [트림])"""
    name = v["modelFamily"]
    base = name[:-2] if name.endswith(" N") else name
    fam = list(cat.family(v))
    for k, items in cat.families.items():
        if k != family_key(v) and k[1] in (base, base + " N"):
            fam += items
    return base, fam


def related_block(v, cat, rates, this_year):
    """'관련 차종' — 정적 HTML(JS 없음). (a) 같은 가족의 다른 세대·트림 (b) 세금이 같은 차(없으면 폴백)
    (c) 계산기 안내. 차종 페이지마다 다른 내용·링크가 생겨 막다른 길과 근사 중복을 줄인다."""
    out = ["<h2>관련 차종</h2>"]
    base, fam = related_family(v, cat)
    fam = sorted(fam, key=trim_sort_key)
    if len(fam) >= 2:
        out.append(f'<h3 class="related-label">같은 {esc(base)} 다른 세대·트림</h3>')
        if len(fam) <= RELATED_OPEN_MAX:
            rows = "".join(related_row(p, v, rates, this_year) for p in fam)
        else:  # 같은 세대만 펼치고 나머지는 접는다 (접혀도 링크는 HTML에 남는다)
            mine = [p for p in fam if gen_key(p) == gen_key(v)]
            rest = [p for p in fam if gen_key(p) != gen_key(v)]
            rows = "".join(related_row(p, v, rates, this_year) for p in mine)
            if rest:
                keys = "·".join(k for k, _, _ in gen_groups(rest) if k)
                inner = gen_labelled_rows(rest, lambda p: related_row(p, v, rates, this_year, cls="hub-trim"))
                rows += (f'<li><details class="hub-group"><summary class="hub-row">'
                         f'<span>다른 세대 {len(rest)}개{" (" + esc(keys) + ")" if keys else ""}</span>'
                         f'<span class="hub-right">{CHEVRON}</span></summary>'
                         f'<ul class="hub-trims">{inner}</ul></details></li>')
        out.append(f'<ul class="hub-list">{rows}</ul>')
    label, note, peers = same_tax_peers(v, cat, rates, exclude={p["id"] for p in fam})
    if peers:
        out.append(f'<h3 class="related-label">{esc(label)}</h3><p class="related-note">{esc(note)}</p>'
                   '<ul class="hub-list">' + "".join(related_row(p, v, rates, this_year) for p in peers) + "</ul>")
    if v.get("vehicleClass", "passenger") == "passenger":
        out.append('<p class="related-calc">목록에 없거나 배기량이 다르면 '
                   '<a href="calculator.html">자동차세 계산기</a>에서 바로 계산해 보세요.</p>')
    else:
        out.append('<p class="related-calc">승용차 자동차세는 '
                   '<a href="calculator.html">자동차세 계산기</a>에서 배기량으로 계산할 수 있어요.</p>')
    return "\n".join(out)


def spec_box(v, site):
    """'한눈에' 미니 박스 (TASKS 개편 B). 연비·주행거리는 null이면 해당 줄 미노출 — 추정 금지."""
    rows = []
    if v["displacementCc"]:
        rows.append(("배기량", f"{v['displacementCc']:,}cc"))
    energy = energy_source(v)
    unit = ENERGY_UNIT.get(energy, "L")  # 연비·단가 단위는 과세 구분이 아니라 실제 에너지를 따른다
    rows.append(("연료", "수소" if energy == "hydrogen" else FUEL_LABELS.get(v["fuelType"], v["fuelType"])))
    fe = v.get("fuelEconomy")
    is_ev = v["fuelType"] == "ev"
    if fe:
        rows.append(("공인연비", f"{fe}km/{unit} (복합)"))
    if is_ev and v.get("rangeKm"):
        rows.append(("인증 주행거리", f"{v['rangeKm']:,}km" + (" (상온 복합)" if energy == "electricity" else "")))
    body = "".join(
        f'<div class="spec-row"><span class="spec-label">{a}</span><span>{b}</span></div>'
        for a, b in rows
    )
    # 병합 구간에서 엔진이 바뀐 차종 등, 연비 값의 기준을 밝혀야 오해가 없는 경우
    if fe and v.get("fuelEconomyNote"):
        body += f'<div class="spec-note">{esc(v["fuelEconomyNote"])}</div>'
    fuel_line = ""
    prices = site.get("fuelPrices", {})
    basis_km = site.get("fuelCostBasisKm", 15000)
    price = prices.get(ENERGY_PRICE_KEY.get(energy, energy))  # 단가가 null(미확인)이면 연료비 줄 미노출
    if fe and price:
        annual_cost = round(basis_km / fe * price)
        fuel_line = (
            f'<div class="spec-fuel">공인연비 기준 연 {basis_km:,}km 주행 시 연료비 약 '
            f'<strong>{annual_cost:,}원</strong> <span>({price:,}원/{unit} 기준)</span></div>'
        )
    return f'<div class="card spec-box">{body}{fuel_line}</div>'


def notebook_cta(v):
    """세금 페이지 → 수첩 프리필 등록 CTA (TASKS #2). 연식 선택 시 JS가 &year= 추가.
    유지비 비교(js/tco.js)는 승용만 목록에 넣으므로 화물·승합 페이지에는 비교 링크를 붙이지 않는다."""
    # 수첩은 화물·승합차에 승용 검사 주기를 적용하지 않는다(js/derive.js passengerInspectionApplies) — 검사 D-day를 약속하지 않는다
    promise = ("소모품 교체 주기·검사 D-day까지 수첩이 챙겨드려요." if v.get("vehicleClass", "passenger") == "passenger"
               else "소모품 교체 주기를 수첩이 챙겨드려요.")
    params = f"model={v['slug']}&fuel={v['fuelType']}"
    if v["displacementCc"]:
        params += f"&cc={v['displacementCc']}"
    # 제목은 h2가 아니라 p(15px/500) — 문서 개요에서 CTA가 섹션 제목이 되지 않게. 스타일은 content.css .cta-*
    return f"""<div class="card cta-card">
  <p class="cta-title">이 차를 타고 계신가요?</p>
  <p class="cta-desc">{promise} 차종·배기량은 미리 채워둘게요.</p>
  <a id="start-notebook" class="btn cta-btn" href="../index.html?{params}">이 차로 수첩 시작하기</a>
</div>""" + ("" if v.get("vehicleClass", "passenger") != "passenger" else f"""
<a class="btn secondary cta-btn cta-secondary" href="../tco.html?car={v["slug"]}">이 차와 다른 차 유지비 비교하기</a>""")


def sources_block(rates, this_year):
    links = " · ".join(
        f'<a href="{esc(s["url"])}" rel="noopener" target="_blank">{esc(s["label"])}</a>'
        for s in rates["sources"]
    )
    # 연납 공제율이 당해 연도 것이 아니면(폴백) 여기서도 밝힌다. 연납 항목만 따로 재확인했으면 그 시점도 표기
    basis = prepay_basis(rates, this_year, sep="")
    basis = f"(연납은 {basis})" if basis else ""
    pv = rates["prepayDiscount"].get("lastVerified")
    checked = f" · 연납 기준 확인 {pv}" if pv and pv != rates["lastVerified"] else ""
    return (
        '<div class="sources"><p>근거 법령·출처: ' + links + "</p>"
        f"<p>{this_year}년 세율 기준{basis} · 최종 확인 {rates['lastVerified']}{checked}. "
        "세액은 10원 미만 절사 기준으로 계산한 참고값이에요. 실제 고지서와 단수 차이가 있을 수 있어요.</p></div>"
    )


def table_img_script(v, site, rates, this_year):
    base = site.get("baseUrl", "").rstrip("/")
    watermark = base.replace("https://", "").replace("http://", "") if base else site["siteName"]
    return (
        TABLE_IMG_SCRIPT
        .replace("__TITLE__", f"{v['name']} 자동차세")
        .replace("__META__", f"{v['displacementCc']:,}cc · {this_year}년 세율 기준 · 연납은 1월 신청"
                             + (prepay_basis(rates, this_year, sep="·") or " 기준"))
        .replace("__WATERMARK__", watermark)
        .replace("__SLUG__", v["slug"])
    )


def lump_sum_text(rates):
    """6월 일괄부과 안내 문장 (차종 페이지 lump_sum_note·계산기 결과 카드 공용). 기준이 없으면 빈 문자열."""
    th = rates["prepayDiscount"].get("lumpSumThresholdKrw")
    if not th:
        return ""
    th_label = f"{th // 10000}만원" if th % 10000 == 0 else f"{th:,}원"
    # 6·9월 연납이 해당하지 않는 것은 확정, 1·3월 신청 가능 여부는 1차 출처로 확정 전이라 단서형으로 쓴다
    windows = prepay_windows(rates)
    no = "·".join(str(w["month"]) for w in windows if not w.get("lumpSumEligible", True))
    yes = "·".join(str(w["month"]) for w in windows if w.get("lumpSumEligible", True))
    tail = f" 이때 {no}월 연납은 해당하지 않아요." if no else ""
    if yes:
        tail += f" {yes}월 연납 신청 가능 여부는 등록지 시·군·구청에 확인하세요."
    return (f"자동차세 본세(지방교육세 제외)가 연 {th_label} 이하인 차량은 지자체가 6월에 1년치를 한꺼번에 부과하면서 "
            f"공제를 자동 반영하는 경우가 있어요.{tail}")


def lump_note_toggle(cc, rates, default_age=1):
    """승용 페이지용 일괄부과 안내 — 연식 선택(차령)에 따라 JS가 켜고 끈다. 어느 차령에서도 해당 없으면 넣지 않는다.
    페이지 기본 차령(판매 중 = 신차, 단종 세대 = gen_default 대표 연식)에서 해당하면 처음부터 보이고, 아니면 hidden.
    표 행은 TABLE_MAX_AGE까지라 그보다 오래된 차령은 마지막 행('13년차+')으로 본다."""
    text = lump_sum_text(rates)
    flags = [lump_sum_only(tax_for(cc, a, rates)["base"], rates) for a in range(1, TABLE_MAX_AGE + 1)]
    if not text or not any(flags):
        return ""
    row = min(max(default_age, 1), TABLE_MAX_AGE)
    return f'<p class="notice" id="lump-note"{"" if flags[row - 1] else " hidden"}>{text}</p>'


def lump_sum_note(base, rates):
    """본세(지방교육세 제외)가 소액이면 6월에 1년치가 부과되며 그때 자동 공제된다 — 6·9월 연납은 해당 없음(1·3월은 등록지 확인 안내).
    base = 본세. 승용은 지방교육세를 뺀 값을 넘길 것 (기준이 '지방교육세 별도' 연세액)."""
    if not lump_sum_only(base, rates):
        return ""
    return f'<p class="notice">{lump_sum_text(rates)}</p>'


def nonpassenger_page(v, rates, site, this_year, cat, og=None):
    """화물·승합 페이지. 정액이라 연식별 표를 만들지 않는다(전 행이 같은 값이라 무의미)."""
    t = nonpassenger_tax(v, rates)
    pp = prepay(t["nonBusiness"], rates, this_year)  # 연납은 차종 구분 없이 적용(지방세법 제128조 제3항)
    name = v["name"]
    is_truck = t["kind"] == "truck"
    kind_label = "화물자동차" if is_truck else "승합자동차"
    crumb = crumb_html(v, cat)

    # 같은 배기량이라면 승용차는 얼마인지 — 왜 이렇게 낮은지 이해를 돕는다
    compare = ""
    if v.get("displacementCc"):
        p = tax_for(v["displacementCc"], 1, rates)["annual"]
        compare = (f'<p class="compare-line">같은 배기량({v["displacementCc"]:,}cc) 승용차라면 연 {p:,}원이에요 — '
                   f"{kind_label}는 배기량이 아니라 "
                   f"{'적재정량' if is_truck else '규모'} 기준이라 훨씬 낮아요.</p>")

    if is_truck:
        parts = []
        prev = 0
        for b in rates["truck"]["brackets"]:
            hl = ' class="hl"' if prev < v["payloadKg"] <= b["maxKg"] else ""
            parts.append(f'<tr{hl}><td>{b["maxKg"]:,}kg 이하</td>'
                         f'<td>{b["nonBusinessKrw"]:,}원</td><td>{b["businessKrw"]:,}원</td></tr>')
            prev = b["maxKg"]
        rows = "".join(parts)
        table = ('<h2>적재정량별 세액</h2><div class="table-wrap"><table class="data"><thead><tr>'
                 "<th>적재정량</th><th>자가용(비영업용)</th><th>영업용</th></tr></thead><tbody>"
                 + rows + "</tbody></table></div>"
                 f'<p class="notice">{esc(rates["truck"]["over10tNote"])}</p>')
        basis_desc = (f'<p>{esc(name)}{josa(name, "는", "은")} 적재정량 {v["payloadKg"]:,}kg 화물자동차예요. '
                      "화물자동차 자동차세는 배기량과 관계없이 적재정량 구간별 정액으로 부과돼요.</p>")
    else:
        parts = []
        for sz in rates["van"]["sizes"]:
            hl = ' class="hl"' if sz["key"] == v.get("vanSize", "small") else ""
            parts.append(f'<tr{hl}><td>{esc(sz["label"])}</td>'
                         f'<td>{sz["nonBusinessKrw"]:,}원</td><td>{sz["businessKrw"]:,}원</td></tr>')
        rows = "".join(parts)
        table = ('<h2>규모별 세액</h2><div class="table-wrap"><table class="data"><thead><tr>'
                 "<th>구분</th><th>자가용(비영업용)</th><th>영업용</th></tr></thead><tbody>"
                 + rows + "</tbody></table></div>"
                 f'<p class="notice">대형 기준: {esc(rates["van"]["largeCriteria"])}</p>')
        basis_desc = (f'<p>{esc(name)}{josa(name, "는", "은")} 승차정원 11인 이상 승합자동차예요. '
                      "승합자동차 자동차세는 배기량과 관계없이 규모별 정액으로 부과돼요.</p>")
    at = aging_terms(rates)
    flat_desc = (f"<p>연식과 관계없이 정액이에요. 승용차와 달리 차령 경감({at['start']}년차부터 {at['per']}%씩)이 "
                 f"적용되지 않고, 지방교육세 {at['edu']}%도 붙지 않아요. 그래서 신차든 10년차든 세액이 같아요.</p>")
    faqs = faq_items(v, rates, this_year)

    # 순서: … 표 → primary CTA → h2 계산 방법(산문) → [광고 자리] → 자주 묻는 질문 → 관련 차종 → 기준일 캡션.
    # CTA 바로 뒤에 광고가 붙지 않도록 계산 방법 산문을 CTA와 광고 사이에 둔다
    body = f"""{crumb}
<h1>{esc(name)} 자동차세</h1>
<p class="tax-caption">{esc(kind_label)} · {esc(t["basisLabel"])} · 자가용 기준</p>
<div class="tax-hero">연 {t["nonBusiness"]:,}원</div>
<p class="prepay-line">1월 연납 시 <span class="accent">{pp["pay"]:,}원</span> · {pp["discount"]:,}원 할인{prepay_basis(rates, this_year)} &nbsp;|&nbsp; 영업용 {t["business"]:,}원</p>
{prepay_banner(rates, this_year, lump_sum=lump_sum_only(t["nonBusiness"], rates))}
<div class="card spec-box">
  <div class="spec-row"><span class="spec-label">분류</span><span>{esc(kind_label)}</span></div>
  <div class="spec-row"><span class="spec-label">과세 기준</span><span>{esc(t["basisLabel"])}</span></div>
  <div class="spec-row"><span class="spec-label">연료</span><span>{esc(FUEL_LABELS.get(v["fuelType"], v["fuelType"]))}</span></div>
</div>
{class_note_line(v)}{compare}
{table}
{lump_sum_note(t["nonBusiness"], rates)}
{notebook_cta(v)}
<h2>계산 방법</h2>
{basis_desc}
{flat_desc}
{ad_slot(site, "taxArticle")}
{faq_section(faqs)}
{related_block(v, cat, rates, this_year)}
{sources_block(rates, this_year)}
{faq_jsonld(faqs)}
{breadcrumb_jsonld(v, cat, site)}"""
    title = f"{name} 자동차세 — 연 {t['nonBusiness']:,}원 (자가용) | {site['siteName']}"
    nm_kind = f"{name} · {kind_label}" if name.endswith(")") else f"{name}({kind_label})"  # ')(' 중복 방지
    desc = (f"{nm_kind} 자동차세는 자가용 연 {t['nonBusiness']:,}원, 영업용 {t['business']:,}원. "
            f"{'적재정량' if is_truck else '규모'} 기준 정액이라 연식과 무관합니다.")
    return page(site, title, desc, body, canonical=page_canonical(site, f"tax/{v['slug']}.html"), og=og,
                head_extra=adsense_head(site, ("taxArticle",)))


def vehicle_page(v, rates, site, this_year, cat, og=None):
    cc = v["displacementCc"]
    name = v["name"]
    fuel = FUEL_LABELS.get(v["fuelType"], v["fuelType"])
    crumb = crumb_html(v, cat)

    if v["fuelType"] == "ev":
        ev = rates["displacement"]["ev"]
        annual = ev["annualTotalKrw"]
        pp = prepay(annual, rates, this_year)
        faqs = faq_items(v, rates, this_year)
        # 순서: … primary CTA → h2 계산 방법(산문) → [광고 자리] → 자주 묻는 질문 → 관련 차종 → 기준일 캡션
        body = f"""{crumb}
<h1>{esc(name)} 자동차세</h1>
<p class="tax-caption">{esc(fuel_caption(v))} · 비영업용 승용 · 연식 무관 정액</p>
<div class="tax-hero">연 {annual:,}원</div>
<p class="prepay-line">1월 연납 시 <span class="accent">{pp["pay"]:,}원</span> · {pp["discount"]:,}원 할인{prepay_basis(rates, this_year)}</p>
{prepay_banner(rates, this_year, lump_sum=lump_sum_only(ev["baseKrw"], rates))}
{spec_box(v, site)}
{class_note_line(v)}{trim_compare_line(v, cat.vehicles, rates, this_year)}
{lump_sum_note(ev["baseKrw"], rates)}
{notebook_cta(v)}
<h2>계산 방법</h2>
<p>{flat_basis_text(v)} 배기량 기준 대신 정액(본세 {won(ev["baseKrw"])} + 지방교육세 {won(ev["educationTaxKrw"])})이 적용돼요. 차령 경감도 적용되지 않아요.</p>
{ad_slot(site, "taxArticle")}
{faq_section(faqs)}
{related_block(v, cat, rates, this_year)}
{sources_block(rates, this_year)}
{faq_jsonld(faqs)}
{breadcrumb_jsonld(v, cat, site)}"""
        title = f"{name} 자동차세 — 연 {annual:,}원 고정 | {site['siteName']}"
        why = "수소전기차도 전기차와 같은 '그 밖의 승용자동차' 정액" if is_hydrogen(v) else "전기차 정액"
        desc = f"{name} 자동차세는 연 {annual:,}원 고정({why}). 연납 할인과 계산 근거까지 정리했습니다."
        return page(site, title, desc, body, canonical=page_canonical(site, f"tax/{v['slug']}.html"), og=og,
                    head_extra=adsense_head(site, ("taxArticle",)))

    new_tax = tax_for(cc, 1, rates)
    # 단종 세대는 대표 금액을 마지막 연식 기준으로 (gen_default). 판매 중이면 신차 기준 그대로
    span = gen_span(v, rates, this_year)
    g = span["g"] if span else None
    d_age = g["age"] if g else 1   # 실제 차령 — 캡션·FAQ 문구
    d_row = g["row"] if g else 1   # 연식표 행(13년차+까지) — 하이라이트·일괄부과 안내
    d_tax = tax_for(cc, d_age, rates)
    d_prepay = prepay(d_tax["annual"], rates, this_year)
    basis = prepay_basis(rates, this_year)  # 폴백이면 " · 2026년 공제율 기준"
    basis_paren = f"({prepay_basis(rates, this_year, sep='')})" if basis else ""
    # 캡션: 단종 세대는 '세대 연식 · 기준 등록 연도', 판매 중은 '연료 · 배기량 · 비영업용 승용 · 신차 기준'
    if g:
        cap_prefix = f"{v.get('generation') or ''} {year_range(v)}년식".strip()
        d_caption = f"{cap_prefix} · {g['year']}년 등록({d_age}년차) 기준"
    else:
        cap_prefix = f"{fuel} · {cc:,}cc · 비영업용 승용"
        d_caption = f"{cap_prefix} · 신차 기준"

    rows = []
    row_data = {}
    for age in range(1, TABLE_MAX_AGE + 1):
        t = tax_for(cc, age, rates)
        p = prepay(t["annual"], rates, this_year)
        year_text, sub = age_row_label(age, this_year)
        hl = ' class="hl"' if g and age == d_row else ""
        rows.append(
            f'<tr id="age-{age}"{hl}><td>{year_text}<span class="age-sub">{sub}</span></td>'
            f"<td>{t['discountRate']*100:.0f}%</td><td>{won(t['annual'])}</td><td>{won(p['pay'])}</td></tr>"
        )
        row_data[str(age)] = {"label": year_text + sub, "annual": t["annual"], "pay": p["pay"],
                              "lump": lump_sum_only(t["base"], rates)}
    table = (
        '<div class="table-wrap"><table class="data"><thead><tr>'
        "<th>등록 연도</th><th>경감률</th><th>연세액</th><th>1월 연납 시</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )

    # select에는 selected를 주지 않는다 — 비어 있음 = 페이지 기본(단종 세대는 대표 연식, 판매 중은 신차).
    # 그래야 수첩 CTA의 &year=가 사용자가 직접 고를 때만 붙는 동작과 화면이 어긋나지 않는다.
    # 단종 세대는 표보다 오래된 연식(캡션의 기본 등록 연도 포함)도 고를 수 있게 첫 연식까지 넣는다 — 금액은 '13년차+' 행
    oldest = this_year - TABLE_MAX_AGE
    if g:
        oldest = min(oldest, v.get("modelYearFrom") or g["year"])
    year_options = "".join(
        f'<option value="{y}">{y}년</option>' for y in range(this_year, oldest - 1, -1)
    )
    # DESIGN.md: 히어로 금액·연납 한 줄이 연식 선택에 반응한다 (별도 결과 카드 없음)
    picker = f"""<div class="year-picker">
  <label for="reg-year">우리 차 등록 연도</label>
  <select id="reg-year"><option value="">등록 연도 선택</option>{year_options}</select>
</div>
<p class="notice">자동차등록증의 최초 등록 연도로 고르세요.</p>
<script>
(function () {{
  var rows = {json.dumps(row_data, ensure_ascii=False)};
  window.__TAX_ROWS__ = rows; // 표 이미지 저장(#10)에서 재사용
  var THIS_YEAR = {this_year}, MAX_AGE = {TABLE_MAX_AGE};
  // 선택을 비우면 페이지 기본으로 돌아간다 (단종 세대 = 대표 연식, 판매 중 = 신차) — build.py gen_default
  var DEFAULT_AGE = {d_age}, DEFAULT_HL = {"true" if g else "false"};
  var DEFAULT_CAPTION = {json.dumps(d_caption, ensure_ascii=False)}, CAPTION_PREFIX = {json.dumps(cap_prefix, ensure_ascii=False)};
  var sel = document.getElementById('reg-year');
  sel.addEventListener('change', function () {{
    document.querySelectorAll('tr.hl').forEach(function (r) {{ r.classList.remove('hl'); }});
    var realAge = sel.value ? Math.max(1, THIS_YEAR - Number(sel.value) + 1) : DEFAULT_AGE;
    var age = Math.min(MAX_AGE, realAge);
    var d = rows[String(age)];
    document.getElementById('hero-amount').textContent = '연 ' + d.annual.toLocaleString('ko-KR') + '원';
    document.getElementById('prepay-line').innerHTML = '1월 연납 시 <span class="accent">' +
      d.pay.toLocaleString('ko-KR') + '원</span> · ' + (d.annual - d.pay).toLocaleString('ko-KR') + '원 할인__BASIS__';
    document.getElementById('tax-caption').textContent = sel.value ?
      CAPTION_PREFIX + ' · ' + sel.value + '년 등록(' + realAge + '년차) 기준' : DEFAULT_CAPTION;
    if (sel.value || DEFAULT_HL) {{
      var row = document.getElementById('age-' + age);
      if (row) {{
        row.classList.add('hl');
        if (sel.value) row.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
      }}
    }}
    // 차령 경감으로 본세가 기준 이하가 되면 6월 일괄부과 차량 — 6·9월 연납 안내를 빼고 일괄부과 안내를 보인다
    var lumpNote = document.getElementById('lump-note');
    if (lumpNote) lumpNote.hidden = !d.lump;
    var B = window.ChailjiPrepayBanner, bannerEl = document.querySelector('.prepay-banner');
    if (B && B.update && bannerEl) B.update(bannerEl, {{ lumpSum: d.lump }});
    var cta = document.getElementById('start-notebook');
    if (cta) {{
      var base = cta.getAttribute('href').split('&year=')[0];
      cta.setAttribute('href', sel.value ? base + '&year=' + sel.value : base);
    }}
  }});
}})();
</script>""".replace("__BASIS__", esc(basis))

    at = aging_terms(rates)
    faqs = faq_items(v, rates, this_year)
    # 순서: 브레드크럼 → 제목 → 히어로 금액 → 연납 한 줄(+ 신청 기간 안내 줄) → h2 연식별 → 연식 select → 표
    # → 표 이미지 저장 → 일괄부과 안내 → primary CTA → h2 계산 방법(산문) → [광고 자리] → 자주 묻는 질문
    # → 관련 차종 → 기준일 캡션(.sources, 맨 끝). 광고 자리는 CTA·select·표와 떨어지게 계산 방법 산문 뒤
    body = f"""{crumb}
<h1>{esc(name)} 자동차세</h1>
<p class="tax-caption" id="tax-caption">{esc(d_caption)}</p>
<div class="tax-hero" id="hero-amount">연 {d_tax["annual"]:,}원</div>
<p class="prepay-line" id="prepay-line">1월 연납 시 <span class="accent">{d_prepay["pay"]:,}원</span> · {d_prepay["discount"]:,}원 할인{basis}</p>
{prepay_banner(rates, this_year, lump_sum=lump_sum_only(d_tax["base"], rates), age_based=True)}
{spec_box(v, site)}
{gen_summary_line(v, rates, this_year)}{class_note_line(v)}{trim_compare_line(v, cat.vehicles, rates, this_year)}
<h2>{esc(name)} 연식별 자동차세</h2>
{picker}
{table}
<button type="button" class="btn secondary table-save" id="save-table-img">표를 이미지로 저장 (공유용)</button>
{table_img_script(v, site, rates, this_year)}
{lump_note_toggle(cc, rates, d_row)}
{notebook_cta(v)}
<h2>계산 방법</h2>
<p>본세 = 배기량 × cc당 세액({new_tax["perCc"]}원/cc 구간) → 차령 {at["start"]}년차부터 (차령 − {at["start"] - 1}) × {at["per"]}% 경감(최대 {at["max"]}%) → 지방교육세 {at["edu"]}% 가산. 6월·12월에 절반씩 부과되며, 1월에 연납 신청하면 {prepay_months_label(rates)}의 {d_prepay["rate"]*100:.0f}%를 공제받아요{basis_paren}. 공제액은 날짜로 나눠 연세액 × {d_prepay["days"]}/{d_prepay["yearDays"]}({prepay_period_label(rates, this_year)} 일수 ÷ 그 해 일수) × {d_prepay["rate"]*100:.0f}%로 계산하고 10원 미만은 버려요.</p>
<p>차령은 대략 올해 − 등록 연도 + 1로 계산해요.</p>
{ad_slot(site, "taxArticle")}
{faq_section(faqs)}
{related_block(v, cat, rates, this_year)}
{sources_block(rates, this_year)}
{faq_jsonld(faqs)}
{breadcrumb_jsonld(v, cat, site)}"""

    # 이름이 ')'로 끝나면 '(1,995cc)'를 붙이지 않는다 — ')(' 중복 방지
    nm_cc = f"{name} · {cc:,}cc" if name.endswith(")") else f"{name}({cc:,}cc)"
    if span:
        amt = amount_range_text(span["lo"]["annual"], span["hi"]["annual"])
        named = YEARS_IN_NAME.search(name)  # 이름에 연식이 있으면 괄호로 또 쓰지 않는다
        yrs = "" if named else f" ({year_range(v)}년식)"
        title = f"{name} 자동차세 — {this_year}년 {amt}{yrs} | {site['siteName']}"
        desc = (f"{nm_cc} 자동차세는 {this_year}년 기준 {amt}({'' if named else year_range(v) + '년식, '}차령 경감 반영). "
                f"등록 연도별 세액·1월 연납 할인까지 표로 정리했습니다.")
    else:
        title = f"{name} 자동차세 — 신차 연 {new_tax['annual']:,}원, 연식별 계산표 | {site['siteName']}"
        desc = (f"{nm_cc} 자동차세는 신차 기준 연 {new_tax['annual']:,}원. "
                f"연식(차령)별 경감·1월 연납 할인까지 표로 정리했습니다.")
    return page(site, title, desc, body, canonical=page_canonical(site, f"tax/{v['slug']}.html"), og=og,
                head_extra=adsense_head(site, ("taxArticle",)))


def pct(t):
    """tax_for 결과의 경감률 '35%'."""
    return f"{t['discountRate']*100:.0f}%"


def gen_summary_line(v, rates, this_year):
    """단종 세대 히어로 아래 한 줄 요약 — 세대 전체의 올해 세액 범위. 판매 중이면 빈 문자열."""
    span = gen_span(v, rates, this_year)
    if not span:
        return ""
    g, lo, hi = span["g"], span["lo"], span["hi"]
    yrs = f"{year_range(v)}년식"
    if g["age"] >= max_discount_age(rates):  # 마지막 연식까지 경감 상한 — 세대 전체가 같은 금액
        new = tax_for(v["displacementCc"], 1, rates)["annual"]
        return (f'<p class="compare-line">{this_year}년 기준 이 세대({yrs})는 모두 차령 경감 {pct(hi)}가 적용돼 '
                f'<strong>연 {hi["annual"]:,}원</strong>이에요 — 신차 금액(연 {new:,}원)은 이 세대에 해당 없어요.</p>')
    if lo["annual"] == hi["annual"]:  # 한 해짜리 세대(2025년식) — 차령이 하나뿐이고 상한도 아니다
        return (f'<p class="compare-line">{this_year}년 기준 이 세대({yrs})는 차령 {g["age"]}년차라 {pct(hi)} 경감돼 '
                f'<strong>연 {hi["annual"]:,}원</strong>이에요. 등록 연도를 고르면 정확한 금액이 나와요.</p>')
    return (f'<p class="compare-line">{this_year}년 기준 이 세대({yrs})는 차령 {g["age"]}~{g["oldAge"]}년차라 '
            f'{hi["discountRate"]*100:.0f}~{pct(lo)} 경감돼 <strong>{amount_range_text(lo["annual"], hi["annual"])}</strong>이에요. '
            "등록 연도를 고르면 정확한 금액이 나와요.</p>")


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
    ctx.fillText('등록 연도', 24, y);
    ctx.textAlign = 'right';
    ctx.fillText('연세액', 440, y);
    ctx.fillText('1월 연납 시', 690, y);
    ctx.textAlign = 'left';
    ages.forEach(function (age, i) {
      y += rowH;
      if (i % 2 === 1) { ctx.fillStyle = '#f7f9fc'; ctx.fillRect(0, y - 28, W, rowH); }
      ctx.fillStyle = '#1b2430'; ctx.font = '15px ' + font;
      ctx.fillText(rows[age].label, 24, y); // 화면 표 첫 열과 같은 문구 (build.py age_row_label)
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
    if (!ev && (!isFinite(cc) || cc <= 0)) { card.hidden = true; tableWrap.innerHTML = ''; banner(false, true); return; }
    var yearSel = $('calc-year').value;
    var thisYear = __THIS_YEAR__;
    var nowYear = new Date().getFullYear(); // 연납 공제율·일수 기준 (tax-rates.json fallbackRule·januaryProration)
    var age = yearSel ? Math.min(__MAX_AGE__, Math.max(1, thisYear - Number(yearSel) + 1)) : 1;
    var annual, base, label;
    if (ev) {
      annual = T.evTax(rates);
      base = rates.displacement.ev.baseKrw;
      label = '전기차·수소전기차 정액 (연식 무관)';
      tableWrap.innerHTML = '';
    } else {
      cc = Math.round(cc);
      var t = T.taxFor(rates, cc, age);
      annual = t.annual;
      base = t.base;
      label = cc.toLocaleString('ko-KR') + 'cc · ' +
        (yearSel ? yearSel + '년 등록 · ' + age + '년차' + (age === __MAX_AGE__ ? ' 이상' : '') : '신차 기준') +
        (t.discountRate ? ' · ' + Math.round(t.discountRate * 100) + '% 경감' : '');
      var rows = '';
      for (var a = 1; a <= __MAX_AGE__; a++) {
        var ta = T.taxFor(rates, cc, a);
        var pa = T.prepay(rates, ta.annual, nowYear);
        // 첫 열은 차종 페이지 연식표와 같은 형식 — '2026년' + 12px muted ' · 신차'/' · N년차'/' · 13년차+' (build.py age_row_label)
        var sub = a === 1 ? '신차' : (a === __MAX_AGE__ ? a + '년차+' : a + '년차');
        rows += '<tr' + (yearSel && a === age ? ' class="hl"' : '') + '><td>' + (thisYear - a + 1) + '년<span class="age-sub"> · ' + sub +
          '</span></td><td>' + Math.round(ta.discountRate * 100) + '%</td><td>' + won(ta.annual) + '</td><td>' + won(pa.pay) + '</td></tr>';
      }
      tableWrap.innerHTML = '<table class="data"><thead><tr><th>등록 연도</th><th>경감률</th><th>연세액</th><th>1월 연납 시</th></tr></thead><tbody>' + rows + '</tbody></table>';
    }
    var p = T.prepay(rates, annual, nowYear);
    $('cr-label').textContent = label;
    $('cr-amount').textContent = '연 ' + won(annual);
    $('cr-prepay').textContent = '1월 연납 시 ' + won(p.pay) + ' (' + won(p.discount) + ' 할인)' +
      (p.fallback ? ' · ' + p.year + '년 공제율 기준' : '');
    // 본세(지방교육세 제외)가 기준 이하면 6월 일괄부과 차량 — 6·9월 연납이 없다 (build.py lump_sum_only와 같은 기준).
    // 신청 기간 안내 줄에서 6·9월을 빼고 결과 카드에 일괄부과 안내를 붙인다
    var th = rates.prepayDiscount.lumpSumThresholdKrw;
    var lump = !!th && base <= th;
    $('cr-lump').hidden = !lump;
    banner(lump, !ev);
    card.hidden = false;
  }
  // 연납 신청 기간 안내 줄을 입력에 맞춰 다시 그린다 (js/prepay-banner.js). 전기차는 차령과 무관한 정액
  function banner(lumpSum, ageBased) {
    var B = window.ChailjiPrepayBanner, el = document.querySelector('.prepay-banner');
    if (B && B.update && el) B.update(el, { lumpSum: lumpSum, ageBased: ageBased });
  }
  document.addEventListener('input', render);
  document.addEventListener('change', render);
})();
</script>"""


def calculator_page(rates, site, this_year, og=None):
    year_options = "".join(
        f'<option value="{y}">{y}년</option>' for y in range(this_year, this_year - TABLE_MAX_AGE - 1, -1)
    )
    d = rates["displacement"]
    at = aging_terms(rates)
    bracket_rows = "".join(
        f"<tr><td>{'~' + format(b['maxCc'], ',') + 'cc' if b['maxCc'] else format(d['brackets'][i-1]['maxCc'], ',') + 'cc 초과'}</td>"
        f"<td>{b['wonPerCc']}원/cc</td></tr>"
        for i, b in enumerate(d["brackets"])
    )
    body = f"""<p class="crumb"><a href="index.html">자동차세</a> › 계산기</p>
<h1>자동차세 계산기</h1>
<p class="lede">배기량(cc)과 등록 연도만 넣으면 자동차세와 1월 연납액을 바로 계산해요. 비영업용 승용 기준.</p>
{prepay_banner(rates, this_year, age_based=True)}
<div class="card">
  <div class="field-row">
    <div class="field"><label for="calc-cc">배기량(cc)</label>
      <input id="calc-cc" type="number" min="0" inputmode="numeric" placeholder="예: 1998"></div>
    <div class="field"><label for="calc-year">등록 연도</label>
      <select id="calc-year"><option value="">신차 기준</option>{year_options}</select></div>
  </div>
  <label class="toggle-row" style="border:none;padding-bottom:0;"><span>전기차·수소전기차예요 (배기량 없음 — 정액)</span><input type="checkbox" id="calc-ev" style="width:20px;height:20px;"></label>
  <p class="notice">배기량은 자동차등록증에서 확인할 수 있어요.</p>
</div>
<div class="card year-result-card" id="calc-result" hidden>
  <div class="label" id="cr-label"></div>
  <div class="amount" id="cr-amount"></div>
  <div class="label" id="cr-prepay"></div>
  <p class="notice" id="cr-lump" hidden>{esc(lump_sum_text(rates))}</p>
</div>
<div class="table-wrap" id="calc-table"></div>
<h2>세율표</h2>
<div class="table-wrap"><table class="data"><thead><tr><th>배기량 구간</th><th>cc당 세액</th></tr></thead><tbody>{bracket_rows}
<tr><td>전기차·수소전기차</td><td>연 {won(d["ev"]["annualTotalKrw"])} 고정</td></tr></tbody></table></div>
<p>본세는 배기량 × cc당 세액이에요. 여기에 지방교육세 {at["edu"]}%가 붙고, {at["start"]}년차부터 차령 경감(연 {at["per"]}%p, 최대 {at["max"]}%)이 적용돼요.
  내 차종의 연식별 표는 <a href="index.html">차종별 페이지</a>에서 볼 수 있어요.</p>
{sources_block(rates, this_year)}
{ad_slot(site, "calcEnd")}
{CALC_SCRIPT.replace("__THIS_YEAR__", str(this_year)).replace("__MAX_AGE__", str(TABLE_MAX_AGE))}"""
    title = f"자동차세 계산기 — 배기량·연식으로 바로 계산 | {site['siteName']}"
    desc = "배기량(cc)과 등록 연도만 넣으면 자동차세 연세액·1월 연납 할인액을 계산합니다. 차령 경감·전기차 정액 반영."
    return page(site, title, desc, body, canonical=page_canonical(site, "tax/calculator.html"), og=og,
                head_extra=adsense_head(site, ("calcEnd",)))


def search_norm(s):
    """검색 색인 정규화 — 소문자 + 공백·'|' 제거. js/hub-search.js normalize()와 같은 규칙."""
    return re.sub(r"[\s|]+", "", str(s).lower())


def family_aliases(cat, k, this_year):
    """가족 공통 별칭 — 현행 트림(modelYearTo 없음·올해 이후) 별칭 중 공백·숫자가 없는 한 단어만.
    오타 별칭('아반테')이 대표 트림 하나에만 들어 있어도 가족 전 트림이 검색되게 하되,
    세대 특정 별칭('그랜저ig', 'hg220')은 퍼뜨리지 않는다 — '그랜저 ig'에 HG가 섞이지 않게."""
    out = []
    for v in cat.families[k]:
        if v.get("modelYearTo") and v["modelYearTo"] < this_year:
            continue
        for a in v.get("aliases") or []:
            if a and not re.search(r"[\s\d]", a) and a not in out:
                out.append(a)
    return out


def search_index(v, fam_aliases):
    """트림 하나의 검색 색인(data-q): 정규화한 토큰을 '|'로 잇는다. 질의에는 '|'가 없으므로
    토큰 경계를 넘는 일치('그랜저'+'ig…')가 생기지 않는다."""
    gen = v.get("generation") or ""
    raw = [v["name"], v["brand"], v["modelFamily"], gen, v["brand"] + v["modelFamily"], v["modelFamily"] + gen,
           v["brand"] + v["name"]] + list(v.get("aliases") or []) + list(fam_aliases)
    toks = []
    for t in raw:
        n = search_norm(t)
        if n and n not in toks:
            toks.append(n)
    # 다른 토큰 안에 통째로 들어 있는 토큰은 뺀다 — 부분일치 결과는 그대로이고 허브 HTML이 가벼워진다
    # ('현대'·'그랜저'·'ig'는 '현대그랜저ig2.4'에 이미 있다)
    return "|".join(t for t in toks if not any(t != o and t in o for o in toks))


def aging_terms(rates):
    """차령 경감·교육세 문구용 숫자 — tax-rates.json에서 (하드코딩 금지)."""
    d = rates["displacement"]
    a = d["agingDiscount"]
    return {"start": a["startCarAge"], "per": f"{a['ratePerYear']*100:.0f}", "max": f"{a['maxRate']*100:.0f}",
            "fullAge": max_discount_age(rates), "edu": f"{d['educationTaxRate']*100:.0f}"}


def index_page(cat, rates, site, this_year, og=None):
    """허브. 순서: h1 → lede → 연납 배너 → 검색(JS 있을 때만) → 브랜드 칩 → 브랜드별 목록 → 계산기 안내
    → h2 계산 원리(세율표·설명·notice) → 출처. 브랜드·모델 그룹·트림마다 slug 기반 id가 있어
    차종 페이지 브레드크럼(index.html#model-grandeur)과 칩이 가리킬 수 있다."""
    def trim_row(v, q, pad=False):
        return (f'<li><a class="hub-trim" id="{esc(v["slug"])}" href="{esc(v["slug"])}.html" data-q="{esc(q)}">'
                f'{hub_inner(v, pad)}</a></li>')

    def hub_inner(v, pad):
        inner = row_inner(v, rates, this_year)
        if not pad:
            return inner
        # 단일 행도 셰브론 자리(16px + gap 8px)를 비워 그룹 행과 금액 열을 맞춘다
        name, price = inner.split('<span class="hub-price">', 1)
        return f'{name}<span class="hub-right"><span class="hub-price">{price}<span class="chevron-pad" aria-hidden="true"></span></span>'

    # 브랜드 → 모델 그룹(modelFamily) → (세대 라벨) → 트림. JS 없이 <details> 기본 동작만 사용 —
    # 접힌 상태에서도 모든 트림 링크가 HTML에 존재한다 (SEO 크롤링 통로)
    sections, chips = [], []
    for brand, fam_keys in cat.brands.items():
        bid = cat.brand_ids[brand]
        chips.append(f'<a class="chip" href="#{bid}">{esc(brand)}</a>')
        rows = []
        for k in fam_keys:
            trims = cat.families[k]
            fam_al = family_aliases(cat, k, this_year)
            if len(trims) == 1:
                v = trims[0]
                rows.append(f'<li><a class="hub-row" id="{esc(v["slug"])}" href="{esc(v["slug"])}.html" '
                            f'data-q="{esc(search_index(v, fam_al))}">{hub_inner(v, True)}</a></li>')
                continue
            # 패키지 트림(N Line 등)은 모델 그룹 안에서 다시 묶는다 — 단 2개 이상일 때만 중첩 details.
            # 묶음은 가장 최신 멤버의 세대 아래에 둔다
            subs = {}
            for v in trims:
                if v.get("trimGroup"):
                    subs.setdefault(v["trimGroup"], []).append(v)
            subs = {tg: sorted(m, key=trim_sort_key) for tg, m in subs.items() if len(m) >= 2}
            in_sub = {v["id"] for m in subs.values() for v in m}
            groups = gen_groups(trims)
            inner = ""
            for key, label, items in groups:
                plain = [v for v in items if v["id"] not in in_sub]
                here = [tg for tg, m in subs.items() if gen_key(m[0]) == key]
                if not plain and not here:
                    continue
                if len(groups) >= 2:
                    inner += f'<li class="hub-gen">{esc(label)}</li>'
                inner += "".join(trim_row(v, search_index(v, fam_al), pad=bool(subs)) for v in plain)
                for tg in here:
                    members = subs[tg]
                    sub_min = min(rep_annual(v, rates, this_year) for v in members)
                    inner += (
                        f'<li><details class="hub-subgroup"><summary class="hub-trim">'
                        f'<span class="hub-name">{esc(tg)}</span>'
                        f'<span class="hub-right"><span class="hub-price">연 {sub_min:,}원부터</span>{CHEVRON}</span>'
                        f'</summary><ul class="hub-trims nested">'
                        + "".join(trim_row(v, search_index(v, fam_al)) for v in members)
                        + "</ul></details></li>"
                    )
            min_tax = min(rep_annual(v, rates, this_year) for v in trims)
            rows.append(
                f'<li><details class="hub-group" id="{cat.family_ids[k]}"><summary class="hub-row">'
                f'<span class="hub-name">{esc(k[1])}</span>'
                f'<span class="hub-right"><span class="hub-price">연 {min_tax:,}원부터</span>{CHEVRON}</span>'
                f'</summary><ul class="hub-trims">{inner}</ul></details></li>'
            )
        sections.append(f'<section class="hub-brand"><h2 class="brand-title" id="{bid}">{esc(brand)}</h2>'
                        f'<ul class="hub-list">{"".join(rows)}</ul></section>')

    d = rates["displacement"]
    at = aging_terms(rates)
    bracket_rows = "".join(
        f"<tr><td>{'~' + format(b['maxCc'], ',') + 'cc' if b['maxCc'] else format(d['brackets'][i-1]['maxCc'], ',') + 'cc 초과'}</td>"
        f"<td>{b['wonPerCc']}원/cc</td></tr>"
        for i, b in enumerate(d["brackets"])
    )
    body = f"""<h1>차종별 자동차세 계산</h1>
<p class="lede">배기량과 연식만으로 정해지는 자동차세를 차종별로 미리 계산해 뒀어요. 승용은 비영업용 기준이에요.</p>
{prepay_banner(rates, this_year, amount_note=False)}
<div class="hub-search" hidden>
  <label for="hub-q">차종 검색</label>
  <input id="hub-q" type="search" placeholder="예: 그랜저 IG, 쏘렌토" autocomplete="off" enterkeyhint="search">
  <p class="hub-status" id="hub-status" aria-live="polite"></p>
  <p class="hub-empty" id="hub-empty" hidden>찾는 차종이 없어요. <a href="calculator.html">자동차세 계산기</a>에서 배기량만 넣으면 바로 계산할 수 있어요.</p>
</div>
<div class="brand-chips" role="navigation" aria-label="브랜드 바로가기">{"".join(chips)}</div>
{"".join(sections)}
<p class="hub-more">찾는 차종이 없나요? <a href="calculator.html">자동차세 계산기</a>에서 배기량만 넣으면 바로 계산할 수 있어요.</p>
<h2>자동차세 계산 원리</h2>
<div class="table-wrap"><table class="data"><thead><tr><th>배기량 구간</th><th>cc당 세액</th></tr></thead><tbody>{bracket_rows}
<tr><td>전기차·수소전기차</td><td>연 {won(d["ev"]["annualTotalKrw"])} 고정</td></tr></tbody></table></div>
<p>본세는 배기량 × cc당 세액이에요. 여기에 지방교육세 {at["edu"]}%가 붙고, {at["start"]}년차부터 차령 경감(연 {at["per"]}%p, 최대 {at["max"]}%)이 적용돼요.</p>
<p class="notice">목록의 금액은 판매 중 모델은 신차, 단종 모델은 마지막 연식의 {this_year}년 세액이에요.</p>
{sources_block(rates, this_year)}
{ad_slot(site, "hubEnd")}
<script src="../js/hub-search.js" defer></script>"""
    title = f"차종별 자동차세 계산 — 연식별 세액·연납 할인 | {site['siteName']}"
    desc = "아반떼·그랜저·쏘렌토 등 인기 차종의 자동차세를 연식별로 계산. cc당 세율, 차령 경감, 연납 할인까지."
    return page(site, title, desc, body, canonical=page_canonical(site, "tax/index.html"), og=og,
                head_extra=adsense_head(site, ("hubEnd",)))


def vehicle_og_spec(v, rates, this_year):
    """차종 페이지 썸네일 문구. 페이지 히어로와 같은 숫자를 보여준다 (판매 중 = 신차, 단종 세대 = gen_default 대표 연식)."""
    name = v["name"]
    foot = f"{this_year}년 세율 기준"
    # 연납 공제율이 당해 연도 것이 아니면 썸네일에도 밝힌다 (차종별 보조 문구보다 우선)
    basis = prepay_basis(rates, this_year, sep=" · 연납은 ")
    if v.get("vehicleClass", "passenger") != "passenger":
        t = nonpassenger_tax(v, rates)
        kind_label = "화물자동차" if t["kind"] == "truck" else "승합자동차"
        hero = f"연 {t['nonBusiness']:,}원"
        caption = f"{kind_label} · {t['basisLabel']} · 자가용"
        sub = f"1월 연납 시 {prepay(t['nonBusiness'], rates, this_year)['pay']:,}원 · 영업용 연 {t['business']:,}원"
        foot += basis or " · 연식과 무관한 정액"
    elif v["fuelType"] == "ev":
        annual = rates["displacement"]["ev"]["annualTotalKrw"]
        hero = f"연 {annual:,}원"
        caption = f"{fuel_caption(v)} · 비영업용 승용 · 연식 무관 정액"
        sub = f"1월 연납 시 {prepay(annual, rates, this_year)['pay']:,}원"
        foot += basis or (" · 전기차와 같은 정액" if is_hydrogen(v) else "")
    else:
        cc = v["displacementCc"]
        fuel = FUEL_LABELS.get(v["fuelType"], v["fuelType"])
        span = gen_span(v, rates, this_year)
        if span:  # 단종 세대 — 페이지 히어로와 같은 대표 연식 금액 (gen_default)
            g, lo, hi = span["g"], span["lo"], span["hi"]
            hero = f"연 {hi['annual']:,}원"
            caption = f"{fuel} · {cc:,}cc · {g['year']}년 등록({g['age']}년차) 기준"
            sub = (f"1월 연납 시 {prepay(hi['annual'], rates, this_year)['pay']:,}원 · "
                   f"{year_range(v)}년식 {amount_range_text(lo['annual'], hi['annual'])}")
        else:
            t1 = tax_for(cc, 1, rates)
            t_last = tax_for(cc, TABLE_MAX_AGE, rates)
            hero = f"연 {t1['annual']:,}원"
            caption = f"{fuel} · {cc:,}cc · 신차 기준"
            sub = (f"1월 연납 시 {prepay(t1['annual'], rates, this_year)['pay']:,}원 · "
                   f"{max_discount_age(rates)}년 이상이면 연 {t_last['annual']:,}원")
        foot += basis or " · 연식별 경감표는 사이트에서"
    return {"kind": "amount", "label": "자동차세", "name": name, "caption": caption,
            "hero": hero, "sub": sub, "foot": foot, "alt": f"{name} 자동차세 {hero}"}


def page_og_spec(title, lede, foot=None):
    return {"kind": "page", "title": title, "lede": lede, "foot": foot, "alt": f"{title} — {lede}"}


# 직접 작성한 페이지(index.html·tco.html)가 고정 URL로 참조하는 썸네일. 문구를 바꾸면 그 페이지의 og:image도 확인할 것
STATIC_OG = {
    "og/home.png": page_og_spec("내 차 수첩", "소모품 교체 주기·검사 D-day를 한눈에", "기록은 내 브라우저에만 저장돼요 · 회원가입 없음"),
    "og/tco.png": page_og_spec("유지비 비교", "자동차세 + 연료비 + 보험 + 감가, 두 차를 나란히", "월 유지비로 환산해 비교해요"),
}


def build_images(renderer, vehicles, rates, this_year):
    """썸네일·아이콘 생성. 반환: {slug|"index"|"calculator": {"url","alt"}} — 쓸 수 있는 것만."""
    renderer.icons()
    for rel, spec in STATIC_OG.items():
        renderer.og(rel, spec, versioned=False)
    og = {}

    def add(key, rel, spec):
        url = renderer.og(rel, spec)
        if url:
            og[key] = {"url": url, "alt": spec["alt"]}

    for v in vehicles:
        add(v["slug"], f"og/tax/{v['slug']}.png", vehicle_og_spec(v, rates, this_year))
    renderer.prune("og/tax", {f"{v['slug']}.png" for v in vehicles})
    add("index", "og/tax-index.png",
        page_og_spec("차종별 자동차세", f"인기 차종 {len(vehicles)}종 · 연식별 세액과 1월 연납 할인", f"{this_year}년 세율 기준"))
    add("calculator", "og/tax-calculator.png",
        page_og_spec("자동차세 계산기", "배기량과 등록 연도만 넣으면 바로 계산", f"{this_year}년 세율 기준 · 전기차 정액 반영"))
    renderer.report()
    return og


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
        f"{base}/about.html",
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
    prepay_windows(rates)
    all_active = [v for v in load("vehicles.json")["vehicles"] if v["status"] == "active"]
    # 분류 가드: 승용(passenger)이 아닌 차종은 배기량 과세 대상이 아니다.
    # 화물은 적재량 기준, 승합은 규모별 정액이라 이 사이트의 계산이 성립하지 않는다.
    # 분류별 생성 조건: 승용은 배기량(또는 전기차), 화물은 적재정량, 승합은 규모가 있어야 계산된다
    def buildable(v):
        cls = v.get("vehicleClass", "passenger")
        if cls == "truck":
            return bool(v.get("payloadKg"))
        if cls == "van":
            return bool(v.get("vanSize"))
        return v["fuelType"] == "ev" or bool(v["displacementCc"])

    vehicles = [v for v in all_active if buildable(v)]
    skipped = [v for v in all_active if not buildable(v)]
    this_year = datetime.date.today().year

    og = build_images(images.Renderer(ROOT, site), vehicles, rates, this_year)

    cat = Catalog(vehicles, this_year)
    OUT_DIR.mkdir(exist_ok=True)
    slugs = []
    for v in vehicles:
        out = OUT_DIR / f"{v['slug']}.html"
        if v.get("vehicleClass", "passenger") == "passenger":
            html_out = vehicle_page(v, rates, site, this_year, cat, og=og.get(v["slug"]))
        else:
            html_out = nonpassenger_page(v, rates, site, this_year, cat, og=og.get(v["slug"]))
        out.write_text(html_out, encoding="utf-8")
        slugs.append(v["slug"])
    (OUT_DIR / "index.html").write_text(index_page(cat, rates, site, this_year, og=og.get("index")), encoding="utf-8")
    (OUT_DIR / "calculator.html").write_text(
        calculator_page(rates, site, this_year, og=og.get("calculator")), encoding="utf-8")
    # 빌드 대상에서 빠진 차종(삭제·slug 변경·sample 전환·배기량 비움)의 옛 페이지 삭제 —
    # 남겨 두면 sitemap에도 목록에도 없는 낡은 세액 페이지가 계속 공개된다 (og/tax 썸네일 정리와 짝)
    keep = {f"{s}.html" for s in slugs} | {"index.html", "calculator.html"}
    for p in sorted(OUT_DIR.glob("*.html")):
        if p.name not in keep:
            p.unlink()
            print(f"· 더 이상 만들지 않는 페이지 삭제: tax/{p.name}")
    print(f"· tax/ 페이지 {len(slugs)}개 + index + calculator 생성")
    if skipped:
        print(f"· 배기량 미확정 스켈레톤 {len(skipped)}종 미생성 (cc 채우면 자동 생성)")
    kinds = {}
    for v in vehicles:
        kinds[v.get("vehicleClass", "passenger")] = kinds.get(v.get("vehicleClass", "passenger"), 0) + 1
    print("· 분류별: " + " / ".join(f"{k} {n}종" for k, n in kinds.items()))
    build_sitemap(site, slugs)
    # 애드센스 ads.txt와 손으로 쓴 루트 페이지의 광고·문의 마커 (data/site.json adsense·contactEmail)
    sync_ads_txt(site)
    try:
        sync_hand_pages(site)
    except MarkerError as e:
        print(f"빌드 오류: {e}")
        print("고치는 법: 마커는 여는·닫는 짝을 정확한 형태로 한 번씩만 씁니다 (값이 비었을 때 공백·줄바꿈 없이):")
        print("  <!-- adsense:head --><!-- /adsense:head -->")
        print("  <!-- adsense:slot 이름 --><!-- /adsense:slot -->   (수첩 화면 index.html에는 금지)")
        print("  <!-- site:contact --><!-- /site:contact -->")
        sys.exit(1)


if __name__ == "__main__":
    main()
