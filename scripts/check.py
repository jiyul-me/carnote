#!/usr/bin/env python3
"""차일지 — 커밋 전 검사 한 번에 돌리기 (깃허브 CI가 보는 것과 같은 검사).

사용법:
  python3 scripts/check.py              전부
  python3 scripts/check.py build        하나만 (data · tests · parity · build · links 중 골라 여러 개도 가능)

  data    data/*.json 실수 (scripts/validate_data.py)
  tests   JS 로직 테스트 (tests/run.js — node가 없으면 macOS jsc로, 둘 다 없으면 건너뜀)
  parity  세액 계산 일치: build.py ↔ js/tax-calc.js (scripts/check_tax_parity.py)
  build   빌드 결과 최신 여부: 지금 data로 빌드하면 커밋된 tax/·og/·icons/·sitemap.xml·ads.txt와
          손으로 쓴 루트 페이지(index.html·tco.html·privacy.html 등)의 광고·문의 마커 구간이 똑같이 나오나
          (빌드가 더 이상 만들지 않는 tax/ 페이지·썸네일이 남아 있어도 '지워짐'으로 잡는다)
          + 광고를 두지 않는 페이지(수첩 index.html·소개 about.html·개인정보처리방침 privacy.html·
            이용약관 terms.html)에 광고 슬롯 마커·광고 코드가 없나
  links   링크·앵커·공통 크롬 (scripts/check_links.py — 깨진 링크, #id, 상단 내비·푸터,
          손 페이지마다 있어야 할 광고·문의 마커)

빌드 검사는 저장소를 임시 폴더에 복사해 거기서 build.py를 돌리고 비교한다 —
data/site.json의 adsense·contactEmail만 바꾸고 빌드를 안 돌린 상태(ads.txt·손 페이지 마커가 낡음)도 여기서 잡힌다.
작업 중인 파일(tax/·og/ 포함)은 절대 건드리지 않는다. sitemap.xml은 <lastmod> 날짜가 빌드한 날로
매일 바뀌므로 그 날짜만 지우고 비교한다 — 주소 목록(차종 추가·삭제 반영)은 그대로 비교된다.
Python 3.9 호환 (사용자 Mac 기본 python3).
"""
import datetime
import difflib
import filecmp
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checklib import (ROOT, NO_JS_RUNTIME_HELP, annotate, find_js_runtime, heading, in_ci,  # noqa: E402
                      jsc_load_list)

PASS, FAIL, SKIP = "통과", "실패", "건너뜀"

# build.py가 쓰는 생성물. build.py가 og/tax/*.png·tax/*.html 중 더 이상 안 만드는 것을 지우므로
# 지금 것을 복사해 둔 위에 빌드하면 남은 옛 파일이 '지워짐'으로 드러난다
GEN_DIRS = ("tax", "og", "icons")
# ads.txt는 site.json adsense.publisherId가 있을 때만 생긴다(비면 빌드가 지움) — 양쪽에 다 없으면 같다
GEN_FILES = ("favicon.ico", "robots.txt", "sitemap.xml", "ads.txt")
ADS_TXT = "ads.txt"
# 손으로 쓰는 루트 페이지(index·tco·privacy·terms·about …). build.py는 그 안의 마커 구간
# (<!-- adsense:head -->·<!-- adsense:slot 이름 -->·<!-- site:contact -->)만 site.json 값으로 채운다.
# build.py가 루트 *.html 전부를 훑으므로 같은 범위를 복사해 비교한다 — 값이 비어 있고 마커가 빈 형태면
# 빌드해도 한 글자도 안 바뀌어 그대로 통과한다(마커 바깥을 손으로 고친 것은 비교에 영향 없음)
HAND_PAGE_GLOB = "*.html"
# 광고를 두지 않는 손 페이지 — 광고 슬롯 마커·광고 코드 금지. (파일, 이름)
#  수첩: 입력·설정 화면 광고 금지 정책 (README '수첩에 광고를 넣지 않는 이유')
#  소개·개인정보처리방침·이용약관: privacy.html 4절·about.html의 약속('…페이지에도 광고를 두지 않습니다')
# 광고를 둘 수 있는 페이지를 늘리려면 privacy.html 4절 문구부터 고친다
NOTEBOOK_PAGE = "index.html"
NO_AD_PAGES = ((NOTEBOOK_PAGE, "수첩 화면"), ("about.html", "소개"), ("privacy.html", "개인정보처리방침"),
               ("terms.html", "이용약관"))
NO_AD_SIGNS = ("adsense:slot", "adsbygoogle")
# sitemap.xml은 <lastmod>에 빌드한 날짜가 들어가 매일 바뀐다 — 그 날짜만 지우고 비교
SITEMAP = "sitemap.xml"
SITEMAP_LASTMOD = re.compile(r"<lastmod>[^<]*</lastmod>")
SITEMAP_LOC = re.compile(r"<loc>([^<]*)</loc>")
# 빌드에 필요한 입력 (임시 복사본에 넣을 것)
BUILD_INPUTS = ("scripts", "data")
IGNORE_NAMES = (".DS_Store", "__pycache__")
SHOW_MAX = 10


def run(cmd):
    """출력을 그대로 흘려 보여 주고 종료 코드만 돌려준다."""
    sys.stdout.flush()
    return subprocess.call(cmd, cwd=str(ROOT))


# ── 1. 데이터 ────────────────────────────────────────────

def check_data():
    return PASS if run([sys.executable, "scripts/validate_data.py"]) == 0 else FAIL


# ── 2. JS 테스트 ─────────────────────────────────────────

def check_tests(js):
    kind, exe = js
    if kind == "node":
        return PASS if run([exe, "tests/run.js"]) == 0 else FAIL
    if kind == "jsc":
        print("node가 없어 macOS jsc로 돌려요 ({})".format(exe))
        failed = []
        for t in sorted((ROOT / "tests").glob("*.test.js")):
            rel = "tests/" + t.name
            files = jsc_load_list(t)
            print("· " + rel)
            if not files:
                print("  실패 — 첫 줄에 '/* jsc 실행: jsc js/대상.js {} */' 주석이 없어요.".format(rel))
                failed.append(rel)
                continue
            if run([exe] + files) != 0:
                failed.append(rel)
        if failed:
            print("JS 테스트 실패: " + ", ".join(failed))
            print("고치는 법: 위 'FAIL' 줄의 기대값·실제값을 보고 js/ 코드나 테스트 기대값을 고치세요.")
            return FAIL
        print("JS 테스트 모두 통과")
        return PASS
    print("JS 테스트를 건너뛰었어요.")
    print(NO_JS_RUNTIME_HELP)
    if in_ci():
        print("CI에서는 건너뛸 수 없어요 → 워크플로에 actions/setup-node 단계가 있는지 확인하세요.")
        return FAIL
    return SKIP


# ── 3. 세액 일치 ─────────────────────────────────────────

def check_parity(js):
    if not js[0]:
        print("세액 일치 검사를 건너뛰었어요 — node·jsc가 없어요 (깃허브 CI에서는 돌아가요).")
        return FAIL if in_ci() else SKIP
    return PASS if run([sys.executable, "scripts/check_tax_parity.py"]) == 0 else FAIL


# ── 4. 빌드 결과 최신 여부 ────────────────────────────────

def _copy_tree(src, dst):
    if src.is_dir():
        shutil.copytree(str(src), str(dst), ignore=shutil.ignore_patterns(*IGNORE_NAMES))
    elif src.is_file():
        shutil.copy2(str(src), str(dst))


def _hand_pages(root):
    """루트의 손 페이지 {이름: 경로} — build.py가 마커를 채우는 범위(루트 *.html)."""
    return {p.name: p for p in sorted(root.glob(HAND_PAGE_GLOB)) if p.is_file()}


def _gen_files(root):
    """생성물 경로의 파일 목록 {상대경로: 절대경로} — 손 페이지(마커 구간을 빌드가 채움)도 포함."""
    out = {}
    for d in GEN_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(str(base)):
            dirnames[:] = [n for n in dirnames if n not in IGNORE_NAMES]
            for f in filenames:
                if f in IGNORE_NAMES:
                    continue
                p = Path(dirpath) / f
                out[p.relative_to(root).as_posix()] = p
    for f in GEN_FILES:
        if (root / f).is_file():
            out[f] = root / f
    out.update(_hand_pages(root))
    return out


def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _sitemap_norm(text):
    """sitemap.xml에서 날짜(<lastmod> 값)만 지운 내용 — 주소 목록·순서·형식은 그대로 남는다."""
    return SITEMAP_LASTMOD.sub("<lastmod></lastmod>", text)


def _same(rel, a, b):
    """생성물 하나가 같은가. sitemap.xml은 날짜만 다르면 같다고 본다."""
    if rel == SITEMAP:
        ta, tb = _read_text(a), _read_text(b)
        if ta is not None and tb is not None:
            return _sitemap_norm(ta) == _sitemap_norm(tb)
    return filecmp.cmp(str(a), str(b), shallow=False)


def _sitemap_diff(old, new):
    """sitemap.xml 주소 목록 차이 — 한 줄짜리 XML이라 줄 단위 diff로는 안 보여서 주소로 비교한다."""
    a = SITEMAP_LOC.findall(_read_text(old) or "")
    b = SITEMAP_LOC.findall(_read_text(new) or "")
    in_a, in_b = set(a), set(b)
    lines = []
    for label, urls in (("빠져 있는 주소 (빌드하면 들어가요)", [u for u in b if u not in in_a]),
                        ("남아 있는 옛 주소 (빌드하면 빠져요)", [u for u in a if u not in in_b])):
        if not urls:
            continue
        lines.append("{} {}개:".format(label, len(urls)))
        lines += ["  " + u for u in urls[:5]]
        if len(urls) > 5:
            lines.append("  … 외 {}개".format(len(urls) - 5))
    return lines or ["주소 목록은 같고 순서·형식만 달라요"]


def _text_diff(old, new, rel):
    """바뀐 텍스트 파일의 앞부분 몇 줄 (무엇이 바뀌는지 감 잡기용)."""
    try:
        a = old.read_text(encoding="utf-8").splitlines()
        b = new.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return []
    lines = [ln for ln in difflib.unified_diff(a, b, "지금 " + rel, "빌드하면 " + rel, n=0, lineterm="")
             if not ln.startswith("@@")]
    return [ln[:160] + ("…" if len(ln) > 160 else "") for ln in lines[:8]]


def _sitemap_date_only_changed():
    """작업 폴더의 sitemap.xml이 커밋된 것과 날짜(lastmod)만 다른가 — 그렇다면 커밋 안 해도 CI는 통과한다."""
    try:
        head = subprocess.check_output(["git", "show", "HEAD:" + SITEMAP], cwd=str(ROOT), stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, OSError):
        return False
    cur = _read_text(ROOT / SITEMAP)
    return cur is not None and _sitemap_norm(head.decode("utf-8", "replace")) == _sitemap_norm(cur)


def _uncommitted_generated():
    """생성물 중 git에 아직 안 올라간(수정·새 파일·삭제) 것. git이 없으면 None.
    sitemap.xml은 날짜(lastmod)만 바뀐 경우 빼고 센다."""
    if not (ROOT / ".git").exists() or not shutil.which("git"):
        return None
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all", "--"] + list(GEN_DIRS) + list(GEN_FILES),
            cwd=str(ROOT), stderr=subprocess.DEVNULL, encoding="utf-8")
    except (subprocess.CalledProcessError, OSError):
        return None
    paths = [ln[3:] for ln in out.splitlines() if ln.strip()]
    return [r for r in paths if not (r == SITEMAP and _sitemap_date_only_changed())]


def _list_order(rel):
    """목록 순서 — 루트 파일(ads.txt·손 페이지·sitemap.xml 등)을 먼저 보여 tax/ 수백 개에 묻히지 않게."""
    return ("/" in rel, rel)


def _git_tracked(rel):
    """git이 이 경로를 추적 중인가 (지워진 파일을 git add로 담을 수 있나). git이 없으면 True로 본다."""
    if not (ROOT / ".git").exists() or not shutil.which("git"):
        return True
    return subprocess.call(["git", "ls-files", "--error-unmatch", "--", rel], cwd=str(ROOT),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0


def _git_add_line(changed, added, removed):
    """빌드 뒤 커밋할 경로 — 늘 있는 생성물 + 이번에 바뀐 루트 파일(ads.txt·손 페이지).
    없는 경로를 넣으면 git add 전체가 실패하므로, 지워질 파일은 git이 추적 중일 때만 넣는다."""
    base = ["tax", "og", "icons", "favicon.ico", "robots.txt", "sitemap.xml"]
    extra = {r for r in changed + added if "/" not in r and r not in base}
    extra |= {r for r in removed if "/" not in r and r not in base and _git_tracked(r)}
    return "git add " + " ".join(base + sorted(extra))


def check_no_ad_pages():
    """광고를 두지 않는 페이지(NO_AD_PAGES)에 광고 슬롯 마커나 광고 코드(adsbygoogle)가 없는지. 소유 확인 메타 자리
    (<!-- adsense:head --> 마커)만 허용 — build.py는 index.html의 슬롯 마커만 오류로 멈추고 소개·방침·약관의 슬롯
    마커는 그대로 채우며, 손으로 넣은 광고 코드는 빌드가 모르므로 여기서 잡는다. 없는 파일은 건너뛴다.
    반환: 통과 여부."""
    found = []  # (파일, 이름, 줄, 표시, 원문 줄)
    checked = []
    for page, label in NO_AD_PAGES:
        text = _read_text(ROOT / page)
        if text is None:
            continue
        checked.append(page)
        found += [(page, label, i, sign, ln.strip()) for i, ln in enumerate(text.splitlines(), 1)
                  for sign in NO_AD_SIGNS if sign in ln]
    if not found:
        print("광고 없는 페이지({}): 광고 슬롯·광고 코드 없음 — 통과".format("·".join(checked) or "없음"))
        return True
    bad = [(page, label) for page, label in NO_AD_PAGES if any(f[0] == page for f in found)]
    print("광고를 두지 않는 페이지({})에 광고 슬롯 마커나 광고 코드가 있어요 — 실패".format(
        ", ".join("{} {}".format(label, page) for page, label in bad)))
    for page, label, line, sign, src in found[:SHOW_MAX]:
        print("  {}:{}  '{}'  {}".format(page, line, sign, src[:120] + ("…" if len(src) > 120 else "")))
        annotate("error", "{}에는 광고를 넣지 않아요 ('{}')".format(label, sign), file=page, line=line,
                 title="광고 금지 페이지")
    print("고치는 법: 그 페이지에서 광고 슬롯 마커 구간(<!-- adsense:slot 이름 -->…<!-- /adsense:slot -->)과 손으로 넣은")
    print("  광고 코드를 지우고 python3 scripts/build.py 를 돌리세요 — head 마커 안의 adsbygoogle.js는 빌드가 같이 빼요.")
    print("  이 페이지들에는 광고 자리를 두지 않고, head의 <!-- adsense:head --><!-- /adsense:head -->")
    print("  (애드센스 소유 확인 메타 자리)만 둬요 — head 마커는 지우지 마세요.")
    if any(page == NOTEBOOK_PAGE for page, _ in bad):
        print("  수첩(index.html): 입력·설정 화면 광고 금지 정책, 버튼·토스트 옆 실수 클릭, 화면 다시 그리기마다 광고 재요청")
        print("  — README '수첩에 광고를 넣지 않는 이유'.")
    if any(page != NOTEBOOK_PAGE for page, _ in bad):
        print("  소개·개인정보처리방침·이용약관: 개인정보처리방침 4절이 '소개·개인정보처리방침·이용약관 페이지에도 광고를 두지")
        print("  않습니다'라고 약속해요. 광고 자리는 차종별 자동차세·계산기·유지비 비교에만 둬요.")
    return False


def check_build():
    ads_ok = check_no_ad_pages()
    print("")
    return PASS if check_build_fresh() == PASS and ads_ok else FAIL


def check_build_fresh():
    tmp = Path(tempfile.mkdtemp(prefix="chailji-build-"))
    try:
        # 1) 지금 작업 폴더 그대로(커밋 안 한 data 변경 포함) 임시 폴더에 복사 — 손 페이지(루트 *.html)도
        for name in BUILD_INPUTS + GEN_DIRS + GEN_FILES + tuple(_hand_pages(ROOT)):
            _copy_tree(ROOT / name, tmp / name)
        # 2) 임시 폴더에서 빌드 — 작업 폴더의 파일은 건드리지 않는다
        sys.stdout.flush()
        proc = subprocess.run([sys.executable, "scripts/build.py"], cwd=str(tmp),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
        if proc.returncode != 0:
            print("빌드(scripts/build.py)가 오류로 멈췄어요:")
            print("\n".join(proc.stdout.strip().splitlines()[-25:]))
            print("")
            print("고치는 법: 마지막 줄의 오류(파일·줄 번호)를 보세요. data/*.json 값 때문이면")
            print("  python3 scripts/validate_data.py 가 더 쉬운 말로 알려 줘요.")
            annotate("error", "scripts/build.py 실행 실패", file="scripts/build.py", title="빌드 실패")
            return FAIL
        print("\n".join("  " + ln for ln in proc.stdout.strip().splitlines()))

        # 3) 비교 (sitemap.xml은 lastmod 날짜만 빼고). 빌드가 지운 옛 파일은 removed로 잡힌다
        now, built = _gen_files(ROOT), _gen_files(tmp)
        changed = sorted([r for r in now.keys() & built.keys() if not _same(r, now[r], built[r])], key=_list_order)
        added = sorted(built.keys() - now.keys(), key=_list_order)
        removed = sorted(now.keys() - built.keys(), key=_list_order)
        if not (changed or added or removed):
            print("결과: 지금 data/*.json·build.py로 빌드한 결과가 tax/·og/·icons/·sitemap.xml·ads.txt와 "
                  "손 페이지 마커 구간까지 똑같아요 — 통과")
            pending = _uncommitted_generated()
            if pending:
                print("참고: 생성물 중 아직 커밋하지 않은 파일이 {}개 있어요 (예: {}).".format(len(pending), pending[0]))
                print("      빌드 결과는 최신이니, 커밋할 때 이 파일들도 같이 넣어야 깃허브 CI가 통과해요.")
            return PASS

        print("")
        print("결과: 빌드 결과가 최신이 아니에요 — 실패 (바뀜 {}개 · 새로 생김 {}개 · 지워짐 {}개)".format(
            len(changed), len(added), len(removed)))
        for label, items in (("바뀜", changed), ("새로 생김", added), ("지워짐", removed)):
            for r in items[:SHOW_MAX]:
                print("  [{}] {}".format(label, r))
            if len(items) > SHOW_MAX:
                print("  … {} 외 {}개".format(label, len(items) - SHOW_MAX))
        first_text = next((r for r in changed if r.endswith((".html", ".txt"))), None)
        if first_text:
            print("  {} 에서 바뀌는 줄 (앞부분):".format(first_text))
            for ln in _text_diff(now[first_text], built[first_text], first_text):
                print("    " + ln)
        if SITEMAP in changed:
            print("  {} 차이:".format(SITEMAP))
            for ln in _sitemap_diff(now[SITEMAP], built[SITEMAP]):
                print("    " + ln)
        if [r for r in removed if r != ADS_TXT]:
            print("  [지워짐]은 빌드가 더 이상 만들지 않는 파일이에요 (차종 삭제·slug 변경·sample 전환 등).")
            print("  그대로 두면 목록에도 sitemap에도 없는 낡은 페이지가 계속 공개돼요.")
        if ADS_TXT in removed:
            print("  ads.txt [지워짐]: data/site.json adsense.publisherId가 비어 있어서예요. 광고를 끈 게 맞으면 빌드 후 커밋하고,")
            print("  아니면 publisherId에 게시자 ID('pub-'+16자리)를 넣으세요.")
        elif ADS_TXT in changed or ADS_TXT in added:
            print("  ads.txt [{}]: data/site.json adsense.publisherId가 바뀌었어요.".format("새로 생김" if ADS_TXT in added else "바뀜"))
        hand = sorted(r for r in changed if "/" not in r and r.endswith(".html"))
        if hand:
            print("  손 페이지 [바뀜] ({}): data/site.json의 adsense·contactEmail을 바꾸고 빌드를 안 돌렸어요.".format(", ".join(hand)))
            print("  빌드는 그 페이지의 마커 구간(<!-- adsense:head --> 등)만 채워요 — 마커 바깥은 그대로예요.")
        print("")
        print("고치는 법:")
        print("  data/*.json이나 build.py를 바꾼 뒤 python3 scripts/build.py를 돌리고 결과를 같이 커밋하세요.")
        if removed:
            print("  빌드가 [지워짐] 파일도 지워 주고, 아래 git add가 그 삭제까지 담아요.")
        print("    python3 scripts/build.py")
        print("    " + _git_add_line(changed, added, removed))
        print("  (git add -A 한 줄도 돼요 — 작업 중인 다른 파일까지 담기니 git status로 먼저 확인하세요)")
        print("  tax/ 파일을 손으로 고쳤다면 다음 빌드 때 사라져요 — scripts/build.py의 템플릿을 고치세요.")
        try:
            import PIL  # noqa: F401
        except ImportError:
            print("  이 컴퓨터에 Pillow가 없어 썸네일(og/)을 새로 못 그려요 → pip3 install --user pillow")
        today = datetime.date.today()
        print("참고: 1월 1일이 지나 연도(this_year)가 바뀌면 모든 차종 페이지의 연식표·썸네일 문구가 바뀌는 게 정상이에요.")
        print("      해가 바뀌면 빌드를 한 번 돌려 커밋하면 돼요." + (" (지금이 1월이라 그 경우일 수 있어요)" if today.month == 1 else ""))
        annotate("error", "빌드 결과가 최신이 아니에요. python3 scripts/build.py 를 돌리고 결과를 같이 커밋하세요.",
                 title="빌드 결과 최신 아님")
        return FAIL
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)


# ── 5. 링크 ──────────────────────────────────────────────

def check_links():
    return PASS if run([sys.executable, "scripts/check_links.py"]) == 0 else FAIL


CHECKS = (
    ("data", "데이터 검사 (data/*.json)"),
    ("tests", "JS 테스트 (tests/*.test.js)"),
    ("parity", "세액 계산 일치 (build.py ↔ js/tax-calc.js)"),
    ("build", "빌드 결과 최신 여부 (tax/·og/·sitemap.xml·ads.txt·손 페이지 마커) + 수첩·소개·방침·약관 광고 금지"),
    ("links", "링크·앵커·공통 크롬 (nav·푸터·광고·문의 마커)"),
)


def main(argv):
    names = [k for k, _ in CHECKS]
    wanted = argv or names
    unknown = [a for a in wanted if a not in names]
    if unknown:
        print("모르는 검사 이름: {} — 쓸 수 있는 이름: {}".format(", ".join(unknown), ", ".join(names)))
        return 2
    js = find_js_runtime()
    results = []
    for i, (key, label) in enumerate([c for c in CHECKS if c[0] in wanted], 1):
        heading("{}. {}".format(i, label))
        if key == "data":
            r = check_data()
        elif key == "tests":
            r = check_tests(js)
        elif key == "parity":
            r = check_parity(js)
        elif key == "build":
            r = check_build()
        else:
            r = check_links()
        results.append((label, r))

    if len(results) > 1:
        heading("요약")
        for label, r in results:
            print("  " + r + " " * (8 - 2 * len(r)) + label)  # 한글은 두 칸 폭 — 열 맞춤
    failed = [label for label, r in results if r == FAIL]
    print("")
    if failed:
        print("실패 {}개 — 위에서 '고치는 법'을 보고 고친 뒤 python3 scripts/check.py 를 다시 돌리세요.".format(len(failed)))
        return 1
    skipped = [label for label, r in results if r == SKIP]
    if skipped:
        print("모두 통과 (건너뜀 {}개 — 깃허브 CI에서는 전부 돌아가요)".format(len(skipped)))
    else:
        print("모두 통과 — 커밋해도 좋아요.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
