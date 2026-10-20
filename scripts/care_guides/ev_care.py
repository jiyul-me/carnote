"""차 관리 가이드 — 전기차 소모품 관리 (care/ev-care.html).

숫자 출처
- 소모품 주기·방식·전기차 해당 여부는 data/parts.json(c.part·c.interval_text·type·appliesTo) — 수첩과 같은 값.
  가격 값은 쓰지 않는다. 표의 '방식' 이름은 replacement-schedule 글의 TYPE_LABEL·WORK_LABEL과 같게 둔다
  (같은 수첩 종류에 이름이 둘이면 안 된다 — 그 글에서 이름을 바꾸면 여기 KIND도 같이).
- 검사 주기·기간·과태료는 inspection 글이 다룬다. 이 글은 전기차만 다른 점(배출가스 검사 빠짐·고전원 절연 확인)만 쓰고
  그 글로 잇는다. 전기차 자동차세는 data/tax-rates.json(c.rates['displacement']['ev']) — 자동차세 가이드와 같은 값.
- 아래 TESLA_*·HMG_* 상수는 parts.json에 없는 제조사 안내라 출처와 함께 여기 둔다(바뀌면 고치고 GUIDE['updated']도).
- 데이터 차이(2026-10 조사)
  · 에어컨·히터 필터·브레이크액: 수첩 기본값과 테슬라 모델 Y 설명서(실내 필터 2년, 브레이크액 4년마다 상태 확인)가 다르다.
    글은 수첩 기본값을 기준으로 쓰고 _maker_gap()이 차이를 밝힌다.
  · 전용(저전도) 냉각수: 어느 회로에 쓰는지·교체 주기가 차종·연식마다 다르다(공식 매뉴얼 원문은 확인 못 함).
    혼용 금지 문구는 현대 수소전기차(NH2) 설명서에서만 확인해 그렇게 밝힌다. 주기는 수첩 기본값 + 설명서 확인.
  · 감속기 오일·브레이크 패드 수명 배수·타이어 마모 %·고전압 배터리 보증 기간: 공식 수치를 찾지 못해 숫자를 쓰지 않는다.
  · 전기차 배출가스 검사 면제: inspection.json regularInspection.note('전기차는 배출가스 검사 면제')를 따른다 —
    inspection 글('배출가스 검사만 빠져요')과 같은 표현. note에서 그 문구가 빠지면 _emission_text()가 확인 안내로 바꾼다.
    (2026-10 교차 점검 때 웹 재확인은 검색 한도로 못 했다 — 근거 출처는 inspection 글의 생활법령·서울시 자료.)
  · 공단 검사소 배터리 진단 서비스: 언론 보도(보안뉴스)만 근거라 시작 연도를 쓰지 않고 '있었다고 하니'로 쓴다.
  · HMG_* 수치(80% 안팎까지 채우기·25~75% 사이에서 쓰기)는 원 조사의 뉴스룸 기사 기준. 2026-10 검토 때 웹으로 재확인하지 못했다.
"""
import re

from care_guides import num, table

GUIDE = {"slug": "ev-care", "short": "전기차 소모품 관리", "published": "2026-10-20", "updated": "2026-10-20",
         "og_title": "전기차 소모품 관리", "og_lede": "엔진오일은 없지만 타이어·12V 배터리는 더 챙겨요",
         "summary": "엔진이 없어 빠지는 소모품, 전기차 소모품 주기표, 빨리 닳을 수 있는 타이어와 덜 닳는 브레이크, "
                    "전용 냉각수·12V 배터리·고전압 배터리 관리, 검사와 자동차세"}

# 테슬라 모델 Y 오너스 매뉴얼 — 유지보수 정비 주기 (SRC_TESLA_Y)
TESLA_CABIN_YEARS = 2            # 실내 에어 필터
TESLA_HEPA_YEARS = 3             # HEPA·카본 필터
TESLA_FLUID_CHECK_YEARS = 4      # 브레이크액 상태 확인(필요하면 교체)
TESLA_ROTATION_TREAD_MM = 1.5    # 앞뒤 트레드 깊이 차이가 이만큼 이상이면 위치교환
TESLA_CALIPER_KM = 20000         # 제설제 쓰는 지역 — 매년 또는 이 거리마다 캘리퍼 세척·윤활
# 현대자동차그룹 뉴스룸 — 리튬이온 배터리 충전 습관 (SRC_HMG_STORY)
HMG_IDEAL_PCT = 80
HMG_RANGE_PCT = (25, 75)

SRC_TESLA_Y = ("테슬라 모델 Y 오너스 매뉴얼 — 유지보수 정비 주기",
               "https://www.tesla.com/ownersmanual/modely/ko_kr/GUID-E95DAAD9-646E-4249-9930-B109ED7B1D91.html")
SRC_KIA_REGEN = ("기아 취급설명서 — 회생 제동 시스템(MV1 2027)",
                 "https://ownersmanual.kia.com/full_webhelp/MV1/2027/ko_KR/topics/t00194.html")
SRC_SAE_REGEN = ("SAE 2022-01-1161 — Estimating Brake Pad Life in Regenerative Braking Intensive Vehicle Applications",
                 "https://saemobilus.sae.org/content/2022-01-1161")
SRC_JDP_TIRE = ("DBusiness — J.D. Power 조사: 전기차 타이어가 무게·토크로 더 빨리 닳아요",
                "https://www.dbusiness.com/daily-news/report-tires-on-evs-wear-out-faster-due-to-greater-weight-and-higher-torque/")
SRC_FIRESTONE = ("Firestone Complete Auto Care — Do EV Tires Wear Out Faster?",
                 "https://firestonecompleteautocare.com/blog/tires/ev-tire-wear")
SRC_JALOPNIK = ("Jalopnik — Why EV tires wear out faster than gas cars",
                "https://jalopnik.com/2074138/why-ev-tires-wear-out-faster-than-gas-cars/")
SRC_HY_FCEV_COOLANT = ("현대 취급설명서 — 연료전지 냉각수 점검(수소전기차 NH2 2026)",
                       "https://ownersmanual.hyundai.com/full_webhelp/NH2/2026/ko_KR/topic_ovb_2q5_42c.html")
SRC_AUTOPIAN = ("The Autopian — 아이오닉 5 배터리 냉각 회로의 저전도 냉각수",
                "https://www.theautopian.com/electric-car-owner-pays-1500-for-fake-sounding-ion-flush-service-heres-what-that-is/")
SRC_NHTSA_TSB = ("NHTSA — 현대 서비스 기술 공지 MC-11033696(12V 방전 개선 소프트웨어, 미국)",
                 "https://static.nhtsa.gov/odi/tsbs/2026/MC-11033696-0001.pdf")
SRC_HMG_STORY = ("현대자동차그룹 뉴스룸 — 전기차 배터리 이야기",
                 "https://www.hyundaimotorgroup.com/ko/story/CONT0000000000044655")
SRC_HY_US_CHARGE = ("Hyundai USA — 전기차 충전 안내(한국어)", "https://www.hyundaiusa.com/us/ko/hybrid-and-ev/charging")
SRC_SMARTTODAY = ("스마트투데이 — 현대차·기아 \"전기차 배터리 100% 완충해도 안전\"",
                  "https://www.smarttoday.co.kr/ko-kr/articles/57728")
SRC_HY_WARRANTY = ("현대자동차 — 보증기간 안내",
                   "https://www.hyundai.com/kr/ko/customer-service/car-management-service/warranty-period/normal-period.html")
SRC_HY_HEV_SERVICE = ("현대자동차 — 아이오닉 하이브리드 서비스(보증) 안내",
                      "https://www.hyundai.com/kr/ko/vehicles/ioniq-hybrid/19pe/service.html")
SRC_BOANNEWS = ("보안뉴스 — 전기차 배터리 검사로 내 차 안전 지킨다", "https://m.boannews.com/html/detail.html?idx=109022")

# 표의 '방식' 칸 — replacement-schedule 글의 TYPE_LABEL·WORK_LABEL과 같은 이름
KIND = {"replace": "주기 교체", "inspect": "주기 점검", "refill": "보충", "on-failure": "고장 시 교체"}
KIND_BY_ID = {"tire-rotation": "주기 작업"}  # 위치교환은 새 부품이 아니라 타이어끼리 자리를 바꾸는 작업
KIND_HELP = {  # 표 위 설명 — 표에 나오는 방식만, 이 순서로
    "주기 교체": "때가 되면 새것으로 바꿔요",
    "주기 점검": "때가 되면 상태를 보고, 닳았거나 문제가 있을 때만 바꿔요",
    "주기 작업": "새 부품을 사는 게 아니라 정해진 작업을 해요(타이어끼리 자리 바꾸기)",
    "보충": "정해진 주기 없이 줄어들면 채워요",
    "고장 시 교체": "고장 나거나 불이 나가면 바꿔요",
}
NO_CYCLE = {"refill": "떨어지면", "on-failure": "고장 나면"}
SAME = "다른 차와 같아요"
EV_NOTE = {
    "coolant-ev": "전기차 전용이에요. 지정 냉각수만 써요",
    "reduction-gear-oil-ev": "전기차 전용이에요. 기준이 제조사마다 달라요",
    "brake-pad-front": "회생제동 덕분에 덜 닳는 편이에요",
    "brake-pad-rear": "회생제동 덕분에 덜 닳는 편이에요",
    "brake-disc": "덜 써서 생기는 녹도 살펴요",
    "tire": "무게·힘 때문에 빨리 닳을 수 있어요",
    "tire-rotation": "고르게 닳도록 꼭 챙겨요",
    "wheel-alignment": "쏠림·한쪽 마모가 보이면 바로 점검해요",
    "battery-12v": "방전되면 차가 안 켜질 수 있어요",
}
# 전기차에 없는 엔진 쪽 항목 — 보여 줄 순서와 이름(None이면 parts.json 이름에서 괄호를 뗀다)
NO_EV_SHOW = (("engine-oil", None), ("spark-plug", None), ("timing-belt", None), ("drive-belt", None),
              ("air-filter", None), ("coolant", "엔진 냉각수"), ("atf", None))
SAME_SHOW = ("brake-fluid", "cabin-filter", "wiper", "ac-refrigerant", "key-battery")


def _short(name):
    return re.sub(r"\s*\([^()]*\)", "", name).strip()


def _when(c, pid):
    """문장용 '…때에'/'…마다' — interval_text 끝말에 맞춰 조사를 붙인다."""
    t = c.interval_text(pid)
    return t + "에" if t.endswith("때") else t


def _cycle(c, p):
    """표의 주기 칸 — '10,000km 또는 6개월' · '40,000km마다' · '떨어지면'."""
    if not p.get("intervalKm") and not p.get("intervalMonths"):
        return NO_CYCLE.get(p["type"], "상태를 보고")
    return c.interval_text(p["id"]).replace(" 중 먼저 오는 때", "")


def _ev_parts(c):
    return [p for p in c.parts.values() if "ev" in p["appliesTo"]]


def _no_ev_names(c):
    """전기차에 없는 엔진 쪽 항목 이름 — appliesTo에 ev가 없는 것만."""
    out = []
    for pid, label in NO_EV_SHOW:
        p = c.parts.get(pid)
        if p and "ev" not in p["appliesTo"]:
            out.append(label or _short(p["name"]))
    fuel = [p for p in c.parts.values() if p["id"].startswith("fuel-filter")]
    if fuel and all("ev" not in p["appliesTo"] for p in fuel):
        out.append("연료필터")
    return out


def _kind(p):
    return KIND_BY_ID.get(p["id"]) or KIND.get(p["type"], "관리")


def _ev_table(c):
    B = c.B
    rows = []
    for p in _ev_parts(c):
        rows.append([B.esc(p["name"]), B.esc(_cycle(c, p)), B.esc(_kind(p)),
                     B.esc(EV_NOTE.get(p["id"], SAME))])
    return table(["항목", "수첩 알림", "방식", "전기차에서는"], rows)


def _kind_help(c):
    """표 위 '방식' 설명 — 표에 실제로 나오는 방식만 <li>로."""
    used = {_kind(p) for p in _ev_parts(c)}
    items = [f"<li>{k}: {v}.</li>" for k, v in KIND_HELP.items() if k in used]
    return "<ul>\n" + "\n".join(items) + "\n</ul>" if items else ""


def _emission_text(c):
    """전기차 배출가스 검사 — inspection.json note에 면제가 적혀 있을 때만 단정한다."""
    note = c.inspection.get("regularInspection", {}).get("note", "")
    if "전기차는 배출가스 검사 면제" in note:
        return "배기가스가 나오지 않는 차라 배출가스 검사만 빠지고, 차가 안전한지 보는 검사는 똑같이 받아요."
    return "배출가스 검사를 받는지는 예약할 때 검사소에 확인하세요. 차가 안전한지 보는 검사는 똑같이 받아요."


def _maker_gap(c):
    """에어컨·히터 필터·브레이크액 — 수첩 기본값과 테슬라 모델 Y 설명서의 차이."""
    cabin, fluid = c.part("cabin-filter"), c.part("brake-fluid")
    maker = (f"예를 들어 테슬라 모델 Y 설명서는 에어컨·히터 필터(설명서 이름은 실내 에어 필터)를 {TESLA_CABIN_YEARS}년마다, "
             f"고성능 필터(HEPA·카본 필터)는 {TESLA_HEPA_YEARS}년마다 바꾸라고 해요. "
             f"브레이크액은 {TESLA_FLUID_CHECK_YEARS}년마다 상태를 확인해 필요하면 바꾸라고 해요.")
    cm, fm = cabin.get("intervalMonths"), fluid.get("intervalMonths")
    if not cm or not fm:
        return maker + " 차일지 기본값과 기준이 다르니 내 차 설명서를 꼭 확인하세요."
    mine = "위 표의 차일지 기본값"
    if cm < TESLA_CABIN_YEARS * 12 and fm < TESLA_FLUID_CHECK_YEARS * 12:
        return maker + f" {mine}은 둘 다 이보다 짧은, 보수적인 값이에요."
    if cm > TESLA_CABIN_YEARS * 12 and fm > TESLA_FLUID_CHECK_YEARS * 12:
        return maker + f" {mine}은 이보다 길 수 있으니 설명서 주기를 꼭 확인하세요."
    return maker + f" {mine}과는 기준이 서로 달라요."


def _ym(mo):
    y, m = divmod(mo, 12)
    if not y:
        return f"{m}개월"
    return f"{y}년" if not m else f"{y}년 {m}개월"


def _battery_when(c):
    """12V 배터리 — '42개월(3년 6개월)마다'. 개월만 있고 딱 떨어지지 않을 때만 괄호로 풀어 준다."""
    p = c.part("battery-12v")
    mo = p.get("intervalMonths")
    if mo and not p.get("intervalKm") and mo >= 12 and mo % 12:
        return f"{mo}개월({_ym(mo)})마다"
    return _when(c, "battery-12v")


def _won(x):
    return f"{x // 10000}만원" if x % 10000 == 0 else f"{x:,}원"


def build(c):
    B = c.B
    notebook = c.link_notebook("차일지 수첩")
    schedule = c.link_care("replacement-schedule", "소모품 교체 주기표")
    tire = c.link_care("tire", "타이어 관리 글")
    brake = c.link_care("brake", "브레이크 글")
    battery = c.link_care("battery", "배터리 교체·방전 대처 글")
    fluids = c.link_care("fluids", "냉각수·오일 점검 글")
    inspection = c.link_care("inspection", "자동차 검사 글")
    tax = c.link_tax("guide-ev.html", "전기·수소차 자동차세 글")

    no_ev = _no_ev_names(c)
    no_ev_text = (f"{notebook}도 전기차에는 {B.esc(', '.join(no_ev))} 같은 항목을 보여 주지 않아요."
                  if no_ev else f"{notebook}은 연료에 맞는 항목만 보여 줘요.")
    same = ", ".join(_short(c.part(pid)["name"]) for pid in SAME_SHOW if "ev" in c.part(pid)["appliesTo"])
    n_ev = len(_ev_parts(c))

    rotation_when = _when(c, "tire-rotation")
    align_when = _when(c, "wheel-alignment")
    pad_when = _when(c, "brake-pad-front")
    coolant_when = _when(c, "coolant-ev")
    gear_when = _when(c, "reduction-gear-oil-ev")
    batt_when = _battery_when(c)
    tread = num(TESLA_ROTATION_TREAD_MM, 1)
    lo, hi = HMG_RANGE_PCT

    ev_tax = c.rates["displacement"]["ev"]["annualTotalKrw"]

    summary = ("<strong>한눈에</strong> 전기차는 엔진이 없어 엔진오일·점화플러그 같은 엔진 소모품을 바꾸지 않아요. "
               "대신 무거운 차체와 큰 힘 때문에 타이어가 빨리 닳을 수 있고, 12V 배터리 방전과 전용 냉각수는 따로 챙겨야 해요. "
               "차를 움직이는 고전압 배터리는 제조사 설명서와 보증 안내를 따르는 게 기본이에요.")

    body = f"""<h2>엔진이 없어서 빠지는 것들</h2>
<p>전기차는 엔진 대신 모터로 달려요. 그래서 엔진과 변속기, 연료 장치에 딸린 소모품은 바꿀 일이 없어요. {no_ev_text}
그 대신 감속기 오일(모터의 힘을 바퀴로 전하는 기어 장치에 든 오일)처럼 전기차에만 있는 항목이 생겨요.</p>
<p>그렇다고 관리할 게 없다는 뜻은 아니에요. 크게 나누면 이래요.</p>
<ul>
<li><strong>덜 챙겨도 되는 것</strong>: 엔진 소모품은 없고, 브레이크 패드는 덜 닳는 편이에요.</li>
<li><strong>똑같이 챙길 것</strong>: {B.esc(same)}예요.</li>
<li><strong>더 챙길 것</strong>: 빨리 닳을 수 있는 타이어, 방전되면 차가 안 켜지는 12V 배터리, 전용 냉각수, 그리고 충전 습관이에요.</li>
</ul>
<h2>수첩이 알려 주는 전기차 소모품</h2>
<p>수첩에서 연료를 '전기'로 고르면 아래 {n_ev}가지를 알려 줘요. 주행거리와 기간이 함께 적힌 것은 둘 중 먼저 오는 때가 기준이에요.
'방식' 칸은 때가 되면 무엇을 하면 되는지 알려 줘요. 이름은 소모품 교체 주기표와 같아요.</p>
{_kind_help(c)}
{_ev_table(c)}
<p>이 주기는 차일지 기본값이라 제조사 권장과 다를 수 있어요. 전기차는 특히 제조사마다 차이가 커요. {B.esc(_maker_gap(c))}
내 차 설명서의 정기 점검표가 다르면 설명서를 따르고, 수첩 알림은 정비소에서 상태를 확인하는 때로 쓰세요.
모든 소모품을 한 표로 보려면 {schedule}를 보세요.</p>
<h2>타이어는 더 자주 살펴요</h2>
<p>전기차는 큰 배터리를 싣고 있어 차가 무거운 편이고, 모터는 출발하자마자 큰 힘(토크)을 내요. 그래서 타이어가
내연기관차(휘발유·경유차)보다 빨리 닳을 수 있다는 미국 조사 회사 J.D. Power의 조사와 정비 업계 설명이 있어요.
얼마나 빨리 닳는지는 차와 운전 습관마다 달라요.</p>
<ol>
<li><strong>위치교환</strong>: 수첩 알림대로 {B.esc(rotation_when)} 앞뒤 타이어 위치를 바꿔 고르게 닳게 해요.
테슬라 모델 Y 설명서도 정해진 거리마다, 또는 앞뒤 타이어의 홈 깊이 차이가 {tread}mm 이상 벌어지면 위치를 바꾸라고 해요.</li>
<li><strong>마모 확인</strong>: 홈 바닥에 살짝 솟은 턱(마모한계 표시)이 땅에 닿는 면과 거의 같은 높이가 되면 바꿀 때예요.</li>
<li><strong>공기압 확인</strong>: 운전석 문을 열면 보이는 공기압 라벨이나 설명서에 적힌 값과 맞는지 자주 봐요.
마모와 공기압을 확인하는 법은 {tire}에 있어요.</li>
<li><strong>쏠림 확인</strong>: 똑바로 달리는데 차가 한쪽으로 쏠리거나 타이어 한쪽만 닳으면 휠 얼라인먼트(바퀴 정렬)를 점검받아요.
수첩은 {B.esc(align_when)} 점검하라고 알려 줘요.</li>
<li><strong>부드럽게 출발하기</strong>: 급출발·급가속을 줄이면 타이어가 덜 닳는 데 도움이 돼요.</li>
</ol>
<h2>브레이크는 덜 닳지만 점검은 받아요</h2>
<p>전기차는 속도를 줄일 때 모터를 발전기처럼 돌려 전기를 만들고, 그 전기를 배터리에 다시 채워요. 이걸 회생제동이라고 해요.
그만큼 패드로 디스크를 잡는 마찰 브레이크를 덜 써서 패드가 덜 닳는 편이에요. 패드를 얼마나 더 오래 쓸 수 있는지는
운전 습관과 회생제동 세기 설정에 따라 달라서 숫자로 말하기 어려워요.</p>
<p>덜 쓰는 게 문제가 되기도 해요. 디스크에 녹이 슬거나 캘리퍼(패드를 미는 집게)가 뻑뻑해질 수 있다는 지적이 있어요.
테슬라 모델 Y 설명서는 겨울에 제설제(염화칼슘 등)를 뿌리는 지역에서 탄다면 매년 또는 {TESLA_CALIPER_KM:,}km마다
캘리퍼를 청소하고 윤활하라고 해요. 내 차 설명서에도 비슷한 항목이 있는지 찾아보세요.
패드가 많이 남아 보여도 수첩 알림(앞 패드는 {B.esc(pad_when)})이 오면 정비소에서 바퀴를 떼고 봐 달라고 하세요.</p>
<p>브레이크액은 시간이 지나면 공기 중 수분을 머금어 성능이 떨어져요. 그래서 전기차도 기간이 되면 똑같이 바꿔요.
자세한 건 {brake}에 있어요.</p>
<h2>전용 냉각수·감속기 오일은 설명서대로</h2>
<p>전기차도 배터리와 모터, 전력 장치를 식혀야 해서 냉각수가 있어요. 차에 따라 냉각수가 도는 길(냉각 회로) 가운데 일부에
전기가 잘 통하지 않는 전용 냉각수(저전도 냉각수)를 써요. 어느 회로에 어떤 냉각수를 쓰는지는 차종·연식마다 달라요.
지정되지 않은 냉각수나 일반 부동액을 넣거나 섞으면 안 돼요. 전기차처럼 전용 냉각수를 쓰는 현대 수소전기차의 설명서에도
일반 냉각수가 섞이면 위험하니 보충을 지정 정비소에 맡기라고 적혀 있어요.</p>
<p>수첩은 전용 냉각수를 {B.esc(coolant_when)} 점검하라고 알려 줘요. 교체 시기는 제조사마다 차이가 커서 설명서 정기 점검표를
꼭 확인하세요. 감속기 오일도 바꿀 필요가 없다는 제조사부터 점검 뒤 바꾸라는 곳까지 기준이 달라요.
수첩은 {B.esc(gear_when)} 점검 알림을 주지만, 이것도 설명서가 먼저예요.</p>
<p>전기차에는 아주 높은 전압이 흐르는 부품이 있어요. 흔히 주황색으로 표시된 케이블과 부품은 만지지 말고,
냉각수 통 뚜껑이나 감속기 마개를 직접 열지 마세요. 보충과 교체는 전기차를 다루는 정비소에 맡겨요.
직접 볼 수 있는 것은 {fluids}에 정리했어요.</p>
<h2>12V 배터리 방전을 조심해요</h2>
<p>전기차에도 작은 12V 배터리가 따로 있어요. 차의 전자 장치를 켜는 배터리라, 차를 움직이는 큰 배터리(고전압 배터리)가
넉넉해도 12V 배터리가 방전되면 차가 켜지지 않을 수 있어요. 계기판에 주행 준비 표시(READY)가 뜨지 않는 거예요.</p>
<ul>
<li><strong>오래 세워 둘 때</strong>: 주차 중에도 녹화하는 블랙박스(차를 꺼도 전기를 쓰는 상시전원 연결)나 나중에 단 전기 장치는
12V 배터리를 계속 써요. 배터리 전압이 낮아지면 블랙박스가 스스로 꺼지는 '저전압 차단' 설정이 켜져 있는지 확인하세요.</li>
<li><strong>소프트웨어 업데이트</strong>: 제조사가 12V 방전을 줄이는 소프트웨어 업데이트를 내놓기도 해요(미국에서 나온 정비 공지 사례).
점검 때 내 차에 받을 업데이트가 있는지 물어보세요.</li>
<li><strong>교체</strong>: 수첩은 {B.esc(batt_when)} 바꿀 때라고 알려 줘요.</li>
</ul>
<p>방전됐다면 먼저 설명서를 보세요. 다른 배터리에 잠깐 연결해 전기를 빌려 오는 점프 시동은 연결 위치와 방법이
내연기관차와 다를 수 있어요. 확실하지 않으면 보험 긴급출동을 부르세요. 대처와 예방은 {battery}에 자세히 있어요.</p>
<h2>고전압 배터리는 제조사 안내를 따라요</h2>
<p>고전압 배터리는 차일지 수첩에 소모품으로 넣지 않았어요. 종류와 관리 방식이 차마다 달라서
제조사 안내를 따르는 게 가장 정확해요. 현대자동차그룹이 안내하는 충전 습관은 이래요.</p>
<ul>
<li>평소에는 {HMG_IDEAL_PCT}% 안팎까지만 채우는 게 이상적이라고 해요. 남은 양이 {lo}~{hi}% 사이를 오가게 쓰면
배터리가 늙는 것(열화)을 줄일 수 있다고도 해요.</li>
<li>그렇다고 100% 충전이 배터리 수명에 문제가 되는 건 아니라고 해요. 배터리를 지켜보고 조절하는 장치(BMS)가
안전한 범위에서 관리하니, 먼 길을 가기 전에는 가득 채워도 돼요.</li>
<li>날마다 하는 충전은 천천히 채우는 완속 충전이 배터리를 오래 쓰는 데 더 좋고, 빨리 채우는 급속 충전은
장거리 갈 때 쓰라고 해요(현대 미국 안내).</li>
</ul>
<p>배터리 종류(예: 흔히 LFP라고 부르는 리튬인산철 배터리)에 따라 권장 충전량이 다를 수 있으니 내 차 설명서가 먼저예요.
몇 %까지 채울지(충전 한도) 차 화면에서 정해 둘 수 있는 차도 있어요. 메뉴 이름은 설명서에서 확인하세요.</p>
<p>보증도 확인해 두세요. 고전압 배터리의 보증 기간과 주행거리는 차종·연식마다 달라요. 현대차 보증은 기간과 주행거리 중
하나라도 먼저 다 차면 끝나요. 처음 산 개인 고객에게만 주는 조건도 있어요(예를 들어 현대 하이브리드 배터리 평생 보증이 그래요).
중고로 샀다면 보증서를 확인하고, 보증이 이어지는지 제조사 고객센터에 물어보세요.</p>
<h2>검사·자동차세, 같은 것과 다른 것</h2>
<p>전기차도 다른 자가용 승용차와 같은 주기로 자동차검사를 받아요. 언제 받는지, 기간을 넘기면 과태료가 얼마인지는
{inspection}에 정리했어요. 여기서는 전기차라서 다른 점만 짚을게요.</p>
<ul>
<li><strong>빠지는 것</strong>: {_emission_text(c)}</li>
<li><strong>더 보는 것</strong>: 높은 전압이 흐르는 배터리와 전기 장치(고전원 전기장치)에서 전기가 새지 않게 잘 막혀 있는지(절연)
확인해요.</li>
<li><strong>함께 물어볼 것</strong>: 한국교통안전공단 검사소에서 배터리 상태를 진단해 알려 주는 서비스도 있었다고 하니(언론 보도),
검사 예약할 때 받을 수 있는지 물어보세요.</li>
</ul>
<p>자동차세는 배기량으로 매기는데 전기차는 배기량이 없어서, 자가용(비영업용) 전기 승용차는 1년에 {_won(ev_tax)}으로
금액이 정해져 있어요(정액). 차값이나 연식과 관계없이 같아요. 이유는 {tax}에 정리했어요.</p>"""

    faqs = [
        ("전기차도 엔진오일을 갈아야 하나요?",
         "아니요. 엔진이 없어서 엔진오일·점화플러그 같은 엔진 소모품은 바꾸지 않아요. 대신 감속기 오일과 배터리·모터를 식히는 "
         "전용 냉각수가 있어요. 둘 다 기준이 제조사마다 달라서 설명서를 확인하고, 보충과 교체는 정비소에 맡기세요."),
        ("전기차 냉각수는 직접 채워도 되나요?",
         "권하지 않아요. 차에 따라 전기가 잘 통하지 않는 전용 냉각수를 쓰고, 지정되지 않은 냉각수나 일반 부동액이 섞이면 안 돼요. "
         "근처에 고전압 부품도 있으니 냉각수 통 뚜껑을 열지 말고, 양이 모자라 보이면 전기차를 다루는 정비소에 맡기세요."),
        ("전기차 12V 배터리가 방전되면 어떻게 하나요?",
         "차를 움직이는 고전압 배터리가 넉넉해도 12V 배터리가 방전되면 차가 켜지지 않을 수 있어요. 점프 방법과 연결 위치가 "
         "차마다 달라서 설명서를 먼저 보고, 확실하지 않으면 보험 긴급출동을 부르세요. 다시 켜진 뒤에는 정비소에서 12V 배터리 "
         "상태와 방전 원인을 점검받으세요."),
        ("전기차는 매일 100% 충전해도 되나요?",
         f"현대자동차그룹은 평소 {HMG_IDEAL_PCT}% 안팎까지만 채우는 게 이상적이고, 남은 양이 {lo}~{hi}% 사이를 오가게 쓰면 "
         "배터리가 늙는 것(열화)을 줄일 수 있다고 안내해요. 그러면서도 100% 충전이 배터리 수명에 문제가 되는 건 아니라고 해요. "
         "권장은 제조사와 배터리 종류마다 다를 수 있으니 내 차 설명서를 따르세요."),
    ]
    src_data = [(s["label"], s["url"]) for s in c.inspection.get("sources", []) if s.get("url", "").startswith("https://")]
    sources = [SRC_TESLA_Y, SRC_JDP_TIRE, SRC_FIRESTONE, SRC_JALOPNIK, SRC_KIA_REGEN, SRC_SAE_REGEN,
               SRC_HY_FCEV_COOLANT, SRC_AUTOPIAN, SRC_NHTSA_TSB, SRC_HMG_STORY, SRC_HY_US_CHARGE, SRC_SMARTTODAY,
               SRC_HY_WARRANTY, SRC_HY_HEV_SERVICE] + src_data + [SRC_BOANNEWS]
    return {
        "h1": "전기차 소모품, 덜 챙겨도 되는 것과 더 챙길 것",
        "title": "전기차 소모품 관리 — 타이어·브레이크·12V 배터리·냉각수 챙기는 법",
        "description": ("전기차 소모품 관리를 정리했어요. 엔진오일은 없지만 타이어는 빨리 닳을 수 있고, 12V 배터리 방전과 "
                        "전용 냉각수는 따로 챙겨요. 소모품 주기표와 브레이크 점검, 충전 습관, 검사·자동차세까지 담았어요."),
        "lede": ("전기차는 엔진오일을 갈 일이 없어서 관리할 게 거의 없다고들 해요. 반은 맞고 반은 틀려요. "
                 "덜 챙겨도 되는 것과 오히려 더 챙겨야 하는 것을 나눠, 무엇을 언제 확인할지 정리했어요."),
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }
