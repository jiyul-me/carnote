#!/usr/bin/env python3
"""차일지 — 깨진 링크 검사.

저장소의 모든 .html(tests/ 제외)에서 href·src 링크를 찾아 실제 파일이 있는지 본다.
- 상대 링크(../tco.html), 루트 기준 링크(/tax/index.html), 우리 도메인 절대 링크(https://chailji.com/...)
  — 도메인은 data/site.json baseUrl에서 읽는다. 쿼리(?v=)·해시(#)는 떼고 본다.
- 외부 사이트, data:, mailto:, tel:, javascript:, '#'만 있는 링크는 건너뛴다.
- 대소문자까지 똑같아야 통과 — Mac에서는 Tax/Index.html도 열리지만 GitHub Pages에서는 404가 난다.
- sitemap.xml·robots.txt의 우리 도메인 주소, manifest.webmanifest의 아이콘 경로도 같이 본다.

사용법:  python3 scripts/check_links.py     깨진 링크가 있으면 exit 1.
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


class LinkParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.links = []  # (줄, 값)

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        for name, value in attrs:
            if name in LINK_ATTRS and value is not None:
                self.links.append((line, value.strip()))
            elif name == "content" and value and value.startswith(("http://", "https://")):
                self.links.append((line, value.strip()))  # og:image·og:url 같은 meta — 우리 도메인만 검사됨

    handle_startendtag = handle_starttag


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


def main():
    site = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
    base = (site.get("baseUrl") or "").rstrip("/")
    host = urlsplit(base).netloc.lower() if base else ""
    own_hosts = {host, "www." + host} if host else set()

    broken = []  # (파일, 줄, 링크, 사유)
    n_links = 0
    pages = html_files()

    def check(src_rel, line, url, page_dir):
        nonlocal n_links
        target, why = resolve(page_dir, url, own_hosts)
        if target is None:
            return
        n_links += 1
        if why:
            broken.append((src_rel, line, url, why))
            return
        trailing = urlsplit(url).path.endswith("/")
        if not check_target(target, trailing):
            hint = "{} 파일이 없어요".format(target or "index.html")
            if _exists_ci(target):
                hint += " (대소문자만 다른 파일은 있어요 — GitHub Pages는 대소문자를 구분해요)"
            broken.append((src_rel, line, url, hint))

    for page in pages:
        src_rel = page.relative_to(ROOT).as_posix()
        page_dir = posixpath.dirname(src_rel)
        text = page.read_text(encoding="utf-8", errors="replace")
        p = LinkParser()
        p.feed(text)
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

    print("검사: HTML {}개 페이지 + sitemap.xml·robots.txt·manifest.webmanifest, 내부 링크 {:,}개".format(len(pages), n_links))
    if not broken:
        print("결과: 깨진 링크 없음 — 통과")
        return 0

    print("결과: 깨진 링크 {}개 — 실패".format(len(broken)))
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
    print("  - 직접 쓴 페이지(index.html·tco.html 등)라면 링크 주소의 파일 이름·폴더(../)·대소문자를 확인하세요.")
    print("  - 파일을 지우거나 이름을 바꿨다면 그 파일을 가리키는 링크도 같이 고치세요.")
    print("  - 다시 확인: python3 scripts/check_links.py")
    return 1


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
