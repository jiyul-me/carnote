#!/usr/bin/env python3
"""차일지 — 커밋 전 검사 한 번에 돌리기 (깃허브 CI가 보는 것과 같은 검사).

사용법:
  python3 scripts/check.py              전부
  python3 scripts/check.py build        하나만 (data · tests · parity · build · links 중 골라 여러 개도 가능)

  data    data/*.json 실수 (scripts/validate_data.py)
  tests   JS 로직 테스트 (tests/run.js — node가 없으면 macOS jsc로, 둘 다 없으면 건너뜀)
  parity  세액 계산 일치: build.py ↔ js/tax-calc.js (scripts/check_tax_parity.py)
  build   빌드 결과 최신 여부: 지금 data로 빌드하면 커밋된 tax/·og/·icons/와 똑같이 나오나
  links   깨진 링크 (scripts/check_links.py)

빌드 검사는 저장소를 임시 폴더에 복사해 거기서 build.py를 돌리고 비교한다 —
작업 중인 파일(tax/·og/ 포함)은 절대 건드리지 않는다. sitemap.xml은 lastmod가 매일 바뀌어서 비교에서 뺀다.
Python 3.9 호환 (사용자 Mac 기본 python3).
"""
import datetime
import difflib
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checklib import (ROOT, NO_JS_RUNTIME_HELP, annotate, find_js_runtime, heading, in_ci,  # noqa: E402
                      jsc_load_list)

PASS, FAIL, SKIP = "통과", "실패", "건너뜀"

# build.py가 쓰는 생성물. sitemap.xml은 날짜(lastmod)만 매일 바뀌므로 비교 제외 — 복사는 한다
GEN_DIRS = ("tax", "og", "icons")
GEN_FILES = ("favicon.ico", "robots.txt")
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


def _gen_files(root):
    """생성물 경로의 파일 목록 {상대경로: 절대경로}."""
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
    return out


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


def _uncommitted_generated():
    """생성물 중 git에 아직 안 올라간(수정·새 파일) 것. git이 없으면 None."""
    if not (ROOT / ".git").exists() or not shutil.which("git"):
        return None
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all", "--"] + list(GEN_DIRS) + list(GEN_FILES),
            cwd=str(ROOT), stderr=subprocess.DEVNULL, encoding="utf-8")
    except (subprocess.CalledProcessError, OSError):
        return None
    return [ln[3:] for ln in out.splitlines() if ln.strip()]


def check_build():
    tmp = Path(tempfile.mkdtemp(prefix="chailji-build-"))
    try:
        # 1) 지금 작업 폴더 그대로(커밋 안 한 data 변경 포함) 임시 폴더에 복사
        for name in BUILD_INPUTS + GEN_DIRS + GEN_FILES + ("sitemap.xml",):
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

        # 3) 비교 (sitemap.xml 제외)
        now, built = _gen_files(ROOT), _gen_files(tmp)
        changed = sorted(r for r in now.keys() & built.keys() if not filecmp.cmp(str(now[r]), str(built[r]), shallow=False))
        added = sorted(built.keys() - now.keys())
        removed = sorted(now.keys() - built.keys())
        if not (changed or added or removed):
            print("결과: 지금 data/*.json·build.py로 빌드한 결과가 tax/·og/·icons/ 등과 똑같아요 — 통과")
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
        print("")
        print("고치는 법:")
        print("  data/*.json이나 build.py를 바꾼 뒤 python3 scripts/build.py를 돌리고 결과를 같이 커밋하세요.")
        print("    python3 scripts/build.py")
        print("    git add tax og icons favicon.ico robots.txt sitemap.xml")
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
    ("build", "빌드 결과 최신 여부 (tax/·og/·icons/)"),
    ("links", "깨진 링크"),
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
