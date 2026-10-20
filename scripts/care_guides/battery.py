"""차 관리 가이드 — 자동차 배터리 교체 시기와 방전 대처 (care/battery.html).

숫자 출처
- 12V 배터리·스마트키 건전지 교체 주기는 data/parts.json(c.part·c.interval_text) — 수첩과 같은 값. 가격 값은 쓰지 않는다.
- 스마트키 건전지 규격 예는 parts.json key-battery의 note·shopKeyword에서 읽는다(수첩 메모와 같은 표기).
- 아래 상수는 parts.json에 없는 제조사·배터리 회사 안내라 출처와 함께 여기 둔다(바뀌면 고치고 GUIDE['updated']도).
- 데이터 차이(2026-10 조사)
  · 교체 주기: parts.json battery-12v는 기간 하나(수첩 기본값)인데, 공식·제조사 자료에서 고정 교체 연수는 찾지 못했다.
    배터리 회사 안내는 기간보다 상태(시동 전 전압, 점검창 색, 시동 약화)로 점검하라는 쪽이다. 글은 수첩 기본값을
    '차일지 기본값'이라 밝히고 상태 점검이 먼저라고 쓴다. 'N~N년' 같은 연수는 쓰지 않는다.
  · 스마트키 규격: parts.json note는 '대부분 CR2032'인데, 현대 아이오닉 5 설명서는 CR2450이다. 글은 '흔하지만 다른 규격도 있다,
    기존 전지 표기·설명서 확인'으로 쓴다.
  · 하이브리드·전기차: parts.json은 같은 주기를 적용하지만, 12V 리튬 배터리(리셋 버튼 방식)를 쓰는 하이브리드, 일반 12V
    배터리가 없는 수소전기차도 있다. 글에서 차종마다 다를 수 있다고 밝힌다.
  · 보험 긴급출동의 배터리 충전 포함 여부·횟수, 블랙박스 저전압 차단 권장 전압은 공식 확인이 안 되거나 출처마다 달라
    수치를 쓰지 않는다.
  · 점프 순서는 다른 차와 연결할 때의 현대·기아 설명서 순서만 쓴다. 휴대용 점프 스타터는 제품 설명서를 따르라고만 쓴다.
  · 고칠 때 다시 확인할 것(2026-10 검토 때 설명서 사이트 접속 불가): 12V 보조 배터리 세이버+가 '세워 둔 동안(전원 OFF)'
    작동한다는 설명, HEV_RESET_SEC·HEV_READY_MIN·KEY_OTHER_SPEC·ACID_RINSE_MIN, SRC_HY_FCEV 주소(id…cbda).
"""
import re

from care_guides import num, table

GUIDE = {"slug": "battery", "short": "배터리 교체·방전 대처", "published": "2026-10-20", "updated": "2026-10-20",
         "og_title": "배터리 교체·방전 대처", "og_lede": "약해지는 신호부터 점프 시동 순서까지",
         "summary": "교체 시기와 약해지는 신호, 방전됐을 때 할 일과 점프 시동 순서, 블랙박스·겨울철 방전 예방, 전기차 12V와 스마트키 건전지"}

# 배터리 회사(한국앤컴퍼니) 안내 — 한국경제 2026-07 기사
VOLT_CHECK = 12.4          # 시동을 끈 상태 전압이 이 값 이하로 내려가면 충전 상태·노후 점검
PARK_DRIVE_MIN = 30        # 오래 세워 두는 차는 주 1회 이상 시동을 걸어 이만큼(분) 주행 권장
# 기아 취급설명서 — AGM 배터리 분리·교체 뒤 ISG 배터리 센서 보정
KIA_ISG_CAL_HOURS = 4      # 시동을 끈 채 기다리는 시간(약)
KIA_ISG_RESTARTS = (2, 3)  # 그 뒤 시동을 켰다 끄는 횟수
# 현대 그랜저 하이브리드(GN7HEV 2025) 설명서 — 12V 리튬 보조 배터리 리셋
HEV_RESET_SEC = 30         # 리셋 버튼을 누른 뒤 이 시간(초) 안에 시동
HEV_READY_MIN = 30         # READY 상태로 정차·주행해 충전하는 시간(분, 약)
# 현대·기아 설명서 배터리 경고 — 배터리액(황산)이 눈·피부에 닿았을 때 물로 씻어 내는 시간(분 이상), 눈은 곧바로 진료
ACID_RINSE_MIN = 15

SRC_HY_JUMP = ("현대 취급설명서 — 점프 시동(쏘나타 DN8 2026)",
               "https://ownersmanual.hyundai.com/full_webhelp/DN8/2026/ko_KR/id30acfcf3cbd.html")
SRC_KIA_JUMP = ("기아 취급설명서 — 점프 케이블의 연결 순서(SP3 2026)",
                "https://ownersmanual.kia.com/full_webhelp/SP3/2026/ko_KR/topics/t00935.html")
SRC_KIA_JUMP_EN = ("Kia owner's manual — Jump starting (BDm 2024)",
                   "https://ownersmanual.kia.com/full_webhelp/BDm/2024/en_US/topics/t00570.html")
SRC_HY_WARN = ("현대 취급설명서 — 배터리 관련 경고(아이오닉 5 NE1 2025)",
               "https://ownersmanual.hyundai.com/full_webhelp/NE1/2025/ko_KR/id23C5E0NA0UI.html")
SRC_HK_NEWS = ("한국경제 — 한국앤컴퍼니가 제안하는 차량 배터리 관리법(2026-07)",
               "https://www.hankyung.com/article/202607021009P")
SRC_NISSAN_MF = ("Nissan Juke owner's manual — Maintenance-free (MF) battery (2025)",
                 "https://www.nissan.ie/ownership/car-owner-manual/manuals/iom/juke/0f16/e0/2025/maintenance-free-mf-battery-type-b-1.shtml")
SRC_CCC_HEAT = ("Car Care Council — Summer heat takes a toll on your car's battery",
                "https://www.carcare.org/2020/07/summer-heat-takes-a-toll-on-your-cars-battery/")
SRC_KIA_DEVICES = ("Kia owner's manual — 12V battery discharging due to additional electrical devices (QY 2023)",
                   "https://ownersmanual.kia.com/full_webhelp/QY/2023/en_RG/topics/t00169.html")
SRC_MAEIL = ("매일신문 — 블랙박스 저전압 차단 설정(2026-10)",
             "https://www.imaeil.com/page/view/2026101310083126275")
SRC_KIA_ISG = ("Kia owner's manual — ISG system (YBC 2023)",
               "https://ownersmanual.kia.com/full_webhelp/YBC/2023/en_GB/topics/chapter5_4_7.html")
SRC_KIA_ISG_FAULT = ("Kia owner's manual — ISG malfunction (NQ5 2024)",
                     "https://ownersmanual.kia.com/full_webhelp/NQ5/2024/en_US/topics/t00355.html")
SRC_HY_SAVER = ("현대 취급설명서 — 12V 보조 배터리 세이버+ 이해하기(아이오닉 5 NE1 2025)",
                "https://ownersmanual.hyundai.com/full_webhelp/NE1/2025/ko_KR/id23C3H70805Z.html")
SRC_HMG_EV = ("현대자동차그룹 — 전기차 배터리 이야기",
              "https://www.hyundaimotorgroup.com/ko/story/CONT0000000000002069")
SRC_HY_HEV_LI = ("현대 취급설명서 — 12V 리튬 보조 배터리 방전 시(그랜저 하이브리드 GN7HEV 2025)",
                 "https://ownersmanual.hyundai.com/full_webhelp/GN7HEV/2025/ko_KR/id30acfcf3cbd.html")
SRC_HY_HEV = ("현대 취급설명서 — 12V 배터리 방전 시(쏘나타 하이브리드 DN8HEV 2026)",
              "https://ownersmanual.hyundai.com/full_webhelp/DN8HEV/2026/ko_KR/id30acfcf3cbd.html")
SRC_HY_FCEV = ("현대 취급설명서 — 12V 배터리(수소전기차 NH2 2026)",
               "https://ownersmanual.hyundai.com/full_webhelp/NH2/2026/ko_KR/id30acfcf3cbda.html")
SRC_HY_NOTICE = ("현대자동차 — 블루링크 배터리 방전 알림",
                 "https://www.hyundai.com/kr/ko/digital-customer-support/app/myhyundai/bluelink/bluelink-vehicle-care/battery-discharge-notice")
SRC_HY_KEY = ("현대 취급설명서 — 스마트 키 배터리 교체하기(아이오닉 5 NE1 2025)",
              "https://ownersmanual.hyundai.com/full_webhelp/NE1/2025/ko_KR/id23C5B0C0NPN.html")
SRC_KIA_KEY = ("Kia owner's manual — Battery replacement, smart key (SG2 2024)",
               "https://ownersmanual.kia.com/full_webhelp/SG2/2024/en_US/topics/t00134.html")
KEY_OTHER_SPEC = "CR2450"  # 현대 아이오닉 5(NE1) 설명서의 스마트키 건전지 규격 (SRC_HY_KEY)


def _ym(mo):
    """개월 수를 햇수로 — 42 → '3년 6개월', 24 → '2년'."""
    y, m = divmod(mo, 12)
    if not y:
        return f"{m}개월"
    return f"{y}년" if not m else f"{y}년 {m}개월"


def _every(c, pid):
    """문장용 주기 — '42개월마다(3년 6개월)'. interval_text 끝이 '때'면 '…때에'."""
    p = c.part(pid)
    t = c.interval_text(pid)
    mo = p.get("intervalMonths")
    if mo and not p.get("intervalKm") and mo >= 12:
        t += f"({_ym(mo)})"
    return t + "에" if t.endswith("때") else t


def _key_spec(c):
    """parts.json key-battery의 note·shopKeyword에 적힌 흔한 규격(CR…) — 없으면 None."""
    p = c.part("key-battery")
    m = re.search(r"CR\d{4}", " ".join([p.get("note") or "", p.get("shopKeyword") or ""]))
    return m.group(0) if m else None


def _batchim(word):
    """끝 글자에 받침이 있나 — 숫자는 읽는 소리(공·일·삼·육·칠·팔)로 본다."""
    ch = word[-1]
    if ch.isdigit():
        return ch in "013678"
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 != 0
    return False


def _ev_text(c):
    """수첩이 하이브리드·전기차에도 12V 항목을 켜는지(appliesTo)에 맞춘 문장."""
    applies = set(c.part("battery-12v")["appliesTo"])
    kinds = [k for k, on in (("전기차", "ev" in applies), ("하이브리드", "hybrid" in applies)) if on]
    tail = ("수소전기차 중에는 주기적으로 바꾸는 일반 12V 배터리가 없는 차도 있어요. "
            "내 차 설명서의 정기 점검표를 먼저 보세요.")
    if not kinds:
        return "차일지 수첩은 이 차들의 12V 배터리를 따로 알려 주지 않아요. " + tail
    return (f"차일지 수첩은 {'·'.join(kinds)}에도 12V 배터리 항목을 기본으로 켜 두고 같은 기본값"
            f"({c.interval_text('battery-12v')})으로 알려 줘요. 다만 12V 배터리의 종류와 구조에 따라 교체 시기가 "
            "다를 수 있어요. " + tail)


def build(c):
    B = c.B
    when = _every(c, "battery-12v")
    key_when = _every(c, "key-battery")
    volt = num(VOLT_CHECK, 1)
    restarts = "~".join(str(n) for n in KIA_ISG_RESTARTS)
    spec = _key_spec(c)
    notebook = c.link_notebook("차일지 수첩")
    winter = c.link_care("winter", "겨울철 차 관리 글")
    ev = c.link_care("ev-care", "전기차 관리 글")
    schedule = c.link_care("replacement-schedule", "소모품 교체 주기표")

    if spec and spec != KEY_OTHER_SPEC:
        spec_text = (f"규격은 {spec}{'이' if _batchim(spec) else '가'} 흔하지만, 현대 아이오닉 5 설명서처럼 "
                     f"{KEY_OTHER_SPEC}{'을' if _batchim(KEY_OTHER_SPEC) else '를'} 쓰는 차도 있어요. "
                     "기존 건전지에 새겨진 표기나 차 설명서로 확인하세요.")
    else:
        spec_text = "규격은 차마다 달라요. 기존 건전지에 새겨진 표기나 차 설명서로 확인하세요."

    indicator_rows = [
        ["녹색", "정상", "그대로 쓰면서 시동 상태를 지켜봐요"],
        ["검은색", "충전이 필요해요", "정비소에서 충전 상태와 방전 원인을 점검받아요"],
        ["흰색(투명)", "바꿀 때가 됐어요", "정비소에서 상태를 재고 교체를 상담해요"],
    ]

    summary = (f"<strong>한눈에</strong> 차일지 수첩은 12V 배터리를 {B.esc(when)} 바꾸라고 알려 주지만, "
               "그 전이라도 시동이 약해지거나 전압이 떨어지면 점검받으세요. 방전되면 켜 둔 전기 장치를 끄고 보험 긴급출동을 확인하거나, "
               "설명서 순서대로 점프 시동을 해요. 블랙박스 설정과 오래 세워 두는 습관을 챙기면 방전을 줄일 수 있어요.")

    body = f"""<h2>12V 배터리, 언제 어떻게 바꾸나요</h2>
<p>12V 배터리는 시동을 걸고 차 안의 전기 장치에 전기를 줘요. {notebook}은 12V 배터리를 {B.esc(when)} 바꾸라고 알려 줘요. 이건 제조사 기준이 아니라 차일지 기본값이에요.
차와 운전 습관에 따라 더 일찍 약해지기도, 더 오래 가기도 해요. 배터리 회사(한국앤컴퍼니)도 기간보다 시동 상태와 전압을 보고 점검하라고 안내해요.
그러니 알림은 '점검할 때'로 받아들이고, 알림 전이라도 아래 신호가 보이면 점검받으세요.</p>
<p>배터리는 차에 맞는 종류로 바꿔야 해요. 신호 대기 때 엔진이 저절로 꺼졌다 켜지는 기능(ISG, 공회전 제한 장치)이 있는 차는
잦은 시동을 견디도록 만든 배터리를 쓰는 경우가 많아요. 배터리 라벨에 AGM이나 EFB라고 적혀 있으면 이런 배터리예요.
정비소에서 바꿀 때 원래 달려 있던 것과 같은 종류인지 꼭 확인하세요.
기아 설명서는 AGM 배터리를 바꾼 뒤 배터리 센서가 다시 맞춰지도록(보정) 시동을 끈 채 약 {KIA_ISG_CAL_HOURS}시간 세워 두고,
그다음 시동을 {restarts}번 켰다 끄라고 해요. 그래도 ISG OFF 표시가 켜져 있으면 정비소 점검을 받아요. 절차는 제조사마다 달라요.</p>
<p>직접 바꾸면 배터리에서 나오는 가스에 불이 붙거나 단자가 합선될 위험이 있고, 교체 뒤 설정이 필요한 차도 있어요.
정비소에 맡기고, 바꾼 날은 수첩에 기록하세요. 다른 소모품 주기는 {schedule}에 있어요.</p>
<h2>약해졌다는 신호와 확인하는 법</h2>
<p>이런 일이 되풀이되면 점검받으세요.</p>
<ul>
<li>시동을 걸 때 엔진이 힘없이 천천히 돌다가 걸려요(시동 지연).</li>
<li>시동을 걸 때 전조등이 눈에 띄게 어두워져요.</li>
<li>경적 소리가 전보다 약해요.</li>
<li>ISG가 있는 차인데 신호 대기 때 엔진이 잘 안 꺼져요. 다른 이유일 수도 있지만, ISG는 배터리 전압이 충분할 때만 작동해요.</li>
</ul>
<p>이 배터리 회사는 시동을 끈 상태의 전압이 {volt}V 이하로 내려가면 충전이 덜 됐는지, 배터리가 낡았는지 점검하라고 해요.
전압은 정비소에서 재 달라고 하세요.</p>
<p>배터리액을 따로 채울 필요가 없는 무보수(MF) 배터리 중에는 윗면에 동그란 점검창(인디케이터)이 있는 것도 있어요. 색은 일반적으로 이렇게 읽어요.</p>
{table(["점검창 색", "일반적인 뜻", "할 일"], indicator_rows)}
<p>제품마다 표기가 다를 수 있으니 배터리 라벨을 함께 보세요. 점검창이 없거나, AGM처럼 점검창으로 판단하기 어려운 배터리는
전압을 재는 게 정확해요. 단자 주변에 이물질(부식)이 끼면 전기가 잘 흐르지 못하니 정비소에 청소를 부탁하세요.</p>
<h2>방전됐을 때 순서대로 할 일</h2>
<ol>
<li><strong>배터리 문제인지 보기</strong>: 계기판이 희미하거나 아예 안 켜지고, 엔진이 돌지 않거나 힘없이 돌다 말면 방전일 가능성이 커요.
계기판은 잘 켜지는데 차가 키를 알아보지 못하면 스마트키 건전지를 의심해 보세요(아래 '스마트키 건전지도 챙겨요' 참고).</li>
<li><strong>켜 둔 것 끄기</strong>: 전조등·실내등 같은 전기 장치를 꺼요. 시동은 여러 번 거듭 걸지 마세요. 남은 전기까지 써 버릴 수 있어요.</li>
<li><strong>보험 긴급출동 확인</strong>: 가입한 자동차보험의 긴급출동으로 배터리 충전(점프)을 받을 수 있는지 보험사 앱이나 콜센터에 물어보세요.
포함 여부와 횟수·조건은 보험사·상품마다 달라요. 점프가 처음이라면 이쪽을 먼저 권해요.</li>
<li><strong>직접 한다면</strong>: 아래 순서를 따라요. 하이브리드·전기차는 설명서부터 보세요.</li>
<li><strong>시동이 걸린 뒤</strong>: 배터리가 다 찬 게 아니니 바로 끄지 말고 한동안 달려요. 그리고 배터리가 낡았는지,
달리면서 배터리를 채우는 발전기에 문제가 없는지 정비소에서 점검받으세요.</li>
</ol>
<h2>점프 시동 연결 순서와 안전 주의</h2>
<p>점프 시동은 다른 차의 배터리나 차 시동용 휴대 배터리(점프 스타터)에서 전기를 빌려 시동을 거는 거예요.
아래는 다른 차의 도움을 받을 때 현대·기아 설명서가 안내하는 순서예요. 점프 스타터는 연결 방법이 제품마다 다르니
그 제품의 설명서를 따르세요. 엔진룸에 따로 점프 단자가 있는 차도, 배터리가 트렁크에 있는 차도 있으니
설명서 그림으로 위치부터 확인하세요.</p>
<ol>
<li>플러스(+) 케이블(흔히 빨간색)의 한쪽 집게를 방전된 차의 + 단자(또는 + 점프 단자)에 물려요.</li>
<li>플러스(+) 케이블의 다른 쪽을 도와주는 차의 + 단자에 물려요.</li>
<li>마이너스(-) 케이블(흔히 검은색)의 한쪽을 도와주는 차의 - 단자에 물려요.</li>
<li>마이너스(-) 케이블의 다른 쪽은 방전된 차의 - 점프 단자나, 배터리에서 멀리 떨어진 차체의 단단한 금속 부분에 물려요.
방전된 배터리의 - 단자에는 바로 물리지 마세요.</li>
<li>도와주는 차의 시동을 걸고 몇 분 기다린 뒤, 방전된 차의 시동을 걸어요.</li>
<li>시동이 걸리면 연결한 순서의 반대로 떼요. 방전된 차 차체 쪽 마이너스(-) 집게, 도와주는 차의 마이너스(-) 집게,
도와주는 차의 플러스(+) 집게, 방전된 차의 플러스(+) 집게 순서예요.</li>
</ol>
<p>안전을 위해 이것만은 꼭 지켜요.</p>
<ul>
<li>배터리에서는 터질 수 있는 가스가 나와요. 불꽃·담배·라이터를 가까이 두지 마세요.</li>
<li>플러스(+) 집게와 마이너스(-) 집게가 서로 닿으면 불꽃이 튈 수 있어요. 연결하는 동안 집게끼리 부딪히지 않게 해요.</li>
<li>배터리가 얼었거나 배터리액(전해액)이 부족하면 점프하지 마세요. 깨지거나 터질 수 있어요.</li>
<li>12V가 아닌 배터리로는 점프하지 마세요.</li>
<li>시동을 걸 때 벨트·냉각 팬처럼 움직이는 부품 근처에 케이블과 손이 가지 않게 해요.</li>
<li>배터리액(묽은 황산)이 피부나 눈에 닿으면 곧바로 깨끗한 물로 {ACID_RINSE_MIN}분 이상 씻어 내세요.
눈에 들어갔다면 씻은 뒤 바로 병원에 가고, 피부가 따갑거나 화끈거려도 진료를 받으세요.</li>
</ul>
<p>자신이 없으면 무리하지 말고 긴급출동을 부르세요.</p>
<h2>방전을 막는 습관</h2>
<ul>
<li><strong>블랙박스 저전압 차단</strong>: 주차 중에도 녹화하도록 상시전원에 연결한 블랙박스는 세워 둔 동안에도 배터리를 써요.
설정의 '저전압 차단'은 배터리 전압이 정한 값 아래로 떨어지면 블랙박스를 끄는 기능이에요. 겨울에는 차단 전압을 기본값보다
조금 높이라는 권고가 있지만, 권하는 값은 출처마다 달라요. 블랙박스 설명서를 보고 맞추세요. 그래도 배터리가 낡았으면 방전될 수 있어요.</li>
<li><strong>오래 세워 둘 때</strong>: 같은 배터리 회사는 자주 타지 않는 차라면 주 1회 이상 시동을 걸어
{PARK_DRIVE_MIN}분쯤 달리라고 권해요. 알맞은 간격은 차와 배터리 상태에 따라 달라질 수 있어요.</li>
<li><strong>짧은 거리만 반복하지 않기</strong>: 시동에 쓴 전기는 달리는 동안 발전기(엔진 힘으로 전기를 만드는 장치)가 다시 채워요.
아주 짧게 달리고 끄기를 되풀이하면 다 채우지 못해 배터리가 점점 약해질 수 있어요.</li>
<li><strong>나중에 단 전기 장치</strong>: 차를 살 때 달려 나오지 않고 나중에 단 장치가 전기를 많이 쓰면 방전될 수 있어요.
기아 설명서는 이런 장치를 떼어 낸 뒤에도 배터리 방전 경고가 계속 뜨면 정비소에서 점검받으라고 해요.</li>
<li><strong>방전 알림</strong>: 오래 세워 둔 차의 배터리가 줄면 차와 연결된 앱(커넥티드 서비스)으로 알려 주는 차도 있어요.
내 차에 이 기능이 있다면 앱의 알림 설정을 확인해 두세요.</li>
</ul>
<h2>겨울에 더 약해지는 이유와 여름 더위</h2>
<p>추우면 배터리가 낼 수 있는 힘이 줄고, 엔진오일도 걸쭉해져 시동에 힘이 더 들어요. 그래서 이미 약해진 배터리는 추운 아침에
문제가 드러나기 쉬워요. 겨울 준비는 {winter}에 모았어요.</p>
<p>더위도 좋지 않아요. 뜨거우면 배터리 안의 화학 반응이 빨라져 저절로 빠져나가는 전기가 늘고, 부식도 빨라져 수명이 줄어요.
여름에 쌓인 손상이 추운 날 드러나기도 하니,
추위 전에 정비소에 가면 배터리 상태도 재 달라고 하세요.</p>
<h2>하이브리드·전기차의 12V 배터리</h2>
<p>전기차에는 차를 움직이는 큰 배터리(고전압 배터리) 말고도 12V 배터리가 따로 있어요. 12V 배터리는 전자 장치에 전기를 주고,
고전압 배터리를 깨워 차가 움직일 준비를 하게 해요. 그래서 고전압 배터리가
넉넉해도 12V 배터리가 방전되면 READY(주행 준비)가 되지 않을 수 있어요.</p>
<ul>
<li><strong>자동 충전 기능</strong>: 세워 둔 동안 12V 배터리가 줄면 고전압 배터리로 알아서 채워 주는 차도 있어요(현대 전기차의
'12V 보조 배터리 세이버+' 등). 하지만 12V 배터리가 낡았거나 블랙박스 같은 상시전원 기기를 연결해 두면 방전을 막지 못할 수 있어요.</li>
<li><strong>리셋 버튼</strong>: 일부 하이브리드는 12V 리튬 배터리가 방전되면 스스로 전원을 끊어 배터리를 보호해요.
현대 그랜저 하이브리드 설명서는 '12V BATT RESET' 버튼을 누르고 {HEV_RESET_SEC}초 안에 시동을 건 뒤, READY 상태를 유지한 채
약 {HEV_READY_MIN}분 세워 두거나 달려서 충전하라고 해요. 버튼을 되풀이해 누르면 더 깊이 방전돼 점프 시동이 필요할 수 있어요.</li>
<li><strong>점프 시동</strong>: 방법과 연결 위치가 일반 차와 다를 수 있어요. 확실하지 않으면 긴급출동을 부르세요.</li>
</ul>
<p>이런 기능의 이름·버튼 유무·절차는 차마다 달라요. {B.esc(_ev_text(c))} 더 자세한 건 {ev}에 있어요.</p>
<h2>스마트키 건전지도 챙겨요</h2>
<p>스마트키 안에는 동전 모양의 3V 리튬 건전지가 들어 있어요. {notebook}은 스마트키 건전지를 {B.esc(key_when)} 바꾸라고
알려 주는데, 이것도 차일지 기본값이에요. 그 전이라도 멀리서 버튼이 잘 듣지 않거나 차 가까이 가야만 반응하면
건전지부터 의심해 보세요.</p>
<p>{B.esc(spec_text)} 규격이 다른 건전지를 넣거나 +·- 방향을 거꾸로 넣으면 키가 제대로 작동하지 않을 수 있어요.
코인 건전지는 어린이가 삼키면 위험하니 손이 닿지 않는 곳에 두세요.</p>
<p>건전지가 다 됐을 때 문을 열고 시동 거는 법은 설명서의 '스마트 키' 항목에 있어요. 차를 세워 두고 당황하기 전에 미리 읽어 두세요.</p>"""

    faqs = [
        ("자동차 배터리는 몇 년마다 바꿔야 하나요?",
         f"차일지 수첩은 {when} 바꾸라고 알려 줘요. 제조사가 정한 연수가 아니라 차일지가 정한 기본값이라, "
         "차와 운전 습관에 따라 더 이르거나 늦을 수 있어요. "
         f"시동이 느려지거나 시동을 끈 상태에서 전압이 {volt}V 이하로 떨어지면 기간과 상관없이 점검받으세요."),
        ("블랙박스를 켜 두면 배터리가 방전되나요?",
         "주차 중에도 녹화하도록 상시전원에 연결한 블랙박스는 세워 둔 동안에도 배터리를 써서, 오래 세워 두거나 배터리가 낡았으면 "
         "방전될 수 있어요. 블랙박스 설정의 저전압 차단 기능을 켜 두면 배터리 전압이 정한 값 아래로 떨어질 때 블랙박스가 꺼져요. "
         "차단 값은 블랙박스 설명서를 보고 맞추세요."),
        ("점프 케이블은 어떤 순서로 연결하나요?",
         "현대·기아 설명서 기준으로 플러스(+) 케이블은 방전된 차의 + 단자에 먼저 물리고, 다른 쪽을 도와주는 차의 + 단자에 물려요. "
         "마이너스(-) 케이블은 도와주는 차의 - 단자에 물린 뒤, 다른 쪽을 방전된 차의 - 점프 단자나 배터리에서 떨어진 차체 금속에 "
         "물려요. 뗄 때는 연결한 순서의 반대로, 방전된 차 차체 쪽 마이너스(-) 집게부터 떼요. "
         "연결 위치는 설명서 그림으로 먼저 확인하세요."),
        ("전기차도 12V 배터리가 방전되나요?",
         "네. 전기차에도 12V 배터리가 따로 있어서, 고전압 배터리가 넉넉해도 12V 배터리가 방전되면 주행 준비(READY)가 안 될 수 있어요. "
         "세워 둔 동안 12V 배터리가 줄면 고전압 배터리로 채워 주는 기능이 있는 차도 있지만, 배터리가 낡았거나 상시전원 기기를 "
         "연결해 두면 방전될 수 있어요. 대처 방법은 내 차 설명서에서 먼저 확인하세요."),
    ]
    sources = [SRC_HY_JUMP, SRC_KIA_JUMP, SRC_KIA_JUMP_EN, SRC_HY_WARN, SRC_HK_NEWS,
               SRC_NISSAN_MF, SRC_CCC_HEAT, SRC_KIA_DEVICES, SRC_MAEIL, SRC_KIA_ISG, SRC_KIA_ISG_FAULT,
               SRC_HY_SAVER, SRC_HMG_EV, SRC_HY_HEV_LI, SRC_HY_HEV, SRC_HY_FCEV, SRC_HY_NOTICE,
               SRC_HY_KEY, SRC_KIA_KEY]
    return {
        "h1": "자동차 배터리, 언제 바꾸고 방전되면 어떻게 할까",
        "title": "자동차 배터리 교체 시기 — 약해지는 신호·방전 대처·점프 시동 순서",
        "description": ("자동차 12V 배터리 교체 시기와 약해졌다는 신호를 정리했어요. 방전됐을 때 할 일, 점프 시동 연결 순서와 "
                        "주의할 점, 블랙박스·장기 주차 방전 예방, 전기차 12V와 스마트키 건전지까지 담았어요."),
        "lede": ("세워 둔 차가 시동이 안 걸리면 먼저 배터리 방전을 떠올리게 돼요. 배터리를 언제 바꾸는지, 약해졌다는 신호는 무엇인지, "
                 "방전됐을 때 무엇부터 할지 순서대로 정리했어요."),
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }
