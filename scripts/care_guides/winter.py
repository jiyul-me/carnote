"""차 관리 가이드 — 겨울철 자동차 관리 (care/winter.html).

숫자 출처
- 배터리(12V)·냉각수·타이어·워셔액·와이퍼의 주기와 이름은 data/parts.json(c.part·c.interval_text) — 수첩과 같은 값.
  가격 값은 쓰지 않는다. parts.json note의 숫자(배터리 '통상 N~N년', 장수명 냉각수 연수·거리)도 문장에 옮기지 않는다.
- 아래 상수는 parts.json에 없는 법령·제조사 사실이라 출처와 함께 여기 둔다(바뀌면 고치고 GUIDE['updated']도).
- 단정하지 않는 것(2026-10 조사 — 출처끼리 다르거나 공식 확인이 안 됨)
  · 기온에 따른 공기압 감소 폭: 콘티넨탈 안의 페이지끼리도 다르다 → '대략'·범위로만, 출처는 콘티넨탈로 한정.
  · 겨울에 공기압을 얼마나 더 넣을지: 공식 수치 없음 → 추천 공기압에 맞추라고만. '낮추지 말라'는 한국타이어 공식 자료.
  · 사계절 타이어로 겨울나기, 체인 다는 바퀴(같은 모델도 연식마다 다름), 체인 종류 제약 → 설명서 확인.
  · 추위에 따른 배터리 성능 저하 퍼센트, 배터리 점검창 색, 예열 공회전 시간(30초·2~3분·디젤 차이), 지역별 공회전 제한
    시간·기온 예외·과태료, 전기차 겨울 주행거리 감소 폭, 워셔액 메탄올 기준의 현행 법령명·수치, 워셔액 견디는 온도 → 수치 쓰지 않음.
  · 와이퍼 세워 두기: 공식 자료를 확인하지 못해 '하는 사람도 있다, 방법은 설명서'로만 쓴다.
  · 한국타이어 눈길 제동거리 비교는 제조사 자체 시험이라 쓰지 않는다.
  · 겨울용 타이어 기준 7℃: 한국타이어·미쉐린 자료에만 붙인다. 현대·기아 설명서에 같은 수치가 있는지는 검토 때 다시
    확인하지 못해, 설명서 쪽은 '눈길·빙판길에선 겨울용 타이어나 체인'으로만 쓴다(확인되면 함께 적어도 된다).
  · 알루미늄 휠에 금속 체인을 피하라는 문장: 어느 출처인지 다시 확인하지 못해 뺐다. '쓸 수 있는 체인 종류는 설명서'로만.
  · 제설제(염화칼슘) 뒤 차 아래쪽 세차: 제조사 출처를 확인하지 못해 넣지 않았다. 출처를 확인하면 짧게 더한다.
"""
from care_guides import table

GUIDE = {"slug": "winter", "short": "겨울철 차 관리", "published": "2026-10-20", "updated": "2026-10-20",
         "og_title": "겨울철 자동차 관리", "og_lede": "추위 오기 전 점검부터 눈길 대비까지",
         "summary": "추위 전 배터리·냉각수·타이어·워셔액·와이퍼 점검, 겨울용 타이어와 스노체인, 추운 아침 예열·성에 제거, 눈길 감속 기준"}

# 겨울 전 점검표에 넣는 parts.json 항목 (순서대로)
CHECK_PARTS = ("battery-12v", "coolant", "tire", "washer-fluid", "wiper")
CHECK_WHAT = {
    "battery-12v": "시동이 전보다 느린지, 단자·케이블이 헐겁거나 부식되지 않았는지. 정비소에서 배터리 상태 검사",
    "coolant": "양이 충분한지, 사는 곳 겨울 기온에 맞는 농도(어는점)인지",
    "tire": "추천 공기압, 홈 깊이와 고무 상태, 겨울용 타이어가 필요한지",
    "washer-fluid": "겨울용(빙결 방지) 워셔액으로 채웠는지",
    "wiper": "닦을 때 줄무늬가 남거나 소리가 나는지, 고무가 갈라지지 않았는지",
}
TYPE_WORD = {"replace": "교체", "inspect": "점검", "refill": "보충", "on-failure": "고장 나면 교체"}

# 콘티넨탈타이어(한국) — 기온이 10℃ 떨어질 때 공기압이 대략 이만큼 낮아짐 (psi, bar). 회사 안에서도 페이지마다 달라 범위로만.
PSI_DROP_PER_10C = (1, 2)
BAR_DROP_PER_10C = ("0.07", "0.14")
# 한국타이어·미쉐린 — 기온이 이 값(℃) 이하로 내려가는 계절엔 겨울용 타이어 권장
# (현대·기아 설명서는 눈길·빙판길에서 겨울용 타이어나 규격 체인 — 7℃ 수치를 설명서에 붙이지 않는다, 위 docstring)
WINTER_TIRE_C = 7
# 현대 취급설명서(겨울철 운전) — 체인을 달면 체인 제작사 추천 속도와 이 속도(km/h) 중 낮은 쪽 이하
CHAIN_KMH = 30
# 현대 취급설명서(냉각수 점검하기) — 주위 온도별 부동액 비율 예 (℃, %), 이 범위를 벗어나면 부식·과열 우려
COOLANT_MIX = ((-15, 35), (-25, 40), (-35, 50), (-45, 60))
COOLANT_RANGE = (35, 60)
# 도로교통법 시행규칙 제19조 제2항 — 악천후 감속 (최고속도에서 줄이는 비율 %, 조건)
SNOW_MM = 20
SIGHT_M = 100
SLOW_RULES = (
    (20, f"비가 와 노면이 젖었을 때, 눈이 {SNOW_MM}mm 미만 쌓였을 때"),
    (50, f"노면이 얼었을 때, 눈이 {SNOW_MM}mm 이상 쌓였을 때, 폭우·폭설·안개로 {SIGHT_M}m 앞이 잘 안 보일 때"),
)
EX_LIMIT_KMH = 100  # 감속 예시에 쓰는 최고속도
# 미국 에너지부(fueleconomy.gov) — 대부분 제조사가 시동 뒤 이 정도(초) 지나 부드럽게 출발하라고 권함
IDLE_SEC = 30

SRC_CONTI = ("콘티넨탈타이어 — 겨울철의 타이어 공기압",
             "https://www.continental-tires.com/kr/ko/tire-knowledge/tire-pressure-in-winter/")
SRC_HY_TPMS = ("현대 취급설명서 — 타이어 공기압 경보 시스템(TPMS)",
               "https://ownersmanual.hyundai.com/docview/webhelp/Hyundai/2d3fd3b2-2fe7-409e-b843-ae9818f35fe5/id23C5E0QD0YK.html")
SRC_KIA_TPMS = ("기아 취급설명서 — 저압 타이어 감지 시 경고등 및 조치 방법(TK1 2026)",
                "https://ownersmanual.kia.com/full_webhelp/TK1/2026/ko_KR/topics/t00900.html")
SRC_HK_WINTER = ("한국타이어 — 한국타이어가 제안하는 겨울철 차량 안전관리",
                 "https://www.hankooktire.com/kr/ko/company/media-list/media-detail.630778.html")
SRC_HY_WINTER = ("현대 취급설명서 — 겨울철 운전(CE1 2025)",
                 "https://ownersmanual.hyundai.com/full_webhelp/CE1/2025/ko_KR/id23C2G0G0MPF.html")
SRC_KIA_SNOW = ("기아 취급설명서 — 눈 또는 빙판길 주행(CK 2021)",
                "https://ownersmanual.kia.com/full_webhelp/CK/2021/ko_KR/topics/chapter4_22_1.html")
SRC_MICHELIN = ("Michelin — Which winter tyres",
                "https://www.michelin.co.uk/auto/advice/winter-tyres-guide/which-winter-tyres")
SRC_HY_TIRE_GN7 = ("현대 취급설명서 — 타이어 교체(그랜저 GN7 2025)",
                   "https://ownersmanual.hyundai.com/full_webhelp/GN7/2025/ko_KR/id844cd1e1bbb.html")
SRC_KIA_WEAR = ("기아 취급설명서 — 타이어 교체 시기 및 마모 점검(TK1 2026)",
                "https://ownersmanual.kia.com/full_webhelp/TK1/2026/ko_KR/topics/t00964.html")
SRC_HY_SNOW_SX2 = ("현대 취급설명서 — 눈길 또는 빙판길 주행(SX2 2025)",
                   "https://ownersmanual.hyundai.com/full_webhelp/SX2/2025/ko_KR/id6d1ea5987c0.html")
SRC_POLESTAR = ("Polestar 2 취급설명서(한국어) — 스노 체인(2024)",
                "https://www.polestar.com/kr/manual/polestar-2/2024/article/abe6991a681fb99cc0a80151602229c2/")
SRC_LAW_SPEED = ("도로교통법 시행규칙 제19조(자동차등과 노면전차의 속도)",
                 "https://www.law.go.kr/법령/도로교통법시행규칙/제19조")
SRC_EASYLAW_SPEED = ("찾기쉬운 생활법령정보 — 속도제한 및 안전거리 확보",
                     "https://m.easylaw.go.kr/MOB/CsmInfoRetrieve.laf?csmSeq=684&ccfNo=2&cciNo=1&cnpClsNo=2")
SRC_HY_BATT = ("현대 취급설명서 — 배터리 관리(쏘나타 DN8 2026)",
               "https://ownersmanual.hyundai.com/full_webhelp/DN8/2026/ko_KR/id29e0f44e341.html")
SRC_KIA_BATT = ("기아 취급설명서 — 배터리 관리 요령",
                "https://ownersmanual.kia.com/docview/webhelp/Kia/c5c1f799-86d0-48cf-a152-a02d23077a80/topics/t00977.html")
SRC_HY_JUMP = ("현대 취급설명서 — 점프 시동(쏘나타 DN8 2026)",
               "https://ownersmanual.hyundai.com/full_webhelp/DN8/2026/ko_KR/id30acfcf3cbd.html")
SRC_AAA_NE = ("AAA Northeast — Polar Plunge to Bring Frigid Conditions",
              "https://magazine.northeast.aaa.com/daily/newsroom/polar-plunge-to-bring-frigid-conditions-that-can-wreak-havoc-on-vehicles-and-homes/")
SRC_AAA_MPLS = ("AAA Minneapolis — 5 Signs Your Car Battery Won't Make it Through Winter",
                "https://www.minneapolis.aaa.com/magazine/automotive/5-signs-your-car-battery-wont-make-it-through-winter")
SRC_HY_EV = ("현대 취급설명서 — 전기차 주행 정보 확인하기(CE1 2024)",
             "https://ownersmanual.hyundai.com/full_webhelp/CE1/2024/ko_KR/id225KB0H00YK.html")
SRC_KIA_WINTER_MODE = ("기아 취급설명서 — 윈터 모드(PUEV 2024)",
                       "https://ownersmanual.kia.com/full_webhelp/PUEV/2024/ko_KR/topics/t00019.html")
SRC_HY_COOLANT = ("현대 취급설명서 — 냉각수 점검하기",
                  "https://ownersmanual.hyundai.com/docview/webhelp/Hyundai/2d3fd3b2-2fe7-409e-b843-ae9818f35fe5/id244b585f671.html")
SRC_HY_COOLANT_GN7 = ("현대 취급설명서 — 냉각수 점검(그랜저 GN7 2026)",
                      "https://ownersmanual.hyundai.com/full_webhelp/GN7/2026/ko_KR/id158b2569c27.html")
SRC_KIA_WASHER = ("기아 취급설명서 — 워셔액 점검 및 보충(DL3 2024)",
                  "https://ownersmanual.kia.com/full_webhelp/DL3/2024/ko_KR/topics/t01057.html")
SRC_HY_WASHER = ("현대 취급설명서 — 워셔액 보충하기(NH2 2026)",
                 "https://ownersmanual.hyundai.com/full_webhelp/NH2/2026/ko_KR/id23C5G0I097Q.html")
SRC_HY_WASHER_GN7 = ("현대 취급설명서 — 와셔액 분출(그랜저 GN7 2025)",
                     "https://ownersmanual.hyundai.com/full_webhelp/GN7/2025/ko_KR/id88460c6b12f.html")
SRC_SEOUL_METHANOL = ("서울신문 — 스프레이형 제품 안전기준 강화, 워셔액 메탄올 기준(2017.8.22)",
                      "https://m.go.seoul.co.kr/news/2017/08/22/20170822011015")
SRC_EU_METHANOL = ("European Commission — New restriction on methanol in car windscreen washing fluids",
                   "https://single-market-economy.ec.europa.eu/news/new-restriction-methanol-car-windscreen-washing-fluids-2018-04-18_en")
SRC_KIA_START = ("기아 취급설명서 — 엔진 시동 방법",
                 "https://ownersmanual.kia.com/docview/webhelp/Kia/2eef3450-eeeb-45ce-a985-c6eba6ef267f/topics/chapter5_1_3.html")
SRC_HY_START = ("현대 취급설명서 — 엔진 시동 전 확인할 사항",
                "https://ownersmanual.hyundai.com/docview/webhelp/Hyundai/3addf724-4227-4aba-9e18-0d731b74617e/id0c65f0a6e61.html")
SRC_DOE_COLD = ("U.S. DOE fueleconomy.gov — Fuel Economy in Cold Weather",
                "https://www.fueleconomy.gov/feg/coldweather.shtml")
SRC_LAW_IDLE = ("대기환경보전법 제59조(공회전의 제한)",
                "https://www.law.go.kr/법령/대기환경보전법/제59조")
SRC_SEOUL_IDLE = ("서울특별시 자동차공회전 제한에 관한 조례(국가법령정보센터)",
                  "https://www.law.go.kr/LSW/ordinInfoP.do?ordinSeq=1836453")


def _ym(mo):
    """개월 수를 햇수로 — 42 → '3년 6개월', 24 → '2년'."""
    y, m = divmod(mo, 12)
    if not y:
        return f"{m}개월"
    return f"{y}년" if not m else f"{y}년 {m}개월"


def _interval(c, pid):
    """표·문장용 주기 — 기간만 있는 항목은 햇수를 기간 바로 뒤에 넣는다('42개월(3년 6개월)마다')."""
    p = c.part(pid)
    t = c.interval_text(pid)
    mo = p.get("intervalMonths")
    if mo and not p.get("intervalKm") and mo >= 12 and mo % 12:
        t = t[:-2] + f"({_ym(mo)})마다" if t.endswith("마다") else t + f"({_ym(mo)})"
    return t


def _when(c, pid):
    """'…에'/'…마다' — interval_text 끝말에 맞춰 조사를 붙인다."""
    t = _interval(c, pid)
    return t + "에" if t.endswith("때") else t


def _coolant_scope(c):
    """냉각수 항목이 전기차를 빼는지(appliesTo)에 맞춘 문장 — 빼지 않으면 빈 문자열."""
    if "ev" in c.part("coolant")["appliesTo"]:
        return ""
    tail = (" 전기차는 배터리·모터를 식히는 전용 냉각수를 써서 수첩이 따로 알려 줘요."
            if "coolant-ev" in c.parts else "")
    return "표의 냉각수는 엔진이 있는 차(하이브리드 포함) 기준이에요." + tail


def build(c):
    B = c.B
    notebook = c.link_notebook("차일지 수첩")
    battery = c.link_care("battery", "배터리 글")
    tire = c.link_care("tire", "타이어 글")
    fluids = c.link_care("fluids", "냉각수·워셔액 점검 글")
    diesel = c.link_care("diesel-care", "디젤차 관리 글")
    ev = c.link_care("ev-care", "전기차 관리 글")
    schedule = c.link_care("replacement-schedule", "소모품 교체 주기표")
    psi = "~".join(str(n) for n in PSI_DROP_PER_10C)
    bar = "~".join(BAR_DROP_PER_10C)
    lo, hi = COOLANT_RANGE

    check_rows = []
    for pid in CHECK_PARTS:
        p = c.part(pid)
        check_rows.append([B.esc(p["name"]), B.esc(f"{_interval(c, pid)} {TYPE_WORD.get(p['type'], '점검')}"),
                           B.esc(CHECK_WHAT[pid])])
    mix_rows = [[f"영하 {-t}℃", f"{pct}%"] for t, pct in COOLANT_MIX]
    slow_rows = [[B.esc(cond), f"100분의 {pct}", f"시속 {EX_LIMIT_KMH * (100 - pct) // 100}km 이하"]
                 for pct, cond in SLOW_RULES]
    scope = _coolant_scope(c)

    summary = ("<strong>한눈에</strong> 첫 추위 전에 배터리·냉각수·타이어·워셔액·와이퍼를 한 번에 점검하세요. "
               f"기온이 {WINTER_TIRE_C}℃ 아래로 자주 내려가면 겨울용 타이어를 준비하고, 체인은 설명서가 정한 바퀴에 미리 달아 봐요. "
               "추운 아침엔 긴 공회전 대신 잠깐 기다렸다 천천히 출발하고, 눈길·빙판길에선 적어도 법이 정한 만큼 속도를 줄여요.")

    body = f"""<h2>추위 오기 전, 이것부터 점검해요</h2>
<p>추위가 오면 이미 약해진 부품부터 탈이 나요. 첫 추위가 오기 전에 아래 다섯 가지를 한 번에 보세요.</p>
{table(["항목", "차일지 기본 주기", "겨울 전에 볼 것"], check_rows)}
<p>주기는 {notebook}이 알려 주는 기본값이에요. 제조사 권장과 다를 수 있으니 내 차 설명서의 정기 점검표가 먼저예요.
{B.esc(scope)} 다른 소모품 주기는 {schedule}에 있어요.</p>
<h2>배터리: 추운 아침 시동이 가장 걱정이에요</h2>
<p>추우면 배터리가 낼 수 있는 힘이 크게 줄어요. 여름엔 멀쩡하던 배터리가 추운 아침에 시동을 못 거는 이유예요.
오래된 배터리일수록 추위를 더 타요.</p>
<ul>
<li><strong>교체 알림 보기</strong>: 수첩은 12V 배터리를 {B.esc(_when(c, "battery-12v"))} 바꾸라고 알려 줘요.
교체 알림 날짜가 가깝거나 시동이 전보다 느리면 겨울 전에 점검받으세요.</li>
<li><strong>상태 검사받기</strong>: 힘이 얼마나 남았는지는 겉으로 알기 어려워요. 정비소에서 배터리 검사를 받고,
단자·케이블이 헐겁거나 부식되지 않았는지도 함께 봐 달라고 하세요.</li>
<li><strong>충전 상태 지키기</strong>: 충전이 모자란 채로 아주 추운 날씨에 오래 두면 배터리 안의 액체(전해액)가 얼어
케이스가 깨질 수 있어요. 오래 세워 두는 차라면 가끔 충분히 달려 주세요.</li>
</ul>
<p>아주 추운 날 오래 방전돼 있던 배터리는 얼었을 수 있어요. 언 배터리에 점프 시동을 하면 깨지거나 터질 수 있으니
직접 하지 말고 보험 긴급출동이나 정비소를 부르세요. 방전됐을 때 할 일과 점프 시동 순서는 {battery}에 정리했어요.</p>
<h2>냉각수와 워셔액, 얼지 않게</h2>
<p>냉각수는 엔진 열을 식히는 액체예요. 얼지 않게 하는 약품(부동액)과 물을 섞어 써요. 필요한 부동액 비율(농도)은 사는 곳이
얼마나 추운지에 따라 달라요. 현대 설명서의 예는 이래요.</p>
{table(["가장 추울 때 바깥 기온", "부동액 비율"], mix_rows)}
<p>같은 설명서는 부동액 비율이 {lo}%보다 낮거나 {hi}%보다 높으면 부식이나 과열이 생길 수 있다고 해요. 냉각수 종류와 비율은
차마다 다르니 직접 섞어 넣지 말고, 정비소에서 어는점(농도)을 재 달라고 하세요. 교체 시기도 차마다 달라요.
오래 쓰도록 만든 장수명 냉각수는 첫 교체가 훨씬 늦기도 하니 설명서를 확인하세요.</p>
<p><strong>엔진이 뜨거울 때는 냉각수 뚜껑을 열지 마세요.</strong> 뜨거운 냉각수가 뿜어져 나와 데일 수 있어요.</p>
<p>워셔액은 겨울 전에 얼지 않는 겨울용으로 채워요. 탱크에서 얼면 탱크나 워셔 모터가 상할 수 있어요.</p>
<ul>
<li>견디는 온도는 제품마다 달라요. 포장에 적힌 사용 온도를 보고 골라요.</li>
<li>냉각수(부동액)는 워셔액 대신 넣지 마세요. 앞유리에 뿌려지면 앞이 잘 안 보이고 차 도장도 상할 수 있어요.</li>
<li>탱크가 비었을 때는 워셔를 작동하지 마세요.</li>
<li>메탄올(메틸알코올)은 몸에 해로워서 우리나라와 유럽연합은 워셔액의 메탄올 함량을 제한해요. 성분이 표시된 제품을 쓰세요.</li>
</ul>
<p>냉각수 양을 보는 법과 워셔액 채우는 순서는 {fluids}에 있어요.</p>
<h2>타이어: 공기압은 내려가고 고무는 굳어요</h2>
<p>기온이 내려가면 타이어 속 공기가 차가워져, 같은 공간 안의 압력(공기압)이 낮아져요. 타이어 회사 콘티넨탈은 기온이 10℃ 떨어질 때
대략 {psi}psi({bar}bar) 낮아진다고 안내해요(psi·bar는 공기압 단위). 그래서 잘 맞춰 둔 타이어도 첫 추위에 공기압 경고등(TPMS)이
켜질 수 있어요. 대개 고장이 아니라 공기압이 내려간 거예요. 다만 공기압을 맞춘 뒤에도 경고등이 꺼지지 않거나 한 바퀴만 유독 빨리
빠지면 정비소에서 점검받으세요.</p>
<ul>
<li>아침 출발 전, 타이어가 식었을 때 재요.</li>
<li>운전석 문 쪽 라벨이나 설명서의 추천 공기압에 맞춰요.</li>
<li>눈길에 잘 붙으라고 일부러 공기를 빼면 안 돼요(한국타이어). 겨울이라고 얼마나 더 넣으라는 공식 수치도 없으니
추천 값에 맞추면 돼요.</li>
</ul>
<p>일반 타이어는 추우면 고무가 굳어 잘 미끄러져요. 겨울용(스노) 타이어는 고무 배합이 달라 {WINTER_TIRE_C}℃ 아래에서도 덜 굳어요.
타이어 회사(한국타이어·미쉐린)는 기온이 {WINTER_TIRE_C}℃ 이하로 내려가는 계절엔 겨울용 타이어를 쓰라고 안내해요.
현대·기아 설명서는 눈길·빙판길에선 겨울용 타이어나 규격에 맞는 체인을 쓰라고 해요.</p>
<ul>
<li><strong>네 바퀴 모두</strong> 같은 규격으로 바꿔요. 두 바퀴만 바꾸면 앞뒤 바퀴가 길을 붙잡는 힘(접지력)이 달라져 차를 다루기
어려워요. 규격이 섞이면 ABS(급제동 때 바퀴가 잠기지 않게 하는 장치)와 ESC(차가 옆으로 미끄러지지 않게 잡아 주는 장치)도
제대로 작동하지 않을 수 있어요.</li>
<li><strong>봄이 오면</strong> 다시 바꿔요. 기온이 {WINTER_TIRE_C}℃ 위인 날이 이어지면 겨울용은 소음이 크고 빨리 닳아요.</li>
<li><strong>사계절 타이어</strong>로 겨울을 나도 되는지는 차·타이어·사는 곳에 따라 달라요. 기아의 한 설명서는 눈길에 쓸 타이어로
사계절 타이어도 함께 적어 두었지만, 현대의 한 설명서는 겨울용 타이어나 체인을 쓰라고 해요. 눈이 자주 쌓이는 길을 다닌다면
정비소·타이어 전문점과 상의하세요.</li>
</ul>
<p>겨울 전에는 홈 깊이와 고무 상태도 함께 보세요. 확인하는 법은 {tire}에 있어요.</p>
<h2>스노체인은 눈 오기 전에 달아 봐요</h2>
<p>체인은 보통 차를 굴리는 바퀴(구동 바퀴)에 달아요. 하지만 앞바퀴인지 뒷바퀴인지는 차마다, 같은 모델이라도 연식마다 다를 수 있어요.
네 바퀴 굴림(4WD·AWD) 차라고 네 바퀴 모두 다는 것도 아니에요. 현대의 한 설명서는 네 바퀴 굴림이라도 앞바퀴에 달라고 해요.</p>
<ol>
<li>설명서의 체인 항목에서 달 바퀴와 쓸 수 있는 체인 종류를 확인해요.</li>
<li>타이어 옆면에 적힌 크기에 맞는 체인을 미리 준비해요. 마른 날 안전한 곳에서 한 번 달아 봐요. 눈 오는 길가에서 처음 달면 위험해요.</li>
<li>체인을 단 뒤에는 체인 제조사 권장 속도와 시속 {CHAIN_KMH}km 중 낮은 쪽 이하로 천천히 달려요(현대 설명서).</li>
<li>눈이 없는 길에 나오면 바로 떼요.</li>
</ol>
<h2>추운 아침, 출발 전 습관</h2>
<p><strong>예열은 짧게</strong>: 세워 둔 채 오래 공회전할 필요는 없어요. 현대·기아 설명서는 서서 엔진을 데우지 말고
적당한 속도로 달리면서 데우라고 해요. 시동 직후에는 급가속처럼 엔진 회전수를 갑자기 높이는 운전은 피해요.
미국 에너지부에 따르면 대부분 제조사는 시동 뒤 약 {IDLE_SEC}초 지나면 부드럽게 출발하라고 권해요. 엔진과 차에 따라
다를 수 있으니 설명서를 따르세요. 디젤차는 겨울 경유와 요소수도 챙겨야 해서 {diesel}에 따로 정리했어요.</p>
<p><strong>공회전 제한</strong>: 대기환경보전법 제59조에 따라 시·도는 조례로 주차장·차고지 같은 곳의 공회전을 제한할 수 있고,
어기면 과태료가 나올 수 있어요. 허용 시간과 추운 날 예외는 지역마다 달라요. 시·도 누리집이나 국가법령정보센터에서 사는 곳의
공회전 제한 조례(예: 서울시 조례)를 찾아보세요.</p>
<p><strong>성에·눈 치우기</strong>: 출발 전에 이렇게 해요.</p>
<ul>
<li>앞유리 성에 제거 버튼을 눌러 따뜻한 바람으로 유리부터 데워요. 차가운 유리에 워셔액을 뿌리면 그대로 얼어붙을 수 있어요.</li>
<li>와이퍼가 유리에 얼어붙었으면 억지로 작동하지 마세요. 연결 부품이 빠지거나 모터가 상할 수 있어요. 녹은 뒤에 써요.</li>
<li>밤새 눈이 예상돼 와이퍼를 세워 둘 때는 설명서의 와이퍼 항목을 먼저 보세요. 정해진 위치로 옮긴 뒤 세워야 하는 차도 있어요.</li>
<li>앞유리뿐 아니라 옆유리·사이드미러·전조등·후미등의 눈과 성에도 치우고 출발해요.</li>
</ul>
<h2>눈길·빙판길은 속도부터 줄여요</h2>
<p>도로교통법 시행규칙 제19조는 날씨가 나쁠 때 줄여야 할 속도를 정해요. 그 도로의 최고속도에서 아래 비율만큼 줄여요.
날씨에 따라 숫자가 바뀌는 속도 제한 표지가 있으면 그 표지를 따라요.</p>
{table(["노면·날씨", "최고속도에서 줄일 비율", f"최고속도 {EX_LIMIT_KMH}km/h 도로라면"], slow_rows)}
<p>법이 정한 비율은 적어도 이만큼은 줄이라는 기준이에요. 길이 더 미끄러우면 그보다 더 천천히 달려요. 미끄러운 길에서는
급출발·급제동·급한 핸들 조작을 피하고, 앞차와 거리를 평소보다 넉넉히 둬요.</p>
<h2>전기차는 이것도 챙겨요</h2>
<p>전기차는 추우면 차를 움직이는 큰 배터리(구동 배터리)가 차가워져 달릴 수 있는 거리가 줄어요. 고장이 아니라 기온이 오르면
다시 돌아와요(현대 설명서). 배터리를 데우는 윈터 모드도 전기를 써요(기아 설명서). 줄어드는 폭은 차와 날씨마다 다르니
겨울엔 충전을 평소보다 넉넉히 해 두세요. 전기차에도 12V 배터리가 따로 있어 추위에 방전될 수 있어요. 자세한 건 {ev}에 있어요.</p>"""

    faqs = [
        ("겨울에 예열은 몇 분 해야 하나요?",
         "오래 공회전할 필요는 없어요. 현대·기아 설명서는 서 있는 채로 엔진을 데우지 말고 적당한 속도로 달리면서 데우라고 해요. "
         f"미국 에너지부에 따르면 대부분 제조사는 시동 뒤 약 {IDLE_SEC}초 지나면 부드럽게 출발하라고 권해요. "
         "엔진에 따라 다를 수 있으니 내 차 설명서를 따르고, 출발 직후에는 급가속을 피하세요."),
        ("겨울용 타이어로 꼭 바꿔야 하나요?",
         f"타이어 회사(한국타이어·미쉐린)는 기온이 {WINTER_TIRE_C}℃ 이하로 내려가는 계절엔 겨울용 타이어를 권해요. "
         "현대·기아 설명서는 눈길·빙판길에선 겨울용 타이어나 규격 체인을 쓰라고 해요. "
         "사계절 타이어로 충분한지는 차·타이어·사는 곳에 따라 달라요. 바꾼다면 네 바퀴 모두 같은 규격으로 바꾸고, "
         "봄에 날이 풀리면 다시 바꿔요."),
        ("겨울에 전기차 주행거리가 줄었어요. 배터리가 고장 난 건가요?",
         "대개 아니에요. 추우면 차를 움직이는 구동 배터리가 차가워져 달릴 수 있는 거리가 줄지만, 현대 설명서는 고장이나 "
         "영구적인 변화가 아니라 기온이 오르면 다시 돌아온다고 해요. 윈터 모드처럼 배터리를 데우는 기능도 전기를 쓰니 "
         "겨울엔 충전을 넉넉히 해 두세요. 12V 배터리도 따로 있어 추위에 방전될 수 있어요."),
        ("스노체인은 어느 바퀴에 다나요?",
         "보통 차를 굴리는 바퀴에 달지만, 앞바퀴인지 뒷바퀴인지는 차마다, 같은 모델도 연식마다 달라요. "
         "네 바퀴 굴림(4WD·AWD) 차도 네 바퀴 모두 다는 것은 아니에요. 내 차 설명서의 체인 항목을 꼭 확인하고, "
         f"단 뒤에는 체인 제조사 권장 속도와 시속 {CHAIN_KMH}km 중 낮은 쪽 이하로 달리세요."),
    ]
    sources = [SRC_HK_WINTER, SRC_HY_WINTER, SRC_KIA_SNOW, SRC_MICHELIN, SRC_HY_TIRE_GN7, SRC_KIA_WEAR, SRC_CONTI,
               SRC_HY_TPMS, SRC_KIA_TPMS, SRC_HY_SNOW_SX2, SRC_POLESTAR, SRC_HY_BATT, SRC_KIA_BATT, SRC_HY_JUMP,
               SRC_AAA_NE, SRC_AAA_MPLS, SRC_HY_COOLANT, SRC_HY_COOLANT_GN7, SRC_KIA_WASHER, SRC_HY_WASHER,
               SRC_HY_WASHER_GN7, SRC_SEOUL_METHANOL, SRC_EU_METHANOL, SRC_KIA_START, SRC_HY_START, SRC_DOE_COLD,
               SRC_LAW_IDLE, SRC_SEOUL_IDLE, SRC_LAW_SPEED, SRC_EASYLAW_SPEED, SRC_HY_EV, SRC_KIA_WINTER_MODE]
    return {
        "h1": "겨울철 자동차 관리, 추위 오기 전에 챙길 것",
        "title": "겨울철 자동차 관리 — 월동 점검 체크리스트·겨울용 타이어·체인·예열",
        "description": ("겨울철 자동차 관리를 순서대로 정리했어요. 추위 전 배터리·냉각수·타이어·워셔액·와이퍼 점검, "
                        "겨울용 타이어와 스노체인, 추운 아침 예열과 성에 제거, 눈길 감속 기준까지 담았어요."),
        "lede": ("추위가 오면 시동이 늦게 걸리고, 타이어 경고등이 켜지고, 워셔액이 얼기도 해요. 겨울이 오기 전에 점검할 것과 "
                 "눈 오는 날 대비, 추운 아침 습관을 정리했어요."),
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }
