"""차 관리 가이드 — 브레이크 패드·브레이크액 교체 시기 (care/brake.html).

숫자 출처
- 앞·뒤 패드, 디스크, 브레이크액의 점검·교체 주기와 종류(점검/교체)는 data/parts.json(c.part·c.interval_text)
  — 수첩과 같은 값. 가격 값은 쓰지 않는다.
- 아래 상수는 parts.json에 없는 제조사·규격 사실이라 출처와 함께 여기 둔다(바뀌면 고치고 GUIDE['updated']도).
- 데이터 차이(2026-10 조사)
  · 브레이크액: parts.json은 '40,000km 또는 24개월 중 먼저'(교체)인데, 현대 미국판 설명서(NE1N 2026, DN8 2025)는
    48개월(또는 48,000mi) 교체, 브렘보는 제조사 권장 우선·보통 2~3년. 한국판 현대 설명서 표의 기간 조건은 확인하지 못해
    인용하지 않는다. 글은 수첩 기본값을 기준으로 쓰고, 제조사 권장이 차종·시장마다 다르다고 밝힌다(_fluid_compare).
  · 패드·디스크: parts.json은 km 값만 있는 '점검'(type=inspect) 항목. 제조사 설명서도 정해진 교체 거리가 아니라
    정기 점검 때 마모 상태로 바꾸는 항목으로 다룬다 — 글에서 '교체 주기'가 아니라 '점검 시점'으로 쓴다.
  · 하이브리드·전기차 패드가 몇 배·몇 km 더 간다는 수치, 앞·뒤 중 먼저 닳는 쪽, 브레이크액 수분 기준 퍼센트는
    공식 근거를 찾지 못해 쓰지 않는다.
  · 현대 취급설명서(QZ 2026) '라이닝 마모 감지 경보시스템'의 남은 양 % 단위 표시는 QZ가 승용차인지 상용차인지
    확인하지 못해(검토 때 출처 재확인 불가) 2026-10 고치기에서 본문·출처에서 뺐다.
"""
from care_guides import table

GUIDE = {"slug": "brake", "short": "브레이크 패드·브레이크액", "published": "2026-10-20", "updated": "2026-10-20",
         "og_title": "브레이크 패드·브레이크액", "og_lede": "패드는 닳은 만큼, 브레이크액은 기간으로",
         "summary": "패드·디스크·브레이크액 점검 시점, 소리·떨림·경고등 같은 이상 신호, 브레이크액을 기간으로 바꾸는 이유와 하이브리드·전기차 차이"}

# 기아(Discover Kia) 안내 — 패드가 약 이 두께(mm)보다 얇으면 정비소 점검 권장 (차종별 사용 한계는 정비 지침)
KIA_PAD_MM = 3
# 미국 연방 자동차 안전기준 FMVSS No. 116 — 브레이크액 최소 끓는점(℃): (규격, 새 액(건식), 수분을 머금은 액(습식))
FMVSS_BOILING = (("DOT 3", 205, 140), ("DOT 4", 230, 155))
# 현대 미국판 설명서(NE1N 2026, DN8 2025) — 브레이크액 교체 기간(개월, 주행거리와 먼저 오는 때)
HY_US_FLUID_MONTHS = 48
# 브렘보 — 제조사 권장을 우선하되 일반적으로 권하는 브레이크액 교체 주기(년)
BREMBO_FLUID_YEARS = (2, 3)

SRC_KIA_SQUEAK = ("Kia — When do brakes squeak",
                  "https://www.kia.com/ph/discover-kia/ask/when-do-brakes-squeak.html")
SRC_KIA_REPLACE = ("Kia — How often do brakes need to be replaced",
                   "https://www.kia.com/ph/discover-kia/ask/how-often-do-brakes-need-to-be-replaced.html")
SRC_BOSCH_SENSOR = ("Bosch Mobility — Brake pad wear sensor",
                    "https://bosch-mobility.com/en/solutions/sensors/brake-pad-wear-sensor/")
SRC_HY_WARN_NX4 = ("Hyundai owner's manual — Warning and indicator lights (NX4 2025)",
                   "https://ownersmanual.hyundai.com/full_webhelp/NX4/2025/en_US/warning_indicator_lights.html")
SRC_HY_WARN_CN7 = ("Hyundai owner's manual — Warning and indicator lights (CN7 2026)",
                   "https://ownersmanual.hyundai.com/full_webhelp/cn7/2026/en_us/warning_indicator_lights.html")
SRC_HY_FLUID_CHECK = ("Hyundai owner's manual — Checking the brake/clutch fluid level (NX4 2025)",
                      "https://ownersmanual.hyundai.com/full_webhelp/NX4/2025/en_GN/idf5c979cd4b3.html")
SRC_KIA_FLUID_CHECK = ("Kia owner's manual — Checking the brake fluid level (NQ5 2024)",
                       "https://ownersmanual.kia.com/full_webhelp/NQ5/2024/en_US/topics/t00670.html")
SRC_BREMBO_FLUID = ("Brembo — 내 자동차에 적합한 브레이크 오일은?",
                    "https://www.bremboparts.com/asiapacific/ko/support/h%EC%98%AC%EB%B0%94%EB%A5%B8-%EC%A0%9C%ED%92%88-"
                    "%EC%84%A0%ED%83%9D-%EB%B0%A9%EB%B2%95/%EB%82%B4-%EC%9E%90%EB%8F%99%EC%B0%A8%EC%97%90-%EC%A0%81%ED%95%A9"
                    "%ED%95%9C-%EB%B8%8C%EB%A0%88%EC%9D%B4%ED%81%AC-%EC%98%A4%EC%9D%BC%EC%9D%80-195105")
SRC_FMVSS = ("eCFR — 49 CFR 571.116 (FMVSS No. 116 Motor vehicle brake fluids)",
             "https://www.ecfr.gov/current/title-49/subtitle-B/chapter-V/part-571/subpart-B/section-571.116")
SRC_HY_US_NE1N = ("Hyundai owner's manual — Normal maintenance schedule (NE1N 2026)",
                  "https://ownersmanual.hyundai.com/full_webhelp/NE1N/2026/en_US/idc415036e46f.html")
SRC_HY_US_DN8 = ("Hyundai owner's manual — Normal maintenance schedule (DN8 2025)",
                 "https://ownersmanual.hyundai.com/full_webhelp/DN8/2025/en_US/topic_ybb_1yh_lwb.html")
SRC_ZF_JUDDER = ("ZF Aftermarket — Brake judder",
                 "https://aftermarket.zf.com/en/aftermarket-portal/for-workshops/useful-tips/brakes/brake-judder/")
SRC_BFE_WARPED = ("Brake & Front End — Warped Brake Rotors", "https://www.brakeandfrontend.com/?p=193449")
SRC_BFE_REGEN = ("Brake & Front End — Regenerative Brakes: Basic Operation And Behavior",
                 "https://www.brakeandfrontend.com/regenerative-brakes-basic-operation-and-behavior/")
SRC_TT_REGEN = ("Tomorrow's Technician — Toyota Regenerative Braking",
                "https://www.tomorrowstechnician.com/toyota-regenerative-braking/")
SRC_BFE_RUST = ("Brake & Front End — How Regenerative Braking Contributes to Rear Brake Corrosion",
                "https://www.brakeandfrontend.com/how-regenerative-braking-contributes-to-rear-brake-corrosion/")
KIND = {"replace": "교체", "inspect": "점검"}
MEANING = {"replace": "정해진 때에 바꿔요", "inspect": "닳은 정도를 보고 바꿀지 정해요"}
PARTS = ("brake-pad-front", "brake-pad-rear", "brake-disc", "brake-fluid")


def _when(c, pid):
    """문장용 '…때에'/'…마다' — interval_text 끝말에 맞춰 조사를 붙인다."""
    t = c.interval_text(pid)
    return t + "에" if t.endswith("때") else t


def _cycle(c, pid):
    """표의 주기 칸 — '40,000km 또는 24개월'·'60,000km마다'."""
    return c.interval_text(pid).replace(" 중 먼저 오는 때", "")


def _schedule_table(c):
    B = c.B
    rows = []
    for pid in PARTS:
        p = c.part(pid)
        rows.append([B.esc(p["name"]), B.esc(_cycle(c, pid)), KIND.get(p["type"], "관리"),
                     B.esc(MEANING.get(p["type"], "설명서를 따라요"))])
    return table(["항목", "수첩 알림", "종류", "알림이 오면"], rows)


def _disc_ratio(c):
    """디스크 점검이 앞 패드 점검 몇 번에 한 번꼴인지 — 나누어떨어질 때만 문장을 만든다."""
    disc, pad = c.part("brake-disc").get("intervalKm"), c.part("brake-pad-front").get("intervalKm")
    if disc and pad and disc % pad == 0 and disc // pad > 1:
        return f"디스크는 패드보다 천천히 닳아서, 수첩은 앞 패드 점검 {disc // pad}번에 한 번꼴로 디스크 점검 알림을 줘요. "
    return "디스크는 패드보다 천천히 닳아서, 수첩도 패드보다 드물게 디스크 점검 알림을 줘요. "


def _replace_note(c):
    """표의 항목 가운데 '교체' 항목이 브레이크액 하나뿐일 때만 '…만' 문장을 만든다(데이터가 바뀌어도 틀리지 않게)."""
    repl = [pid for pid in PARTS if c.part(pid)["type"] == "replace"]
    if repl == ["brake-fluid"]:
        return f"{len(PARTS)}개 항목 가운데 브레이크액만 정해진 때에 바꾸는 '교체' 항목이에요."
    return "'교체' 항목은 정해진 때에 바꾸고, '점검' 항목은 닳은 정도를 보고 바꿀지 정해요."


def _fluid_compare(c):
    """브레이크액 — 수첩 기본값(개월)과 현대 미국판·브렘보 권장의 차이."""
    mo = c.part("brake-fluid").get("intervalMonths")
    lo, hi = BREMBO_FLUID_YEARS
    maker = (f"제조사 권장은 차종과 판매 지역마다 달라요. 현대의 미국판 설명서에는 {HY_US_FLUID_MONTHS}개월(또는 정해진 주행거리) "
             f"중 먼저 오는 때에 바꾸라고 적힌 차종이 있고, 부품 회사 브렘보는 제조사 권장을 먼저 따르되 보통 {lo}~{hi}년을 권해요.")
    if not mo:
        return maker + " 수첩에는 기간 기준이 없으니 내 차 설명서의 기간도 함께 챙기세요."
    if mo <= lo * 12:
        tail = " 차일지 기본값은 이 가운데 짧은 쪽에 맞춰 일찍 잡은 값이에요."
    elif mo < HY_US_FLUID_MONTHS:
        tail = " 차일지 기본값은 이 사이에 있어요."
    else:
        tail = " 차일지 기본값이 이보다 길 수 있으니 설명서 주기를 꼭 확인하세요."
    return maker + tail


def _boiling_table():
    rows = [[k, f"{dry}℃ 이상", f"{wet}℃ 이상"] for k, dry, wet in FMVSS_BOILING]
    return table(["규격", "새 액", "수분을 머금은 액"], rows)


def build(c):
    B = c.B
    notebook = c.link_notebook("차일지 수첩")
    fluid = c.part("brake-fluid")
    fluid_when = _when(c, "brake-fluid")
    pad_note = c.part("brake-pad-front").get("note") or ""
    regen_memo = " 차일지 수첩의 앞 패드 항목에도 이 내용을 적어 뒀어요." if "회생제동" in pad_note else ""
    green = {"hybrid", "ev"} <= set(fluid["appliesTo"])

    signal_rows = [
        ["밟을 때 높은 '끼익' 소리가 계속 나요", "패드가 얇아져 마모 표시 금속이 디스크에 닿았을 수 있어요",
         "미루지 말고 정비소에서 패드 점검"],
        ["쇠끼리 긁는 '드드득' 소리가 나요", "패드가 거의 다 닳았을 수 있어요", "바로 정비소. 미루면 디스크까지 상해요"],
        ["비 온 뒤 처음 몇 번만 소리가 나요", "디스크 표면의 얇은 녹이 벗겨지는 소리일 수 있어요", "곧 사라지면 대개 괜찮아요. 계속되면 점검"],
        ["밟을 때 핸들이나 페달이 떨려요", "디스크가 고르지 않게 닳았거나 다른 원인일 수 있어요", "정비소에서 원인 진단"],
        ["페달이 물렁하거나 평소보다 깊이 들어가요", "브레이크액이 새거나 액 속에 기포가 생겼을 수 있어요",
         "안전한 곳에 세우고 견인을 불러 정비소로"],
    ]

    summary = ("<strong>한눈에</strong> 브레이크 패드와 디스크는 정해진 거리마다 바꾸는 게 아니라, 점검 때 닳은 정도를 보고 바꿔요. "
               "브레이크액은 수분을 빨아들이면 끓는 온도가 낮아져서 기간도 정해 두고 바꾸는데, 차일지 기본값은 "
               f"{B.esc(c.interval_text('brake-fluid'))}예요. 쇠 긁는 소리, 물렁한 페달, 주차 브레이크를 풀어도 꺼지지 않는 경고등은 "
               "바로 정비소에 가야 할 신호예요.")

    body = f"""<h2>브레이크에서 챙길 것은 셋이에요</h2>
<p>브레이크 페달을 밟으면 그 힘이 브레이크액을 타고 바퀴까지 전해져요. 바퀴에서는 캘리퍼라는 집게가 패드를 밀어,
바퀴와 함께 도는 둥근 쇠판(디스크)을 양쪽에서 꽉 잡아요. 이 마찰로 차가 서요. 뒷바퀴는 차에 따라 바퀴와 함께 도는
통(드럼) 안쪽을 마찰재(라이닝)로 미는 방식을 쓰기도 해요.</p>
<p>그래서 챙길 것은 마찰로 닳는 패드, 함께 닳는 디스크, 힘을 전하는 브레이크액이에요. 브레이크는 조금만 잘못 손대도
위험해서 직접 고치지 말고 정비소에 맡기세요. 이 글은 언제 정비소에 가야 하는지 알아차리는 법을 다뤄요.</p>
<h2>차일지 수첩의 점검·교체 시점</h2>
<p>{notebook}은 아래 시점에 알림을 줘요. 패드와 디스크는 '점검' 알림이에요. 그때 꼭 바꾸라는 뜻이 아니라, 얼마나 닳았는지 보고
바꿀지 정하라는 뜻이에요. 운전 습관, 자주 다니는 길(도심·산길), 차 무게에 따라 닳는 속도가 크게 달라서예요. 제조사 설명서도
패드·디스크를 정해진 거리마다 바꾸는 부품이 아니라 정기 점검 때 상태를 보는 항목으로 다뤄요.</p>
{_schedule_table(c)}
<p>{B.esc(_disc_ratio(c))}{B.esc(_replace_note(c))}</p>
<h2>패드·디스크는 닳은 만큼 바꿔요</h2>
<p>기아의 해외 소비자 안내는 패드가 약 {KIA_PAD_MM}mm보다 얇아지면 정비소에서 점검받으라고 해요. 다만 이건 대략적인 기준이에요.
차종마다 정해진 사용 한계가 따로 있으니 정비소에서 확인하세요. 디스크에도 차종마다 최소 두께가 정해져 있어서, 그보다 얇으면 바꿔요.
두께는 정비소에서 바퀴를 떼고 측정 공구로 재요.</p>
<p>패드가 닳은 것을 알려 주는 방법은 차마다 달라요.</p>
<ul>
<li><strong>소리로 알리는 차</strong>: 패드에 작은 금속 조각(마모 표시)이 붙어 있어요. 패드가 얇아지면 이 조각이 디스크에 닿아
높은 '끼익' 소리를 내요. 바꿀 때가 가까웠다는 신호예요.</li>
<li><strong>경고등으로 알리는 차</strong>: 패드에 마모 센서가 달려 있어요. 센서가 패드와 함께 닳으면 계기판에 경고등이 켜져요.
경고등이 켜지면 정비소에 점검을 맡기세요.</li>
</ul>
<p>내 차가 어느 쪽인지는 차 설명서의 브레이크 항목에서 확인하세요.</p>
<h2>운전 중 이런 소리·떨림이 있으면</h2>
<p>브레이크 이상은 소리·떨림·페달 느낌으로 먼저 나타나요. 아래 표는 짐작해 보는 용도예요. 정확한 원인은 정비소에서 확인해야 해요.</p>
{table(["증상", "흔한 원인", "할 일"], signal_rows)}
<p>제동할 때 떨림(저더)이 생기면 흔히 '디스크가 휘었다'고들 해요. 하지만 업계 자료는 디스크 두께가 고르지 않게 된 것을
더 흔한 원인으로 꼽아요. 떨림은 휠 너트를 잘못 조였을 때, 디스크와 바퀴가 맞닿는 면에 녹이 끼었을 때, 캘리퍼가 잘 움직이지
않을 때도 생겨요. 브레이크가 아닌 다른 부품이 원인일 때도 있어요. 떨림이 생기면 디스크 점검 알림을 기다리지 말고 바로 점검받으세요.</p>
<h2>바로 정비소에 가야 할 때</h2>
<p>쇠 긁는 소리나 물렁한 페달은 미루면 안 되는 신호예요. 경고등도 그래요.
현대 설명서에 나오는 '주차 브레이크 &amp; 브레이크액' 경고등은 주차 브레이크를 걸었을 때 켜지는 게 정상이에요.
주차 브레이크를 풀었는데도 켜져 있으면 브레이크액이 모자랄 수 있다는 뜻이에요. 경고등 모양과 뜻은 차마다 다르니 설명서로 확인해 두세요.</p>
<p>운전 중에 이런 신호가 오면 이렇게 해요.</p>
<ol>
<li>속도를 줄이고 가장 가까운 안전한 곳에 세워요.</li>
<li>차 밑 바닥에 액체가 샌 자국이 있는지 봐요.</li>
<li>액이 새거나, 경고등이 꺼지지 않거나, 브레이크가 평소와 다르면 더 달리지 마세요. 견인을 불러 정비소로 가요.</li>
</ol>
<p>현대 설명서에 나오는 차는 브레이크가 대각선으로 마주 보는 바퀴끼리 묶인 두 갈래(계통)로 나뉘어 있어서, 한쪽이 고장 나도
남은 두 바퀴로 설 수는 있어요. 대신 페달을 더 깊고 세게 밟아야 하고 서는 거리가 길어져요. 차가 선다고 해서 계속 달리면 위험해요.</p>
<h2>브레이크액은 왜 기간으로 바꾸나요</h2>
<p>브레이크액에는 DOT 3·DOT 4처럼 'DOT'로 시작하는 규격 이름이 붙어요. 흔히 쓰는 DOT 3·4·5.1은 공기 중의 수분을
빨아들이는 성질이 있어요. 시간이 지나면 고무 호스와 부품 재질을 통해서도 수분이 아주 조금씩 스며들어요. 그래서 덜 달려도 기간이 지나면 바꿔요.</p>
<p>수분이 늘면 브레이크액이 끓는 온도가 낮아져요. 긴 내리막에서 브레이크를 오래 밟아 뜨거워지면 액이 끓어 기포가 생길 수 있어요.
기포는 눌리면 줄어들어서 페달을 밟아도 힘이 제대로 전해지지 않아요. 이를 베이퍼록이라고 해요. 긴 내리막에서는 브레이크만
오래 밟지 말고 낮은 기어(엔진 브레이크)를 함께 쓰세요. 낮은 기어로 바꾸는 법은 차마다 달라서 설명서에서 확인하세요.</p>
<p>아래는 미국 연방 기준(FMVSS 116)이 정한 최소 끓는점이에요. 한국 기준은 아니지만, 수분을 머금으면 끓는 온도가
얼마나 내려가는지 보여 줘요.</p>
{_boiling_table()}
<p>차일지 수첩은 브레이크액을 {B.esc(fluid_when)} 바꾸라고 알려 줘요. {B.esc(_fluid_compare(c))}
내 차 설명서의 정기 점검표를 확인하세요. 정비소에서 브레이크액 속 수분을 재 보고 바꿀지 정하는 방법도 있어요.</p>
<p>보닛을 열면 브레이크액 통(탱크)이 있어요. 위치는 설명서의 엔진룸 그림에서 찾고, 통 옆면의 MAX·MIN 선 사이에 액이 있는지 봐요.
패드가 닳으면 액이 조금씩 줄어드는 게 정상이라 두 선 사이면 괜찮아요. 자주 채워야 할 만큼 줄면 새는 곳이 있을 수 있으니
점검받으세요. 보충과 교체도 정비소에 맡기세요. 차마다 맞는 규격이 정해져 있어서 설명서나 통 뚜껑에서 확인해야 해요.
특히 이름이 비슷한 DOT 5(실리콘 계열)는 DOT 5.1과 다른 액이라 다른 브레이크액과 섞으면 안 돼요. 엔진오일 같은 다른 기름이
몇 방울만 섞여도 부품이 상할 수 있어요. 엔진룸의 다른 액은 {c.link_care("fluids", "냉각수·미션오일·워셔액 점검")} 글에 모았어요.</p>
<h2>하이브리드·전기차는 이렇게 달라요</h2>
<p>하이브리드·전기차는 속도를 줄일 때 모터를 발전기처럼 돌려요. 전기를 만들면서 생기는 저항으로 먼저 차를 늦추는데,
이를 회생제동이라고 해요. 그만큼 패드를 덜 써서 더 오래가는 편이에요.{regen_memo} 얼마나 더 가는지는 차와 운전 습관에 따라 달라서 숫자로 말하기 어려워요.
급하게 서거나 아주 느린 속도에서 멈출 때는 여전히 패드와 디스크가 차를 세워요.</p>
<p>덜 써서 생기는 문제도 있어요. 디스크에 녹이 끼거나 캘리퍼가 잘 움직이지 않게 될 수 있다는 업계 보고가 있어요.
특히 뒤 브레이크에 잘 생기고, 제설제를 많이 뿌리는 겨울에 더 그렇다고 해요. 패드가 많이 남았어도 알림이 오면 정비소에서
바퀴를 떼고 상태를 봐 달라고 하세요. 내 차 제조사의 권고는 설명서에서 확인하세요.
겨울을 앞두고 챙길 것은 {c.link_care("winter", "겨울철 차 관리")} 글에 모았어요.</p>
<p>브레이크액은 엔진차든 전기차든 똑같이 수분을 빨아들여서, 하이브리드·전기차도 정기적으로 바꿔요. 주기는 내 차 설명서를
확인하세요.{" 수첩에서도 하이브리드·전기차 모두 브레이크액 알림이 켜져요." if green else ""}
전기차에서 따로 챙길 것은 {c.link_care("ev-care", "전기차 관리")} 글에 정리했어요.</p>
<h2>정비소에 맡길 때 확인할 것</h2>
<ul>
<li>앞·뒤 패드의 남은 두께와 디스크 두께·표면을 함께 봐 달라고 해요.</li>
<li>마모 센서가 있는 차라면 센서도 바꿔야 하는지 물어봐요. 보쉬는 패드를 바꿀 때 센서도 함께 바꾸기를 권해요.</li>
<li>버튼으로 거는 전자식 주차 브레이크(EPB) 차는 뒤 패드 작업 방법이 다를 수 있어요. 맡기기 전에 내 차 작업이 가능한지,
시간이 얼마나 걸리는지 물어보세요.</li>
<li>브레이크액을 바꿨다면 설명서 규격으로 넣었는지 정비 명세서에서 확인해요.</li>
<li>바꾸거나 점검받은 날과 그때 주행거리를 {notebook}에 기록해요. 점검만 받고 바꾸지 않았어도 기록해 두면 수첩이 그날부터
다음 알림을 다시 계산해요.</li>
</ul>
<p>다른 소모품의 주기는 {c.link_care("replacement-schedule", "소모품 교체 주기표")}에 모아 두었어요.</p>"""

    faqs = [
        ("브레이크 패드는 몇 km마다 바꿔야 하나요?",
         "정해진 교체 거리는 없어요. 운전 습관과 길, 차에 따라 닳는 속도가 크게 달라서예요. "
         f"차일지 수첩은 앞 패드를 {_when(c, 'brake-pad-front')}, 뒤 패드를 {_when(c, 'brake-pad-rear')} 점검하라고 알려 주고, "
         f"그때 닳은 정도를 보고 바꿀지 정해요. 기아는 패드가 약 {KIA_PAD_MM}mm보다 얇으면 정비소 점검을 권해요."),
        ("브레이크액은 많이 안 탔는데도 바꿔야 하나요?",
         "네. 브레이크액은 시간이 지나며 수분을 빨아들여 끓는 온도가 낮아져요. 그래서 주행거리와 기간 중 먼저 오는 때가 기준이에요. "
         f"차일지 기본값은 {c.interval_text('brake-fluid')}이고, 제조사 권장은 차종마다 달라 내 차 설명서를 확인하세요."),
        ("브레이크에서 끼익 소리가 나면 바로 바꿔야 하나요?",
         "소리 종류에 따라 달라요. 비 온 뒤 처음 몇 번만 나다 사라지는 소리는 디스크의 얇은 녹이 벗겨지는 소리일 수 있어요. "
         "밟을 때마다 높은 소리가 계속 나면 패드의 마모 표시가 닿은 것일 수 있으니 정비소에서 점검받으세요. "
         "쇠끼리 긁는 소리라면 패드가 거의 다 닳았을 수 있어서 바로 정비소에 가야 해요."),
        ("하이브리드나 전기차는 브레이크 관리를 덜 해도 되나요?",
         "아니요, 점검은 똑같이 받아야 해요. 회생제동 덕분에 패드는 더 오래가는 편이지만, 덜 써서 디스크에 녹이 끼거나 "
         "캘리퍼가 잘 움직이지 않을 수 있어요. 브레이크액은 엔진차든 전기차든 똑같이 수분을 빨아들여서 정기적으로 바꿔요. "
         "주기는 내 차 설명서를 확인하세요."),
    ]
    sources = [SRC_KIA_SQUEAK, SRC_KIA_REPLACE, SRC_BOSCH_SENSOR, SRC_ZF_JUDDER, SRC_BFE_WARPED,
               SRC_HY_WARN_NX4, SRC_HY_WARN_CN7, SRC_HY_FLUID_CHECK, SRC_KIA_FLUID_CHECK,
               SRC_BREMBO_FLUID, SRC_FMVSS, SRC_HY_US_NE1N, SRC_HY_US_DN8,
               SRC_BFE_REGEN, SRC_TT_REGEN, SRC_BFE_RUST]
    return {
        "h1": "브레이크 패드·브레이크액, 언제 바꾸고 무엇을 살필까",
        "title": "브레이크 패드 교체 시기 — 브레이크액 교체 주기·이상 신호·하이브리드·전기차 차이",
        "description": ("브레이크 패드·디스크는 닳은 만큼, 브레이크액은 정해진 기간마다 바꿔요. 차일지 수첩의 점검·교체 시점, "
                        "소리·떨림·경고등 같은 이상 신호, 바로 정비소에 가야 할 때, 하이브리드·전기차 차이를 정리했어요."),
        "lede": ("브레이크는 차를 세우는 가장 중요한 장치인데, 패드와 브레이크액을 언제 바꿔야 하는지는 헷갈리기 쉬워요. "
                 "점검·교체 시점과 운전 중 알아챌 수 있는 이상 신호, 바로 정비소에 가야 할 때를 정리했어요."),
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }
