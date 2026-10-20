"""차 관리 가이드 — 냉각수·미션오일·워셔액 점검 (care/fluids.html).

숫자 출처
- 냉각수·미션오일·워셔액·4WD 오일·전기차 냉각수 주기는 data/parts.json(c.part·c.interval_text) — 수첩과 같은 값.
  가격 값은 쓰지 않는다.
- 아래 MANUAL_* 는 제조사 설명서에서 확인한 값(2026-10 조사)으로, 차일지 기본값과 견주는 문장에만 쓴다
  (바뀌면 고치고 GUIDE['updated']도).
- 데이터 차이(2026-10 조사)
  · 미션오일(atf): 수첩은 주기 교체인데, 제조사 설명서는 정기 점검이 필요 없다는 취지이고 가혹 조건 표에서만
    현대 일부 차종이 100,000km 교체다. 수첩 기본값이 더 이르다(보수적). 글은 '차일지 기본값'이라 밝히고, 어느 쪽이
    맞다고 단정하지 않고 운행 조건·설명서·정비소 상담으로 판단하라고 쓴다.
  · 냉각수(coolant): 수첩은 '점검' 주기다(교체 아님). 현대 해외판 설명서는 장수명 냉각수 첫 교체를 200,000km/120개월로
    잡고 그 뒤는 더 짧게 반복, 기아는 판·차종마다 첫 교체 시점이 달랐다(180,000~210,000km). 글에는 현대 예시 하나만,
    설명서 확인 안내와 함께 쓴다.
  · 4WD 오일(diff-oil-4wd): 수첩은 교체 주기인데 현대 일부 차종 표는 '점검'만, 트랜스퍼는 무점검·무교환인 표도 있다.
    물에 잠겼을 때 교체 안내는 설명서 근거가 있다. 글은 차이를 밝힌다.
- 현대 미국판 설명서(SRC_HY_SCHED_US)의 '10년 또는 100,000마일을 넘긴 차도 가혹 조건 표' 문장은 검토 때 원문을
  다시 확인하지 못해, 숫자 없이 '오래 탄 차도 가혹 조건으로 보는 설명서가 있다'로만 쓴다.
- 전기 장치 냉각수 문단은 아이오닉 5(NE1)·수소전기차(NH2) 설명서 근거라 '전기차와 수소전기차'로 쓴다(하이브리드는 확인 못 함).
- 확인하지 못해 쓰지 않은 것: 누유 색깔별 원인 표, 워셔액 메탄올 함량 규제, 부동액 혼합 비율 숫자(차종마다 다름),
  '무교환은 실제로 10만km까지' 같은 언론·커뮤니티 주장, 엔진 과열 때의 세부 순서(설명서 확인으로 안내).
"""
from care_guides import table

GUIDE = {"slug": "fluids", "short": "냉각수·미션오일·워셔액 점검", "published": "2026-10-20", "updated": "2026-10-20",
         "og_title": "냉각수·미션오일·워셔액", "og_lede": "보닛 열고 확인하는 순서와 이상 신호",
         "summary": "보닛 열기 전 안전 순서, 냉각수 양 보는 법과 교체 판단, 미션오일 주기가 설명서와 다를 때 판단법, "
                    "워셔액 직접 채우기, 누유·과열·변속 충격 신호"}

# 설명서 비교용 값 — parts.json 기본값과 견주는 문장에만 쓴다
MANUAL_HY_COOLANT_FIRST_KM = 200000   # 현대 해외판 — 장수명 냉각수 첫 교체(일반 조건) (SRC_HY_SCHED_DN8 등)
MANUAL_HY_COOLANT_FIRST_MONTHS = 120  # 같은 표 — 기간
MANUAL_HY_ATF_SEVERE_KM = 100000      # 현대 일부 차종 가혹 조건 표 — 자동변속기 오일 교체 (SRC_HY_SEVERE_NX4)

# 글에서 링크하는 외부 출처 — 사실을 확인한 곳 (2026-10 확인)
SRC_HY_COOLANT = ("현대 취급설명서 — 냉각수량 점검 및 보충(투싼 NX4 2025)",
                  "https://ownersmanual.hyundai.com/full_webhelp/NX4/2025/ko_KR/id158b2569c27.html")
SRC_KIA_COOLANT = ("기아 취급설명서 — 냉각수 점검(SP3 2026)",
                   "https://ownersmanual.kia.com/full_webhelp/SP3/2026/ko_KR/topics/t00969.html")
SRC_HY_COOLANT_EN = ("Hyundai owner's manual — Checking the coolant level (NX4 2025)",
                     "https://ownersmanual.hyundai.com/full_webhelp/NX4/2025/en_US/idcb22c2a0002.html")
SRC_HY_COOLANT_LX3 = ("Hyundai owner's manual — Engine coolant (Palisade LX3 2026)",
                      "https://ownersmanual.hyundai.com/full_webhelp/LX3/2026/en_US/topic_wtn_bvd_qcc.html")
SRC_KIA_COOLANT_EN = ("Kia owner's manual — Checking the coolant level",
                      "https://ownersmanual.kia.com/docview/webhelp/Kia/ca47032c-3999-43c4-830f-ed5607dfae9c/topics/t00667.html")
SRC_HY_COOLANT_NE1 = ("현대 취급설명서 — 냉각수(아이오닉 5 NE1 2025)",
                      "https://ownersmanual.hyundai.com/full_webhelp/NE1/2025/ko_KR/id244b585f671.html")
SRC_HY_WINTER = ("Hyundai owner's manual — Winter precautions",
                 "https://ownersmanual.hyundai.com/docview/webhelp/Hyundai/4235c092-6d41-4ced-9c20-8f810c9a43d1/idd28aaf786f8.html")
SRC_HY_MOTOR_COOLANT = ("현대 취급설명서 — 구동 모터 냉각수 점검하기(수소전기차 NH2 2026)",
                        "https://ownersmanual.hyundai.com/full_webhelp/NH2/2026/ko_KR/topic_f1d_qsm_y1c.html")
SRC_HY_SCHED_DN8 = ("Hyundai owner's manual — Normal maintenance schedule (Sonata DN8 2025, Australia)",
                    "https://ownersmanual.hyundai.com/full_webhelp/DN8/2025/en_AU/id212434cca84.html")
SRC_HY_SCHED_MX5 = ("Hyundai owner's manual — Normal maintenance schedule (Santa Fe MX5a 2024)",
                    "https://ownersmanual.hyundai.com/full_webhelp/MX5a/2024/en_US/topic_ybb_1yh_lwb.html")
SRC_HY_SCHED_NX4 = ("Hyundai owner's manual — Normal maintenance schedule (Tucson NX4 2025)",
                    "https://ownersmanual.hyundai.com/full_webhelp/NX4/2025/en_US/topic_ybb_1yh_lwb.html")
SRC_HY_SCHED_DN8_27 = ("Hyundai owner's manual — Normal maintenance schedule (Sonata DN8 2027)",
                       "https://ownersmanual.hyundai.com/full_webhelp/DN8/2027/en_US/topic_ybb_1yh_lwb.html")
SRC_KIA_SCHED = ("Kia owner's manual — Scheduled maintenance service",
                 "https://ownersmanual.kia.com/docview/webhelp/doc/f57a2858-3450-4dea-a006-736318b232bc/topics/chapter8_4.html")
SRC_KIA_SCHED_CV1 = ("Kia owner's manual — Scheduled maintenance service (CV1 2024)",
                     "https://ownersmanual.kia.com/full_webhelp/CV1/2024/en_GB/topics/chapter9_4.html")
SRC_HY_SEVERE_NX4 = ("현대 취급설명서 — 가혹 조건 정기 점검(투싼 NX4 2026)",
                     "https://ownersmanual.hyundai.com/full_webhelp/NX4/2026/ko_KR/id7b77f1c5ffe.html")
SRC_HY_ATF = ("현대 취급설명서 — 자동변속기 오일 점검하기",
              "https://ownersmanual.hyundai.com/docview/webhelp/Hyundai/0a0a3fce-8084-4812-b433-39b79b15ed46/topic_ksn_3r2_cbcQ.html")
SRC_KIA_SEVERE = ("기아 취급설명서 — 정기 점검(가혹 조건)",
                  "https://ownersmanual.kia.com/docview/webhelp/doc/60c239ff-44d3-4aa1-9269-d00f359f5df7/topics/chapter8_8.html")
SRC_HY_SEVERE_QV = ("현대 취급설명서 — 가혹 조건(QV 2026)",
                    "https://ownersmanual.hyundai.com/full_webhelp/QV/2026/ko_KR/topic_jtz_wks_s3c.html")
SRC_HY_SCHED_US = ("Hyundai owner's manual — Scheduled maintenance services (Sonata DN8 2025)",
                   "https://ownersmanual.hyundai.com/full_webhelp/DN8/2025/en_US/ide5b10be92ba.html")
SRC_HY_WASHER_LX3 = ("Hyundai owner's manual — Washer fluid (Palisade LX3 2026)",
                     "https://ownersmanual.hyundai.com/full_webhelp/LX3/2026/en_US/topic_tgg_sxd_qcc.html")
SRC_HY_WASHER_NX4 = ("Hyundai owner's manual — Checking the washer fluid level (NX4 2025)",
                     "https://ownersmanual.hyundai.com/full_webhelp/NX4/2025/en_GN/idc8b176bea31.html")
SRC_GN_WASHER = ("Genesis owner's manual — Checking the washer fluid level (JX 2026)",
                 "https://ownersmanual.genesis.com/full_webhelp/JX/2026/en_US/idab9017a4996.html")
SRC_KIA_WASHER = ("Kia owner's manual — Checking the washer fluid level (CL4 2026)",
                  "https://ownersmanual.kia.com/full_webhelp/CL4/2026/en_US/topics/t00763.html")

KIND = {"replace": "교체", "inspect": "점검", "refill": "보충", "on-failure": "고장 시 교체"}


def _when(c, pid):
    """문장용 주기 — interval_text 끝이 '때'면 '…때에'를 붙여 '…때에 점검' 꼴로 이어 쓴다."""
    t = c.interval_text(pid)
    return t + "에" if t.endswith("때") else t


def _verb(c, pid):
    """수첩 항목 종류(type)에 맞춘 동사 — '점검하라고' · '교체하라고' · '보충하라고'."""
    k = KIND.get(c.part(pid)["type"])
    return f"{k}하라고" if k else "챙기라고"


def _cell(c, pid):
    """표 칸 — '40,000km 또는 24개월 중 먼저 오는 때 점검' · '정해진 주기 없이 상태를 보고 보충'."""
    p = c.part(pid)
    return f"{c.interval_text(pid)} {KIND.get(p['type'], '')}".strip()


def _who(c, pid):
    return "직접 해도 돼요" if c.part(pid).get("diy") else "정비소에 맡겨요"


def _coolant_kind_text(c):
    """수첩의 냉각수 항목이 점검인지 교체인지에 맞춘 문장."""
    p = c.part("coolant")
    when = _when(c, "coolant")
    if p["type"] == "inspect":
        return (f"{when} 점검하라고 알려 줘요. 바꾸라는 뜻이 아니라, 정비소에서 양과 농도·상태를 재 보고 "
                "바꿀지 정할 때라는 뜻이에요.")
    return f"{when} {_verb(c, 'coolant')} 알려 줘요."


def _atf_vs_manual(c):
    """수첩 미션오일 기본값과 현대 일부 차종 가혹 조건 표(MANUAL_HY_ATF_SEVERE_KM) 비교 문장 — 그 표하고만 견준다."""
    km = c.part("atf").get("intervalKm")
    if not km:
        return "차일지 기본값은 이 표와 기준이 달라요."
    if km < MANUAL_HY_ATF_SEVERE_KM:
        return "차일지 기본값은 이 가혹 조건 주기보다도 일러요. 조심하는 쪽으로 일찍 잡은 값이에요."
    if km == MANUAL_HY_ATF_SEVERE_KM:
        return ("차일지 기본값은 이 가혹 조건 주기와 같아요. 이 차종들의 일반 조건보다 일찍, "
                "조심하는 쪽으로 잡은 값이에요.")
    return "차일지 기본값은 이 가혹 조건 주기보다 늦어요. 가혹 조건이라면 설명서 주기를 따르세요."


def _ev_coolant_text(c):
    """수첩이 전기차 전용 냉각수 항목을 따로 두는지(appliesTo)에 맞춘 문장."""
    p = c.part("coolant-ev")
    if "ev" not in p.get("appliesTo", []):
        return ""
    return (f"차일지 수첩은 전기차에 '{p['name']}' 항목을 따로 두고 {_when(c, 'coolant-ev')} "
            f"{_verb(c, 'coolant-ev')} 알려 줘요. ")


def _washer_text(c):
    """수첩의 워셔액 항목(주기·diy)에 맞춘 첫 문장."""
    p = c.part("washer-fluid")
    if p.get("intervalKm") or p.get("intervalMonths"):
        head = f"차일지 수첩은 워셔액을 {_when(c, 'washer-fluid')} {_verb(c, 'washer-fluid')} 알려 줘요."
    else:
        head = "워셔액은 차일지 수첩에도 정해진 주기가 없어요. 떨어지면 채우는 항목이에요."
    return head + (" 운전자가 직접 해도 돼요." if p.get("diy") else " 보충은 정비소에 맡겨도 돼요.")


def _diff_text(c):
    """수첩의 4WD 오일 항목이 기본으로 꺼져 있는지(defaultEnabled)에 맞춘 문장."""
    p = c.part("diff-oil-4wd")
    when = f"{_when(c, 'diff-oil-4wd')} {_verb(c, 'diff-oil-4wd')} 알려 줘요."
    if p.get("defaultEnabled", True):
        return f"차일지 수첩의 '{p['name']}' 항목은 {when}"
    return f"차일지 수첩의 '{p['name']}' 항목은 기본으로 꺼져 있어요. 4WD·AWD 차라면 켜서 쓰세요. 켜면 {when}"


def build(c):
    B = c.B
    notebook = c.link_notebook("차일지 수첩")
    coolant, atf, washer, diff, brake_fluid = (c.part(i) for i in ("coolant", "atf", "washer-fluid", "diff-oil-4wd",
                                                                    "brake-fluid"))
    atf_when = c.interval_text("atf")
    first_km = f"{MANUAL_HY_COOLANT_FIRST_KM:,}km"
    first_mo = MANUAL_HY_COOLANT_FIRST_MONTHS
    first_years = first_mo // 12
    severe_km = f"{MANUAL_HY_ATF_SEVERE_KM:,}km"
    engine_oil = c.link_care("engine-oil", "엔진오일 글")
    severe_list = c.link_care("engine-oil", "엔진오일 글의 가혹 조건 목록")
    brake = c.link_care("brake", "브레이크 글")
    winter = c.link_care("winter", "겨울철 차 관리 글")
    ev = c.link_care("ev-care", "전기차 관리 글")
    schedule = c.link_care("replacement-schedule", "소모품 교체 주기표")

    diff_cell = _cell(c, "diff-oil-4wd")
    if not diff.get("defaultEnabled", True):
        diff_cell += "(기본 꺼짐, 4WD·AWD 차만 켜요. 아래 4WD 섹션 참고)"
    rows = [
        [B.esc(coolant["name"]), B.esc(_cell(c, "coolant")),
         f"식었을 때 탱크 눈금 확인. 교체는 {B.esc(_who(c, 'coolant'))}"],
        [B.esc(atf["name"]), B.esc(_cell(c, "atf")),
         f"평소 변속 느낌과 바닥 자국 살피기. 점검·교체는 {B.esc(_who(c, 'atf'))}"],
        [B.esc(washer["name"]), B.esc(_cell(c, "washer-fluid")), f"보충은 {B.esc(_who(c, 'washer-fluid'))}"],
        [B.esc(diff["name"]), B.esc(diff_cell), f"점검·교체는 {B.esc(_who(c, 'diff-oil-4wd'))}"],
        [c.link_care("brake", brake_fluid["name"]), B.esc(_cell(c, "brake-fluid")),
         f"보충·교체는 {B.esc(_who(c, 'brake-fluid'))}"],
    ]

    summary = ("<strong>한눈에</strong> 냉각수는 엔진이 식었을 때 보조 탱크의 MIN·MAX 눈금 사이에 있는지 보고, "
               "뜨거울 때는 절대 캡을 열지 않아요. "
               f"미션오일은 차일지 기본값({B.esc(atf_when)})과 제조사 설명서가 다를 수 있어서 운행 조건과 설명서로 판단해요. "
               "워셔액은 직접 채워도 되지만 겨울에는 얼지 않는 제품을 쓰고, 워셔액 탱크에 냉각수를 넣으면 안 돼요.")

    body = f"""<h2>엔진룸에서 볼 수 있는 액체들</h2>
<p>엔진룸에는 엔진을 식히는 냉각수, 앞유리를 닦는 워셔액, 브레이크에 힘을 전하는 브레이크액이 담긴 통(탱크)이 있어요.
미션오일(자동변속기 오일)은 엔진오일과 다른 오일로, 자동변속기 안에 들어 있어요.</p>
<p>{notebook}이 각 액체를 언제 챙기라고 알려 주는지 표로 정리했어요.</p>
{table(["항목", "차일지 수첩 기본값", "운전자가 할 일"], rows)}
<p>운전자가 직접 해도 되는 건 냉각수 양 확인과 워셔액 보충 정도예요. 냉각수 보충은 내 차에 맞는 냉각수를 알 때만 직접 해요.
엔진오일은 {engine_oil}, 브레이크액은 {brake}에 따로 정리했어요.</p>
<h2>보닛 열기 전에 지킬 안전 순서</h2>
<ol>
<li>평평하고 안전한 곳에 세우고, 변속 레버를 P(주차)에 둔 뒤 주차 브레이크를 걸고 시동을 꺼요. 기울어진 곳에서는
탱크 눈금이 다르게 보일 수 있어요.</li>
<li>엔진이 충분히 식을 때까지 기다려요. 오래 세워 둔 차를 출발 전에 보는 게 가장 편해요.</li>
<li>보닛을 열고 확실히 고정됐는지 확인해요. 여는 방법은 차마다 달라서 설명서를 보세요.</li>
<li>설명서의 엔진룸 그림에서 탱크 위치를 찾아요. 뚜껑에 적힌 표시를 보고, 다른 탱크와 헷갈리지 않게 해요.</li>
<li>냉각 팬은 시동을 꺼도 갑자기 돌 수 있어요. 팬·벨트 근처에는 손을 넣지 말고, 모르는 부품은 만지지 않아요.
하이브리드·전기차에는 고전압 부품이 있으니 설명서가 보라고 한 곳만 확인해요.</li>
</ol>
<p><strong>엔진이 뜨거울 때는 냉각수 탱크 캡이나 라디에이터(엔진 앞쪽에서 냉각수를 식히는 장치) 캡을 절대 열지 마세요.</strong>
냉각 장치 안에는 압력이 걸려 있어서, 뜨거울 때 열면 뜨거운 냉각수와 김이 한꺼번에 뿜어져 나와 크게 다칠 수 있어요.</p>
<h2>냉각수 양 확인하고 보충하는 법</h2>
<p>냉각수에는 얼지 않게 하는 성분이 들어 있어서 흔히 부동액이라고도 불러요. 양은 보조 탱크(리저버 탱크)의 눈금으로 봐요.</p>
<ol>
<li>엔진이 식은 상태에서 보조 탱크를 찾아요.</li>
<li>탱크 옆면의 MIN(최소)과 MAX(최대) 눈금 사이에 냉각수가 있으면 괜찮아요. 탱크 위치와 눈금 표기는 차마다 달라요.</li>
<li>MIN 가까이 있거나 그보다 낮으면 보충해야 해요. 내 차에 맞는 냉각수를 설명서로 확인했을 때만 MAX를 넘기지 않게
조금씩 넣고, 모르겠으면 정비소에 맡겨요.</li>
<li>다 넣었으면 탱크 캡을 끝까지 꽉 잠가요. 덜 잠기면 달리는 동안 냉각수가 넘쳐 엔진이 과열될 수 있어요.</li>
</ol>
<p>가장 조심할 건 무엇을 넣느냐예요. 냉각수는 차마다 정해진 종류가 있고, 보충하는 방법도 차마다 달라요.
제조사에 따라 물과 섞은 냉각수를 넣으라고도 하고, 물만 보태라고도 해요. 물은 증류수처럼 깨끗한 물을 쓰라는 안내도 있어요.
설명서는 알코올이나 메탄올이 든 냉각수를 넣거나 섞지 말라고 해요. 냉각 장치가 크게 고장 날 수 있어요.
종류를 모르는 냉각수를 섞어 넣지는 마세요. 라디에이터 캡은 직접 열지 말고, 확인은 보조 탱크로만 해요.</p>
<p>보충하고 얼마 안 돼 또 줄어 있다면 어딘가 샐 수 있어요. 자주 채워야 한다면 점검을 받으세요.</p>
<h2>냉각수는 언제 바꾸나요</h2>
<p>수첩은 냉각수를 {B.esc(_coolant_kind_text(c))}
냉각수는 시간이 지나면 녹을 막는 첨가제가 줄어들어요. 물을 보태다 보면 농도가 묽어져 얼지 않게 하는 힘도 약해질 수 있어요.
그래서 언젠가는 정비소에서 바꿔야 해요.</p>
<p>교체 시기는 차와 냉각수 종류에 따라 크게 달라요. 오래 쓰도록 만든 장수명 냉각수를 넣은 차는 첫 교체를 꽤 늦게 잡기도 해요.
현대 해외판 설명서 중에는 처음 넣은 냉각수는 {first_km} 또는 {first_mo}개월({first_years}년) 중 먼저 오는 때 바꾸고,
그 뒤로는 더 짧은 간격으로 바꾸라고 한 것이 있어요. 기아 설명서도 차종과 연식에 따라 첫 교체 시점이 달라요.
그러니 수첩의 점검 알림이 오면 상태를 점검받고, 내 차 정기 점검표의 교체 시기와 견줘 정하세요.</p>
<p>겨울이 오기 전에는 내가 사는 곳의 추위에도 냉각수가 얼지 않는지 점검받으세요. 겨울 준비는 {winter}에 모았어요.</p>
<p>전기차와 수소전기차 중에는 배터리·모터 같은 전기 장치를 식히는 냉각수 탱크가 따로 있는 차가 있어요.
여기에는 전기가 잘 통하지 않게 만든 전용 냉각수(저전도 냉각수)만 넣어야 하고, 일반 부동액이나 물을 넣으면 고장이 날 수 있어요.
{B.esc(_ev_coolant_text(c))}자세한 건 {ev}에 있어요.</p>
<h2>미션오일, 수첩 주기와 설명서가 다를 때</h2>
<p>차일지 수첩 기본값은 미션오일을 {B.esc(atf_when)} 바꾸는 거예요.
그런데 제조사 설명서 중에는 자동변속기 오일은 정기적으로 점검할 필요가 없고, 가혹 조건(짧은 거리 반복이나 잦은 정체처럼
차에 부담이 큰 운전 환경)으로 달릴 때만 가혹 조건 점검표의 주기를 따르라는 것도 있어요.
현대 일부 차종의 가혹 조건 표에는 '{severe_km}마다 교체'로 적혀 있어요. {B.esc(_atf_vs_manual(c))}</p>
<p>어느 쪽이 맞다고 하나로 정하기는 어려워요. 정비소에 따라 이보다 일찍 교체를 권하기도 해요. 이렇게 판단해 보세요.</p>
<ol>
<li>내 차 설명서의 정기 점검표와 가혹 조건 표에서 자동변속기 오일 줄을 찾아요.</li>
<li>내 운전이 가혹 조건인지 따져 봐요. 짧은 거리 반복, 잦은 정체, 잦은 급가속·급제동, 험한 길·산길, 트레일러 끌기 같은
것들이에요. 자세한 건 {severe_list}을 보세요.</li>
<li>가혹 조건이라면 그 표의 주기를 따라요. 아니라면 수첩 알림이 올 때 상태를 점검받고 상담해요.</li>
</ol>
<p>가혹 조건 목록과 주기는 차종마다 달라요. 오래 탄 차도 가혹 조건으로 보는 설명서가 있으니, 연식이 오래됐거나
많이 달린 차라면 이 부분을 꼭 확인하세요.</p>
<h2>워셔액은 직접 채워요</h2>
<p>{B.esc(_washer_text(c))}
뿌렸을 때 잘 나오지 않으면 양부터 확인하세요. 눈·비가 잦은 철이나 먼 길을 떠나기 전에 한 번씩 봐 두면 좋아요.</p>
<ol>
<li>위의 안전 순서대로 차를 세우고 시동을 끈 뒤 보닛을 열어요.</li>
<li>워셔액 탱크를 찾아요. 냉각수·브레이크액 탱크와 헷갈리지 않게 뚜껑의 표시를 확인해요.</li>
<li>뚜껑을 열고 넘치지 않게 부어요. 흘린 건 닦아 내요.</li>
<li>뚜껑과 보닛을 닫고, 시동을 건 뒤 운전석에서 워셔액을 뿌려 잘 나오는지 봐요.</li>
</ol>
<ul>
<li><strong>냉각수(부동액)는 워셔액 탱크에 넣지 마세요.</strong> 앞유리에 뿌려지면 앞이 잘 안 보여 사고로 이어질 수 있고,
도장도 상할 수 있어요.</li>
<li>워셔액에는 알코올이 들어 있어 불이 붙을 수 있어요. 담배나 불꽃 가까이에서 다루지 마세요.</li>
<li>추운 철에는 얼지 않는 워셔액을 써요. 맹물은 여름에 워셔액이 없을 때만 잠깐 쓰고, 추워지기 전에 겨울용으로 채워 두세요.</li>
<li>물에 섞어 쓰는 제품이라면 희석 방법과 사용 온도는 제품 표기를 따라요. 물을 많이 섞을수록 얼기 쉬워요.</li>
</ul>
<p>양이 충분한데도 잘 나오지 않으면 정비소에 물어보세요.</p>
<h2>이런 신호가 보이면 정비소에 가요</h2>
<ul>
<li><strong>세워 둔 자리에 액체 자국</strong>: 자국의 위치와 색, 크기를 사진으로 찍어 두세요. 하룻밤 세워 둘 때 차 앞쪽
아래 바닥에 흰 종이를 손이 닿는 만큼 밀어 넣어 두면 떨어지는 곳과 색을 보기 쉬워요. 차 밑으로 들어가지는 마세요.
색만 보고 스스로 판단하지 말고 사진을 정비소에 보여 주세요.</li>
<li><strong>엔진 온도계가 높이 올라갈 때</strong>: 계기판의 엔진 온도계(냉각수 온도계)가 평소보다 높이 올라가거나 과열 경고가
뜨면 엔진이 지나치게 뜨거워졌다는 신호예요. 안전한 곳에 차를 세우고 설명서의 '엔진 과열' 항목을 따르세요.
이 항목은 미리 한 번 읽어 두면 당황하지 않아요. 보닛에서 김이 나면 가까이 가지 말고, 식기 전에는 냉각수 캡을 열지 마세요.
자신이 없으면 보험 긴급출동이나 견인차를 불러요. 온도계 모양은 차마다 달라서, 평소 어디쯤 있는지 알아 두면 이상을
빨리 알아챌 수 있어요.</li>
<li><strong>변속 느낌이 달라졌을 때</strong>: 기어가 바뀔 때 '쿵' 하는 충격이 평소보다 커졌다면 점검받으세요.
가속 페달을 밟아도 엔진 소리만 커지고 속도가 잘 붙지 않을 때, P에서 D·R로 옮겼을 때 반응이 늦을 때도 마찬가지예요.
원인이 미션오일 말고도 여러 가지일 수 있어서 직접 판단하기 어려워요.</li>
</ul>
<h2>4WD라면 하나 더, 그리고 기록</h2>
<p>네 바퀴를 모두 굴리는 4WD·AWD 차에는 앞뒤로 힘을 나누는 트랜스퍼와 뒤쪽 디퍼렌셜(좌우 바퀴로 힘을 나눠 주는 장치)에도
오일이 들어 있어요. {B.esc(_diff_text(c))}</p>
<p>다만 현대 일부 차종의 정기 점검표는 이 오일들을 '점검' 항목으로만 두고, 트랜스퍼 오일은 점검도 교체도 필요 없다고 적은
표도 있어요. 대신 차가 물에 잠긴 적이 있다면 바꾸라고 해요. 내 차의 정기 점검표를 보고 정비소와 상담하세요.</p>
<p>점검하거나 보충·교체했다면 날짜와 주행거리를 {notebook}에 기록해 두세요. 수첩이 그 기록을 바탕으로 다음 점검·교체 때를
알려 줘요. 다른 소모품의 주기는 {schedule}에 모아 두었어요.</p>"""

    faqs = [
        ("냉각수는 얼마마다 바꿔야 하나요?",
         f"차일지 수첩은 냉각수를 {_when(c, 'coolant')} {_verb(c, 'coolant')} 알려 줘요. "
         "교체 시기는 차와 냉각수 종류마다 크게 달라요. "
         f"장수명 냉각수를 넣은 차는 첫 교체를 {first_km} 또는 {first_years}년 중 먼저 오는 때로 늦게 잡는 설명서도 있어요. "
         "점검 결과와 내 차 설명서의 정기 점검표를 보고 정비소에서 정하세요."),
        ("미션오일은 무교환이라는데 안 바꿔도 되나요?",
         "'무교환'은 정해진 교체 시기가 없다는 뜻으로 쓰는 말이에요. 정기적으로 점검할 필요가 없다고 적은 제조사 설명서도 "
         "있지만, 짧은 거리 반복·잦은 정체·산길·트레일러 끌기 같은 가혹 조건으로 달리면 가혹 조건 표의 주기를 따르라고 해요. "
         f"차일지 수첩 기본값은 {atf_when} 교체예요. 운행 조건과 설명서를 보고 정비소와 상담해 정하세요."),
        ("냉각수가 부족하면 물을 넣어도 되나요?",
         "차마다 달라요. 물만 보태라는 설명서도, 물과 섞은 냉각수를 넣으라는 설명서도 있고, 물을 쓴다면 증류수처럼 깨끗한 물을 "
         "쓰라고 해요. 무엇을 넣을지 모르겠거나 냉각수가 자꾸 준다면 직접 넣지 말고 정비소에서 점검받으세요. "
         "엔진이 뜨거울 때는 절대 캡을 열지 마세요."),
        ("겨울에 워셔액에 물을 섞어도 되나요?",
         "제품에 따라 달라요. 물에 섞어 쓰는 제품이라면 희석 방법과 사용 온도는 제품 표기를 따르세요. "
         "물을 많이 섞을수록 얼기 쉬우니 추운 철에는 특히 조심하세요. "
         "맹물은 여름에 워셔액이 없을 때만 잠깐 쓰라는 제조사 안내가 있어요. 냉각수(부동액)는 워셔액 탱크에 절대 넣지 마세요."),
    ]
    sources = [SRC_HY_COOLANT, SRC_KIA_COOLANT, SRC_HY_COOLANT_EN, SRC_HY_COOLANT_LX3, SRC_KIA_COOLANT_EN,
               SRC_HY_COOLANT_NE1, SRC_HY_WINTER, SRC_HY_MOTOR_COOLANT, SRC_HY_SCHED_DN8, SRC_HY_SCHED_MX5,
               SRC_HY_SCHED_NX4, SRC_KIA_SCHED, SRC_KIA_SCHED_CV1, SRC_HY_SEVERE_NX4, SRC_HY_ATF, SRC_KIA_SEVERE,
               SRC_HY_SEVERE_QV, SRC_HY_SCHED_US, SRC_HY_SCHED_DN8_27, SRC_HY_WASHER_LX3, SRC_HY_WASHER_NX4,
               SRC_GN_WASHER, SRC_KIA_WASHER]
    return {
        "h1": "냉각수·미션오일·워셔액, 언제 어떻게 확인할까",
        "title": "냉각수·미션오일 점검과 교체 주기 — 워셔액 보충법과 이상 신호",
        "description": ("냉각수·미션오일·워셔액을 언제, 어떻게 확인하는지 정리했어요. 보닛 열기 전 안전 순서, 냉각수 양 보는 법과 "
                        "교체 판단, 미션오일 교체 주기, 워셔액 보충법, 누유·과열·변속 충격 신호까지 담았어요."),
        "lede": ("보닛을 열면 엔진오일 말고도 여러 액체 탱크가 보여요. 이 글에서는 냉각수·미션오일·워셔액을 언제, 어떻게 "
                 "확인하는지, 정비소에 맡길 것과 직접 할 수 있는 것을 나눠 정리했어요."),
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }
