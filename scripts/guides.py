"""차일지 — 자동차세 가이드 글 (tax/guide.html 목록 + tax/guide-*.html). scripts/build.py가 부른다.

- 글 속 숫자(세율·경감률·연납 공제율·신청 기간·예시 세액)는 전부 data/tax-rates.json과 build.py 계산 함수
  (tax_for·prepay·prepay_windows …)로 만든다. 세율이 바뀌거나 해가 바뀌어 다시 빌드하면 글의 숫자도 같이 바뀐다
  (상수 하드코딩 금지 — TASKS.md 공통 규칙). 예시 차종은 data/vehicles.json에서 slug로 찾는다.
- 사실은 출처로 확인한 것만 쓴다. 지자체마다 안내가 다르거나 확인하지 못한 절차(메뉴 위치·환급 처리 방식 등)는
  단정하지 않고 '차가 등록된 시·군·구청·위택스·ETAX에서 확인'으로 안내한다.
- 글 문장(사실 관계)을 고치면 GUIDES의 updated 날짜도 고친다 — 화면의 '수정'일과 Article 구조화 데이터에 쓰인다.
  숫자만 바뀌는 연례 재빌드는 문장 수정이 아니므로 그대로 둔다(화면에 '{올해}년 세율 기준'이 따로 나온다).
- build.py 모듈을 인자 B로 받는다 (build.py가 이 모듈을 import하므로 여기서 build를 import하면 순환한다).
"""
import calendar
import datetime
import re

# 글 목록 — 순서가 목록·'다른 가이드' 순서다. slug는 tax/{slug}.html (차종 slug와 겹치면 안 된다 —
# scripts/validate_data.py가 'guide'로 시작하는 차종 slug를 막는다). og_*는 공유 썸네일 문구(숫자 없음).
GUIDES = (
    {"slug": "guide-prepay", "short": "연납으로 아끼기", "published": "2026-10-05", "updated": "2026-10-05",
     "og_title": "자동차세 연납 가이드", "og_lede": "1월에 미리 내면 얼마나 아낄까",
     "summary": "1월에 1년치를 미리 내면 얼마나 깎아 주는지, 언제·어디서 신청하는지"},
    {"slug": "guide-payment", "short": "내는 법과 납부 기한", "published": "2026-10-05", "updated": "2026-10-05",
     "og_title": "자동차세 내는 법", "og_lede": "6월·12월 납부, 늦으면 가산세",
     "summary": "6월·12월 납부 기간, 내는 방법과 소소한 공제, 늦게 내면 붙는 가산세·번호판 영치"},
    {"slug": "guide-aging", "short": "차령 경감", "published": "2026-10-05", "updated": "2026-10-05",
     "og_title": "자동차세 차령 경감", "og_lede": "오래 탈수록 세금이 줄어드는 이유",
     "summary": "몇 년차부터 얼마나 줄어드는지, 차령은 어떻게 세는지"},
    {"slug": "guide-used-car", "short": "중고차 사고팔 때", "published": "2026-10-05", "updated": "2026-10-05",
     "og_title": "중고차 자동차세 정산", "og_lede": "판 사람과 산 사람이 날짜로 나눠요",
     "summary": "차를 팔거나 살 때 자동차세를 날짜로 나누는 법, 연납했다면 환급·승계"},
    {"slug": "guide-ev", "short": "전기·수소차 자동차세", "published": "2026-10-05", "updated": "2026-10-05",
     "og_title": "전기·수소차 자동차세", "og_lede": "배기량이 없는 차는 왜 정액일까",
     "summary": "전기·수소차가 정액인 이유와 내연기관차·하이브리드와의 비교"},
    {"slug": "guide-truck-van", "short": "화물차·승합차 자동차세", "published": "2026-10-05", "updated": "2026-10-05",
     "og_title": "화물차·승합차 자동차세", "og_lede": "1톤 트럭·11인승은 왜 세금이 적을까",
     "summary": "1톤 트럭·픽업·11인승 승합차가 배기량 대신 적재정량·규모로 내는 세금"},
)
INDEX_SLUG = "guide"  # 목록 페이지 tax/guide.html

# 글에서 링크하는 외부 출처 — 사실을 확인한 곳 (2026-10 확인)
SRC_LAW_127 = ("지방세법 제127조(세율·차령 경감)", "https://www.law.go.kr/법령/지방세법/제127조")
SRC_LAW_128 = ("지방세법 제128조(납기·연납)", "https://www.law.go.kr/법령/지방세법/제128조")
SRC_CAR_AGE = ("자동차관리법 시행령 제3조(차령 기산일)", "https://www.law.go.kr/법령/자동차관리법시행령/제3조")
SRC_LAW_BASIC_24 = ("지방세기본법 제24조(기한이 휴일이면 다음 날)", "https://www.law.go.kr/법령/지방세기본법/제24조")
SRC_MOIS_2026 = ("행정안전부 — 자동차세 연납 2월 4일 마감(2026.1.29)",
                 "https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000008&nttId=123496")
SRC_MOIS_2025 = ("행정안전부 — 2025년 자동차세 연납 할인율 5% 유지(2025.1.13)",
                 "https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000008&nttId=115039")
SRC_MT_2026 = ("머니투데이 — 자동차세 연납 2월 4일까지 연장(2026.1.29)",
               "https://www.mt.co.kr/policy/2026/01/29/2026012910281370951")
SRC_GOV24 = ("정부24 — 자동차세 연납 및 분납 안내", "https://www.gov.kr/portal/service/serviceInfo/PTR000050446")
SRC_EASYLAW_REFUND = ("찾기쉬운 생활법령정보 — 자동차세 돌려받기",
                      "https://easylaw.go.kr/CSP/CnpClsMain.laf?popMenu=ov&csmSeq=1000&ccfNo=3&cciNo=3&cnpClsNo=1")
SRC_SEOUL_PREPAY = ("서울시 — 자동차세 연세액 납부 안내", "https://mediahub.seoul.go.kr/archives/2016810")
SRC_SEOCHO = ("서초구 — 자동차세(소유분) 안내", "https://www.seocho.go.kr/site/tax/02/10201050000002023050810.jsp")
SRC_MOIS_REFORM = ("행정안전부 — 자동차세 과세기준 개편 착수(2023.9)",
                   "https://mois.go.kr/frt/bbs/type010/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000008&nttId=103636")
# 중고차·납부·화물승합 글 출처 (2026-10 확인)
SRC_LAW_129 = ("지방세법 제129조(이전등록 때 일할계산)", "https://www.law.go.kr/법령/지방세법/제129조")
SRC_LAW_131 = ("지방세법 제131조(체납 시 번호판 영치)", "https://www.law.go.kr/법령/지방세법/제131조")
SRC_REG_26 = ("자동차등록령 제26조(이전등록 신청 기한)", "https://www.law.go.kr/법령/자동차등록령/제26조")
SRC_CAR_MGMT_3 = ("자동차관리법 제3조(승용·승합·화물 구분)", "https://www.law.go.kr/법령/자동차관리법/제3조")
SRC_BASIC_55 = ("지방세기본법 제55조(납부지연가산세)", "https://www.law.go.kr/법령/지방세기본법/제55조")
SRC_SPECIAL_92_2 = ("지방세특례제한법 제92조의2(전자송달·자동납부 공제)",
                    "https://www.law.go.kr/법령/지방세특례제한법/제92조의2")
SRC_UIJEONGBU_PRORATE = ("의정부시 — 자동차세 일할계산 안내", "https://www.ui4u.go.kr/car/contents.do?mId=0505000000")
SRC_TAXTIMES_TRANSFER = ("한국세정신문 — 매도 후 이전등록 없으면 양도인이 납세의무자",
                         "https://www.taxtimes.co.kr/hous01.htm?r_id=214496")
SRC_YEONCHEON_ARREARS = ("연천군 — 지방세 체납 시 불이익", "https://www.yeoncheon.go.kr/www/contents.do?key=4785")
SRC_SEOCHO_AUTOPAY = ("서초구 — 지방세 자동납부 신청 안내", "https://www.seocho.go.kr/site/tax/03/10303020000002023050810.jsp")

# 법령으로 정해진 납부 규칙 — tax-rates.json에 없는 사실값이라 출처와 함께 여기 둔다 (바뀌면 고치고 updated 날짜도)
REGULAR_DUE = ((6, 16, 30, "상반기분(1~6월분)"), (12, 16, 31, "하반기분(7~12월분)"))  # 지방세법 제128조 제1항
LATE_FIRST_PCT = 3                 # 지방세기본법 제55조 — 납부기한이 지나면 바로
LATE_MONTHLY_PCT = 0.66            # 고지서별·세목별 세액이 기준 이상이면 1개월마다 (2024년 이후 성립분)
LATE_MONTHLY_MIN_KRW = 450_000
LATE_MONTHLY_MAX_MONTHS = 60
E_BILL_ONE = (250, 800)            # 지방세특례제한법 제92조의2 — 전자송달·자동납부 중 하나 (고지서 1장당, 조례로 정함)
E_BILL_BOTH = (500, 1600)          # 둘 다
TRANSFER_DEADLINE_DAYS = 15        # 자동차등록령 제26조 — 매매는 산 날부터 15일 안에 이전등록 신청

URL_ETAX = "https://etax.seoul.go.kr"
URL_WETAX = "https://www.wetax.go.kr"

# 개편 논의처럼 '아직 바뀌지 않았다'는 사실을 확인한 시점 — 다시 확인하면 고친다
FACTS_AS_OF = "2026년 10월"


def date_ko(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.year}년 {d.month}월 {d.day}일"


def num(x, digits=0):
    """퍼센트 등 숫자 표기 — 소수점 아래 0은 지운다 (5.0 → '5', 4.575 → '4.58')."""
    s = f"{x:.{digits}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def ext(label_url):
    label, url = label_url
    return f'<a href="{url}" rel="noopener" target="_blank">{label}</a>'


class Ctx:
    """글 공통 재료 — build.py 함수와 세율 데이터, 예시 차종."""

    def __init__(self, B, rates, cat, this_year):
        self.B, self.rates, self.cat, self.y = B, rates, cat, this_year
        self.by_slug = {v["slug"]: v for v in cat.vehicles}
        self.at = B.aging_terms(rates)
        d = rates["displacement"]
        self.brackets = d["brackets"]
        self.ev = d["ev"]
        self.edu_pct = num(d["educationTaxRate"] * 100)
        self.year_key, self.rate, self.fallback = B.prepay_rate(rates, this_year)
        self.rate_pct = num(self.rate * 100, 2)
        self.days, self.year_days = B.prepay_days(rates, this_year)
        self.basis = B.prepay_basis(rates, this_year, sep="")          # '2026년 공제율 기준' 또는 ''
        self.basis_paren = f"({self.basis})" if self.basis else ""
        self.windows = B.prepay_windows(rates)
        p = rates["prepayDiscount"]
        self.jan = next(w for w in self.windows if w["month"] == p["januaryProration"]["windowMonth"])
        self.months = B.prepay_months_label(rates)                     # '2~12월분'
        self.period = B.prepay_period_label(rates, this_year)          # '2월 1일~12월 31일'
        self.th = p.get("lumpSumThresholdKrw")

    def v(self, slug):
        """예시 차종 — 데이터에 없으면 빌드를 멈춘다 (글이 없는 차를 가리키지 않게)."""
        if slug not in self.by_slug:
            raise ValueError(f"가이드 예시 차종 '{slug}'가 data/vehicles.json(빌드 대상)에 없어요 — scripts/guides.py 예시를 고치세요")
        return self.by_slug[slug]

    def link(self, slug, label=None):
        v = self.v(slug)
        return f'<a href="{self.B.esc(slug)}.html">{self.B.esc(label or v["name"])}</a>'

    def tax(self, cc, age=1):
        return self.B.tax_for(cc, age, self.rates)

    def prepay(self, annual):
        return self.B.prepay(annual, self.rates, self.y)

    def window_pct(self, w):
        """그 신청 기간에 연납하면 연세액 대비 몇 %를 공제받는지 (일할 — 납부기한 다음 날~연말 일수 ÷ 그 해 일수 × 공제율)."""
        days = (datetime.date(self.y, 12, 31) - datetime.date(self.y, w["month"], w["endDay"])).days
        return days / self.year_days * self.rate * 100

    def bracket_rows(self):
        """세율표 행 [[배기량 구간, cc당 세액]] + 전기·수소 정액 행."""
        rows = []
        for i, b in enumerate(self.brackets):
            label = f"{b['maxCc']:,}cc 이하" if b["maxCc"] else f"{self.brackets[i - 1]['maxCc']:,}cc 초과"
            rows.append([label, f"{b['wonPerCc']}원"])
        rows.append(["전기·수소차", f"연 {self.ev['baseKrw']:,}원 정액"])
        return rows

    def lump(self, who=True):
        """6월 일괄부과 안내 (본세 기준 이하 차량) — tax-rates.json lumpSumThresholdKrw·applicationWindows.lumpSumEligible.
        6·9월 연납이 해당하지 않는 것은 확인된 사실, 1·3월 신청 가능 여부는 1차 출처로 확정 전이라 단서형
        (build.py lump_sum_text와 같은 기준). who=False면 '어떤 차가 해당하나' 문장을 뺀다(이미 말한 글).
        기준이 없으면 빈 문자열."""
        if not self.th:
            return ""
        th = f"{self.th // 10000}만원" if self.th % 10000 == 0 else f"{self.th:,}원"
        examples = []
        first = self.brackets[0]
        if first["maxCc"] and first["maxCc"] * first["wonPerCc"] <= self.th:
            examples.append(f"배기량 {first['maxCc']:,}cc 이하 경차")
        if self.ev["baseKrw"] <= self.th:
            examples.append("전기·수소차")
        no = "·".join(str(w["month"]) for w in self.windows if not w.get("lumpSumEligible", True))
        yes = "·".join(str(w["month"]) for w in self.windows if w.get("lumpSumEligible", True))
        out = (f"자동차세 본세(지방교육세 제외)가 연 {th} 이하인 차는 지자체가 6월에 1년치를 한꺼번에 부과하면서 "
               "하반기분 세액의 일부를 공제해 주는 경우가 있어요.")
        if who and examples:
            out += f" {'와 '.join(examples)}가 대표적이에요."
        if no:
            out += f" 이런 차는 {no}월 연납 대상이 아니에요."
        if yes:
            out += f" {yes}월 연납이 되는지는 차가 등록된 시·군·구청에 확인하세요."
        return out

    def per_cc(self, cc):
        return next(b["wonPerCc"] for b in self.brackets if b["maxCc"] is None or cc <= b["maxCc"])


def short_name(name):
    """목록용 짧은 이름 — 끝의 연식 괄호를 뗀다 ('봉고3 2.5 디젤 (2012~)' → '봉고3 2.5 디젤')."""
    return re.sub(r"\s*\([^()]*\)$", "", name)


def table(head, rows):
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="table-wrap"><table class="data"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


# ---------------------------------------------------------------- 연납
def prepay_guide(c):
    B, y, w = c.B, c.y, c.jan
    eff = num(c.window_pct(w), 2)
    examples = [("avante-1.6", 1), ("sonata-2.0", 1), ("grandeur-2.5", 1), ("grandeur-2.5", 8)]
    rows = []
    for slug, age in examples:
        v = c.v(slug)
        t = c.tax(v["displacementCc"], age)
        p = c.prepay(t["annual"])
        when = "신차" if age == 1 else f"{age}년차"
        rows.append([f'{c.link(slug)}<span class="age-sub"> · {when}</span>',
                     B.won(t["annual"]), B.won(p["pay"]), B.won(p["discount"])])
    av = c.v("avante-1.6")
    av_t = c.tax(av["displacementCc"])["annual"]
    av_p = c.prepay(av_t)
    raw = av_t * c.days / c.year_days * c.rate
    leap = next(yy for yy in range(y, y + 8) if calendar.isleap(yy))
    l_days, l_ydays = B.prepay_days(c.rates, leap)
    if leap == y:
        leap_txt = "올해는 윤년이라 위 계산이 윤년 기준이에요."
    else:
        leap_txt = (f"윤년({leap}년 등)에는 {B.prepay_period_label(c.rates, leap)}이 {l_days}일, "
                    f"그 해 일수가 {l_ydays}일이에요.")
    win_rows = []
    for x in c.windows:
        win_rows.append([f"{x['month']}월 {x['startDay']}일~{x['endDay']}일", f"{x['month'] + 1}~12월분",
                         f"약 {num(c.window_pct(x), 1)}%"])
    lump = c.lump()
    rate_years = " · ".join(f"{k}년 {num(v * 100, 2)}%" for k, v in sorted(c.rates["prepayDiscount"]["rateByYear"].items()))
    rate_now = ""
    if c.fallback:
        rate_now = (f" {y}년 공제율은 아직 정부 발표 전이라, 차일지는 발표가 나올 때까지 {c.year_key}년 공제율"
                    f"({c.rate_pct}%)로 계산해요. 발표를 확인하면 고쳐요.")

    summary = (f"<strong>한눈에</strong> {w['month']}월 {w['startDay']}일~{w['endDay']}일에 신청하고 그 안에 내면 "
               f"{c.months} 세액의 {c.rate_pct}%{c.basis_paren}를 공제받아요. 연세액으로 치면 약 {eff}% 할인이에요. "
               "서울에 등록된 차는 서울시 ETAX·STAX, 그 밖의 지역은 위택스·스마트위택스에서 신청해요.")
    body = f"""<h2>연납은 어떤 제도인가요</h2>
<p>자동차세는 한 해 세금(연세액)을 상반기분은 6월에, 하반기분은 12월에 나눠 내요. 연납은 1년치를 미리 한 번에 내는 대신,
미리 낸 기간만큼 세금을 깎아 주는 제도예요. 지방세법 제128조에 근거가 있어요.</p>
<p>{w['month']}월에 연납하면 {c.period} 몫({c.months})이 공제 대상이고, 공제율은 {c.rate_pct}%예요{c.basis_paren}.</p>
<h2>얼마나 아낄 수 있나요</h2>
<p>차일지 차종 페이지와 같은 계산이에요. 비영업용 승용차 기준이고, 오래된 차는 차령 경감으로 연세액이 줄어 할인액도 줄어요.</p>
{table(["차종", "연세액", "1월 연납 시", "할인"], rows)}
<p>할인액은 날짜로 나눠 계산해요. 연세액 × {c.days}/{c.year_days}({c.period} 일수 ÷ 그 해 일수) × {c.rate_pct}%를 하고
10원 미만은 버려요. {B.esc(av["name"])} 신차라면 {av_t:,}원 × {c.days}/{c.year_days} × {c.rate_pct}% = {int(raw):,}원이라
{av_p["discount"]:,}원을 할인받아요. {leap_txt}</p>
<h2>언제 신청하나요</h2>
{table(["신청 기간", "공제 대상", "연세액 대비 할인"], win_rows)}
<p>늦게 신청할수록 공제받는 기간이 짧아서 할인이 줄어요. {w['month']}월이 가장 커요.</p>
<p>마지막 날이 토요일·일요일·공휴일이면 다음 평일까지 받아 줘요. 예를 들어 2026년에는 1월 31일이 토요일이라 마감이
2월 2일이었고, 위택스 점검 때문에 다시 2월 4일까지 늘어났어요. 해마다 행정안전부·위택스 공지를 확인하세요.</p>
<p>{B.esc(lump)}</p>
<h2>어디서 신청하나요</h2>
<ol>
<li><strong>서울에 등록된 차</strong>: 서울시 <a href="{URL_ETAX}" rel="noopener" target="_blank">ETAX</a> 또는 STAX 앱에서 신청해요.</li>
<li><strong>그 밖의 지역</strong>: <a href="{URL_WETAX}" rel="noopener" target="_blank">위택스</a> 또는 스마트위택스 앱에서 신청해요.</li>
<li><strong>전화·방문</strong>: 차가 등록된 시·군·구청 세무 부서에 전화하거나 찾아가서 신청할 수도 있어요.</li>
</ol>
<p>메뉴는 보통 '자동차세 연납'이나 '연세액 납부'라는 이름으로 있어요. 어디서 하든 <strong>신청만 하고 끝나는 게 아니라
기한 안에 실제로 내야</strong> 할인을 받아요. 정기분(6월·12월)을 자동이체로 내고 있어도 연납은 자동이체가 되지 않아서 직접 내야 해요.</p>
<h2>다음 해에도 다시 신청해야 하나요</h2>
<p>전년도에 연납했다면 다음 해 1월에 연납 고지서(연세액 신고납부서)를 보내 주는 지자체도 있어요(서울시 등). 하지만 납부까지
자동으로 되지는 않아서 기한 안에 직접 내야 하고, 내지 않으면 원래대로 6월·12월에 나눠 나와요. 새로 산 차는 따로 신청해야 해요.</p>
<h2>연납한 뒤 차를 팔거나 폐차하면</h2>
<p>남은 기간 몫의 세금은 날짜로 계산해서 돌려받아요. 판 경우는 소유권 이전일, 폐차한 경우는 말소일이 기준이에요.
돌려받는 절차와 시기는 지자체마다 안내가 조금씩 달라서, 차가 등록된 시·군·구청 세무 부서에 물어보는 게 가장 빨라요.</p>
<p>차를 사는 사람이 연납한 세금을 그대로 이어받는 방법(연세액 납부 승계)도 있어요. 이때는 환급 대신 두 사람이 직접 정산해요.
차를 사고팔 때 자동차세를 나누는 방법은 <a href="guide-used-car.html">중고차 사고팔 때</a> 글에 정리했어요.</p>"""
    faqs = [
        ("작년에 연납했는데 올해 또 신청해야 하나요?",
         "작년에 연납했다면 1월에 연납 고지서를 보내 주는 지자체도 있지만(서울시 등), 납부는 자동으로 되지 않아요. "
         "고지서를 받았든 아니든 기한 안에 직접 내야 할인돼요."),
        ("할인율(공제율)은 해마다 같나요?",
         f"차일지가 확인한 공제율은 {rate_years}예요. 원래는 2025년부터 3%로 낮출 계획이었지만, "
         "2024년 말 시행령 개정으로 5%가 유지됐어요. 공제율은 시행령으로 정해서 바뀔 수 있어요." + rate_now),
        ("경차나 전기차도 연납할 수 있나요?",
         f"{lump} 1월 연납이 된다면 6월에 한꺼번에 내는 것보다 공제 기간이 길어서 조금 더 아낄 수 있어요."),
        ("연납하면 정확히 얼마를 내나요?",
         "차종 페이지에서 등록 연도를 고르면 그 연식의 '1월 연납 시' 금액이 나와요. 실제 금액은 고지서나 위택스·ETAX에서 확인하세요. "
         "고지서는 10원 미만을 버리는 방식 때문에 몇십 원 다를 수 있어요."),
    ]
    sources = [SRC_LAW_128, SRC_LAW_BASIC_24, SRC_MOIS_2026, SRC_MT_2026, SRC_MOIS_2025, SRC_GOV24, SRC_SEOUL_PREPAY,
               SRC_EASYLAW_REFUND]
    return {
        "h1": "자동차세 연납, 1월에 미리 내면 얼마나 아낄까",
        "title": f"자동차세 연납 신청 방법과 할인액 — {y}년 기준",
        "description": (f"자동차세를 1월에 미리 내면 {c.months} 세액의 {c.rate_pct}%를 공제받아요(연세액의 약 {eff}%). "
                        "신청 기간·방법, 차종별 할인액, 차를 팔 때 환급까지 정리했어요."),
        "lede": ("자동차세는 6월과 12월에 절반씩 나와요. 1년치를 미리 한 번에 내면 남은 기간 세금의 일부를 깎아 주는데, "
                 "이걸 '연납'이라고 해요. 얼마나 아끼는지, 언제·어디서 신청하는지 정리했어요."),
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }


# ---------------------------------------------------------------- 차령 경감
def aging_guide(c):
    B, y, at = c.B, c.y, c.at
    av, tu = c.v("avante-1.6"), c.v("tucson-1.6t")
    cc = av["displacementCc"]
    t1 = c.tax(cc)
    big = c.v("grandeur-2.5")["displacementCc"]
    rows = []
    for age in range(1, at["fullAge"] + 1):
        a, b = c.tax(cc, age), c.tax(big, age)
        label = f"{age}년차" + (" (신차)" if age == 1 else "") + (" 이상" if age == at["fullAge"] else "")
        rows.append([label, f"{a['discountRate'] * 100:.0f}%", B.won(a["annual"]), B.won(b["annual"])])
    # 7~12월 등록 예시 — 3년 전 8월 등록: 올해 상반기분은 차령이 1년 적게(3년차), 하반기분은 4년차
    reg = y - 3
    h1_age, h2_age = y - reg, y - reg + 1
    th1, th2 = c.tax(cc, h1_age), c.tax(cc, h2_age)
    extra = (th1["annual"] - th2["annual"]) // 2 // 10 * 10
    # 경계 비교 — 두 번째 구간 상한(1,600cc) 바로 아래와 그 위 대표 배기량
    mid = c.brackets[1] if len(c.brackets) > 2 else None
    edge = ""
    if mid and mid["maxCc"]:
        lo_v, hi_v = c.v("avante-1.6"), c.v("sonata-2.0")
        a, b = c.tax(lo_v["displacementCc"]), c.tax(hi_v["displacementCc"])
        edge = (f"<li>배기량 {mid['maxCc']:,}cc 이하는 cc당 {mid['wonPerCc']}원, 넘으면 {c.brackets[2]['wonPerCc']}원이라 "
                f"경계에서 차이가 커요. 신차 기준 {c.link('avante-1.6')}({lo_v['displacementCc']:,}cc){B.josa(lo_v['name'], '는', '은')} "
                f"연 {a['annual']:,}원, {c.link('sonata-2.0')}({hi_v['displacementCc']:,}cc){B.josa(hi_v['name'], '는', '은')} "
                f"연 {b['annual']:,}원으로, 세금이 연 {b['annual'] - a['annual']:,}원 차이 나요.</li>")
    t_full = c.tax(cc, at["fullAge"])
    summary = (f"<strong>한눈에</strong> 비영업용 승용차(가솔린·디젤·LPG·하이브리드)는 {at['start']}년차부터 자동차세가 "
               f"해마다 원래 세금의 {at['per']}%씩 줄고, {at['fullAge']}년차부터는 {at['max']}% 경감으로 더 줄지 않아요. "
               "전기·수소차와 화물·승합차는 정액이라 줄지 않아요.")
    body = f"""<h2>자동차세는 어떻게 정해지나요</h2>
<p>승용차 자동차세는 차값이 아니라 배기량으로 정해요. 배기량(cc)에 cc당 세액을 곱한 금액이 본세이고, 여기에 지방교육세
{at['edu']}%가 더해져요.</p>
{table(["배기량", "cc당 세액"], c.bracket_rows())}
<p>예를 들어 {c.link('avante-1.6')}({cc:,}cc){B.josa(av['name'], '는', '은')} {cc:,} × {c.per_cc(cc)}원 = {t1['base']:,}원에 지방교육세 {t1['edu']:,}원을 더해
신차 기준 연 {t1['annual']:,}원이에요. 같은 배기량이면 차종이 달라도 세금이 같아서 {c.link('tucson-1.6t')}({tu['displacementCc']:,}cc)도
같은 금액이에요.</p>
<h2>차령 경감은 이렇게 계산해요</h2>
<p>차령이 {at['start']}년 이상이면 '(차령 − {at['start'] - 1}) × {at['per']}%'만큼 세금이 줄어요. {at['fullAge']}년차에 {at['max']}%가 되고,
그 뒤로는 차령을 {at['fullAge']}년으로 봐서 더 줄지 않아요.</p>
{table(["차령", "경감률", f"{cc:,}cc", f"{big:,}cc"], rows)}
<p>세금은 6월(상반기분)과 12월(하반기분)에 절반씩 나오고 고지서마다 10원 미만을 버려서, 실제 금액은 이 표와 몇십 원 다를 수 있어요.</p>
<h2>차령은 이렇게 세요</h2>
<p>차령은 보통 '올해 − 최초 등록 연도 + 1'이에요. 예를 들어 {y - at['start'] + 1}년 3월에 처음 등록한 차는 {y}년에
{at['start']}년차라 {at['per']}% 줄어요.</p>
<p><strong>7~12월에 처음 등록한 차</strong>는 조금 달라요. 6월에 내는 상반기분은 차령을 1년 적게 세고, 12월에 내는 하반기분부터
1년을 더해요. 예를 들어 {reg}년 8월에 처음 등록한 {cc:,}cc 차라면 {y}년 상반기분은 {h1_age}년차, 하반기분은 {h2_age}년차로
계산해요. 그래서 1년 내내 {h2_age}년차로 계산한 금액(연 {th2['annual']:,}원)보다 약 {extra:,}원 더 나와요.</p>
<p><strong>만든 해를 넘겨 처음 등록한 차</strong>(오래 보관된 재고차 등)는 등록일이 아니라 만든 해의 12월 31일부터 차령을
세요. 그래서 등록한 해로 센 것보다 차령이 많게 나올 수 있어요.</p>
<p>중고로 산 차도 주인이 바뀌었다고 차령이 다시 시작되지 않아요. 처음 등록한 날부터 이어서 세요. 최초 등록일은 자동차등록증에서
확인할 수 있어요.</p>
<h2>경감이 없는 차</h2>
<p>전기차·수소전기차는 배기량이 없어 연 {c.ev['annualTotalKrw']:,}원 정액이라 연식과 관계없이 같아요. 자세한 내용은
<a href="guide-ev.html">전기·수소차 자동차세</a> 글에 정리했어요. <a href="guide-truck-van.html">화물차와 승합차</a>도 적재정량·규모별 정액이라 차령 경감이 없고 지방교육세도 붙지 않아요.</p>
<h2>알아 두면 좋은 점</h2>
<ul>
{edge}
<li>{at['fullAge']}년 이상 된 차는 더 줄지 않아요. {cc:,}cc라면 {at['fullAge']}년차부터 연 {t_full['annual']:,}원으로 그대로예요.</li>
<li>세금은 차값이 아니라 배기량과 차령으로만 정해져요. 같은 배기량이면 국산차와 수입차도 같아요.</li>
</ul>"""
    faqs = [
        ("하이브리드차도 차령 경감이 되나요?",
         f"네. 하이브리드는 엔진 배기량으로 세금을 매기기 때문에 가솔린차와 똑같이 {at['start']}년차부터 경감돼요."),
        (f"{at['fullAge'] + 1}년 넘은 차는 세금이 더 줄지 않나요?",
         f"{at['fullAge']}년차에 경감률이 최대 {at['max']}%가 되고, 그 뒤로는 차령을 {at['fullAge']}년으로 봐서 금액이 그대로예요."),
        ("중고차를 사면 차령이 다시 1년차가 되나요?",
         "아니요. 차령은 차를 처음 등록한 날부터 세기 때문에 주인이 바뀌어도 이어져요."),
        ("내 차의 차령은 어디서 확인하나요?",
         "자동차등록증의 최초 등록일로 계산할 수 있어요. 7~12월에 처음 등록했다면 상반기분은 1년 적게 센다는 점만 기억하세요. "
         "정확한 금액은 고지서에서 확인하세요."),
    ]
    sources = [SRC_LAW_127, SRC_CAR_AGE, SRC_SEOCHO]
    return {
        "h1": "자동차세가 해마다 줄어드는 이유, 차령 경감",
        "title": "자동차세 차령 경감 계산법 — 몇 년차부터 얼마나 줄까",
        "description": (f"비영업용 승용차 자동차세는 {at['start']}년차부터 해마다 원래 세금의 {at['per']}%씩 줄고, "
                        f"{at['fullAge']}년차에 최대 {at['max']}% 경감돼요. 계산식, 차령 세는 법, 7~12월에 등록한 차의 예외까지 "
                        "예시로 정리했어요."),
        "lede": ("같은 차라도 오래 탈수록 자동차세가 줄어요. 차가 오래될수록 세금을 깎아 주는 '차령 경감' 때문이에요. "
                 "언제부터, 얼마나 줄어드는지 정리했어요."),
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }


# ---------------------------------------------------------------- 전기·수소차
def ev_guide(c):
    B, y, at, ev = c.B, c.y, c.at, c.ev
    total, base, edu = ev["annualTotalKrw"], ev["baseKrw"], ev["educationTaxKrw"]
    man = f"{total // 10000}만원" if total % 10000 == 0 else f"{total:,}원"
    evs = [v for v in c.cat.vehicles if v["fuelType"] == "ev" and v.get("vehicleClass", "passenger") == "passenger"]
    ex = " · ".join(c.link(s) for s in ("ray-ev", "ioniq5", "tesla-modely", "nexo"))
    small_v = c.v("morning-1.0")
    small, mid, big = small_v["displacementCc"], c.v("avante-1.6")["displacementCc"], c.v("sonata-2.0")["displacementCc"]
    kei_max = c.brackets[0]["maxCc"]
    ages = sorted({a for a in (1, at["start"], 5, 8, 10) if a < at["fullAge"]} | {at["fullAge"]})
    rows = []
    for age in ages:
        label = f"{age}년차" + (" (신차)" if age == 1 else "") + (" 이상" if age == at["fullAge"] else "")
        rows.append([label, B.won(c.tax(mid, age)["annual"]), B.won(c.tax(big, age)["annual"]), B.won(total)])
    mid_full = c.tax(mid, at["fullAge"])["annual"]
    small_new = c.tax(small)["annual"]
    cmp_mid = "많아요" if mid_full > total else ("같아요" if mid_full == total else "적어요")
    cmp_small = "적어요" if small_new < total else ("같아요" if small_new == total else "많아요")
    hy = c.v("grandeur-hybrid")
    hy_t = c.tax(hy["displacementCc"])["annual"]
    pe = c.prepay(total)
    lump = ""
    if c.th and base <= c.th:
        lump = (f"<p>전기·수소차는 본세가 연 {base:,}원이라 6월 일괄부과 기준에 해당해요. {B.esc(c.lump(who=False))}</p>"
                f"<p>1월 연납이 된다면 {pe['pay']:,}원({pe['discount']:,}원 할인{', ' + c.basis if c.basis else ''})이라 6월에 한꺼번에 "
                "내는 것보다 조금 더 아낄 수 있어요. 자세한 내용은 <a href=\"guide-prepay.html\">연납 가이드</a>에 정리했어요.</p>")
    summary = (f"<strong>한눈에</strong> 비영업용 전기·수소 승용차는 본세 {base:,}원 + 지방교육세 {edu:,}원 = 연 {total:,}원이에요. "
               "차값·크기와 관계없고, 연식이 지나도 그대로예요. 하이브리드는 엔진이 있어서 배기량으로 매겨요.")
    body = f"""<h2>왜 정액일까요</h2>
<p>승용차 자동차세는 배기량(cc)으로 매겨요. 그런데 전기차와 수소전기차는 엔진이 없어서 배기량이 없어요. 그래서 지방세법은 이런 차를
'그 밖의 승용자동차'로 따로 정해 비영업용은 1년에 {base:,}원을 매기고, 여기에 지방교육세 {c.edu_pct}%({edu:,}원)가 더해져요.</p>
<p>그래서 차값이 수천만 원 차이 나도 세금은 같아요. 차일지에 있는 전기·수소 승용차 {len(evs)}종({ex} 등)이 모두 연 {total:,}원이에요.</p>
<h2>내연기관차와 비교하면</h2>
<p>내연기관차는 배기량이 클수록 세금이 많고, 해마다 차령 경감으로 줄어요. 전기·수소차는 처음부터 끝까지 같아요.</p>
{table(["차령", f"{mid:,}cc", f"{big:,}cc", "전기·수소차"], rows)}
<ul>
<li>{mid:,}cc 차는 {at['fullAge']}년차 이상이 돼도 연 {mid_full:,}원이라 전기·수소차(연 {total:,}원)보다 {cmp_mid}.</li>
<li>배기량 {kei_max:,}cc 이하 경차는 신차도 연 {small_new:,}원({c.link('morning-1.0')}, {small:,}cc 기준)이라 전기·수소차보다 {cmp_small}.</li>
</ul>
<h2>차령 경감은 없어요</h2>
<p>내연기관차는 {at['start']}년차부터 해마다 원래 세금의 {at['per']}%씩, 최대 {at['max']}%까지 세금이 줄지만 전기·수소차는 정액이라 줄지 않아요.
오래 탈수록 비슷한 크기의 내연기관차와 세금 차이가 줄어드는 이유예요(<a href="guide-aging.html">차령 경감 알아보기</a>).</p>
<h2>하이브리드는 배기량 기준이에요</h2>
<p>하이브리드차는 엔진이 있어서 전기차가 아니라 일반 승용차처럼 배기량으로 세금을 매겨요. 예를 들어
{c.link('grandeur-hybrid')}({hy['displacementCc']:,}cc){B.josa(hy['name'], '는', '은')} 신차 기준 연 {hy_t:,}원으로, 같은 배기량의 가솔린차와 같아요.</p>
<h2>연납과 6월 일괄부과</h2>
{lump}
<h2>앞으로 바뀔 수 있나요</h2>
<p>자동차세를 배기량 대신 차량 가격 등으로 매기자는 개편 논의가 2023년에 시작됐어요(행정안전부 발표). 하지만 {FACTS_AS_OF} 기준으로
바뀐 법은 없어요. 법이 바뀌면 차일지 계산과 이 글도 함께 고칠게요.</p>"""
    faqs = [
        ("비싼 수입 전기차도 같은 금액인가요?",
         f"네. 비영업용 전기·수소 승용차 자동차세는 차값·크기·브랜드와 관계없이 연 {total:,}원으로 같아요."),
        ("수소차(넥쏘)도 전기차와 같나요?",
         f"네. 수소전기차도 배기량이 없어 전기차와 같은 '그 밖의 승용자동차'로 분류돼 연 {total:,}원이에요."),
        ("오래된 중고 전기차는 세금이 줄어드나요?",
         f"아니요. 정액이라 차령 경감이 없어요. 10년 된 전기차도 신차와 같은 연 {total:,}원이에요."),
        ("하이브리드도 전기차처럼 정액인가요?",
         "아니요. 엔진이 있는 하이브리드는 배기량으로 매기고, 가솔린차와 똑같이 차령 경감도 받아요."),
    ]
    sources = [SRC_LAW_127, SRC_LAW_128, SRC_MOIS_REFORM]
    return {
        "h1": f"전기차·수소차 자동차세는 왜 {man}일까",
        "title": f"전기차 자동차세는 왜 연 {total:,}원일까 — 수소차·하이브리드 비교",
        "description": (f"전기·수소차 자동차세는 배기량이 없어 연 {total:,}원(본세 {base:,}원 + 지방교육세 {edu:,}원) 정액이에요. "
                        "내연기관차와 연식별 비교, 하이브리드, 연납까지 정리했어요."),
        "lede": ("전기차와 수소전기차는 차값이나 크기와 관계없이 자동차세가 같아요. 왜 그런지, "
                 "내연기관차와 비교하면 어떤지 정리했어요."),
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }


# ---------------------------------------------------------------- 납부 방법·기한
def payment_guide(c):
    B = c.B
    due_rows = [[f"{m}월 {s}일~{e}일", label] for m, s, e, label in REGULAR_DUE]
    due_short = ", ".join(f"{m}월 {s}일~{e}일" for m, s, e, _ in REGULAR_DUE)
    big = c.v("grandeur-2.5")
    half = c.tax(big["displacementCc"])["annual"] // 2 // 10 * 10
    late = half * LATE_FIRST_PCT // 100
    # 본세 반년분이 월 가산 기준에 닿는 배기량 — 신차·가장 높은 cc당 세액 기준 (그 아래 차는 처음 3%만 붙는다)
    cc_need = LATE_MONTHLY_MIN_KRW * 2 // c.brackets[-1]["wonPerCc"]
    man = f"{LATE_MONTHLY_MIN_KRW // 10000}만원"
    monthly = num(LATE_MONTHLY_PCT, 2)
    lump = c.lump()
    summary = (f"<strong>한눈에</strong> 상반기분은 {REGULAR_DUE[0][0]}월 {REGULAR_DUE[0][1]}일~{REGULAR_DUE[0][2]}일, "
               f"하반기분은 {REGULAR_DUE[1][0]}월 {REGULAR_DUE[1][1]}일~{REGULAR_DUE[1][2]}일에 내요. 위택스·ETAX·은행·카드로 낼 수 있고, "
               f"기한을 넘기면 {LATE_FIRST_PCT}% 가산세가 바로 붙어요. 계속 밀리면 번호판을 떼어 갈 수 있어요.")
    body = f"""<h2>언제 내나요</h2>
<p>자동차세는 1년치(연세액)를 반으로 나눠 두 번 고지돼요. 지방세법 제128조에 정해진 기간이에요.</p>
{table(["납부 기간", "내는 몫"], due_rows)}
<p>마지막 날이 토요일·일요일·공휴일이면 다음 평일까지 낼 수 있어요. 1월에 1년치를 연납했다면 6월·12월 고지서는 나오지 않아요
(<a href="guide-prepay.html">연납 가이드</a>).</p>
{f"<p>{B.esc(lump)}</p>" if lump else ""}
<h2>어떻게 내나요</h2>
<ul>
<li><strong>위택스·스마트위택스</strong>(서울은 <a href="{URL_ETAX}" rel="noopener" target="_blank">ETAX</a>·STAX): 고지서가 없어도 조회해서 계좌이체나 카드로 낼 수 있어요.</li>
<li><strong>은행</strong>: 인터넷뱅킹·ATM의 지방세 납부 메뉴를 쓰거나, 고지서에 적힌 가상계좌로 이체해요.</li>
<li><strong>자동이체</strong>: 한 번 신청해 두면 6월·12월 정기분이 계좌에서 자동으로 빠져나가요.</li>
</ul>
<h2>전자고지·자동이체로 조금 아끼기</h2>
<p>고지서를 종이 대신 전자로 받거나(전자송달) 자동이체(자동납부)를 신청하면, 고지서 1장마다 세금을 조금 깎아 줘요.
지방세특례제한법 제92조의2에 따라 하나만 신청하면 {E_BILL_ONE[0]:,}~{E_BILL_ONE[1]:,}원, 둘 다 신청하면
{E_BILL_BOTH[0]:,}~{E_BILL_BOTH[1]:,}원 범위에서 지자체 조례로 정해요. 예를 들어 서초구는 하나에 {E_BILL_ONE[1]:,}원, 둘 다 하면 {E_BILL_BOTH[1]:,}원이에요.</p>
<p>큰돈은 아니지만 자동차세 고지서는 1년에 두 번이라 매년 쌓여요. 다만 자동이체를 해 두어도 1월 연납은 자동으로 되지 않아서 직접 내야 해요.</p>
<h2>늦게 내면 붙는 가산세</h2>
<p>납부 기한을 하루라도 넘기면 내야 할 세금의 {LATE_FIRST_PCT}%가 납부지연가산세로 바로 붙어요. 고지서의 세목별 세액이 {man} 이상이면
여기에 1개월마다 {monthly}%씩 더 붙고, 최대 {LATE_MONTHLY_MAX_MONTHS}개월까지 쌓여요(2024년 이후 납세의무가 생긴 세금 기준).</p>
<p>예를 들어 {c.link('grandeur-2.5')} 신차의 하반기분은 약 {half:,}원이라, 기한을 넘기면 약 {late // 100 * 100:,}원이 더 붙어요.
자동차세 본세가 한 번에 {man}을 넘으려면 신차 기준 배기량이 {cc_need:,}cc쯤 돼야 해서, 대부분의 승용차는 {LATE_FIRST_PCT}%만 붙어요.</p>
<h2>계속 안 내면 번호판을 떼어 가요</h2>
<p>독촉을 받고도 자동차세를 내지 않으면 지자체가 자동차 번호판을 떼어 보관할 수 있어요(번호판 영치, 지방세법 제131조).
지자체마다 운영 기준이 조금 다르지만, 한 번 밀리면 영치를 예고하고 두 번 이상 밀리면 영치하는 곳이 많아요. 다른 지역에서 밀린
세금 때문에 영치될 수도 있어요.</p>
<p>번호판이 영치되면 그 차는 운행할 수 없고, 밀린 세금을 내야 돌려받아요. 그래도 내지 않으면 차를 압류해 공매할 수도 있어요.</p>"""
    faqs = [
        ("고지서를 잃어버렸어요. 어떻게 내나요?",
         "위택스(서울은 ETAX)에 로그인하면 내 자동차세를 조회해서 바로 낼 수 있어요. 은행 인터넷뱅킹의 지방세 납부 메뉴에서도 조회돼요."),
        ("기한을 하루 넘겼는데 얼마나 더 내나요?",
         f"내야 할 세금의 {LATE_FIRST_PCT}%가 바로 붙어요. 하반기분이 {half:,}원이면 약 {late // 100 * 100:,}원이에요. "
         f"세목별 세액이 {man} 이상일 때만 1개월마다 {monthly}%씩 더 붙어요."),
        ("자동이체를 해 두면 연납도 자동으로 되나요?",
         "아니요. 자동이체는 6월·12월 정기분에만 적용돼요. 1월 연납은 신청 기간에 직접 신청하고 내야 할인돼요."),
        ("자동차세를 밀리면 번호판을 바로 떼어 가나요?",
         "보통은 고지와 독촉, 영치 예고를 거친 뒤예요. 기준은 지자체마다 조금 다르지만 두 번 이상 밀린 차를 영치하는 곳이 많아요. "
         "밀린 세금을 내면 번호판을 돌려받을 수 있어요."),
    ]
    sources = [SRC_LAW_128, SRC_LAW_BASIC_24, SRC_BASIC_55, SRC_SPECIAL_92_2, SRC_LAW_131, SRC_YEONCHEON_ARREARS,
               SRC_SEOCHO_AUTOPAY]
    return {
        "h1": "자동차세 언제·어떻게 내나요, 늦으면 얼마나 더 낼까",
        "title": "자동차세 납부 기간·방법과 가산세 — 6월·12월 정리",
        "description": (f"자동차세는 {due_short}에 내요. 위택스·은행·자동이체로 내는 법, 전자고지 공제, "
                        f"늦으면 붙는 {LATE_FIRST_PCT}% 가산세와 번호판 영치까지 정리했어요."),
        "lede": "자동차세는 1년에 두 번, 6월과 12월에 나와요. 언제 어디서 내는지, 늦으면 무엇이 붙는지 정리했어요.",
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }


# ---------------------------------------------------------------- 중고차 사고팔 때
def used_car_guide(c):
    B, y = c.B, c.y
    v = c.v("avante-1.6")
    age = 5
    annual = c.tax(v["displacementCc"], age)["annual"]
    moved = datetime.date(y, 4, 1)  # 예시 이전등록일
    seller_days = (moved - datetime.date(y, 1, 1)).days
    buyer_days = c.year_days - seller_days
    seller = annual * seller_days // c.year_days // 10 * 10
    buyer = annual * buyer_days // c.year_days // 10 * 10
    last = moved - datetime.timedelta(days=1)  # 판 사람은 이전등록일 전날까지
    rows = [["판 사람", f"1월 1일~{last.month}월 {last.day}일", f"{seller_days}일", f"약 {seller:,}원"],
            ["산 사람", f"{moved.month}월 {moved.day}일~12월 31일", f"{buyer_days}일", f"약 {buyer:,}원"]]
    summary = ("<strong>한눈에</strong> 차를 사고팔면 그해 자동차세는 소유권 이전등록일을 기준으로 날짜만큼 나눠 내요. 판 사람은 "
               "이전등록일 전날까지, 산 사람은 이전등록일부터예요. 연납했다면 남은 기간 몫을 돌려받거나 산 사람에게 넘길 수 있어요.")
    body = f"""<h2>날짜로 나눠서 내요</h2>
<p>1년 중간에 차 주인이 바뀌면 자동차세를 각자 가진 날만큼 나눠서 판 사람과 산 사람에게 따로 부과해요(지방세법 제129조).
기준은 소유권 이전등록일이에요. 판 사람은 이전등록일 전날까지, 산 사람은 이전등록일부터 몫을 내요.</p>
<p>계산은 '연세액 × 가진 날 수 ÷ 그 해 일수'예요. 예를 들어 {y - age + 1}년에 처음 등록한 {c.link('avante-1.6')}({age}년차, 연 {annual:,}원){B.josa(v['name'], '를', '을')}
{y}년 {moved.month}월 {moved.day}일에 이전등록했다면 이렇게 나눠요.</p>
{table(["", "기간", "일수", "자동차세"], rows)}
<p>실제 고지 금액은 지자체 계산 방식과 10원 미만 절사 때문에 조금 다를 수 있어요.</p>
<h2>이전등록은 빨리 하는 게 좋아요</h2>
<p>차를 넘겨주고도 이전등록이 늦어지면, 그동안의 자동차세는 서류상 주인인 판 사람에게 나와요. 매매로 산 사람은 산 날부터
{TRANSFER_DEADLINE_DAYS}일 안에 이전등록을 신청해야 해요(자동차등록령 제26조). 중고차 매매업체를 거치면 업체가 대신 해 주는 경우가 많아요.</p>
<p>차를 실제로 넘긴 날(양도일)이 이전등록일보다 빠르다면, 일할계산신청서에 매매계약서처럼 소유권이 바뀐 걸 증명하는 서류를 붙여
신청할 수 있어요. 그러면 양도일을 기준으로 나눠 줘요. 신청은 차가 등록된 시·군·구청에 하세요.</p>
<h2>연납했다면 돌려받거나 넘겨줘요</h2>
<p>1월에 1년치를 연납한 차를 팔면, 이전등록일부터 남은 기간 몫을 날짜로 계산해 돌려받아요. 돌려받는 절차와 시기는 지자체마다
조금 달라서 차가 등록된 시·군·구청 세무 부서에 물어보는 게 가장 빨라요.</p>
<p>산 사람이 동의하면 연납한 세금을 그대로 이어받게 할 수도 있어요(연세액 납부 승계). 이때는 돌려받는 대신 두 사람이 남은 기간 몫을
직접 정산해요. 연납 자체는 <a href="guide-prepay.html">연납 가이드</a>에 정리했어요.</p>
<h2>폐차하거나 수출할 때</h2>
<p>폐차나 수출로 등록을 말소하면 말소등록일까지만 자동차세를 내요. 이미 낸 세금이 있으면 남은 기간 몫을 날짜로 계산해 돌려받아요.</p>
<h2>중고차를 산 사람이 알아 둘 점</h2>
<ul>
<li>차령은 처음 등록한 날부터 이어서 세요. 주인이 바뀌어도 세금이 새 차처럼 다시 오르지 않아요(<a href="guide-aging.html">차령 경감</a>).</li>
<li>전 주인의 연납을 이어받지 않았다면, 다음 해부터는 직접 연납을 신청해야 할인받아요.</li>
<li>차를 사면 자동차세와 별도로 이전등록 때 취득세를 내요.</li>
</ul>"""
    faqs = [
        ("차를 팔았는데 자동차세 고지서가 나왔어요.",
         "이전등록일 전날까지는 판 사람 몫이라 고지서가 나올 수 있어요. 이전등록이 늦어졌는데 실제로 차를 넘긴 날이 더 빠르다면, "
         "매매계약서 같은 증명 서류를 붙여 시·군·구청에 일할계산신청을 하세요."),
        ("산 사람은 언제부터 자동차세를 내나요?",
         "소유권 이전등록일부터 그해 12월 31일까지의 몫을 내요. 날짜로 나눠 계산해요."),
        ("연납한 차를 팔면 어떻게 되나요?",
         "이전등록일부터 남은 기간 몫을 날짜로 계산해 돌려받아요. 산 사람이 동의하면 연납을 그대로 이어받게 하고 두 사람이 직접 정산할 수도 있어요."),
        ("중고차를 사면 자동차세가 새 차처럼 다시 올라가나요?",
         "아니요. 차령은 처음 등록한 날부터 이어서 세기 때문에 주인이 바뀌어도 그 연식의 세금 그대로예요."),
    ]
    sources = [SRC_LAW_129, SRC_REG_26, SRC_UIJEONGBU_PRORATE, SRC_EASYLAW_REFUND, SRC_TAXTIMES_TRANSFER]
    return {
        "h1": "중고차 사고팔 때 자동차세, 누가 얼마나 낼까",
        "title": "중고차 자동차세 정산 — 이전등록일 기준 일할계산과 연납 환급",
        "description": ("차를 사고팔면 자동차세는 이전등록일을 기준으로 날짜만큼 나눠 내요. 계산 예시, 이전등록 기한, "
                        "연납 환급·승계, 폐차할 때까지 정리했어요."),
        "lede": ("1년 중간에 차를 팔거나 사면 그해 자동차세는 누가 낼까요? 날짜로 나누는 방법과, 연납했을 때 돌려받는 방법을 "
                 "정리했어요."),
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }


# ---------------------------------------------------------------- 화물차·승합차
def truck_van_guide(c):
    B, rates = c.B, c.rates
    tr, vn = rates["truck"], rates["van"]
    first, small = tr["brackets"][0], next(s for s in vn["sizes"] if s["key"] == "small")
    business_small = small["businessKrw"]
    truck_rows = [[f"{b['maxKg']:,}kg 이하", f"{b['nonBusinessKrw']:,}원", f"{b['businessKrw']:,}원"] for b in tr["brackets"]]
    van_rows = [[s["label"], f"{s['nonBusinessKrw']:,}원", f"{s['businessKrw']:,}원"] for s in vn["sizes"]]
    one_ton = [v for v in c.cat.vehicles if v.get("vehicleClass") == "truck" and v.get("payloadKg")
               and v["payloadKg"] <= first["maxKg"]]
    pick = [s for s in ("porter2", "bongo3", "rexton-sports-2.2d", "porter2-electric") if s in c.by_slug]
    n_trucks = sum(1 for v in c.cat.vehicles if v.get("vehicleClass") == "truck")
    trucks_line = (f"차일지에 있는 화물차 {n_trucks}종이 모두 이 구간이에요." if len(one_ton) == n_trucks
                   else f"차일지에 있는 화물차 {n_trucks}종 중 {len(one_ton)}종이 이 구간이에요.")
    porter = c.v("porter2")
    rexton = c.v("rexton-sports-2.2d")
    nt = B.nonpassenger_tax(porter, rates)["nonBusiness"]
    rex_t = B.nonpassenger_tax(rexton, rates)["nonBusiness"]
    porter_as_car = c.tax(porter["displacementCc"])["annual"]
    car_v, van_v = c.v("carnival-2.2d"), c.v("carnival-11")
    car_t = c.tax(car_v["displacementCc"])["annual"]
    van_t = B.nonpassenger_tax(van_v, rates)["nonBusiness"]
    pt, pv = c.prepay(nt), c.prepay(van_t)
    lump_line = ""
    if c.th and max(nt, van_t) <= c.th:
        lump_line = (f"<p>자가용 1톤 트럭과 소형 승합차는 본세가 연 {c.th // 10000}만원 이하라 6월 일괄부과 기준에도 해당해요. "
                     f"{B.esc(c.lump(who=False))} 1월 연납이 된다면 1톤 트럭은 {pt['pay']:,}원({pt['discount']:,}원 할인), "
                     f"소형 승합차는 {pv['pay']:,}원({pv['discount']:,}원 할인)이에요{c.basis_paren}.</p>")
    summary = (f"<strong>한눈에</strong> 화물차는 적재정량, 승합차는 크기에 따라 정해진 금액을 내요. 자가용 1톤 트럭은 연 {nt:,}원, "
               f"11인승 이상 소형 승합차는 연 {van_t:,}원이에요. 승용차와 달리 지방교육세와 차령 경감이 없어요.")
    body = f"""<h2>승용·승합·화물은 어떻게 나뉘나요</h2>
<p>자동차관리법은 10명 이하가 타는 차를 승용차, 11명 이상이 타는 차를 승합차, 짐을 싣는 공간을 갖춘 차를 화물차로 나눠요.
자동차세도 이 구분을 따라 승용차만 배기량으로 매기고, 승합차와 화물차는 정해진 금액을 매겨요.</p>
<p>그래서 같은 모델이라도 정원에 따라 세금이 크게 달라요. {c.link('carnival-2.2d')}(7·9인승){B.josa(car_v['name'], '는', '은')} 승용차라 신차 기준 연 {car_t:,}원이지만,
같은 엔진의 {c.link('carnival-11', '카니발 11인승')}은 승합차라 연 {van_t:,}원이에요. 짐칸이
있는 픽업트럭({c.link('rexton-sports-2.2d', '렉스턴 스포츠')}·{c.link('tasman-2.5t', '타스만')})도 화물차예요.</p>
<h2>화물차는 적재정량으로 정해요</h2>
<p>적재정량은 실을 수 있는 짐의 무게예요. 자동차등록증에서 확인할 수 있어요. 구간별 세액은 이래요.</p>
{table(["적재정량", "자가용(비영업용)", "영업용"], truck_rows)}
<p>{B.esc(tr["over10tNote"])}.</p>
<p>{" · ".join(c.link(s, short_name(c.v(s)["name"])) for s in pick)}처럼 적재정량이 {first['maxKg']:,}kg 이하인 차는 자가용이면 모두 연 {nt:,}원이에요.
엔진이 크든 전기차든 상관없어요. 같은 배기량({porter['displacementCc']:,}cc)의 승용차라면 신차 기준 연 {porter_as_car:,}원이에요.
{trucks_line}</p>
<h2>승합차는 크기로 정해요</h2>
{table(["구분", "자가용(비영업용)", "영업용"], van_rows)}
<p>대형은 {B.esc(vn["largeCriteria"])}인 차예요. {c.link('carnival-11', '카니발 11인승')}·{c.link('staria-11', '스타리아 투어러 11인승')}처럼 개인이 많이 타는 11인승은
소형이라 자가용이면 연 {van_t:,}원이에요.</p>
<h2>승용차와 다른 점</h2>
<ul>
<li><strong>지방교육세가 없어요.</strong> 승용차는 본세에 {c.edu_pct}%가 더 붙지만, 화물·승합차는 정해진 금액만 내요.</li>
<li><strong>오래 타도 줄지 않아요.</strong> 차령 경감은 승용차에만 있어서 신차든 오래된 차든 같아요.</li>
<li><strong>영업용은 더 낮아요.</strong> 돈을 받고 짐이나 사람을 나르는 영업용(노란 번호판)은 1톤 트럭 연 {first['businessKrw']:,}원,
소형 승합차 연 {business_small:,}원이에요.</li>
</ul>
{lump_line}"""
    faqs = [
        ("픽업트럭도 화물차인가요?",
         f"네. 렉스턴 스포츠·타스만처럼 짐칸이 있는 픽업트럭은 화물차로 등록돼 적재정량으로 세금을 내요. "
         f"렉스턴 스포츠(적재정량 {rexton['payloadKg']:,}kg)는 자가용이면 연 {rex_t:,}원이에요."),
        ("카니발 11인승은 자동차세가 얼마인가요?",
         f"11인승은 승합차(소형)라 자가용이면 연 {van_t:,}원이에요. 7·9인승은 승용차라 배기량으로 계산해서 신차 기준 연 {car_t:,}원이에요."),
        ("화물차도 오래되면 세금이 줄어드나요?",
         "아니요. 차령 경감은 승용차에만 있어서 화물차·승합차는 연식과 관계없이 같은 금액이에요."),
        ("전기 화물차도 전기 승용차처럼 13만원인가요?",
         f"아니요. 전기 화물차도 화물차라 적재정량으로 매겨요. 포터2 일렉트릭처럼 {first['maxKg']:,}kg 이하면 자가용 연 {nt:,}원이에요."),
    ]
    sources = [SRC_LAW_127, SRC_CAR_MGMT_3, SRC_LAW_128]
    return {
        "h1": "화물차·승합차 자동차세는 왜 적을까",
        "title": "화물차·승합차 자동차세 — 1톤 트럭·픽업·11인승 세액 정리",
        "description": (f"화물차는 적재정량, 승합차는 크기로 정한 금액을 내요. 자가용 1톤 트럭 연 {nt:,}원, 11인승 소형 승합 연 {van_t:,}원. "
                        "승용차와 다른 점과 연납까지 정리했어요."),
        "lede": "1톤 트럭이나 11인승 승합차는 배기량이 커도 자동차세가 몇만 원이에요. 왜 그런지, 얼마인지 정리했어요.",
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }


BUILDERS = {"guide-prepay": prepay_guide, "guide-payment": payment_guide, "guide-aging": aging_guide,
            "guide-used-car": used_car_guide, "guide-ev": ev_guide, "guide-truck-van": truck_van_guide}


def build_all(B, rates, cat, this_year):
    """[(메타, 글)] — 메타는 GUIDES 항목, 글은 h1·title·description·lede·summary·body·faqs·sources."""
    c = Ctx(B, rates, cat, this_year)
    return [(g, BUILDERS[g["slug"]](c)) for g in GUIDES]
