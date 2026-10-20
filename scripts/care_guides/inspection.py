"""차 관리 가이드 — 자동차 검사 주기와 과태료 (care/inspection.html).

숫자 출처
- 첫 검사·주기·검사 기간·과태료 금액은 data/inspection.json(c.inspection) — 수첩 D-day와 같은 값.
- 아래 상수는 inspection.json에 없는 법령 사실이라 출처와 함께 여기 둔다(바뀌면 고치고 GUIDE['updated']도).
- 데이터 차이(2026-10 조사): inspection.json은 첫 검사를 등록 후 4년으로 두지만, 자동차관리법 시행규칙 별표 15의2가
  2024.12.17 개정(2025.1.1 시행)되어 신조차의 최초 검사유효기간을 5년으로 늘렸다(제·개정이유). 어느 차부터 5년인지
  (부칙 적용례)는 원문으로 확인하지 못해서, 글은 수첩 기본값을 기준으로 쓰고 '5년일 수 있어요'로만 밝힌 뒤
  등록증·사이버검사소 확인으로 안내한다. 데이터가 5년으로 바뀌면 law_note()·first_item() 등이 문장을 바꾼다.
- 수첩과의 차이(운영자 확인 필요): js/derive.js inspectionStatus는 '최근 검사일 + intervalYears'로 만료일을 잡는다.
  법은 검사 기간 안의 검사를 만료일에 받은 것으로 치므로, 실제 검사일을 넣으면 수첩 날짜가 어긋난다.
  글은 그 칸에 '검사 전 등록증의 유효기간 만료일'을 넣으라고 안내한다(수첩 코드는 이 모듈 밖이라 고치지 않음).
- 확인하지 못한 절차(재검사 날수 세는 법·수수료, 운행정지 중 운행 조건)는 단정하지 않고 검사소·시·군·구청 확인으로 안내한다.
"""
import datetime

from care_guides import ext, table

GUIDE = {"slug": "inspection", "short": "자동차 검사 주기", "published": "2026-10-20", "updated": "2026-10-20",
         "og_title": "자동차 검사 주기·과태료", "og_lede": "언제 받고, 늦으면 얼마를 낼까",
         "summary": "내 차 검사 날짜 계산법, 받을 수 있는 기간, 늦으면 붙는 과태료와 예약·준비물"}

# 자동차관리법 시행령 별표 2 — 검사 지연 30일 이내 정액, 31일째부터 계산해 3일 초과할 때마다 가산,
# 115일 이상은 최대 금액 (금액은 inspection.json)
PENALTY_FIRST_DAYS = 30
PENALTY_STEP_DAYS = 3
# 자동차관리법 시행규칙 별표 15의2 (2024.12.17 개정, 2025.1.1 시행) — 신조 비사업용 승용차 최초 검사유효기간.
# 적용 대상(부칙)은 확인하지 못해 글에서는 '~일 수 있어요'로만 쓴다.
LAW_NEW_CAR_FIRST_YEARS = 5
LAW_NEW_CAR_YEAR = 2025
LAW_NEW_CAR_FROM = "2025년 1월 1일"
# 같은 개정(시행규칙 제77조제2항) — 검사 기간 앞쪽이 만료일 전 90일로 늘어난 날
WINDOW_CHANGED_FROM = "2025년 1월 1일"
# 한국교통안전공단 정기검사 안내 — 부적합 뒤 재검사 기간(기준일·날수 세는 법은 경우마다 달라 '보통 ~ 정도'로만 쓴다)
RECHECK_DAYS = 10
TS_PHONE = "1577-0990"

# 날짜 계산 예시 — 2025년 전에 등록한 차 (첫 유효기간 끝은 예시로 '등록일 + 첫 검사 연수 - 1일'로 둔다)
EX_REG = datetime.date(2023, 5, 20)

SRC_EASYLAW_REGULAR = ("찾기쉬운 생활법령정보 — 자동차 정기검사는 꼭 받아야 해요",
                       "https://www.easylaw.go.kr/CSP/CnpClsMain.laf?csmSeq=675&ccfNo=2&cciNo=2&cnpClsNo=1")
SRC_EASYLAW_PENALTY = ("찾기쉬운 생활법령정보 — 자동차 정기검사 과태료",
                       "https://easylaw.go.kr/CSP/OnhunqueansInfoRetrieve.laf?onhunqnaAstSeq=96&onhunqueSeq=5621")
SRC_LAW_84 = ("자동차관리법 제84조(과태료)", "https://www.law.go.kr/법령/자동차관리법/제84조")
SRC_DECREE_PENALTY = ("자동차관리법 시행령 — 별표 2(과태료의 부과기준)", "https://www.law.go.kr/법령/자동차관리법시행령")
SRC_RULE_REVISION = ("국가법령정보센터 — 자동차관리법 시행규칙 제·개정이유(2024.12.17 개정)",
                     "https://www.law.go.kr/LSW/lsRvsRsnListP.do?lsId=007928&chrClsCd=010102&lsRvsGubun=all")
SRC_TS_REGULAR = ("한국교통안전공단 — 정기검사", "https://main.kotsa.or.kr/portal/contents.do?menuCode=01010200")
SRC_TS_COMPREHENSIVE = ("한국교통안전공단 — 종합검사", "https://main.kotsa.or.kr/portal/contents.do?menuCode=01010300")
SRC_EASYLAW_EMISSION = ("찾기쉬운 생활법령정보 — 자동차 배출가스 정기검사 등",
                        "https://easylaw.go.kr/CSP/CnpClsMainBtr.laf?popMenu=ov&csmSeq=1454&ccfNo=2&cciNo=2&cnpClsNo=1")
SRC_SEOUL_EV = ("서울시 미디어허브 — 자동차 검사 부적합 판정 받지 않으려면", "https://mediahub.seoul.go.kr/archives/2005753")
SRC_GWANAK = ("관악구 — 자동차 검사(유효기간 연장)", "https://www.gwanak.go.kr/site/gwanak/08/10802020000002016051206.jsp")

URL_CYBERTS = "https://www.cyberts.kr"


def won(x):
    """40000 → '4만원', 25000 → '25,000원'."""
    return f"{x // 10000}만원" if x % 10000 == 0 else f"{x:,}원"


def day_ko(d, with_year=True):
    return f"{d.year}년 {d.month}월 {d.day}일" if with_year else f"{d.month}월 {d.day}일"


def span_ko(a, b):
    return f"{day_ko(a)} ~ {day_ko(b, with_year=a.year != b.year)}"


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 2월 29일
        return d.replace(year=d.year + n, day=28)


def fine_for(days, pen):
    """검사 기간이 끝난 뒤 days일째의 과태료 어림값.
    시행령 별표 2의 '31일째부터 계산하여 3일 초과 시마다'를 (days - 31) // 3 번 가산으로 센다.
    이렇게 세면 115일째에 처음 최대 금액이 되어, 표의 '115일 이상'(max_from)과 맞는다."""
    if days <= PENALTY_FIRST_DAYS:
        return pen["within30DaysKrw"]
    extra = (days - PENALTY_FIRST_DAYS - 1) // PENALTY_STEP_DAYS * pen["per3DaysAfterKrw"]
    return min(pen["maxKrw"], pen["within30DaysKrw"] + extra)


def law_note(first):
    """수첩 기본값(첫 검사 연수)과 2025년 개정(신조차 5년)의 차이를 밝히는 문장."""
    if first < LAW_NEW_CAR_FIRST_YEARS:
        return (f"다만 {LAW_NEW_CAR_FROM}부터 시행된 자동차관리법 시행규칙 개정에는 공장에서 새로 나와 처음 등록하는 차(신조차)의 "
                f"첫 검사 유효기간을 {LAW_NEW_CAR_FIRST_YEARS}년으로 늘리는 내용이 있어요. 어느 차부터 적용되는지는 등록 시기 등에 따라 "
                f"다를 수 있어요. 최근에 새 차를 샀다면 첫 검사가 수첩 계산보다 {LAW_NEW_CAR_FIRST_YEARS - first}년 늦을 수 있으니, "
                "바로 아래 방법으로 꼭 확인하세요.")
    return (f"이 기준은 {LAW_NEW_CAR_FROM}부터 시행된 개정에 따른 것이라, 그 전에 등록한 차는 첫 검사가 더 빨랐을 수 있어요. "
            "내 차 날짜는 바로 아래에서 설명하는 자동차등록증이나 사이버검사소 조회로 꼭 확인하세요.")


def first_item(first):
    """첫 검사 목록 줄 — 수첩 기본값이 개정 전 기준이면 등록 시기에 따라 나눠 말한다."""
    if first < LAW_NEW_CAR_FIRST_YEARS:
        return (f"<li><strong>첫 검사</strong>: {LAW_NEW_CAR_YEAR}년 전에 등록한 차는 최초 등록일로부터 {first}년 뒤에 "
                f"첫 검사 유효기간이 끝나요. {LAW_NEW_CAR_YEAR}년부터 새로 등록한 차는 {LAW_NEW_CAR_FIRST_YEARS}년일 수 있어요"
                f"(아래 설명을 보세요). 차일지 수첩은 {first}년 기준으로 계산해요.</li>")
    return (f"<li><strong>첫 검사</strong>: 새 차는 최초 등록일로부터 {first}년 뒤에 첫 검사 유효기간이 끝나요. "
            "차일지 수첩도 이 기준으로 계산해요.</li>")


def build(c):
    ri, pen = c.inspection["regularInspection"], c.inspection["penalty"]
    first, every = ri["firstInspectionAfterYears"], ri["intervalYears"]
    before, after = ri["windowBeforeDays"], ri["windowAfterDays"]
    label = ri["vehicleClassLabel"]
    w30, step, top = won(pen["within30DaysKrw"]), won(pen["per3DaysAfterKrw"]), won(pen["maxKrw"])
    steps_to_max = -(-(pen["maxKrw"] - pen["within30DaysKrw"]) // pen["per3DaysAfterKrw"])
    max_from = PENALTY_FIRST_DAYS + steps_to_max * PENALTY_STEP_DAYS + 1
    cyberts = ext(("사이버검사소", URL_CYBERTS))
    old_rule = first < LAW_NEW_CAR_FIRST_YEARS  # 수첩 기본값이 2025년 개정 전 기준인지

    # 날짜 예시 (inspection.json 값으로 계산)
    ex_reg = EX_REG if old_rule else EX_REG.replace(year=LAW_NEW_CAR_YEAR)
    ex_note = f"{LAW_NEW_CAR_YEAR}년 전에 등록해서 {first}년 기준" if old_rule else f"{first}년 기준"
    exp1 = add_years(ex_reg, first) - datetime.timedelta(days=1)
    win_a, win_b = exp1 - datetime.timedelta(days=before), exp1 + datetime.timedelta(days=after)
    exp2, exp3 = add_years(exp1, every), add_years(exp1, every * 2)
    date_rows = [
        ["최초 등록일", day_ko(ex_reg)],
        ["첫 검사 유효기간 끝", day_ko(exp1)],
        ["검사 받을 수 있는 기간", span_ko(win_a, win_b)],
        ["다음 유효기간 끝", day_ko(exp2)],
        ["그다음 유효기간 끝", day_ko(exp3)],
    ]

    # 과태료 표 (inspection.json 금액으로 계산)
    mid = [d for d in (60, 90) if PENALTY_FIRST_DAYS < d < max_from]
    pen_rows = [[f"{PENALTY_FIRST_DAYS}일까지", w30],
                [f"{PENALTY_FIRST_DAYS + 1}일째부터", f"{PENALTY_STEP_DAYS}일 넘을 때마다 {step}씩 더해져요"]]
    pen_rows += [[f"{d}일째", f"약 {won(fine_for(d, pen))}"] for d in mid]
    pen_rows.append([f"{max_from}일 이상", f"{top}(최대)"])

    newer = (f"({LAW_NEW_CAR_YEAR}년부터 새로 등록한 차는 {LAW_NEW_CAR_FIRST_YEARS}년 뒤일 수 있어요)"
             if old_rule else "")
    summary = (f"<strong>한눈에</strong> 자가용 승용차는 최초 등록일로부터 {first}년 뒤에 첫 검사를 받고{newer}, "
               f"그 뒤로 {every}년마다 받아요. 유효기간 만료일 {before}일 전부터 {after}일 뒤까지 받으면 되고, "
               f"이 기간을 넘기면 과태료가 {w30}부터 최대 {top}까지 붙어요.")
    desc_newer = (f"({LAW_NEW_CAR_YEAR}년 이후 새 차는 {LAW_NEW_CAR_FIRST_YEARS}년일 수 있어요) " if old_rule else " ")
    description = (f"자동차 검사 주기와 과태료를 정리했어요. 자가용 승용차는 등록 {first}년 뒤{desc_newer}첫 검사, "
                   f"그 뒤 {every}년마다 받아요. 만료일 {before}일 전부터 {after}일 뒤까지 받을 수 있고, "
                   "날짜 계산법·과태료·예약·준비물·전기차 차이까지 담았어요.")

    body = f"""<h2>자동차 검사는 언제 받나요</h2>
<p>자동차는 일정한 때마다 나라가 정한 검사를 받아야 해요(자동차관리법 제43조). 차가 안전하게 달릴 수 있는지,
배출가스가 기준 안에 있는지 확인하는 절차예요. 이 글은 {label}차(개인이 타는 자가용 승용차) 기준이에요.</p>
<p>용어 몇 가지를 먼저 알아 두세요. 검사의 효력이 이어지는 기간을 '검사 유효기간', 그 마지막 날을 '만료일'이라고 해요.
새 차는 처음 등록한 날부터 첫 유효기간이 시작되고, 검사를 통과하면(적합 판정) 다음 유효기간이 이어져요.
만료일 앞뒤로 검사를 받을 수 있는 날들은 '검사 기간'이라고 불러요. 검사에서 떨어지는 것은 '부적합'이라고 해요.</p>
<ul>
{first_item(first)}
<li><strong>그다음</strong>: {every}년마다 받아요.</li>
<li><strong>화물차·승합차·영업용 차</strong>: 주기가 달라요. 자동차등록증에 적힌 검사 유효기간을 확인하세요.</li>
</ul>
<p>{law_note(first)}</p>
<h2>내 차 검사 날짜 계산하기</h2>
<p>가장 정확한 건 자동차등록증의 '검사 유효기간' 칸이에요. 검사를 받을 때마다 다음 유효기간이 여기에 적혀요.
등록증이 손에 없으면 한국교통안전공단(TS)의 {cyberts}에서 차량 번호로 유효기간을 조회할 수 있어요.</p>
<p>직접 어림해 보려면 이 순서로 따져 보세요.</p>
<ol>
<li>등록증에서 최초 등록일을 찾아요.</li>
<li>첫 검사 유효기간은 최초 등록일로부터 {first}년 뒤쯤 끝나요(위의 개정 내용도 함께 보세요).</li>
<li>그 뒤로는 만료일에 {every}년씩 더해요.</li>
<li>만료일 {before}일 전부터 {after}일 뒤까지가 검사를 받을 수 있는 기간이에요(아래에서 자세히 설명해요).</li>
</ol>
<p>예를 들어 {day_ko(ex_reg)}에 처음 등록한 승용차({ex_note})의 등록증에 첫 유효기간이 {day_ko(exp1)}까지로 적혀 있다고 해 볼게요.</p>
{table(["구분", "날짜"], date_rows)}
<p>검사 기간 안에 적합 판정을 받으면 다음 만료일은 이렇게 {every}년씩 밀려요. 기간의 첫날·마지막 날은 날짜를 세는 방법에 따라 하루쯤 다를 수 있으니,
정확한 기간은 사이버검사소에서 확인하세요.</p>
<p>날짜를 외워 두기 어렵다면 {c.link_notebook("차일지 수첩")}에 차를 등록해 두세요. 최초 등록일을 넣으면 검사 만료일과 남은 날(D-day)을 보여 주고,
폰 캘린더로 내보내면 만료일이 알림과 함께 일정에 들어가요. 알림은 만료일 가까이에 오니, 검사 기간이 시작되는 날(만료일 {before}일 전)은 따로 적어 두세요.</p>
<p>수첩의 '최근 검사일' 칸에 날짜를 넣으면 그 날짜에서 {every}년 뒤를 다음 만료일로 계산해요. 그런데 검사 기간 안에 받은 검사는
만료일에 받은 것으로 쳐 줘요(바로 아래에서 설명해요). 그래서 검사소에 간 날을 넣으면 수첩 날짜가 실제보다 이르거나 늦게 나올 수 있어요.
검사 기간 안에 받았다면 이 칸에는 검사 전 등록증에 적혀 있던 유효기간 만료일을 넣으세요. 수첩 날짜는 추정이라, 등록증과 다르면 등록증이 맞아요.</p>
<h2>만료일 {before}일 전부터 {after}일 뒤까지 받을 수 있어요</h2>
<p>'검사 기간'은 만료일을 가운데 두고 앞뒤로 이어져요. 이 안에서 적합 판정을 받으면 실제로 받은 날과 상관없이 만료일에 받은 것으로 쳐 줘요.
그래서 일찍 받아도 다음 검사 날짜가 당겨지지 않아요.</p>
<p>앞쪽 기간은 {WINDOW_CHANGED_FROM}부터 {before}일로 늘었어요. 예전 안내문이나 일부 누리집에는 더 짧게 적혀 있을 수 있어요.</p>
<p>검사 기간 끝 무렵에는 원하는 날짜에 예약하기 어려울 수 있어요. 검사 기간이 시작되면 바로 예약 날짜를 잡아 두는 게 마음 편해요.
부적합이 나와도 고칠 시간이 남거든요.</p>
<h2>늦으면 과태료, 오래 안 받으면 운행정지까지</h2>
<p>검사 기간이 끝날 때까지 검사를 받지 않으면 과태료를 내요(자동차관리법 제84조). 늦은 날수는 검사 기간(만료일 뒤 {after}일까지)이 끝난 다음 날부터 따져요.</p>
{table(["검사 기간이 끝난 뒤", "과태료"], pen_rows)}
<p>'약'이라고 적은 금액은 {PENALTY_STEP_DAYS}일 단위를 세는 방법에 따라 {step}쯤 다를 수 있어요. 과태료는 차가 등록된 시·군·구청이 매기니,
정확한 금액은 고지서로 확인하세요. 고지서에 적힌 의견 제출 기한 안에 미리 내면 금액을 깎아 주는 제도도 있으니 꼼꼼히 보세요.</p>
<p>과태료를 냈다고 검사를 받은 건 아니에요. 오래 받지 않으면 이런 순서로 불이익이 커져요.</p>
<ol>
<li>시·군·구청이 검사를 받으라는 명령(검사 명령)을 보내요.</li>
<li>그래도 받지 않으면 차를 몰지 못하게 하는 운행정지 명령이 나와요.</li>
<li>운행정지 중에 차를 몰면 벌금이나 징역 같은 형사 처벌을 받을 수 있어요.</li>
<li>그래도 끝까지 검사를 받지 않으면 번호판을 떼어 가거나(번호판 영치), 시·군·구청이 직접 차 등록을 없앨(직권 말소) 수도 있어요.</li>
</ol>
<p>운행정지 중에도 검사를 받으러 가는 길에는 임시로 운행할 수 있어요. 다만 이때 챙길 서류(명령서·등록증 등)와 조건은
명령을 보낸 시·군·구청에 먼저 확인하고 움직이세요. 처분이 나오는 순서와 시기도 지역과 상황에 따라 다를 수 있어요.</p>
<h2>정기검사와 종합검사는 무엇이 다른가요</h2>
<p>차가 등록된 지역에 따라 받는 검사 종류가 달라요. 주기는 같아요.</p>
<ul>
<li><strong>정기검사</strong>: 차가 안전 기준에 맞는지 확인하는 기본 검사예요.</li>
<li><strong>종합검사</strong>: 정기검사와 배출가스 정밀검사(장비로 배출가스를 더 꼼꼼히 재는 검사) 등을 한 번에 묶은 검사예요.
종합검사를 받으면 묶인 검사를 모두 받은 것으로 쳐요.</li>
</ul>
<p>종합검사는 대기관리권역(공기 오염을 특별히 관리하는 지역)과 일부 큰 도시처럼 정해진 지역에 등록된 차가 받아요.
대상 지역은 시·군·구 단위로 정해져 있고 바뀐 적도 있어서, 내 차가 해당하는지는 사이버검사소나 차가 등록된 시·군·구청에서 확인하세요.</p>
<h2>어디서 예약하고 무엇을 챙기나요</h2>
<p>검사는 TS 검사소나, 검사를 할 수 있도록 지정받은 민간 정비업체(지정정비사업자, 이하 민간 검사소)에서 받아요.
민간 검사소는 종합검사를 하지 않는 곳도 있으니 미리 물어보세요.</p>
<ol>
<li>사이버검사소(누리집·모바일)에서 차량 번호로 검사 유효기간을 확인해요.</li>
<li>TS 검사소는 사이버검사소에서 가까운 곳과 날짜를 골라 예약해요. 공단 콜센터({TS_PHONE})로도 예약할 수 있어요.
민간 검사소는 그곳에 직접 연락해 예약해요.</li>
<li>예약한 날 아래 준비물을 챙겨 차를 몰고 가요.</li>
</ol>
<ul>
<li><strong>자동차등록증 원본</strong>: 검사 결과와 다음 유효기간을 여기에 적어 줘요.</li>
<li><strong>의무보험 가입 확인</strong>: 전산으로 조회되면 따로 챙기지 않아도 돼요.</li>
<li><strong>검사 수수료</strong>: 검사 종류·차종·검사소마다 달라요. 예약할 때 확인하세요.</li>
<li><strong>그 밖의 서류</strong>: 신분증 같은 서류가 필요한지는 검사소마다 다를 수 있어요. 예약할 때 함께 물어보세요.</li>
</ul>
<p>검사 전에 집에서 쉽게 볼 수 있는 것도 확인해 두세요. 고장 난 곳을 미리 고쳐 가면 다시 오는 수고를 줄일 수 있어요.</p>
<ul>
<li>전조등·브레이크등·방향지시등이 모두 켜지는지</li>
<li>계기판에 계속 켜져 있는 경고등이 없는지</li>
<li>타이어가 많이 닳지 않았는지({c.link_care("tire", "타이어 점검 방법")})</li>
</ul>
<p>검사를 앞두고 소모품도 한꺼번에 점검해 보면 좋아요. 어떤 소모품을 언제 바꾸는지는 {c.link_care("replacement-schedule", "소모품 교체 주기")} 글에 모아 두었어요.</p>
<h2>부적합이 나오거나 기간 안에 못 받을 때</h2>
<p>검사에서 기준에 맞지 않는 곳이 나오면 '부적합' 판정을 받아요. 이때는 그 부분을 정비소에서 고친 뒤, 정해진 재검사 기간 안에 다시 받으면 돼요.
재검사 기간은 보통 {RECHECK_DAYS}일 정도로 짧은데, 언제 검사를 받았는지 등에 따라 기간을 세는 방법이 달라질 수 있어요.
정확한 마감일과 재검사 수수료는 검사 결과표나 검사소에서 알아 두세요.</p>
<p>도난·사고나 정비가 오래 걸리는 것처럼 어쩔 수 없는 사정으로 기간 안에 받기 어렵다면, 검사 유효기간 연장(유예)을 신청할 수 있어요.
연장 신청서와 자동차등록증, 사유를 보여 주는 서류가 필요해요. 어디에 내는지, 어떤 사유를 받아 주는지는 지역마다 안내가 다를 수 있으니,
사정이 생기면 검사 기간이 끝나기 전에 차가 등록된 시·군·구청에 먼저 연락하세요.</p>
<h2>전기차·하이브리드는 무엇이 다른가요</h2>
<p>전기차도 다른 승용차와 같은 주기로 검사를 받아요. 차가 안전한지 보는 검사는 똑같이 받고, 배출가스가 나오지 않는 차라
배출가스 검사만 빠져요. 종합검사 지역에 등록된 전기차도 마찬가지예요.</p>
<p>검사에서는 높은 전압이 흐르는 배터리와 전기 장치(고전원 전기장치)도 따로 봐요. 전기가 새지 않게 잘 막혀 있는지(절연), 제대로 작동하는지 확인해요.
'전기차는 검사 면제'라는 말은 틀려요. 기간을 놓치면 과태료도 똑같이 붙어요. 평소 관리할 점은 {c.link_care("ev-care", "전기차 관리")} 글에 정리했어요.</p>
<p>하이브리드는 엔진이 함께 달린 차라 배출가스가 나와요. 전기차처럼 배출가스 검사가 빠진다고 생각하지 말고,
종합검사 지역이라면 어떤 검사를 받는지 예약할 때 확인하세요.</p>"""

    if old_rule:
        q_first = f"새 차를 샀는데 첫 검사는 {first}년 뒤인가요, {LAW_NEW_CAR_FIRST_YEARS}년 뒤인가요?"
        a_first = (f"차일지 수첩은 최초 등록일로부터 {first}년 뒤로 계산해요. 그런데 {LAW_NEW_CAR_FROM}부터 시행된 개정에 새 차의 "
                   f"첫 검사 유효기간을 {LAW_NEW_CAR_FIRST_YEARS}년으로 늘리는 내용이 있어서, 등록 시기에 따라 "
                   f"{LAW_NEW_CAR_FIRST_YEARS}년이 적용될 수 있어요. 내 차 날짜는 자동차등록증의 검사 유효기간이나 "
                   "TS 사이버검사소 조회로 확인하세요.")
    else:
        q_first = "새 차를 샀는데 첫 검사는 언제인가요?"
        a_first = (f"최초 등록일로부터 {first}년 뒤에 첫 검사 유효기간이 끝나요. {LAW_NEW_CAR_FROM} 전에 등록한 차는 더 빨랐을 수 있으니, "
                   "내 차 날짜는 자동차등록증의 검사 유효기간이나 TS 사이버검사소 조회로 확인하세요.")
    faqs = [
        ("검사를 일찍 받으면 다음 검사도 당겨지나요?",
         f"아니요. 만료일 {before}일 전부터 {after}일 뒤까지인 검사 기간 안에서 적합 판정을 받으면, 실제로 받은 날과 상관없이 "
         f"만료일에 받은 것으로 쳐 줘요. 그래서 기간이 시작되자마자 받아도 다음 만료일은 그대로 {every}년 뒤예요. "
         "부적합이 나와도 고칠 시간이 남으니 일찍 받는 편이 마음 편해요."),
        (q_first, a_first),
        ("검사 기간을 넘겼는데 과태료는 얼마인가요?",
         f"검사 기간이 끝난 뒤 {PENALTY_FIRST_DAYS}일까지는 {w30}이에요. 그 뒤로는 {PENALTY_STEP_DAYS}일 넘을 때마다 {step}씩 더해지고, "
         f"{max_from}일 이상이면 최대 {top}이에요. 차가 등록된 시·군·구청이 매기니 정확한 금액은 고지서로 확인하세요. "
         "과태료를 내도 검사는 따로 받아야 해요."),
        ("전기차는 검사를 안 받아도 되나요?",
         "아니요. 전기차도 같은 주기로 검사를 받아요. 배출가스 검사만 빠지고, 안전 검사와 고전원 전기장치 절연 상태 확인은 받아요. "
         "기간을 놓치면 과태료도 똑같이 붙어요."),
    ]
    src_data = [(s["label"], s["url"]) for s in c.inspection.get("sources", []) if s.get("url", "").startswith("https://")]
    sources = src_data + [SRC_LAW_84, SRC_DECREE_PENALTY, SRC_RULE_REVISION, SRC_EASYLAW_REGULAR, SRC_EASYLAW_PENALTY,
                          SRC_TS_REGULAR, SRC_TS_COMPREHENSIVE, SRC_EASYLAW_EMISSION, SRC_SEOUL_EV, SRC_GWANAK]
    return {
        "h1": "자동차 검사, 언제 받고 늦으면 얼마를 낼까",
        "title": "자동차 검사 주기와 과태료 — 검사 날짜 계산·예약·준비물",
        "description": description,
        "lede": ("자동차 검사는 날짜를 놓치기 쉬워요. 안내가 꼭 오는 것도 아니고, 늦으면 과태료가 붙어요. "
                 "내 차 검사 날짜를 계산하는 법부터 예약·준비물, 검사에서 떨어졌을 때(부적합) 할 일까지 정리했어요."),
        "summary": summary, "body": body, "faqs": faqs, "sources": sources,
    }
