"""자동차 소모품 교체 주기 한눈에 — care/replacement-schedule.html (차 관리 가이드의 허브 글).

- 표는 data/parts.json의 모든 소모품을 분류(categories)별로 그린다. 주기 숫자는 c.interval_text()로만 만든다
  (수첩과 같은 값). 가격 값은 쓰지 않는다(콘텐츠 페이지 노출 금지).
- 제조사 설명서와 비교하는 문장은 아래 MANUAL_* 상수(출처 확인한 설명서 값)와 parts.json 값을 견주어 만든다 —
  parts.json 기본값이 바뀌면 '더 길다/짧다' 문장도 따라 바뀐다. 설명서 숫자 자체는 글에 쓰지 않는다.
- 정기검사 첫 검사 햇수는 inspection.json regularInspection(firstInspectionAfterYears·firstInspectionByRegistration)
  에서만 꺼낸다 — 수첩(js/derive.js)이 같은 값으로 만료일을 계산한다.
- 출처 정리(2026-10): 설명서 딥링크는 검색 결과에 같은 URL이 나온 것만 남겼다. DN8 2024(점화플러그 엔진별 주기)·
  NX4 2025·기아 MQ4 2026 링크는 확인하지 못해 뺐고, 점화플러그 줄은 관찰한 차이가 아니어서 '설명서와 다를 때'
  목록에서 뺐다(엔진별 줄을 보라는 안내는 '내 차 설명서의 주기는 이렇게 찾아요' 3단계에 있다).
  QZ 2026 정기 점검 일람표는 상용 디젤 트럭 설명서로 보여 뺐다 — '먼저 오는 때' 문장은 DN8 2026·TK1 2026이 받친다.
  남은 한계: 설명서 비교값(MANUAL_*)은 페이지가 있는 것만 확인했고 표 안 수치는 이번 정리에서 다시 읽지 못했다.
  변속기 오일은 설명서 표기를 그대로 옮기지 않고(따옴표 인용 없이) '통상 조건에 주기를 두지 않은 경우'로 풀어 썼다.
"""
from care_guides import table, ext, date_ko

GUIDE = {
    "slug": "replacement-schedule", "short": "소모품 교체 주기 한눈에", "published": "2026-10-20", "updated": "2026-10-20",
    "og_title": "소모품 교체 주기 한눈에", "og_lede": "엔진오일부터 와이퍼까지 언제 바꿀까",
    "summary": "엔진오일·타이어·브레이크·배터리 등 소모품 전체의 교체·점검 주기를 분류별 표로",
}

# 글에서 링크하는 외부 출처 — 사실을 확인한 곳 (2026-10 확인 · 설명서 딥링크는 웹 검색 결과에 같은 URL이 나온 것만)
SRC_HY_DN8_26 = ("현대 취급설명서 — 통상 조건 점검·교체 주기(DN8 2026)",
                 "https://ownersmanual.hyundai.com/full_webhelp/DN8/2026/ko_KR/id6b219dd157c.html")
SRC_HY_SEVERE = ("현대 취급설명서 — 가혹 조건(GN7 2023)",
                 "https://ownersmanual.hyundai.com/full_webhelp/GN7/2023/ko_KR/id7b77f1c5ffe.html")
SRC_KIA_TK1 = ("기아 취급설명서 — 정기 점검·통상 조건 점검 주기 안내(TK1 2026)",
               "https://ownersmanual.kia.com/full_webhelp/TK1/2026/ko_KR/topics/t00929.html")
SRC_KIA_SERVICE = ("기아 취급설명서 — 서비스 알림 모드(TK1 2026)",
                   "https://ownersmanual.kia.com/full_webhelp/TK1/2026/ko_KR/topics/t00435.html")
SRC_TS_REGULAR = ("한국교통안전공단 — 정기검사", "https://main.kotsa.or.kr/portal/contents.do?menuCode=01010200")
SRC_EASYLAW = ("찾기쉬운 생활법령정보 — 자동차 검사받기",
               "https://easylaw.go.kr/CSP/CnpClsMainBtr.laf?popMenu=ov&csmSeq=675&ccfNo=2&cciNo=2&cnpClsNo=1")
# 검사 유효기간은 시행규칙 별표에 있다 — 조문·별표 번호까지는 확인하지 못해 법령 이름 수준 링크로 둔다
SRC_LAW_RULE = ("국가법령정보센터 — 자동차관리법 시행규칙", "https://www.law.go.kr/법령/자동차관리법시행규칙")
URL_CYBERTS = "https://www.cyberts.kr"
URL_HY_MANUAL = "https://ownersmanual.hyundai.com"
URL_KIA_MANUAL = "https://ownersmanual.kia.com"

# 설명서 비교용 값 — 글에 숫자로 쓰지 않고 parts.json 기본값과 견주기만 한다
MANUAL_OIL_KM = (10000, 15000)        # 쏘나타 DN8 2026 통상 조건 — 엔진에 따라 10,000km·15,000km (SRC_HY_DN8_26)
MANUAL_CABIN_MONTHS = 12              # 쏘나타 DN8 2026 통상 조건 — 공조 장치용 에어필터 (SRC_HY_DN8_26)

FUEL = {"gasoline": "가솔린", "diesel": "디젤", "lpg": "LPG", "hybrid": "하이브리드", "ev": "전기차"}
TYPE_LABEL = {"replace": "주기 교체", "inspect": "주기 점검", "refill": "보충", "on-failure": "고장 시 교체"}
# parts.json에서 type이 'replace'지만 새 부품으로 바꾸는 일이 아닌 항목 — 표에는 '주기 작업'으로 보인다
WORK_IDS = ("tire-rotation",)
WORK_LABEL = "주기 작업"
NO_CYCLE = {"refill": "떨어지면", "on-failure": "고장 나면"}

# 표 이름에서 이어지는 자세한 글 (ORDER의 slug)
DETAIL = {
    "engine-oil": "engine-oil", "air-filter": "filters", "fuel-filter-diesel": "diesel-care",
    "fuel-filter-gasoline": "filters", "fuel-filter-lpg": "filters", "def-urea": "diesel-care",
    "coolant": "fluids", "coolant-ev": "ev-care", "atf": "fluids", "diff-oil-4wd": "fluids",
    "reduction-gear-oil-ev": "ev-care", "brake-pad-front": "brake", "brake-pad-rear": "brake",
    "brake-fluid": "brake", "brake-disc": "brake", "tire": "tire", "tire-rotation": "tire",
    "wheel-alignment": "tire", "battery-12v": "battery", "key-battery": "battery", "cabin-filter": "filters",
    "wiper": "winter", "washer-fluid": "fluids",
}

# 기본 꺼진 항목(defaultEnabled false) — 표의 '해당 차' 칸과 설명
OFF_WHO = {"timing-belt": "벨트 방식 엔진만", "def-urea": "요소수 넣는 디젤만",
           "fuel-filter-gasoline": "설명서에 교체 항목 있는 차만", "fuel-filter-lpg": "설명서에 교체 항목 있는 차만",
           "diff-oil-4wd": "사륜구동(4WD·AWD) 차만"}
FUEL_FILTER_TXT = ("연료 펌프와 한 덩어리로 연료탱크 안에 들어 있어 따로 바꾸지 않는 차도 있어요. "
                   "설명서 정기 점검표에 교체 항목이 있을 때만 켜세요.")
OFF_WHY = {
    "timing-belt": ("엔진 안 부품들이 움직이는 순간(타이밍)을 맞춰 주는 벨트예요. 벨트 대신 쇠사슬 모양의 체인을 쓰는 "
                    "엔진도 많아요. 설명서 정기 점검표에 타이밍벨트 항목이 있을 때만 수첩에서 켜세요. 벨트를 쓰는 엔진이라도 "
                    "교체 주기는 엔진마다 달라서 차일지 기본값과 맞지 않을 수 있어요. 헷갈리면 정비소에 물어보세요."),
    "def-urea": "배기가스 속 오염 물질을 줄이려고 넣는 액체예요. 요소수 주입구가 있는 디젤차만 해당해요.",
    "fuel-filter-gasoline": FUEL_FILTER_TXT,
    "fuel-filter-lpg": FUEL_FILTER_TXT,
    "diff-oil-4wd": ("네 바퀴를 모두 굴리는 사륜구동(4WD·AWD) 차에서 앞뒤 바퀴로 힘을 나눠 주는 트랜스퍼와, "
                     "따로 달린 디퍼렌셜(코너를 돌 때 좌우 바퀴가 다르게 돌 수 있게 해 주는 장치)의 오일이에요. "
                     "사륜구동 차라면 설명서 정기 점검표에서 이 항목을 확인하고 수첩에서 켜세요."),
}

# 분류 묶음 — h2 하나에 표 여러 개. parts.json에 새 분류가 생기면 마지막 묶음에 붙는다
GROUPS = (
    ("엔진·구동계 소모품 주기표", ("engine", "drivetrain")),
    ("브레이크·타이어·하체 소모품 주기표", ("brake", "tire", "chassis")),
    ("전기·에어컨·외장 소모품 주기표", ("electrical", "hvac", "body")),
)


def _cat_intro(c):
    winter = c.link_care("winter", "겨울철 관리 글")
    return {
        "engine": ("오일·필터·벨트처럼 엔진과 연료 쪽 소모품이에요. 전기차의 구동 배터리(고전압 배터리)와 모터를 식히는 "
                   "전용 냉각수도 수첩에서는 여기에 넣었어요. '저전도'는 전기가 잘 통하지 않게 만든 냉각수라는 뜻이에요."),
        "drivetrain": ("엔진·모터의 힘을 바퀴까지 보내는 장치예요. 전기차의 감속기는 모터의 빠른 회전을 바퀴에 맞게 "
                       "줄여 주는 장치예요."),
        "brake": ("차를 세우는 장치예요. 안전과 바로 이어져서 점검 때를 넘기지 않는 게 좋아요. 뒷바퀴에 드럼 브레이크를 "
                  "쓰는 차는 패드 대신 라이닝이 닳아요."),
        "tire": ("위치교환은 타이어끼리 자리를 바꿔 끼워 고르게 닳게 하는 일이에요. 휠 얼라인먼트는 차가 똑바로 "
                 "굴러가도록 바퀴 각도를 맞추는 일이에요."),
        "chassis": "쇼크업소버는 노면 충격과 차의 출렁임을 잡아 주는 부품이에요.",
        "electrical": "차의 전기 장치예요. 전기차에도 12V 배터리가 따로 있어요.",
        "hvac": "에어컨과 히터 쪽이에요.",
        "body": f"와이퍼·워셔액 같은 항목이에요. 겨울에는 얼지 않는 워셔액을 쓰세요. 자세한 건 {winter}에 정리했어요.",
    }


def _batchim(word):
    """마지막 글자에 받침이 있나 — 괄호 꼬리('배터리(12V)')는 떼고 본다."""
    w = word.split("(")[0].strip() or word
    ch = w[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 != 0
    return False


def _eun(word):
    return word + ("은" if _batchim(word) else "는")


def _fuels(p):
    s = set(p["appliesTo"])
    if s >= set(FUEL):
        return "모든 차"
    if s == set(FUEL) - {"ev"}:
        return "전기차 제외"
    return "·".join(v for k, v in FUEL.items() if k in s)


def _cycle(c, p):
    """표의 주기 칸 — '10,000km 또는 12개월'(먼저 오는 때는 표 위에서 설명) · '40,000km마다' · '떨어지면'."""
    if not p.get("intervalKm") and not p.get("intervalMonths"):
        return NO_CYCLE.get(p["type"], "상태를 보고")
    return c.interval_text(p["id"]).replace(" 중 먼저 오는 때", "")


def _when(c, pid):
    """문장용 '…에'/'…마다' — interval_text 끝말에 맞춰 조사를 붙인다."""
    t = c.interval_text(pid)
    return t + "에" if t.endswith("때") else t


def _row(c, p):
    B = c.B
    name = c.link_care(DETAIL[p["id"]], p["name"]) if p["id"] in DETAIL else B.esc(p["name"])
    who = _fuels(p) if p.get("defaultEnabled", True) else OFF_WHO.get(p["id"], f"{_fuels(p)} 중 해당 차만")
    how = WORK_LABEL if p["id"] in WORK_IDS else TYPE_LABEL.get(p["type"], p["type"])
    return [name, B.esc(_cycle(c, p)), B.esc(how), B.esc(who)]


def _tables(c):
    cats = c.part_categories or {}
    by_cat = {}
    for p in c.parts.values():
        by_cat.setdefault(p["category"], []).append(p)
    grouped = [cid for _, ids in GROUPS for cid in ids]
    groups = [(t, list(ids)) for t, ids in GROUPS]
    groups[-1][1].extend(cid for cid in by_cat if cid not in grouped)
    intro = _cat_intro(c)
    out = []
    for title, ids in groups:
        parts = []
        for cid in ids:
            if cid not in by_cat:
                continue
            label = cats.get(cid, cid)
            parts.append(f"<p>{c.B.esc(label)} — {intro.get(cid, '')}</p>".replace(" — </p>", "</p>"))
            parts.append(table(["소모품", "주기", "방식", "해당 차"], [_row(c, p) for p in by_cat[cid]]))
        if parts:
            out.append(f"<h2>{title}</h2>\n" + "\n".join(parts))
    return "\n".join(out)


def _first_example(c):
    """'먼저 오는 때' 예 — km·개월이 둘 다 있는 첫 항목(엔진오일)을 1년 주행거리 두 가지로 따져 본다."""
    p = c.parts.get("engine-oil")
    if not (p and p.get("intervalKm") and p.get("intervalMonths")):
        p = next((x for x in c.parts.values() if x.get("intervalKm") and x.get("intervalMonths")), None)
    if not p or not c.fuel_km:
        return ""
    km, mo = p["intervalKm"], p["intervalMonths"]
    out = [f"예를 들어 {_eun(p['name'])} {c.interval_text(p['id'])}예요."]
    for annual in (c.fuel_km, c.fuel_km // 3):
        need = km / annual * 12
        if need < mo:
            out.append(f"1년에 {annual:,}km를 달리면 약 {round(need)}개월 만에 {km:,}km가 차서 주행거리가 먼저 와요.")
        else:
            out.append(f"1년에 {annual:,}km만 달리면 {km:,}km를 채우기 전에 {mo}개월이 먼저 지나요. "
                       "덜 달렸어도 이때가 바꿀 때예요.")
    return " ".join(out)


def _work_item(c):
    """'방식' 설명의 '주기 작업' 줄 — WORK_IDS 항목이 parts.json에 있을 때만."""
    names = [c.parts[i]["name"] for i in WORK_IDS if i in c.parts]
    if not names:
        return ""
    return (f"<li>{WORK_LABEL}: 때가 되면 정해진 작업을 해요. 새 부품을 사는 일은 아니에요. "
            f"예를 들어 {c.B.esc(_eun(names[0]))} 타이어끼리 자리를 바꿔 끼우는 일이에요.</li>\n")


def _manual_diffs(c):
    """차일지 기본값과 설명서가 다른 예 — parts.json 값과 MANUAL_* 를 견주어 문장을 고른다."""
    items = []
    oil = c.part("engine-oil").get("intervalKm") or 0
    items.append("엔진오일: 같은 차종이라도 엔진에 따라 설명서 주기가 달랐고, "
                 + ("차일지 기본값보다 주기가 긴 엔진도 있었어요." if oil < MANUAL_OIL_KM[1]
                    else "차일지 기본값과 주기가 다른 엔진도 있었어요."))
    cabin = c.part("cabin-filter").get("intervalMonths")
    if cabin and cabin < MANUAL_CABIN_MONTHS:
        items.append("에어컨·히터 필터: 설명서가 차일지 기본값보다 기간을 길게 잡은 경우가 있었어요. "
                     "차일지 기본값은 더 자주 바꾸는 쪽이에요.")
    atf = c.part("atf")
    if atf["type"] == "replace":
        items.append(f"{atf['name']}: 설명서의 통상 조건에는 따로 점검·교환 주기를 두지 않고, 가혹 조건으로 "
                     "달릴 때만 주기에 맞춰 점검·교환하라고 안내하는 경우가 있어요. "
                     "차일지 기본값은 정비 현장에서 흔히 바꾸는 시기를 따랐어요. 설명서를 따르는 게 원칙이지만 "
                     "이 항목은 차를 쓰는 방식에 따라 판단이 갈려요. 수첩 알림이 오면 정비소에서 오일 상태를 함께 "
                     "봐 달라고 하세요.")
    cool = "냉각수: 오래 쓰는 냉각수(장수명 냉각수)를 넣은 차는 첫 교체를 훨씬 늦게 잡는 설명서도 있어요."
    if c.part("coolant")["type"] == "inspect":
        cool += " 그래서 차일지는 '주기 점검'으로 두고 상태를 보게 했어요."
    items.append(cool)
    return "<ul>" + "".join(f"<li>{c.B.esc(t)}</li>" for t in items) + "</ul>"


def _off_list(c):
    """기본 꺼진 항목 설명 — 같은 설명은 이름을 묶는다."""
    groups = []
    for p in c.parts.values():
        if p.get("defaultEnabled", True):
            continue
        why = OFF_WHY.get(p["id"], "같은 연료라도 일부 차에만 있는 항목이에요. 내 차 설명서에서 확인하세요.")
        for g in groups:
            if g[1] == why:
                g[0].append(p["name"])
                break
        else:
            groups.append(([p["name"]], why))
    return "<ul>" + "".join(f"<li>{c.B.esc('·'.join(n))}: {c.B.esc(w)}</li>" for n, w in groups) + "</ul>"


def _fuel_missing(c):
    """연료에 따라 없는 항목 — 전기차·디젤차 예."""
    ps = list(c.parts.values())
    ev_no = [p["name"] for p in ps if "ev" not in p["appliesTo"] and p["id"] in ("engine-oil", "spark-plug")]
    diesel_no = [p["name"] for p in ps if "diesel" not in p["appliesTo"] and p["id"] == "spark-plug"]
    out = []
    if ev_no:
        out.append(f"전기차에는 {'·'.join(ev_no)} 같은 엔진 쪽 항목이 없어요.")
    if diesel_no:
        out.append(f"디젤차에는 {diesel_no[0]} 항목이 없어요.")
    return " ".join(out)


def _inspection_note(c):
    """정기검사 주기 문장 — 첫 검사 햇수는 inspection.json의 기본값과 등록일별 값(firstInspectionByRegistration)으로 만든다.
    수첩도 같은 값으로 최초 등록일에 맞춰 첫 검사를 계산한다."""
    ri = c.inspection["regularInspection"]
    first = ri["firstInspectionAfterYears"]
    out = [f"{c.B.esc(ri['vehicleClassLabel'])}차는 처음 등록한 날부터 {first}년 뒤에 첫 검사를 받아요."]
    for r in sorted(ri.get("firstInspectionByRegistration") or [], key=lambda r: r["registeredOnOrAfter"]):
        if r["years"] != first:
            out.append(f"{date_ko(r['registeredOnOrAfter'])} 이후 새로 등록한 신차는 {r['years']}년 뒤예요.")
    out.append(f"그 뒤로는 {ri['intervalYears']}년마다 받아요. 말소했다가 다시 등록한 차처럼 예외도 있으니, "
               f"내 차 날짜는 자동차등록증이나 {ext(('TS 사이버검사소', URL_CYBERTS))}에서 확인하세요.")
    return " ".join(out)


def build(c):
    B = c.B
    n = len(c.parts)
    oil, rot, pad = c.part("engine-oil"), c.part("tire-rotation"), c.part("brake-pad-front")
    notebook = c.link_notebook("내 차 수첩")
    ev_only = [p["name"] for p in c.parts.values() if p["appliesTo"] == ["ev"]]
    ev_count = sum(1 for p in c.parts.values() if "ev" in p["appliesTo"])

    summary = (f"<strong>한눈에</strong> 차일지 기본값으로 {B.esc(_eun(oil['name']))} {B.esc(_when(c, 'engine-oil'))} 바꾸고, "
               f"{B.esc(_eun(rot['name']))} {B.esc(_when(c, 'tire-rotation'))} 해요. "
               "'주기 점검' 항목은 때가 되면 상태를 보고 필요할 때만 바꾸고, 짧은 거리·막히는 길 위주로 달리면 더 일찍 챙겨요. "
               "내 차 설명서(매뉴얼)의 정기 점검표에 주기가 있으면 그 주기를 따르세요.")

    body = f"""<h2>표 읽는 법</h2>
<p>아래 표의 주기는 차일지 {notebook}이 교체 시기를 계산할 때 쓰는 기본값과 똑같아요. 모두 {n}가지 소모품을
분류별로 모았어요. 알맞은 주기는 차종·엔진마다 달라서, 내 차 설명서(매뉴얼)에 주기가 있으면 그 주기를 따르세요.</p>
<p>주행거리와 기간이 함께 적힌 항목은 <strong>둘 중 먼저 오는 때</strong>에 챙겨요. 현대·기아 차량 설명서의 정기 점검표도
같은 방식이에요. {B.esc(_first_example(c))}</p>
<p>'방식' 칸은 무엇을 하면 되는지 알려 줘요.</p>
<ul>
<li>주기 교체: 때가 되면 새것으로 바꿔요.</li>
{_work_item(c)}<li>주기 점검: 때가 되면 상태를 확인하고, 닳았거나 문제가 있을 때만 바꿔요. 예를 들어 {B.esc(_eun(pad['name']))}
{B.esc(_when(c, pad['id']))} 닳은 정도를 보고, 얇아졌을 때 바꿔요.</li>
<li>보충: 정해진 주기 없이 줄어들면 채워요.</li>
<li>고장 시 교체: 고장 나거나 불이 나가면 바꿔요.</li>
</ul>
<p>표에서 이름에 링크가 걸린 소모품은 확인 방법과 주의점을 따로 정리한 글로 이어져요.</p>
{_tables(c)}
<h2>이런 운전이 많으면 더 일찍 챙겨요</h2>
<p>현대·기아 차량 설명서는 점검표를 '통상 조건'(보통 운전)과 '가혹 조건' 두 가지로 나눠요. 가혹 조건은 차에 부담이 큰
운전 환경이에요. 이런 환경에서 주로 달린다면 통상 주기보다 더 자주 점검하고 바꾸라고 안내해요. 대표적인 예는 이래요.</p>
<ul>
<li>짧은 거리를 자주 반복해서 달려요.</li>
<li>막히는 길에서 가다 서다를 자주 하거나, 시동을 켠 채 서 있는 공회전이 길어요.</li>
<li>모래·먼지가 많은 길이나 비포장길을 자주 달려요.</li>
</ul>
<p>짧은 출퇴근과 막히는 도심 운전이 대부분이라면 가혹 조건에 해당할 수 있어요. 산길·트레일러·업무용 운행 같은 나머지
조건은 {c.link_care("engine-oil", "엔진오일 글의 가혹 조건 체크리스트")}에 모아 두었어요. 하나씩 짚어 보고, 내 차 설명서의
가혹 조건 목록과도 견줘 보세요. 목록은 차종·연식마다 조금씩 달라요. 얼마나 앞당길지도 차마다 달라서 설명서의 가혹 조건 표를
따르는 게 가장 정확해요.</p>
<p>차일지 수첩은 통상 조건 기본값 하나로 계산해요. 가혹 조건이라면 수첩 알림보다 일찍 챙기고, 설정의 '알림 기준'에서
임박 표시가 더 일찍 뜨게 바꿔 두세요. 설명서가 권하지 않는 규격의 엔진오일을 넣었다면, 운전 환경과 상관없이 가혹 조건
주기로 바꾸라는 설명서도 있어요. 오일 규격 보는 법도 같은 엔진오일 글에 정리했어요.</p>
<h2>내 차에만 해당하는 항목이 있어요</h2>
<p>표에는 모든 차의 항목이 다 들어 있어서, 연료에 따라 필요 없는 것도 있어요. {B.esc(_fuel_missing(c))}
수첩에 차를 등록하면 연료에 맞는 항목만 보여요.</p>
<p>몇몇 항목은 같은 연료라도 일부 차에만 있어요. 그래서 수첩에서 기본으로 꺼져 있고, 내 차에 해당하면 설정의 '추적 항목'에서 켜요.</p>
{_off_list(c)}
<p>디젤차에서 챙길 것은 {c.link_care("diesel-care", "디젤차 관리 글")}, 전기차는 {c.link_care("ev-care", "전기차 관리 글")}에 따로 정리했어요.</p>
<h2>차일지 기본값과 설명서가 다를 때</h2>
<p>차일지 기본값은 여러 차에 두루 맞추려고 잡은 숫자라, 제조사 설명서와 다를 수 있어요. 현대·기아 몇몇 차종의 설명서를
살펴보니 이런 차이가 있었어요.</p>
{_manual_diffs(c)}
<p>내 차 설명서의 주기는 이렇게 찾아요.</p>
<ol>
<li>현대 차는 {ext(("현대 온라인 취급설명서", URL_HY_MANUAL))}, 기아 차는 {ext(("기아 온라인 취급설명서", URL_KIA_MANUAL))}에서
차종과 연식을 골라요. 다른 제조사는 제조사 홈페이지, 차에 있는 설명서 책자, 서비스센터에서 확인해요.</li>
<li>'정기 점검' 항목에서 통상 조건 표와 가혹 조건 표를 찾아요.</li>
<li>같은 차종이라도 엔진마다 주기가 달라요. 내 차 엔진(연료·배기량)에 맞는 줄을 보세요.</li>
<li>내 운전이 가혹 조건에 가까우면 가혹 조건 표의 주기를 따르세요.</li>
</ol>
<p>설명서 주기를 따르는 게 원칙이에요. 수첩 알림이 설명서보다 일찍 오면 '이제 상태를 볼 때'라는 신호로 쓰고, 정비소에서
확인한 뒤 설명서 주기에 맞추면 돼요. 반대로 설명서 주기가 더 짧으면 수첩 알림이 늦게 와요. 이때는 알림을 기다리지 말고
설명서 때에 맞춰 바꾸세요. 수첩 설정의 '알림 기준'에서 임박 표시가 더 일찍 뜨게 바꿔 둘 수도 있어요.</p>
<h2>수첩에 기록하면 때를 알려 줘요</h2>
<p>{notebook}은 이 표의 주기로 다음 교체·점검 때를 계산해요. 이렇게 쓰면 돼요.</p>
<ol>
<li>차를 등록하고 연료 종류를 골라요. 그 연료에 맞는 항목이 켜져요.</li>
<li>최근에 바꾼 것부터 날짜와 그때 주행거리를 기록해요. 점검만 받은 날도 기록하면 그날부터 다음 때를 다시 세요.</li>
<li>주유하거나 정비할 때 주행거리를 함께 적으면 주행거리 기준 시기가 더 정확해져요.</li>
<li>때가 가까워지면 '임박', 지나면 '지남'으로 보여요. 일정을 폰 캘린더로 내보내면 알림도 받을 수 있어요.</li>
</ol>
<p>차에 따라 계기판의 '서비스 알림' 기능에 주기를 넣어 두면 차가 직접 알려 주기도 해요. 기능과 메뉴 이름은 차종마다 달라요.</p>
<p>정기 자동차검사는 소모품 교체와 별개예요. {_inspection_note(c)}
수첩에 최초 등록일과 최근 검사일을 넣으면 다음 검사 만료일도 함께 챙겨 줘요. 검사를 받을 수 있는 기간과 늦었을 때 내는 과태료는
{c.link_care("inspection", "자동차 검사 글")}에 정리했어요.</p>"""

    ev_tail = f"{'·'.join(ev_only)}처럼 전기차에만 있는 항목도 있어요. " if ev_only else ""
    faqs = [
        ("중고차를 샀는데 이전에 언제 바꿨는지 모르면 어떻게 하나요?",
         "판매자에게 정비 기록이 남아 있는지부터 물어보세요. 기록이 없으면 정비소에서 엔진오일·브레이크·타이어 같은 "
         "주요 항목을 한 번 점검받는 게 좋아요. 바꾸거나 점검한 날과 그때 주행거리를 수첩에 기록하면, 수첩이 그날부터 "
         "다음 때를 세요."),
        ("차일지 주기와 내 차 설명서 주기가 다르면 어느 쪽을 따르나요?",
         "설명서를 따르세요. 차일지 기본값은 여러 차에 두루 맞춘 숫자라 제조사·엔진에 따라 다를 수 있어요. "
         "수첩 알림이 설명서보다 일찍 오면 정비소에서 상태를 확인하는 때로 쓰고, 설명서 주기가 더 짧으면 "
         "알림을 기다리지 말고 설명서 때에 맞춰 바꾸세요."),
        ("'주기 점검' 항목은 때가 되면 꼭 바꿔야 하나요?",
         "아니요. 주기 점검은 상태를 확인하는 때예요. 정비소에서 닳은 정도나 새는 곳을 보고, 문제가 있을 때만 바꿔요. "
         "괜찮다면 계속 쓰고, 점검한 날을 수첩에 기록해 두면 그날부터 다음 점검 때를 다시 세요."),
        ("전기차는 어떤 소모품을 챙기나요?",
         f"이 표의 {n}가지 중 전기차에 해당하는 것은 {ev_count}가지예요. 엔진오일·점화플러그 같은 엔진 쪽 항목은 없고, "
         f"{ev_tail}브레이크·타이어·12V 배터리·에어컨 필터는 똑같이 챙겨요. "
         "전기차는 제조사마다 주기 차이가 커서 내 차 설명서를 꼭 확인하세요."),
    ]
    sources = [SRC_HY_DN8_26, SRC_HY_SEVERE, SRC_KIA_TK1, SRC_KIA_SERVICE,
               SRC_TS_REGULAR, SRC_EASYLAW, SRC_LAW_RULE]
    return {
        "h1": "자동차 소모품 교체 주기, 한눈에 보는 표",
        "title": "자동차 소모품 교체 주기표 — 엔진오일부터 와이퍼까지 한눈에",
        "description": (f"엔진오일·타이어·브레이크·배터리 등 자동차 소모품 {n}가지의 교체·점검 주기를 분류별 표로 정리했어요. "
                        "'먼저 오는 때' 규칙, 가혹 조건, 내 차 설명서 주기와 다를 때 따르는 법까지 담았어요."),
        "lede": ("차가 처음 생기면 무엇을 언제 바꿔야 할지 막막해요. 차일지 수첩이 쓰는 기본 주기를 분류별 표로 모으고, "
                 "표 읽는 법과 내 차에 맞추는 법을 정리했어요."),
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }
