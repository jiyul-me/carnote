"""차일지 — 검사 스크립트 공용 도구 (check.py · validate_data.py · check_tax_parity.py · check_links.py).

- 사이트에 쓰이는 상수는 여기 두지 않는다. 경로·실행기 찾기·출력 형식만.
- Python 3.9에서도 돌아야 한다 (사용자 Mac 기본 python3). match문, X | Y 타입 표기 금지.
"""
import os
import re
import shutil
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# macOS에 기본으로 들어 있는 JavaScriptCore 셸. PATH에는 보통 없어서 직접 찾는다
JSC_CANDIDATES = (
    "/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc",
    "/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc",
    "/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Resources/jsc",
    "/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Resources/jsc",
)

# 테스트 파일 첫 줄 주석: /* jsc 실행: jsc js/x.js tests/x.test.js ...
# tests/run.js도 같은 규칙으로 읽는다 — '무엇을 로드해 실행하나'의 단일 출처는 테스트 파일 첫 줄
JSC_HEADER = re.compile(r"jsc 실행:\s*jsc\s+(.*)")


def in_ci():
    """깃허브 액션 등 CI에서 도는 중인가. CI에서는 '건너뜀'이 곧 검사 누락이라 실패로 다룬다."""
    return os.environ.get("CI", "").lower() in ("1", "true", "yes")


def in_github():
    return os.environ.get("GITHUB_ACTIONS") == "true"


def find_node():
    return shutil.which("node")


def find_jsc():
    found = shutil.which("jsc")
    if found:
        return found
    for cand in JSC_CANDIDATES:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def find_js_runtime():
    """('node'|'jsc', 경로). node를 먼저 찾고, 없으면 macOS jsc. 둘 다 없으면 (None, None)."""
    node = find_node()
    if node:
        return "node", node
    jsc = find_jsc()
    if jsc:
        return "jsc", jsc
    return None, None


NO_JS_RUNTIME_HELP = (
    "  node도 jsc(macOS 기본 JavaScriptCore)도 찾지 못했어요.\n"
    "  - node를 설치하면 이 컴퓨터에서도 돌아가요: https://nodejs.org (LTS 버전)\n"
    "  - 찾아본 jsc 위치: PATH, " + JSC_CANDIDATES[0] + " 외 " + str(len(JSC_CANDIDATES) - 1) + "곳\n"
    "  깃허브에 올리면 CI가 node로 이 검사를 대신 돌려요."
)


def jsc_load_list(test_path):
    """테스트 파일 첫 줄의 'jsc 실행: jsc a.js b.js'에서 로드할 파일 목록(저장소 기준 상대 경로).
    .js로 끝나지 않는 토큰(설명 괄호 등)이 나오면 거기서 멈춘다. 형식이 없으면 None."""
    with open(test_path, encoding="utf-8") as f:
        first = f.readline()
    m = JSC_HEADER.search(first)
    if not m:
        return None
    files = []
    for tok in m.group(1).split():
        if not tok.endswith(".js"):
            break
        files.append(tok)
    return files or None


def annotate(level, message, file=None, line=None, title=None):
    """깃허브 액션에서 돌 때만 PR 화면(Files changed)에 빨간 주석을 남긴다. 로컬에서는 아무것도 안 한다.
    level: 'error' | 'warning'"""
    if not in_github():
        return
    props = []
    if file:
        props.append("file=" + file)
    if line:
        props.append("line=" + str(line))
    if title:
        props.append("title=" + title.replace(",", " ").replace("::", ":"))
    msg = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print("::{} {}::{}".format(level, ",".join(props), msg))


def heading(text):
    """'── 1. 데이터 검사 ─────' 구분선. 한글은 터미널에서 두 칸 폭이라 그만큼 줄여 끝을 맞춘다."""
    width = sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)
    print("")
    print("── " + text + " " + "─" * max(4, 56 - width))
