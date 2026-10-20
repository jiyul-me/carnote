"""차 관리 가이드 글 하나를 빌드 없이 그려 보고 기본 규칙을 검사한다 (글 쓰는 동안 쓰는 도구).

사용법:  python3 scripts/render_care.py engine-oil          글 텍스트 미리보기 + 검사
         python3 scripts/render_care.py engine-oil --html   본문 HTML 그대로
ORDER에 없는 글도 그릴 수 있다(쓰는 중인 글). 전체 사이트에 반영하려면 ORDER에 넣고 python3 scripts/build.py.
검사: 필수 키, 출처(https), FAQ 개수, 상대 링크가 실제 파일을 가리키는지, 해요체, 금지어(TODO 등).
Python 3.9 호환.
"""
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build as B  # noqa: E402
import care_guides  # noqa: E402

ROOT = HERE.parent
KEYS = ("h1", "title", "description", "lede", "summary", "body", "faqs", "sources")
GUIDE_KEYS = ("slug", "short", "published", "updated", "og_title", "og_lede", "summary")


def setup():
    site, rates = B.load("site.json"), B.load("tax-rates.json")
    B.prepay_windows(rates)
    vs = [v for v in B.load("vehicles.json")["vehicles"] if v["status"] == "active"]

    def buildable(v):
        cls = v.get("vehicleClass", "passenger")
        if cls == "truck":
            return bool(v.get("payloadKg"))
        if cls == "van":
            return bool(v.get("vanSize"))
        return v["fuelType"] == "ev" or bool(v["displacementCc"])

    import datetime
    y = datetime.date.today().year
    vehicles = [v for v in vs if buildable(v)]
    return site, rates, B.Catalog(vehicles, y), y


def text_of(h):
    h = re.sub(r"<(h2|h3|p|li|tr)[^>]*>", "\n", h)
    h = re.sub(r"</t[dh]>", " | ", h)
    return html.unescape(re.sub(r"<[^>]+>", "", h))


def lint(slug, g, art):
    probs = []
    for k in GUIDE_KEYS:
        if not g.get(k):
            probs.append(f"GUIDE에 '{k}'가 없어요")
    for k in KEYS:
        if k not in art or not art[k]:
            probs.append(f"build()가 '{k}'를 돌려주지 않아요")
    if probs:
        return probs
    if not 3 <= len(art["faqs"]) <= 6:
        probs.append(f"FAQ는 3~6개로 (지금 {len(art['faqs'])}개)")
    for i, s in enumerate(art["sources"]):
        if not (isinstance(s, tuple) and len(s) == 2 and str(s[1]).startswith("https://")):
            probs.append(f"sources[{i}]는 (이름, 'https://…') 짝이어야 해요: {s!r}")
    if "<h2>" not in art["body"]:
        probs.append("본문(body)에 <h2> 소제목이 없어요")
    if len(text_of(art["body"])) < 1200:
        probs.append(f"본문이 너무 짧아요 ({len(text_of(art['body']))}자) — 1,200자 이상")
    allhtml = " ".join([art["summary"], art["body"]] + [a for _, a in art["faqs"]])
    for href in re.findall(r'href="([^"]+)"', allhtml):
        if href.startswith(("https://", "http://", "#", "mailto:")):
            continue
        target = (ROOT / "care" / href.split("#")[0]).resolve()
        planned = href.endswith(".html") and "/" not in href and href[:-5] in care_guides.ORDER + (slug,)
        if not target.exists() and not planned:
            probs.append(f"링크 대상이 없어요: {href}")
    if "priceKrw" in Path(care_guides.__file__).with_name(care_guides.module_name(slug) + ".py").read_text(encoding="utf-8"):
        probs.append("parts.json priceKrw는 글에 쓰지 않아요 (수첩 내부 참고용 — 콘텐츠 페이지 노출 금지)")
    for bad in ("TODO", "FIXME", "XXX", "lorem", "[확인 필요"):
        if bad.lower() in allhtml.lower():
            probs.append(f"남은 표시가 있어요: {bad}")
    plain = text_of(allhtml)
    for sent in re.split(r"(?<=[.!?])\s+", plain):
        s = sent.strip()
        if re.search(r"(습니다|합니다|입니다|됩니다)[.!?]?$", s):
            probs.append(f"해요체로 써요(합쇼체 발견): …{s[-30:]}")
            break
    for q, a in art["faqs"]:
        if not q.strip().endswith("?"):
            probs.append(f"FAQ 질문은 물음표로 끝나요: {q}")
        if "<" in q or "<" in a:
            probs.append(f"FAQ는 HTML 없이 글자만 (화면·구조화 데이터에 그대로 들어가요): {q}")
    if len(art["description"]) > 160:
        probs.append(f"description이 길어요 ({len(art['description'])}자) — 160자 이하")
    return probs


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    slug = sys.argv[1]
    site, rates, cat, y = setup()
    c = care_guides.Ctx(B, rates, site, cat, y)
    m = care_guides.load(slug)
    art = m.build(c)
    if "--html" in sys.argv:
        print(art["body"])
        return
    print("=" * 60)
    print(art["h1"])
    print(f"[title] {art['title']}\n[description] {art['description']}\n[lede] {art['lede']}")
    print("[한눈에] " + text_of(art["summary"]).strip())
    print(text_of(art["body"]))
    print("--- 자주 묻는 질문")
    for q, a in art["faqs"]:
        print(f"Q. {q}\nA. {text_of(a).strip()}")
    print("--- 출처")
    for lb, u in art["sources"]:
        print(f"- {lb}: {u}")
    probs = lint(slug, m.GUIDE, art)
    print("=" * 60)
    if probs:
        print("검사: 고칠 것 {}개".format(len(probs)))
        for p in probs:
            print("  - " + p)
        sys.exit(1)
    print("검사: 통과")


if __name__ == "__main__":
    main()
