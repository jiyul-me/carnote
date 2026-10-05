#!/usr/bin/env python3
"""차일지 — 링크·앵커·공통 크롬 검사.

1. 깨진 링크: 저장소의 모든 .html(tests/ 제외)에서 href·src 링크를 찾아 실제 파일이 있는지 본다.
   - 상대 링크(../tco.html), 루트 기준 링크(/tax/index.html), 우리 도메인 절대 링크(https://chailji.com/...)
     — 도메인은 data/site.json baseUrl에서 읽는다. 쿼리(?v=)는 떼고 본다.
   - 외부 사이트, data:, mailto:, tel:, javascript:, '#'만 있는 링크는 건너뛴다.
   - 대소문자까지 똑같아야 통과 — Mac에서는 Tax/Index.html도 열리지만 GitHub Pages에서는 404가 난다.
   - sitemap.xml·robots.txt의 우리 도메인 주소, manifest.webmanifest의 아이콘 경로도 같이 본다.
2. 앵커: 같은 사이트 안 링크의 #조각(크럼의 index.html#가족, 브랜드 칩의 #브랜드 등)이 대상 페이지에
   id로 있는지 본다 — 없으면 페이지 맨 위가 열려 '바로가기'가 조용히 고장 난다. JSON-LD 속 우리 도메인
   주소의 #조각도 본다. 수첩(index.html)의 #settings·#car/new 같은 해시는 화면 이동 경로라 보지 않는다.
3. 공통 크롬 — scripts/build.py(page()·topbar_nav()·footer_links())와 손으로 쓰는 루트 페이지가 같은 마크업을 쓰는 계약:
   - 상단 내비: <nav class="topbar-right topbar-nav" aria-label="주 메뉴"> 안 링크가 정확히
     [수첩, 자동차세, 유지비 비교](index.html·tax/index.html·tco.html)이고, 현재 위치(aria-current="page")는
     수첩 화면=수첩, tax/ 페이지=자동차세, tco.html=유지비 비교에만 있다(privacy·terms·about은 없음).
   - 푸터 2번째 줄 링크가 [소개·문의, 개인정보처리방침, 이용약관](about.html·privacy.html·terms.html) 순서다.
   - 손 페이지(루트 *.html)의 head에 <!-- adsense:head --> … <!-- /adsense:head --> 마커가 있다
     (build.py가 site.json adsense.publisherId로 소유 확인 메타를 채우는 자리).
   - 손 페이지 광고·문의 마커 계약(HAND_MARKERS): tco.html에 <!-- adsense:slot tcoEnd -->,
     privacy·terms·about에 <!-- site:contact -->가 정확히 한 번 있고, 계약에 없는 페이지·이름의 마커는 없다.
     마커 이름 오타나 삭제는 build.py가 그 자리를 조용히 비우고 끝나 빌드 검사로는 안 잡히므로 여기서 잡는다.
   대상은 루트와 tax/의 .html이고, 검색엔진 소유 확인 파일(naver….html·google….html)은 뺀다.
   about.html(소개·문의)이 아직 없으면 공통 크롬 도입 전 저장소로 보고 위 넷은 '참고'로만 알린다(실패 아님) —
   about.html이 생기면 오류가 된다.

사용법:  python3 scripts/check_links.py     깨진 링크·없는 #id·크롬 불일치가 있으면 exit 1.
Python 3.9 호환.
"""
import json
import os
import posixpath
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checklib import ROOT, annotate  # noqa: E402

LINK_ATTRS = ("href", "src")
SKIP_DIRS = ("tests", "node_modules", "scripts")  # 점(.)으로 시작하는 폴더(.git·.github·.claude 등)도 건너뜀
SHOW_MAX = 30
SHOW_PAGES = 5  # 같은 문제를 가진 페이지는 몇 개만 이름을 보인다

# 앵커 검사에서 뺄 페이지 — 수첩은 #settings·#expenses·#part/{id}·#car/new 해시를 화면 이동에 쓴다(app.js)
SPA_PAGES = ("index.html",)

# 공통 크롬 계약 (scripts/build.py NAV_ITEMS·footer_links와 같은 값)
NAV_CLASS = "topbar-nav"
NAV_LABEL = "주 메뉴"
NAV_LINKS = (("수첩", "index.html"), ("자동차세", "tax/index.html"), ("유지비 비교", "tco.html"))
FOOT_LINKS = (("소개·문의", "about.html"), ("개인정보처리방침", "privacy.html"), ("이용약관", "terms.html"))
# 현재 위치(aria-current="page")를 달 내비 항목 — 페이지 경로로 정한다. '/'로 끝나면 그 폴더 전부
CURRENT_FOR = (("index.html", "수첩"), ("tco.html", "유지비 비교"), ("tax/", "자동차세"))
CHROME_DIRS = ("", "tax")  # 공통 크롬을 보는 폴더 (루트·tax/)
CONTRACT_PAGE = "about.html"  # 이 페이지가 생기면 공통 크롬·마커 검사가 오류가 된다(그 전에는 참고)
HEAD_OPEN, HEAD_CLOSE = "<!-- adsense:head -->", "<!-- /adsense:head -->"
SLOT_CLOSE, CONTACT_OPEN, CONTACT_CLOSE = "<!-- /adsense:slot -->", "<!-- site:contact -->", "<!-- /site:contact -->"
# 손 페이지 광고·문의 마커 계약 — 어느 손 페이지에 어떤 마커(여는 것, 닫는 것)가 정확히 한 번 있어야 하는가
# (plan.json adsense 계약·README '손 페이지 마커 규칙'). head 마커는 모든 손 페이지 공통이라 위에서 따로 본다.
# 표에 없는 페이지에는 slot·contact 마커를 두지 않는다 — 수첩·소개·개인정보처리방침·이용약관에는 광고가 없고
# (privacy.html 4절 약속), 광고가 게재되는 손 페이지는 유지비 비교뿐이다. 광고 자리를 늘리려면 privacy.html 4절
# 문구와 이 표, scripts/validate_data.py HAND_SLOT_WHERE를 함께 고친다.
HAND_MARKERS = {
    "tco.html": (("<!-- adsense:slot tcoEnd -->", SLOT_CLOSE),),
    "privacy.html": ((CONTACT_OPEN, CONTACT_CLOSE),),
    "terms.html": ((CONTACT_OPEN, CONTACT_CLOSE),),
    "about.html": ((CONTACT_OPEN, CONTACT_CLOSE),),
}
# 본문 마커(광고 자리·문의)의 여는 마커 — 형식이 build.py MARKER와 같은 것만. 형식이 어긋난 마커는 build.py가 멈춘다
BODY_MARKER_RE = re.compile(r"<!-- (?:adsense:slot [A-Za-z][A-Za-z0-9]*|site:contact) -->")
VERIFY_FILE = re.compile(r"^(naver|google)[0-9a-f]+\.html$")  # 검색엔진 소유 확인용 한 줄 파일
HEAD_RE = re.compile(r"<head\b[^>]*>(.*?)</head\s*>", re.S | re.I)


def _marker_pages():
    """[(빈 형태 마커, [페이지])] — HAND_MARKERS를 마커별로 묶은 것 (안내 문구용)."""
    out = {}
    for page, markers in HAND_MARKERS.items():
        for o, c in markers:
            out.setdefault(o + c, []).append(page)
    return list(out.items())


CONTRACT_MARKUP = (
    ("상단 내비 (현재 위치 링크에만 aria-current=\"page\")",
     '<nav class="topbar-right topbar-nav" aria-label="주 메뉴"><a href="index.html">수첩</a>'
     '<a href="tax/index.html">자동차세</a><a href="tco.html">유지비 비교</a></nav>'),
    ("푸터 2번째 줄",
     '<p><a href="about.html">소개·문의</a> · <a href="privacy.html">개인정보처리방침</a> · '
     '<a href="terms.html">이용약관</a></p>'),
    ("head 안 (공백·줄바꿈 없이)", HEAD_OPEN + HEAD_CLOSE),
) + tuple(("{} 본문 (공백·줄바꿈 없이, 이 페이지에만 한 번)".format("·".join(pages)), markup)
          for markup, pages in _marker_pages())


class PageParser(HTMLParser):
    """링크·id·상단 내비·푸터 줄을 한 번에 모은다."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.links = []  # (줄, 값)
        self.ids = set()
        self.navs = []  # {"line", "label", "links": [a], "others": [태그]}
        self.foot = None  # {"line", "lines": [[a, ...], ...], "p_lines": [줄]} — 첫 footer.foot의 <p> 줄마다 링크
        self._nav = None
        self._in_foot = False
        self._a = None

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        for name, value in attrs:
            if name in LINK_ATTRS and value is not None:
                self.links.append((line, value.strip()))
            elif name == "content" and value and value.startswith(("http://", "https://")):
                self.links.append((line, value.strip()))  # og:image·og:url 같은 meta — 우리 도메인만 검사됨
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("name"):
            self.ids.add(a["name"])
        classes = (a.get("class") or "").split()
        if tag == "nav" and NAV_CLASS in classes:
            self._nav = {"line": line, "label": a.get("aria-label"), "links": [], "others": []}
            self.navs.append(self._nav)
        elif tag == "footer" and "foot" in classes and self.foot is None:
            self.foot = {"line": line, "lines": [], "p_lines": []}
            self._in_foot = True
        elif tag == "p" and self._in_foot:
            self.foot["lines"].append([])
            self.foot["p_lines"].append(line)
        elif tag == "a":
            rec = {"href": a.get("href"), "current": a.get("aria-current"), "text": [], "line": line}
            if self._nav is not None:
                self._nav["links"].append(rec)
                self._a = rec
            elif self._in_foot and self.foot["lines"]:
                self.foot["lines"][-1].append(rec)
                self._a = rec
        elif tag in ("button", "input", "select") and self._nav is not None:
            self._nav["others"].append(tag)

    # <a/> 같은 자기 닫힘 태그는 HTMLParser 기본 동작대로 handle_starttag → handle_endtag (내용 없음)

    def handle_endtag(self, tag):
        if tag == "a":
            self._a = None
        elif tag == "nav":
            self._nav = None
        elif tag == "footer":
            self._in_foot = False

    def handle_data(self, data):
        if self._a is not None:
            self._a["text"].append(data)


def link_text(rec):
    return " ".join("".join(rec["text"]).split())


def html_files():
    out = []
    for dirpath, dirnames, filenames in os.walk(str(ROOT)):
        relp = Path(dirpath).relative_to(ROOT)
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and not (relp == Path(".") and d in SKIP_DIRS))
        for f in sorted(filenames):
            if f.endswith(".html"):
                out.append(Path(dirpath) / f)
    return out


def exists_exact(rel_posix):
    """ROOT 기준 경로가 대소문자까지 정확히 존재하면 ('file'|'dir'), 아니면 None."""
    cur = ROOT
    for part in [p for p in rel_posix.split("/") if p]:
        try:
            names = os.listdir(str(cur))
        except OSError:
            return None
        if part not in names:
            return None
        cur = cur / part
    return "dir" if cur.is_dir() else "file"


def resolve(page_rel_dir, url, own_hosts):
    """링크 → (검사할 ROOT 기준 경로 | None=검사 안 함, 사유 | None)."""
    if not url or url.startswith("#"):
        return None, None
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme in ("http", "https") or url.startswith("//"):
        if parts.netloc.lower() not in own_hosts:
            return None, None  # 외부 사이트
        path = parts.path or "/"
    elif scheme:
        return None, None  # data:, mailto:, tel:, javascript:, intent: …
    else:
        path = parts.path
        if not path:
            return None, None  # '?x=1'처럼 같은 페이지
    path = unquote(path)
    if path.startswith("/"):
        target = posixpath.normpath(path.lstrip("/") or ".")
    else:
        target = posixpath.normpath(posixpath.join(page_rel_dir, path))
    if target == ".." or target.startswith("../"):
        return "", "사이트 폴더 밖을 가리켜요"
    if target == ".":
        target = ""
    return target, None


def check_target(target, trailing_slash):
    kind = exists_exact(target) if target else "dir"
    if kind == "file" and not trailing_slash:
        return True
    if kind == "dir":
        return exists_exact((target + "/" if target else "") + "index.html") == "file"
    return False


def page_of(target):
    """링크 대상 경로 → 실제로 열리는 .html (폴더면 그 안 index.html)."""
    kind = exists_exact(target) if target else "dir"
    if kind == "dir":
        return (target + "/" if target else "") + "index.html"
    return target


# ── 공통 크롬 ─────────────────────────────────────────────

def fmt(items):
    return "[" + ", ".join(map(str, items)) + "]" if items else "(없음)"


def expected_current(src_rel):
    for key, label in CURRENT_FOR:
        if src_rel == key or (key.endswith("/") and src_rel.startswith(key)):
            return label
    return None


def chrome_problems(src_rel, page_dir, parser, text, own_hosts):
    """[(줄, 문제)] — 상단 내비·푸터 2번째 줄·(손 페이지) adsense:head 마커와 광고·문의 마커 계약."""
    probs = []

    def dest(rec):
        target, _ = resolve(page_dir, rec["href"] or "", own_hosts)
        return page_of(target) if target is not None else rec["href"]

    want_names = [n for n, _ in NAV_LINKS]
    if len(parser.navs) != 1:
        probs.append((None, "상단 내비(<nav class=\"topbar-right topbar-nav\">) 개수가 1이 아니에요 (지금 {}개)".format(len(parser.navs))))
    else:
        nav = parser.navs[0]
        names = [link_text(r) for r in nav["links"]]
        if names != want_names:
            probs.append((nav["line"], "상단 내비 항목이 계약과 달라요 — 지금 {}, 계약 {}".format(fmt(names), fmt(want_names))))
        else:
            got = [dest(r) for r in nav["links"]]
            want = [p for _, p in NAV_LINKS]
            if got != want:
                probs.append((nav["line"], "상단 내비 링크 주소가 계약과 달라요 — 지금 {}, 계약 {}".format(fmt(got), fmt(want))))
        if nav["label"] != NAV_LABEL:
            probs.append((nav["line"], "상단 내비에 aria-label=\"{}\"가 없어요".format(NAV_LABEL)))
        if nav["others"]:
            probs.append((nav["line"], "상단 내비 안에 링크 말고 다른 요소({})도 있어요 — 내비는 링크 3개만 둬요(설정은 내 차 카드·푸터로)".format(
                ", ".join("<{}>".format(t) for t in sorted(set(nav["others"]))))))
        cur = [link_text(r) for r in nav["links"] if r["current"] is not None]
        bad_value = [r["current"] for r in nav["links"] if r["current"] not in (None, "page")]
        exp = expected_current(src_rel)
        if bad_value:
            probs.append((nav["line"], "aria-current 값은 \"page\"만 써요 (지금: {})".format(", ".join(bad_value))))
        elif cur != ([exp] if exp else []):
            want_cur = "'{}' 하나".format(exp) if exp else "없음(내비 3곳 밖의 페이지)"
            probs.append((nav["line"], "현재 위치 표시(aria-current=\"page\")가 계약과 달라요 — 지금 {}, 계약 {}".format(fmt(cur), want_cur)))

    want_foot = [n for n, _ in FOOT_LINKS]
    foot = parser.foot
    if foot is None:
        probs.append((None, "푸터(<footer class=\"foot\">)가 없어요"))
    elif len(foot["lines"]) < 2:
        probs.append((foot["line"], "푸터 2번째 줄(소개·문의 · 개인정보처리방침 · 이용약관)이 없어요"))
    else:
        recs = foot["lines"][1]
        names = [link_text(r) for r in recs]
        if names != want_foot:
            probs.append((foot["p_lines"][1], "푸터 2번째 줄 링크가 계약과 달라요 — 지금 {}, 계약 {}".format(fmt(names), fmt(want_foot))))
        else:
            got = [dest(r) for r in recs]
            want = [p for _, p in FOOT_LINKS]
            if got != want:
                probs.append((foot["p_lines"][1], "푸터 2번째 줄 링크 주소가 계약과 달라요 — 지금 {}, 계약 {}".format(fmt(got), fmt(want))))

    if "/" not in src_rel:  # 손 페이지(루트)
        m = HEAD_RE.search(text)
        head = m.group(1) if m else ""
        line = text.count("\n", 0, m.start()) + 1 if m else None
        o, c = head.count(HEAD_OPEN), head.count(HEAD_CLOSE)
        if o == 0 or c == 0:
            probs.append((line, "head 안에 광고 마커(애드센스 소유 확인 메타 자리)가 없어요 — {}".format(HEAD_OPEN + HEAD_CLOSE)))
        elif o > 1 or c > 1 or head.find(HEAD_CLOSE) < head.find(HEAD_OPEN):
            probs.append((line, "head의 광고 마커가 두 번 있거나 순서가 뒤바뀌었어요 — 여는·닫는 마커를 한 번씩만 써요"))
        probs += hand_marker_problems(src_rel, text)
    return probs


def hand_marker_problems(src_rel, text):
    """[(줄, 문제)] — 손 페이지 광고·문의 마커가 계약(HAND_MARKERS)대로 정확히 한 번씩 있는지, 계약에 없는 마커는 없는지.
    문제 문구에는 페이지 이름을 넣지 않는다 — 같은 문제를 가진 페이지끼리 묶여 보이게."""
    def line_of(pos):
        return text.count("\n", 0, pos) + 1

    probs = []
    want = HAND_MARKERS.get(src_rel, ())
    for o, c in want:
        n = text.count(o)
        if n == 0:
            probs.append((None, "광고·문의 마커 {}가 없어요 — 계약상 이 페이지에 정확히 한 번 있어야 해요 "
                                "(지웠거나 이름에 오타가 나면 빌드가 그 자리를 조용히 비워 광고·이메일이 안 나와요)".format(o + c)))
        elif n > 1:
            probs.append((line_of(text.find(o)), "광고·문의 마커 {}가 {}번 있어요 — 한 번만 둬요".format(o, n)))
    allowed = {o for o, _ in want}
    for m in BODY_MARKER_RE.finditer(text):
        if m.group(0) not in allowed:
            if src_rel in HAND_MARKERS:
                why = "이 페이지에 둘 마커는 {}뿐이에요".format(", ".join(o for o, _ in want))
            else:
                why = "이 페이지에는 광고·문의 마커를 두지 않아요"
            probs.append((line_of(m.start()), "계약에 없는 마커 {}가 있어요 — {} (이름 오타인지, 광고를 두지 않는 페이지인지 보세요)".format(
                m.group(0), why)))
    return probs


def main():
    site = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
    base = (site.get("baseUrl") or "").rstrip("/")
    host = urlsplit(base).netloc.lower() if base else ""
    own_hosts = {host, "www." + host} if host else set()

    broken = []  # (파일, 줄, 링크, 사유)
    counts = {"links": 0, "anchors": 0}
    pages = html_files()
    parsed = {}  # 상대경로 → (원문, PageParser)
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        p = PageParser()
        p.feed(text)
        p.close()
        parsed[page.relative_to(ROOT).as_posix()] = (text, p)
    id_cache = {}

    def ids_of(rel):
        if rel in parsed:
            return parsed[rel][1].ids
        if rel not in id_cache:
            p = PageParser()
            p.feed((ROOT / rel).read_text(encoding="utf-8", errors="replace"))
            id_cache[rel] = p.ids
        return id_cache[rel]

    def check_anchor(src_rel, line, url, page, frag):
        frag = unquote(frag)
        if not frag or frag.startswith(":~:") or not page.endswith(".html") or page in SPA_PAGES:
            return
        counts["anchors"] += 1
        if frag not in ids_of(page):
            broken.append((src_rel, line, url, "{} 안에 id=\"{}\"인 요소가 없어요 — 링크를 누르면 페이지 맨 위가 열려요".format(page, frag)))

    def check(src_rel, line, url, page_dir):
        target, why = resolve(page_dir, url, own_hosts)
        if target is None:
            if url.startswith("#"):  # 같은 페이지 안 앵커(브랜드 칩 등)
                check_anchor(src_rel, line, url, src_rel, url[1:])
            return
        counts["links"] += 1
        if why:
            broken.append((src_rel, line, url, why))
            return
        trailing = urlsplit(url).path.endswith("/")
        if not check_target(target, trailing):
            hint = "{} 파일이 없어요".format(target or "index.html")
            if _exists_ci(target):
                hint += " (대소문자만 다른 파일은 있어요 — GitHub Pages는 대소문자를 구분해요)"
            broken.append((src_rel, line, url, hint))
            return
        frag = urlsplit(url).fragment
        if frag:
            check_anchor(src_rel, line, url, page_of(target), frag)

    for src_rel, (text, p) in parsed.items():
        page_dir = posixpath.dirname(src_rel)
        seen = set()
        for line, url in p.links:
            seen.add(url)
            check(src_rel, line, url, page_dir)
        if base:  # JSON-LD·인라인 스크립트 속 우리 도메인 절대 주소
            for m in re.finditer(re.escape(base) + r"(/[^\s\"'<>\\)]*)?", text):
                if m.group(0) not in seen:
                    seen.add(m.group(0))
                    check(src_rel, text.count("\n", 0, m.start()) + 1, m.group(0), page_dir)

    for name in ("sitemap.xml", "robots.txt"):
        f = ROOT / name
        if f.exists() and base:
            text = f.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(re.escape(base) + r"(/[^\s\"'<>]*)?", text):
                check(name, text.count("\n", 0, m.start()) + 1, m.group(0), "")

    manifest = ROOT / "manifest.webmanifest"
    if manifest.exists():
        mf = json.loads(manifest.read_text(encoding="utf-8"))
        for icon in mf.get("icons", []):
            if icon.get("src"):
                check("manifest.webmanifest", None, icon["src"], "")

    print("검사: HTML {}개 페이지 + sitemap.xml·robots.txt·manifest.webmanifest, 내부 링크 {:,}개 · #앵커 {:,}개".format(
        len(pages), counts["links"], counts["anchors"]))
    links_ok = report_links(broken)
    chrome_ok = check_chrome(parsed, own_hosts)
    return 0 if links_ok and chrome_ok else 1


def report_links(broken):
    if not broken:
        print("결과: 깨진 링크·없는 #id 없음 — 통과")
        return True
    print("결과: 깨진 링크·없는 #id {}개 — 실패".format(len(broken)))
    for src_rel, line, url, why in broken[:SHOW_MAX]:
        where = "{}:{}".format(src_rel, line) if line else src_rel
        print("  {}  →  {}".format(where, url))
        print("      {}".format(why))
        annotate("error", "깨진 링크 {} — {}".format(url, why), file=src_rel, line=line, title="깨진 링크")
    if len(broken) > SHOW_MAX:
        print("  … 외 {}개".format(len(broken) - SHOW_MAX))
    print("")
    print("고치는 법:")
    print("  - tax/ 안의 페이지라면 손으로 고치지 말고 scripts/build.py의 템플릿을 고친 뒤 python3 scripts/build.py 를 돌리세요.")
    print("    차종을 빼거나 slug를 바꿔 빌드가 더 이상 만들지 않는 페이지(썸네일이 없어 og:image가 깨짐)는 build.py가 지워 줘요")
    print("    — 돌린 뒤 지워진 파일까지 같이 커밋하세요: git add tax og icons favicon.ico robots.txt sitemap.xml")
    print("  - 직접 쓴 페이지(index.html·tco.html 등)라면 링크 주소의 파일 이름·폴더(../)·대소문자를 확인하세요.")
    print("  - '#id인 요소가 없어요'는 그 페이지에 id가 없거나 이름이 바뀐 거예요. 허브(tax/index.html)의 브랜드·모델 id는")
    print("    build.py가 slug로 만들어요 — 링크를 만드는 쪽과 id를 만드는 쪽을 같은 함수로 맞추세요.")
    print("  - 파일을 지우거나 이름을 바꿨다면 그 파일을 가리키는 링크도 같이 고치세요.")
    print("  - 다시 확인: python3 scripts/check_links.py")
    return False


def check_chrome(parsed, own_hosts):
    """공통 크롬(상단 내비·푸터 2번째 줄·손 페이지 광고 마커). 통과 여부를 돌려준다."""
    targets = [(rel, tp) for rel, tp in parsed.items()
               if posixpath.dirname(rel) in CHROME_DIRS and not VERIFY_FILE.match(posixpath.basename(rel))]
    hand = [rel for rel, _ in targets if "/" not in rel]
    groups = {}  # 문제 → [(페이지, 줄)]
    for rel, (text, p) in targets:
        for line, msg in chrome_problems(rel, posixpath.dirname(rel), p, text, own_hosts):
            groups.setdefault(msg, []).append((rel, line))
    enforced = exists_exact(CONTRACT_PAGE) == "file"
    print("")
    print("공통 크롬: 페이지 {}개(루트 {} + tax/ {})의 상단 내비·푸터 + 손 페이지 {}개의 광고·문의 마커".format(
        len(targets), len(hand), len(targets) - len(hand), len(hand)))
    if not groups:
        print("결과: 계약 마크업과 모두 같아요 — 통과")
        return True
    n_pages = len({rel for items in groups.values() for rel, _ in items})
    if enforced:
        print("결과: 계약과 다른 페이지 {}개 — 실패".format(n_pages))
    else:
        print("참고: 계약과 다른 페이지 {}개 — 소개·문의 페이지({})가 아직 없어 공통 크롬 도입 전으로 보고".format(
            n_pages, CONTRACT_PAGE))
        print("      경고만 해요(통과). 그 페이지가 생기면 아래가 오류가 돼요.")
    for msg, items in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:SHOW_MAX]:
        print("  [{}쪽] {}".format(len(items), msg))
        names = ["{}:{}".format(rel, line) if line else rel for rel, line in items[:SHOW_PAGES]]
        print("      " + ", ".join(names) + (" … 외 {}쪽".format(len(items) - SHOW_PAGES) if len(items) > SHOW_PAGES else ""))
        rel, line = items[0]
        annotate("error" if enforced else "warning", "{} ({}쪽)".format(msg, len(items)), file=rel, line=line,
                 title="공통 크롬 불일치")
    if not enforced:
        return True
    print("")
    print("고치는 법:")
    print("  - tax/ 페이지는 scripts/build.py의 page()·topbar_nav()·footer_links()를 고친 뒤 python3 scripts/build.py.")
    print("  - 손 페이지(index.html·tco.html·privacy.html·terms.html·about.html)는 아래 계약 마크업을 그대로 쓰세요")
    print("    (tax/ 안에서는 경로 앞에 ../):")
    for label, markup in CONTRACT_MARKUP:
        print("    {}:".format(label))
        print("      " + markup)
    print("  - 현재 위치 aria-current=\"page\": 수첩 화면은 '수첩', tax/ 페이지는 '자동차세', tco.html은 '유지비 비교'에만.")
    print("  - 광고·문의 마커는 위에 적힌 페이지에만 정확히 한 번 둬요(tco.html은 </main> 바로 앞, 나머지는 문의 문단).")
    print("    수첩·소개·개인정보처리방침·이용약관에는 광고 자리를 두지 않아요. 광고 자리를 늘리려면 privacy.html 4절의")
    print("    '광고가 게재되는 페이지' 문구, 이 파일의 HAND_MARKERS, scripts/validate_data.py HAND_SLOT_WHERE를 함께 고쳐요.")
    print("  - 다시 확인: python3 scripts/check_links.py")
    return False


def _exists_ci(target):
    """대소문자 무시하고는 존재하는지 (안내용)."""
    cur = ROOT
    for part in [p for p in target.split("/") if p]:
        try:
            names = {n.lower(): n for n in os.listdir(str(cur))}
        except OSError:
            return False
        if part.lower() not in names:
            return False
        cur = cur / names[part.lower()]
    return True


if __name__ == "__main__":
    sys.exit(main())
