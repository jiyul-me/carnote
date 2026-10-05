#!/usr/bin/env python3
"""차일지 — data/*.json 검사기. 잘못된 숫자 하나가 곧 잘못된 세액이라, 빌드 전에 데이터 실수를 잡는다.

사용법:  python3 scripts/validate_data.py
결과:    [오류]가 하나라도 있으면 exit 1 (CI 실패). [경고]만 있으면 통과(exit 0).
메시지:  어느 파일 · 몇 번째 항목(id) · 몇 번째 줄 · 어떤 필드가 · 왜 문제인지 · 어떻게 고치는지.

site.json의 광고 자리 이름과 짝이 되는 손 페이지(루트 *.html)의 <!-- adsense:slot 이름 --> 마커 이름도 본다
(오타가 나면 광고가 소리 없이 빠지는데 빌드 결과는 앞뒤가 맞아 빌드 검사로는 안 잡힌다).

여기 있는 범위 값(배기량 600~8000cc 등)은 '데이터가 말이 되는가'만 보는 검사용 경계다.
세율 같은 사이트 상수는 여기 두지 않는다 — 세율은 data/tax-rates.json에서만 읽는다.
Python 3.9 호환 (사용자 Mac 기본 python3).
"""
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checklib import ROOT, annotate  # noqa: E402

FUEL_TYPES = ("gasoline", "diesel", "lpg", "hybrid", "ev")
# energySource = 실제로 넣는 에너지(연비·단가·충전량 단위). fuelType(과세 구분)마다 쓸 수 있는 값 —
# 수소전기차는 세법상 ev 정액이라 fuelType ev + energySource hydrogen. 생략하면 첫 번째 값으로 유도된다
ENERGY_FOR_FUEL = {"gasoline": ("gasoline",), "diesel": ("diesel",), "lpg": ("lpg",), "hybrid": ("gasoline",),
                   "ev": ("electricity", "hydrogen")}
ENERGY_SOURCES = ("gasoline", "diesel", "lpg", "electricity", "hydrogen")
ENERGY_UNIT = {"electricity": "km/kWh", "hydrogen": "km/kg"}  # 나머지 km/L
VEHICLE_CLASSES = ("passenger", "van", "truck")
STATUSES = ("active", "sample")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9.-]*$")
RESERVED_SLUGS = ("index", "calculator")  # tax/index.html·tax/calculator.html을 덮어쓴다
RESERVED_PREFIX = "guide"  # tax/guide.html·tax/guide-*.html은 자동차세 가이드 글 (scripts/guides.py)

# site.json adsense·contactEmail — 형식 검사용. 광고 자리 이름은 두 갈래로 고정이다:
#  BUILD_SLOT_NAMES  build.py가 생성 페이지 템플릿에 채우는 자리(차종·허브·계산기)
#  HAND_SLOT_WHERE   손 페이지에 <!-- adsense:slot 이름 --> 마커로 두는 자리 → 그 마커가 있어야 할 곳
# 손 페이지 마커 이름은 HAND_SLOT_WHERE 키 중 하나여야 한다 — 오타가 나면 빌드가 그 자리를 빈칸으로 두어 광고가
# 소리 없이 빠지므로 오류로 잡는다(마커 이름으로 허용 목록을 넓히지 않는다). 어느 손 페이지에 어떤 마커가
# 정확히 한 번 있어야 하는지는 scripts/check_links.py HAND_MARKERS가 본다 — 광고 자리를 늘리면 둘 다 고친다
AD_KEYS = ("publisherId", "slots", "note")
BUILD_SLOT_NAMES = ("taxArticle", "hubEnd", "calcEnd")
HAND_SLOT_WHERE = {"tcoEnd": "tco.html의 </main> 바로 앞"}
AD_SLOT_NAMES = BUILD_SLOT_NAMES + tuple(HAND_SLOT_WHERE)
AD_SLOT_MARKER = re.compile(r"<!-- adsense:slot ([A-Za-z][A-Za-z0-9]*) -->")
CONTACT_MARKER = "<!-- site:contact -->"
PUB_ID_RE = re.compile(r"^pub-\d{16}$")
AD_SLOT_RE = re.compile(r"^\d+$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")

CC_MIN, CC_MAX = 600, 8000
ECONOMY_RANGE = {"ice": (3, 40), "electricity": (2, 10), "hydrogen": (50, 200)}  # 내연(km/L) / 전기(km/kWh) / 수소(km/kg)
RANGE_KM = (50, 1000)
YEAR_MIN = 1980

VEHICLE_REQUIRED = ("id", "status", "name", "brand", "modelFamily", "generation", "slug", "aliases",
                    "fuelType", "displacementCc", "fuelEconomy", "modelYearFrom", "modelYearTo")
VEHICLE_OPTIONAL = ("vehicleClass", "payloadKg", "vanSize", "rangeKm", "classNote",
                    "fuelEconomyNote", "trimGroup", "energySource")

# json.JSONDecodeError 영어 메시지 → 쉬운 설명
JSON_HINTS = (
    ("Expecting ',' delimiter", "쉼표(,)가 빠졌어요 — 앞 줄 끝에 쉼표가 있는지 보세요"),
    ("Expecting property name enclosed in double quotes",
     "키는 큰따옴표로 감싸야 해요 — 중괄호 } 바로 앞 항목 뒤에 쉼표가 남아 있지 않은지 보세요"),
    ("Expecting value", "값이 없어요 — 대괄호 ] 바로 앞 항목 뒤에 쉼표가 남았거나, 값 자리가 비었어요"),
    ("Expecting ':' delimiter", "키와 값 사이 콜론(:)이 빠졌어요"),
    ("Unterminated string", "큰따옴표가 닫히지 않았어요"),
    ("Invalid control character", "문자열 안에 줄바꿈·탭이 그대로 들어갔어요"),
    ("Extra data", "JSON이 끝난 뒤에 글자가 더 있어요 — 괄호 짝을 확인하세요"),
    ("Unexpected UTF-8 BOM", "파일 맨 앞에 BOM이 있어요 — 'UTF-8(BOM 없음)'으로 다시 저장하세요"),
)


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def _add(self, bucket, level, file, where, msg, fix, line):
        head = file
        if where:
            head += " " + where
        if line:
            head += " · {}번째 줄 근처".format(line)
        text = head + "\n       " + msg
        if fix:
            text += "\n       → " + fix
        bucket.append(text)
        annotate(level, msg + ((" → " + fix) if fix else ""), file=file, line=line,
                 title="데이터 " + ("오류" if level == "error" else "경고"))

    def error(self, file, where, msg, fix=None, line=None):
        self._add(self.errors, "error", file, where, msg, fix, line)

    def warn(self, file, where, msg, fix=None, line=None):
        self._add(self.warnings, "warning", file, where, msg, fix, line)


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def is_str(x):
    return isinstance(x, str) and x.strip() != ""


def show(x):
    return json.dumps(x, ensure_ascii=False)


def load_json(name, report):
    """data/<name>을 읽는다. 문법 오류·한 객체 안 중복 키도 [오류]로 보고. 반환: (데이터|None, 원문)"""
    file = "data/" + name
    try:
        text = (ROOT / "data" / name).read_text(encoding="utf-8")
    except FileNotFoundError:
        report.error(file, None, "파일이 없어요.", "파일 이름이 바뀌었거나 지워졌는지 확인하세요.")
        return None, ""
    except UnicodeDecodeError:
        report.error(file, None, "UTF-8로 읽을 수 없어요.", "편집기에서 인코딩을 UTF-8로 다시 저장하세요.")
        return None, ""
    dups = []

    def hook(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                dups.append(k)
            obj[k] = v
        return obj

    try:
        data = json.loads(text, object_pairs_hook=hook)
    except json.JSONDecodeError as e:
        hint = next((h for key, h in JSON_HINTS if e.msg.startswith(key)), e.msg)
        report.error(file, None, "JSON 문법 오류 ({}번째 글자 근처): {}".format(e.colno, hint),
                     "그 줄과 바로 앞 줄을 보세요. 수정 후 다시 실행하면 다음 오류까지 확인돼요.", line=e.lineno)
        return None, text
    for k in sorted(set(dups)):
        report.error(file, None, "한 객체 안에 같은 키가 두 번 있어요 ({}) — 뒤의 값만 쓰이고 앞의 값은 조용히 무시돼요.".format(k),
                     "둘 중 맞는 값 하나만 남기세요.")
    return data, text


def id_lines(text):
    """'"id": "xxx"' 줄 번호 목록 {id: [줄, ...]} — 오류 메시지에 줄 번호를 붙이는 용도."""
    out = {}
    for i, ln in enumerate(text.splitlines(), 1):
        m = re.search(r'"id"\s*:\s*"([^"]*)"', ln)  # 한 줄에 한 항목인 형식·여러 줄 형식 모두
        if m:
            out.setdefault(m.group(1), []).append(i)
    return out


class ItemLocator:
    """n번째 항목 → '12번째 항목(id: xxx)' + 줄 번호. 같은 id가 여러 번이면 순서대로 줄을 짝짓는다."""

    def __init__(self, text):
        self.lines = id_lines(text)
        self.seen = {}

    def locate(self, idx, item):
        vid = item.get("id") if isinstance(item, dict) else None
        if not isinstance(vid, str):
            return "{}번째 항목(id 없음)".format(idx + 1), None
        n = self.seen.get(vid, 0)
        self.seen[vid] = n + 1
        lines = self.lines.get(vid, [])
        return "{}번째 항목(id: {})".format(idx + 1, vid), (lines[n] if n < len(lines) else None)


# ── vehicles.json ────────────────────────────────────────

def check_vehicles(data, text, rates, report):
    file = "data/vehicles.json"
    vs = data.get("vehicles") if isinstance(data, dict) else None
    if not isinstance(vs, list):
        report.error(file, None, "최상위에 \"vehicles\": [ ... ] 배열이 없어요.", "파일 구조를 git으로 이전 버전과 비교해 보세요.")
        return 0
    van_keys = None  # tax-rates.json을 못 읽었으면 vanSize 검사는 건너뜀 (그쪽 오류가 먼저 보고됨)
    if rates and isinstance(rates.get("van"), dict) and isinstance(rates["van"].get("sizes"), list):
        van_keys = [s.get("key") for s in rates["van"]["sizes"] if isinstance(s, dict)]
    year_max = datetime.date.today().year + 2
    loc = ItemLocator(text)
    first_id = {}
    first_slug = {}
    known = set(VEHICLE_REQUIRED) | set(VEHICLE_OPTIONAL)

    for idx, v in enumerate(vs):
        where, line = loc.locate(idx, v)

        def err(msg, fix=None):
            report.error(file, where, msg, fix, line)

        def warn(msg, fix=None):
            report.warn(file, where, msg, fix, line)

        if not isinstance(v, dict):
            err("항목이 { ... } 객체가 아니에요.")
            continue
        missing = [k for k in VEHICLE_REQUIRED if k not in v]
        if missing:
            err("필수 필드가 없어요: " + ", ".join(missing),
                "값을 모르면 null로라도 적어 두세요 (예: \"fuelEconomy\": null). 다른 항목을 복사해 고치면 빠뜨리지 않아요.")
        for k in v:
            if k not in known:
                warn("모르는 필드예요 ({}) — 오타면 빌드가 이 값을 무시해요.".format(k),
                     "알려진 필드: " + ", ".join(VEHICLE_REQUIRED + VEHICLE_OPTIONAL))

        for k in ("id", "name", "brand", "modelFamily", "slug"):
            if k in v and not is_str(v[k]):
                err("{} 값이 비었거나 문자열이 아니에요 (지금: {}).".format(k, show(v[k])), "큰따옴표로 감싼 글자로 적으세요.")
        if "generation" in v and v["generation"] is not None and not isinstance(v["generation"], str):
            err("generation은 문자열이어야 해요 (지금: {}).".format(show(v["generation"])))

        vid = v.get("id")
        if is_str(vid):
            if vid in first_id:
                err("id가 {}번째 항목과 겹쳐요 ({}).".format(first_id[vid], vid),
                    "id는 파일 전체에서 하나뿐이어야 해요. 배기량·세대가 다르면 id 끝을 다르게 하세요 (예: -1.6t, -hev).")
            else:
                first_id[vid] = idx + 1

        slug = v.get("slug")
        if is_str(slug):
            if not SLUG_RE.match(slug):
                err("slug는 주소(tax/<slug>.html)에 쓰여서 영어 소문자·숫자·점(.)·하이픈(-)만 쓸 수 있어요 (지금: {}).".format(show(slug)),
                    "예: avante-1.6 / 대문자·공백·한글·밑줄(_)을 빼세요.")
            elif slug in RESERVED_SLUGS:
                err("이 slug는 tax/{}.html(허브·계산기)을 덮어써요.".format(slug), "다른 slug를 쓰세요.")
            elif slug == RESERVED_PREFIX or slug.startswith(RESERVED_PREFIX + "-"):
                err("'{}'로 시작하는 slug는 자동차세 가이드 글 주소(tax/{}.html)와 겹칠 수 있어요.".format(RESERVED_PREFIX, slug),
                    "차종 이름으로 시작하는 다른 slug를 쓰세요.")
            if slug in first_slug:
                err("slug가 {}번째 항목과 겹쳐요 ({}) — 한 페이지가 다른 차종 페이지를 덮어써요.".format(first_slug[slug], slug),
                    "배기량이 다르면 새 slug를 쓰세요. 같은 모델·배기량의 세대 교체라면 기존 항목의 modelYearTo를 닫고 새 항목을 만들지 마세요.")
            else:
                first_slug[slug] = idx + 1

        status = v.get("status")
        if "status" in v and status not in STATUSES:
            err("status에 쓸 수 없는 값이에요 (지금: {}).".format(show(status)), "active(페이지 생성) 또는 sample(구조 예시) 중 하나로 적으세요.")

        fuel = v.get("fuelType")
        if "fuelType" in v and fuel not in FUEL_TYPES:
            err("fuelType에 쓸 수 없는 값이에요 (지금: {}).".format(show(fuel)), "다음 중 하나로 적으세요: " + ", ".join(FUEL_TYPES))

        energy = None  # 연비 단위·범위 판단용. fuelType이 잘못됐으면 None
        if fuel in FUEL_TYPES:
            energy = ENERGY_FOR_FUEL[fuel][0]
        if "energySource" in v:
            es = v["energySource"]
            if es not in ENERGY_SOURCES:
                err("energySource에 쓸 수 없는 값이에요 (지금: {}).".format(show(es)),
                    "다음 중 하나로 적거나, fuelType에서 유도되는 값이면 필드를 빼세요: " + ", ".join(ENERGY_SOURCES))
            elif fuel in FUEL_TYPES and es not in ENERGY_FOR_FUEL[fuel]:
                err("energySource({})가 fuelType({})과 맞지 않아요 — fuelType은 과세 구분, energySource는 실제로 넣는 에너지예요.".format(es, fuel),
                    "fuelType {}에는 {}만 쓸 수 있어요. 수소전기차는 fuelType \"ev\" + energySource \"hydrogen\"이에요(세법상 전기차와 같은 정액).".format(
                        fuel, " / ".join(ENERGY_FOR_FUEL[fuel])))
            else:
                energy = es

        cls = v.get("vehicleClass", "passenger")
        if cls not in VEHICLE_CLASSES:
            err("vehicleClass에 쓸 수 없는 값이에요 (지금: {}).".format(show(cls)),
                "passenger(승용) / van(승합) / truck(화물) 중 하나로 적거나, 승용이면 필드를 빼세요.")

        cc = v.get("displacementCc")
        if "displacementCc" in v:
            if fuel == "ev":
                if cc is not None:
                    err("전기차는 배기량이 없어 displacementCc가 null이어야 해요 (지금: {}). 전기차 세금은 정액이에요.".format(show(cc)),
                        "\"displacementCc\": null 로 바꾸세요. 전기차가 아니라면 fuelType을 고치세요.")
            elif cc is None:
                if cls == "passenger" and status == "active":
                    warn("배기량 미확정 스켈레톤 — displacementCc가 null이라 이 차종 페이지는 빌드에서 빠져요.",
                         "제조사 제원표로 확인한 배기량(cc)을 정수로 채우면 자동으로 페이지가 생겨요. 추정값은 넣지 마세요.")
            elif not is_int(cc):
                err("displacementCc가 정수가 아니에요 (지금: {}).".format(show(cc)),
                    "cc 단위 정수로 적으세요 (예: 1598). 따옴표·소수점·쉼표 없이.")
            elif not (CC_MIN <= cc <= CC_MAX):
                err("displacementCc가 말이 안 되는 값이에요 (지금: {}cc, 허용 {}~{}cc).".format(cc, CC_MIN, CC_MAX),
                    "리터(1.6)가 아니라 cc(1598)로 적었는지, 숫자 자릿수가 맞는지 확인하세요.")

        if cls == "truck":
            kg = v.get("payloadKg")
            if not (is_int(kg) and kg > 0):
                err("화물(truck)은 payloadKg(적재정량 kg)가 꼭 있어야 해요 — 화물 세액이 이 값으로 정해져요 (지금: {}).".format(show(kg)),
                    "양의 정수로 적으세요 (예: 1톤 트럭이면 1000).")
        elif "payloadKg" in v:
            warn("payloadKg는 화물(truck)에서만 쓰여요 — 이 항목에서는 무시돼요.",
                 "화물차라면 \"vehicleClass\": \"truck\"을 추가하세요.")

        if cls == "van":
            size = v.get("vanSize")
            if van_keys is not None and size not in van_keys:
                err("승합(van)은 vanSize가 꼭 있어야 해요 — 승합 세액이 규모로 정해져요 (지금: {}).".format(show(size)),
                    "data/tax-rates.json van.sizes의 key 중 하나로 적으세요: " + ", ".join(str(k) for k in van_keys))
        elif "vanSize" in v:
            warn("vanSize는 승합(van)에서만 쓰여요 — 이 항목에서는 무시돼요.",
                 "승합차라면 \"vehicleClass\": \"van\"을 추가하세요.")

        y_from, y_to = v.get("modelYearFrom"), v.get("modelYearTo")
        if "modelYearFrom" in v:
            if not is_int(y_from):
                err("modelYearFrom이 연도 정수가 아니에요 (지금: {}).".format(show(y_from)), "예: 2020 (따옴표 없이)")
            elif not (YEAR_MIN <= y_from <= year_max):
                err("modelYearFrom이 범위 밖이에요 (지금: {}, 허용 {}~{}).".format(y_from, YEAR_MIN, year_max), "연도 자릿수를 확인하세요.")
        if "modelYearTo" in v and y_to is not None:
            if not is_int(y_to):
                err("modelYearTo가 연도 정수가 아니에요 (지금: {}).".format(show(y_to)), "예: 2023, 지금도 판매 중이면 null")
            elif not (YEAR_MIN <= y_to <= year_max):
                err("modelYearTo가 범위 밖이에요 (지금: {}, 허용 {}~{}).".format(y_to, YEAR_MIN, year_max), "연도 자릿수를 확인하세요.")
            elif is_int(y_from) and y_from > y_to:
                err("modelYearFrom이 modelYearTo보다 늦어요 (지금: {} ~ {}).".format(y_from, y_to), "두 값이 서로 바뀌지 않았는지 보세요.")

        eco = v.get("fuelEconomy")
        if eco is not None and "fuelEconomy" in v:
            lo, hi = ECONOMY_RANGE.get(energy, ECONOMY_RANGE["ice"])
            unit = ENERGY_UNIT.get(energy, "km/L")
            if not is_num(eco):
                err("fuelEconomy가 숫자가 아니에요 (지금: {}).".format(show(eco)), "예: 14.3 (따옴표 없이), 모르면 null")
            elif not (lo <= eco <= hi):
                err("fuelEconomy가 말이 안 되는 값이에요 (지금: {}{}, 허용 {}~{}{}).".format(eco, unit, lo, hi, unit),
                    "전기차는 km/kWh, 수소전기차(energySource hydrogen)는 km/kg, 나머지는 km/L 단위의 공인 복합연비예요. 단위·소수점 위치를 확인하세요.")

        if "rangeKm" in v and v["rangeKm"] is not None:
            rk = v["rangeKm"]
            if not is_num(rk) or not (RANGE_KM[0] <= rk <= RANGE_KM[1]):
                err("rangeKm이 말이 안 되는 값이에요 (지금: {}, 허용 {}~{}km).".format(show(rk), RANGE_KM[0], RANGE_KM[1]),
                    "인증 주행거리(km)를 숫자로 적거나, 모르면 null로 두세요.")
            elif fuel != "ev":
                warn("rangeKm은 전기차 페이지에만 표시돼요 — 이 항목에서는 무시돼요.")

        if "aliases" in v:
            al = v["aliases"]
            if not isinstance(al, list) or not all(is_str(a) for a in al):
                err("aliases는 문자열 배열이어야 해요 (지금: {}).".format(show(al)),
                    "예: [\"아반떼\", \"avante\"] — 없으면 빈 배열 []")

        for k in ("classNote", "fuelEconomyNote", "trimGroup"):
            if k in v and v[k] is not None and not is_str(v[k]):
                err("{} 값은 문자열이어야 해요 (지금: {}).".format(k, show(v[k])))
    return len(vs)


# ── tax-rates.json ───────────────────────────────────────

def check_tax_rates(rates, report):
    file = "data/tax-rates.json"
    if not isinstance(rates, dict):
        report.error(file, None, "최상위가 { ... } 객체가 아니에요.")
        return

    def err(where, msg, fix=None):
        report.error(file, where, msg, fix)

    lv = rates.get("lastVerified")
    if not (isinstance(lv, str) and re.match(r"^\d{4}-(0[1-9]|1[0-2])$", lv)):
        err("lastVerified", "'YYYY-MM' 형식이 아니에요 (지금: {}) — 모든 세금 페이지 하단 '최종 확인' 문구에 그대로 찍혀요.".format(show(lv)),
            "예: \"2026-08\" (월은 두 자리)")

    d = rates.get("displacement")
    if not isinstance(d, dict):
        err("displacement", "승용 세율 블록(displacement)이 없어요.")
        return

    br = d.get("brackets")
    if not isinstance(br, list) or not br:
        err("displacement.brackets", "배기량 구간표가 비었어요.")
    else:
        prev = None
        for i, b in enumerate(br):
            w = "displacement.brackets {}번째 구간".format(i + 1)
            if not isinstance(b, dict):
                err(w, "구간이 { ... } 객체가 아니에요.")
                continue
            mx = b.get("maxCc")
            last = i == len(br) - 1
            if last:
                if mx is not None:
                    err(w, "마지막 구간의 maxCc가 null이 아니에요 (지금: {}) — 그보다 큰 배기량은 세율을 못 찾아요.".format(show(mx)),
                        "마지막 구간은 \"maxCc\": null (상한 없음)이어야 해요.")
            elif mx is None:
                err(w, "마지막이 아닌 구간의 maxCc가 null이에요 — 뒤 구간이 영영 안 쓰여요.",
                    "maxCc null은 마지막 구간에만 쓰세요.")
            elif not (is_int(mx) and mx > 0):
                err(w, "maxCc가 양의 정수가 아니에요 (지금: {}).".format(show(mx)))
            elif prev is not None and mx <= prev:
                err(w, "maxCc가 앞 구간보다 커야 해요 (지금: 앞 구간 {} 다음에 {}) — 구간은 작은 배기량부터 오름차순이어야 해요.".format(prev, mx),
                    "maxCc는 '이하(≤)' 기준이에요. 순서와 숫자를 확인하세요.")
            if is_int(mx):
                prev = mx
            wpc = b.get("wonPerCc")
            if not (is_num(wpc) and wpc > 0):
                err(w, "wonPerCc(cc당 세액)가 양수가 아니에요 (지금: {}).".format(show(wpc)))

    ag = d.get("agingDiscount")
    if not isinstance(ag, dict):
        err("displacement.agingDiscount", "차령 경감 블록이 없어요.")
    else:
        if not (is_int(ag.get("startCarAge")) and ag["startCarAge"] >= 1):
            err("agingDiscount.startCarAge", "1 이상 정수여야 해요 (지금: {}).".format(show(ag.get("startCarAge"))))
        for k in ("ratePerYear", "maxRate"):
            x = ag.get(k)
            if not (is_num(x) and 0 <= x <= 1):
                err("agingDiscount." + k, "0~1 사이 비율이어야 해요 (지금: {}).".format(show(x)),
                    "퍼센트가 아니라 비율로 적으세요 (5% → 0.05, 50% → 0.5).")

    et = d.get("educationTaxRate")
    if not (is_num(et) and 0 <= et <= 1):
        err("displacement.educationTaxRate", "0~1 사이 비율이어야 해요 (지금: {}).".format(show(et)), "30% → 0.3")

    ev = d.get("ev")
    if not isinstance(ev, dict):
        err("displacement.ev", "전기차 정액 블록이 없어요.")
    else:
        vals = [ev.get(k) for k in ("annualTotalKrw", "baseKrw", "educationTaxKrw")]
        if not all(is_int(x) and x >= 0 for x in vals):
            err("displacement.ev", "annualTotalKrw·baseKrw·educationTaxKrw는 0 이상 정수(원)여야 해요 (지금: {}).".format(show(vals)))
        elif vals[0] != vals[1] + vals[2]:
            err("displacement.ev",
                "합계가 안 맞아요: annualTotalKrw {:,} ≠ baseKrw {:,} + educationTaxKrw {:,} (= {:,}) — 전기차 페이지 FAQ 숫자가 서로 어긋나요.".format(
                    vals[0], vals[1], vals[2], vals[1] + vals[2]),
                "세 값 중 바뀐 것을 확인해 합이 맞게 고치세요.")

    p = rates.get("prepayDiscount")
    if not isinstance(p, dict):
        err("prepayDiscount", "연납 공제 블록이 없어요.")
    else:
        rby = p.get("rateByYear")
        if not isinstance(rby, dict) or not rby:
            err("prepayDiscount.rateByYear", "연도별 공제율이 비었어요.", "예: {\"2026\": 0.05}")
        else:
            for y, r in rby.items():
                if not re.match(r"^\d{4}$", y):
                    err("prepayDiscount.rateByYear", "키가 네 자리 연도가 아니에요 (지금: {}) — '가장 최근 연도'를 고르는 계산이 틀어져요.".format(show(y)),
                        "예: \"2027\"")
                if not (is_num(r) and 0 <= r <= 0.1):
                    err("prepayDiscount.rateByYear[{}]".format(y), "공제율이 0~0.1 범위 밖이에요 (지금: {}).".format(show(r)),
                        "퍼센트가 아니라 비율로 적으세요 (5% → 0.05).")
        ws = p.get("applicationWindows")
        months = set()
        if not isinstance(ws, list) or not ws:
            err("prepayDiscount.applicationWindows", "연납 신청 기간 목록이 비었어요 — 1월 연납 공제 일수도 여기서 계산해요.",
                "예: [{\"month\": 1, \"startDay\": 16, \"endDay\": 31, \"coveredMonths\": 11, \"label\": \"1월 연납\", ...}]")
        else:
            for i, w in enumerate(ws):
                where = "prepayDiscount.applicationWindows {}번째".format(i + 1)
                if not isinstance(w, dict):
                    err(where, "{ ... } 객체가 아니에요.")
                    continue
                m, sd, ed = w.get("month"), w.get("startDay"), w.get("endDay")
                if not (is_int(m) and 1 <= m <= 12):
                    err(where, "month가 1~12 정수가 아니에요 (지금: {}).".format(show(m)))
                    continue
                if m in months:
                    err(where, "{}월 기간이 두 번 나와요.".format(m))
                months.add(m)
                # 평년 말일 기준 — 2월 29일은 평년에 없는 날이라 일수 계산이 깨진다
                last = (datetime.date(2023 + (m == 12), m % 12 + 1, 1) - datetime.timedelta(days=1)).day
                if not (is_int(sd) and is_int(ed) and 1 <= sd <= ed <= last):
                    err(where, "startDay·endDay가 이상해요 (지금: {}월 {}~{}일) — {}월은 {}일까지예요.".format(m, show(sd), show(ed), m, last),
                        "법정 신청 기간은 16일~말일이에요 (지방세법 제128조 제3항).")
                cm = w.get("coveredMonths")
                if not (is_int(cm) and 0 < cm < 12):
                    err(where, "coveredMonths(공제 대상 월 수)가 1~11 정수가 아니에요 (지금: {}).".format(show(cm)),
                        "신청 다음 달~12월의 개월 수예요 — 1월 신청이면 11.")
                lead = w.get("bannerLeadDays", 0)
                if not (is_int(lead) and 0 <= lead <= 120):
                    err(where, "bannerLeadDays(예고 일수)가 0~120 정수가 아니에요 (지금: {}).".format(show(lead)),
                        "신청 기간 중에만 안내하려면 0, 미리 알리려면 시작 며칠 전부터인지 적으세요.")
        jp = p.get("januaryProration")
        if not isinstance(jp, dict):
            err("prepayDiscount.januaryProration", "1월 연납 일할 블록이 없어요.")
        else:
            if jp.get("method") != "daily":
                err("prepayDiscount.januaryProration.method", "'daily'(일할)여야 해요 (지금: {}).".format(show(jp.get("method"))),
                    "공제액 = 연세액 × (납부기한 다음 날~12/31 일수 ÷ 365(윤년 366)) × 공제율 — 지방세법 제128조 제3항 계산식.")
            wm = jp.get("windowMonth")
            if not (is_int(wm) and wm in months):
                err("prepayDiscount.januaryProration.windowMonth",
                    "applicationWindows에 없는 달이에요 (지금: {}) — 공제 일수를 그 기간의 endDay(납부기한)로 계산해요.".format(show(wm)),
                    "1월 연납이면 1.")
            if "coveredMonths" in jp or "totalMonths" in jp:
                err("prepayDiscount.januaryProration", "월할(coveredMonths·totalMonths) 키가 남아 있어요 — 계산은 일할로 바뀌었어요.",
                    "두 키를 지우세요 (공제 대상 월 수는 applicationWindows.coveredMonths가 문구용으로 갖고 있어요).")

    van = rates.get("van")
    if isinstance(van, dict):
        keys = set()
        for i, s in enumerate(van.get("sizes") or []):
            w = "van.sizes {}번째".format(i + 1)
            if not isinstance(s, dict) or not is_str(s.get("key")):
                err(w, "key가 없어요.")
                continue
            if s["key"] in keys:
                err(w, "key '{}'가 겹쳐요.".format(s["key"]))
            keys.add(s["key"])
            for k in ("businessKrw", "nonBusinessKrw"):
                if not (is_int(s.get(k)) and s[k] >= 0):
                    err(w + " (" + s["key"] + ")", "{} 값은 0 이상 정수(원)여야 해요 (지금: {}).".format(k, show(s.get(k))))

    truck = rates.get("truck")
    if isinstance(truck, dict):
        prev = None
        for i, b in enumerate(truck.get("brackets") or []):
            w = "truck.brackets {}번째 구간".format(i + 1)
            mx = b.get("maxKg") if isinstance(b, dict) else None
            if not (is_int(mx) and mx > 0):
                err(w, "maxKg가 양의 정수가 아니에요 (지금: {}).".format(show(mx)))
                continue
            if prev is not None and mx <= prev:
                err(w, "maxKg가 앞 구간보다 커야 해요 (지금: 앞 구간 {} 다음에 {}) — 오름차순이어야 해요.".format(prev, mx))
            prev = mx
            for k in ("businessKrw", "nonBusinessKrw"):
                if not (is_int(b.get(k)) and b[k] >= 0):
                    err(w, "{} 값은 0 이상 정수(원)여야 해요 (지금: {}).".format(k, show(b.get(k))))


# ── parts.json · site.json · affiliate.json ──────────────

def check_parts(data, text, report):
    file = "data/parts.json"
    parts = data.get("parts") if isinstance(data, dict) else None
    if not isinstance(parts, list):
        report.error(file, None, "최상위에 \"parts\": [ ... ] 배열이 없어요.")
        return []
    cats = data.get("categories") if isinstance(data.get("categories"), dict) else {}
    loc = ItemLocator(text)
    seen = {}
    for idx, p in enumerate(parts):
        where, line = loc.locate(idx, p)
        if not isinstance(p, dict):
            report.error(file, where, "항목이 { ... } 객체가 아니에요.", line=line)
            continue
        pid = p.get("id")
        if not is_str(pid):
            report.error(file, where, "id가 없어요 — 수첩 기록이 소모품을 id로 찾아요.", line=line)
        elif pid in seen:
            report.error(file, where, "id가 {}번째 항목과 겹쳐요 ({}) — 기록이 엉뚱한 소모품에 붙어요.".format(seen[pid], pid),
                         "id는 하나뿐이어야 해요. 이미 쓰던 id는 바꾸지 말고(사용자 기록이 그 id를 참조) 새 항목의 id를 바꾸세요.", line)
        else:
            seen[pid] = idx + 1
        cat = p.get("category")
        if cats and not (isinstance(cat, str) and cat in cats):
            report.error(file, where, "category가 categories 목록에 없어요 (지금: {}).".format(show(cat)),
                         "다음 중 하나로 적으세요: " + ", ".join(cats), line)
        at = p.get("appliesTo")
        if not isinstance(at, list) or not at or any(f not in FUEL_TYPES for f in at):
            report.error(file, where, "appliesTo에 모르는 연료가 있거나 비었어요 (지금: {}).".format(show(at)),
                         "다음 중에서 고르세요: " + ", ".join(FUEL_TYPES), line)
        for k in ("intervalKm", "intervalMonths"):
            x = p.get(k)
            if x is not None and not (is_int(x) and x > 0):
                report.error(file, where, "{} 값이 양의 정수가 아니에요 (지금: {}).".format(k, show(x)), "기준이 없으면 null로 두세요.", line)
    return list(seen)


def key_line(text, key):
    """원문에서 '"key":'가 처음 나오는 줄 번호 (없으면 None) — site.json처럼 키가 한 번씩만 나오는 파일용."""
    m = re.search('"' + re.escape(key) + r'"\s*:', text or "")
    return text.count("\n", 0, m.start()) + 1 if m else None


def hand_page_texts():
    """루트 손 페이지(index·tco·privacy·terms·about …) {이름: 원문} — build.py가 마커를 채우는 범위(루트 *.html)."""
    out = {}
    for page in sorted(ROOT.glob("*.html")):
        try:
            out[page.name] = page.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
    return out


def hand_page_slot_markers(pages):
    """손 페이지의 <!-- adsense:slot 이름 --> 마커 [(페이지, 줄, 이름)]."""
    return [(name, text.count("\n", 0, m.start()) + 1, m.group(1))
            for name, text in pages.items() for m in AD_SLOT_MARKER.finditer(text)]


def check_hand_slot_markers(pages, report):
    """손 페이지 광고 마커 이름이 계약(HAND_SLOT_WHERE)에 있는 이름인지 — site.json 값과 상관없이 늘 본다.
    이름에 오타가 나면 build.py는 그 자리를 빈칸으로 두고 adsbygoogle.js도 빼서 빌드 결과가 앞뒤가 맞아 보이므로
    빌드 검사로는 안 잡힌다."""
    hand = ", ".join(HAND_SLOT_WHERE)
    new_slot = ("광고 자리를 새로 두려는 거라면 개인정보처리방침 4절의 '광고가 게재되는 페이지' 문구, "
                "scripts/validate_data.py HAND_SLOT_WHERE, scripts/check_links.py HAND_MARKERS, data/site.json slots를 "
                "함께 고치세요 (수첩·소개·개인정보처리방침·이용약관에는 광고를 두지 않아요).")
    for page, line, name in hand_page_slot_markers(pages):
        where = "<!-- adsense:slot {} -->".format(name)
        if name in BUILD_SLOT_NAMES:
            report.error(page, where,
                         "이 이름({})은 build.py가 생성 페이지에 채우는 광고 자리예요 — 손 페이지에 쓰면 같은 광고 단위가 "
                         "두 곳에 나가요.".format(name),
                         "손 페이지 광고 자리 이름은 {}예요. ".format(hand) + new_slot, line)
        elif name not in HAND_SLOT_WHERE:
            near = [n for n in HAND_SLOT_WHERE if n.lower() == name.lower()]
            report.error(page, where,
                         "손 페이지 광고 자리 이름이 계약에 없어요 (지금: {}) — 빌드가 이 자리를 빈칸으로 두고 "
                         "광고 스크립트도 빼서, 슬롯 ID를 채워도 광고가 소리 없이 안 나와요.".format(show(name)),
                         "대소문자까지 같아야 해요 → {}".format(near[0]) if near else
                         "손 페이지 광고 자리 이름은 {}예요. 오타면 고치세요. ".format(hand) + new_slot, line)


def check_adsense(ad, text, report, pages):
    """site.json adsense — build.py가 이 값으로 ads.txt·소유 확인 메타·광고 코드를 켜고 끈다.
    pages: 손 페이지 {이름: 원문} — 채운 손 페이지 슬롯을 받아 줄 마커가 실제로 있는지 본다."""
    file = "data/site.json"
    if ad is None:
        return  # 키가 없으면 빈 값과 같다(광고 0)
    if not isinstance(ad, dict):
        report.error(file, "adsense", "{{ ... }} 객체가 아니에요 (지금: {}).".format(show(ad)),
                     '{"publisherId": "", "slots": {}} 형태로 두세요. 광고를 안 쓰면 publisherId를 ""로.',
                     key_line(text, "adsense"))
        return
    for k in ad:
        if k not in AD_KEYS:
            report.warn(file, "adsense." + k, "모르는 키예요 — 빌드는 {}만 읽어서 이 값은 무시돼요.".format(", ".join(AD_KEYS)),
                        "오타인지 보세요 (대소문자까지 같아야 해요: publisherId).", key_line(text, k))

    pub = ad.get("publisherId")
    pub_ok = False
    if pub not in (None, ""):
        line = key_line(text, "publisherId")
        if not isinstance(pub, str):
            report.error(file, "adsense.publisherId", "문자열이 아니에요 (지금: {}).".format(show(pub)),
                         '따옴표로 감싸 "pub-0000000000000000" 형식으로 쓰세요. 아직 없으면 "".', line)
        elif pub.strip().startswith("ca-pub-"):
            report.error(file, "adsense.publisherId",
                         "'ca-pub-'으로 시작해요 (지금: {}) — 여기에는 'pub-'로 시작하는 게시자 ID만 넣어요. "
                         "메타·광고 코드의 'ca-'는 빌드가 붙여요(ads.txt에는 ca- 없이 들어가요).".format(show(pub)),
                         "앞의 ca-를 지우세요 → {}".format(show(pub.strip()[3:])), line)
        elif pub != pub.strip():
            report.error(file, "adsense.publisherId", "앞뒤에 공백이 있어요 (지금: {}).".format(show(pub)),
                         "공백을 지우세요 → {}".format(show(pub.strip())), line)
        elif not PUB_ID_RE.match(pub):
            report.error(file, "adsense.publisherId",
                         "'pub-' + 숫자 16자리 형식이 아니에요 (지금: {}) — ads.txt·소유 확인이 엉뚱한 계정을 가리켜요.".format(show(pub)),
                         "애드센스 계정 정보에 있는 '게시자 ID'를 그대로 복사해 넣으세요 (예: \"pub-0000000000000000\"). "
                         "아직 없으면 \"\"로 두세요.", line)
        else:
            pub_ok = True

    slots = ad.get("slots")
    if slots is None:
        return
    if not isinstance(slots, dict):
        report.error(file, "adsense.slots", "{{ ... }} 객체가 아니에요 (지금: {}).".format(show(slots)),
                     '{"taxArticle": "", "hubEnd": "", "calcEnd": "", "tcoEnd": ""} 형태로 두세요.', key_line(text, "slots"))
        return
    known = list(AD_SLOT_NAMES)  # 손 페이지 마커 이름으로 넓히지 않는다 — 마커 오타가 '아는 이름'이 되지 않게
    filled = []
    for name, sid in slots.items():
        where = "adsense.slots." + name
        line = key_line(text, name)
        if name not in known:
            report.warn(file, where, "이 이름의 광고 자리가 없어요 — 값을 넣어도 어디에도 광고가 안 나와요.",
                        "쓸 수 있는 이름: {} (taxArticle 차종 페이지 · hubEnd 차종 목록 · calcEnd 계산기 · tcoEnd 유지비 비교). "
                        "오타인지 보세요.".format(", ".join(known)), line)
        if sid in (None, ""):
            continue
        if is_int(sid):
            report.error(file, where, "숫자가 따옴표 없이 들어갔어요 (지금: {}).".format(show(sid)),
                         "따옴표로 감싸 문자열로 쓰세요 → \"{}\"".format(sid), line)
        elif not (isinstance(sid, str) and AD_SLOT_RE.match(sid)):
            report.error(file, where, "광고 단위 ID는 숫자만이에요 (지금: {}).".format(show(sid)),
                         "애드센스에서 만든 광고 단위의 ID(숫자)를 넣으세요. 아직 없으면 \"\"로 두세요.", line)
        else:
            filled.append(name)
    if filled and not pub_ok and pub in (None, ""):
        report.warn(file, "adsense.slots", "publisherId가 비어 있어 슬롯 ID({})가 있어도 광고가 하나도 나오지 않아요.".format(
                        ", ".join(filled)),
                    "게시자 ID를 publisherId에 넣거나, 광고를 끄려는 거라면 슬롯도 \"\"로 비우세요.", key_line(text, "publisherId"))
    marked = {name for _, _, name in hand_page_slot_markers(pages)}
    for name in filled:
        if name in HAND_SLOT_WHERE and name not in marked:
            report.warn(file, "adsense.slots." + name,
                        "광고 단위 ID가 있는데 손 페이지에 <!-- adsense:slot {} --> 마커가 없어 이 광고가 어디에도 안 나와요.".format(name),
                        "{}에 <!-- adsense:slot {} --><!-- /adsense:slot -->를 다시 넣고 빌드하세요 "
                        "(마커를 지웠거나 이름에 오타가 난 경우예요).".format(HAND_SLOT_WHERE[name], name), key_line(text, name))


def check_site(site, report, text="", pages=None):
    file = "data/site.json"
    if pages is None:
        pages = hand_page_texts()
    if not isinstance(site, dict):
        report.error(file, None, "최상위가 { ... } 객체가 아니에요.")
        return
    base = site.get("baseUrl")
    if not (isinstance(base, str) and re.match(r"^https://[a-z0-9.-]+\.[a-z]{2,}/?$", base)):
        report.error(file, "baseUrl", "'https://도메인' 형식이 아니에요 (지금: {}) — canonical·sitemap·공유 썸네일 주소가 전부 여기서 나와요.".format(show(base)),
                     "예: \"https://chailji.com\" (https, 경로 없이)")
    if not is_str(site.get("siteName")):
        report.error(file, "siteName", "사이트 이름이 비었어요.")
    check_adsense(site.get("adsense"), text, report, pages)
    email = site.get("contactEmail")
    if email not in (None, ""):
        if not (isinstance(email, str) and EMAIL_RE.match(email)):
            report.error(file, "contactEmail", "이메일 형식이 아니에요 (지금: {}) — 개인정보처리방침·이용약관·소개 페이지에 그대로 나가요.".format(show(email)),
                         "'이름@도메인.최상위도메인' 형식의 사이트 전용 주소를 넣으세요 (예: \"contact@example.com\" 형식, 앞뒤 공백 없이). "
                         "아직 없으면 \"\"로 두면 이메일 문단이 숨겨져요.", key_line(text, "contactEmail"))
        elif not any(CONTACT_MARKER in t for t in pages.values()):
            report.warn(file, "contactEmail",
                        "주소가 있는데 손 페이지에 {} 마커가 하나도 없어 이메일이 어디에도 안 나와요.".format(CONTACT_MARKER),
                        "privacy.html·terms.html·about.html의 문의 문단에 <!-- site:contact --><!-- /site:contact -->를 "
                        "다시 넣고 빌드하세요.", key_line(text, "contactEmail"))


def check_affiliate(data, part_ids, report):
    file = "data/affiliate.json"
    links = data.get("links") if isinstance(data, dict) else None
    if not isinstance(links, dict):
        report.error(file, "links", "links가 { ... } 객체가 아니에요.", "비어 있으면 \"links\": {} 로 두세요.")
        return
    for k, url in links.items():
        if part_ids and k not in part_ids:
            report.error(file, "links", "키가 data/parts.json의 소모품 id가 아니에요 (지금: {}) — 이 링크는 어디에도 안 보여요.".format(show(k)),
                         "parts.json의 id를 그대로 쓰세요 (예: engine-oil).")
        if url not in ("", None) and not (isinstance(url, str) and url.startswith("https://")):
            report.error(file, "links." + k, "링크가 https:// 주소가 아니에요 (지금: {}).".format(show(url)))


def main():
    report = Report()
    loaded = {}
    names = sorted(p.name for p in (ROOT / "data").glob("*.json"))
    for name in names:  # 모든 data/*.json — 최소한 문법·중복 키는 본다
        loaded[name] = load_json(name, report)
    for required in ("vehicles.json", "tax-rates.json", "parts.json", "site.json"):
        if required not in loaded:
            loaded[required] = load_json(required, report)  # '파일이 없어요' 보고

    rates = loaded["tax-rates.json"][0]
    if rates is not None:
        check_tax_rates(rates, report)
    n_vehicles = 0
    if loaded["vehicles.json"][0] is not None:
        n_vehicles = check_vehicles(loaded["vehicles.json"][0], loaded["vehicles.json"][1],
                                    rates if isinstance(rates, dict) else None, report)
    part_ids = []
    if loaded["parts.json"][0] is not None:
        part_ids = check_parts(loaded["parts.json"][0], loaded["parts.json"][1], report)
    pages = hand_page_texts()
    check_hand_slot_markers(pages, report)
    if loaded["site.json"][0] is not None:
        check_site(loaded["site.json"][0], report, loaded["site.json"][1], pages)
    if loaded.get("affiliate.json", (None, ""))[0] is not None:
        check_affiliate(loaded["affiliate.json"][0], part_ids, report)

    for w in report.warnings:
        print("[경고] " + w)
    for e in report.errors:
        print("[오류] " + e)
    if report.warnings or report.errors:
        print("")
    print("검사한 파일: data/ 안 JSON {}개 (차종 {}개)".format(len(names), n_vehicles))
    if report.errors:
        print("결과: 오류 {}개 · 경고 {}개 — 실패".format(len(report.errors), len(report.warnings)))
        print("고치는 법: 위 [오류]마다 '→' 뒤 안내대로 고친 다음 python3 scripts/validate_data.py 로 다시 확인하세요.")
        return 1
    print("결과: 오류 0개 · 경고 {}개 — 통과".format(len(report.warnings)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
