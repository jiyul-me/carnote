"""차일지 — 공유 썸네일(og:image)·앱 아이콘 PNG 생성기. build.py가 호출한다.

- 그림만 그린다. 세액 등 문구는 build.py가 data/*.json으로 계산해 spec으로 넘긴다 (하드코딩 금지 규칙).
- Pillow가 필요하다 (pip3 install pillow). 없으면 그리지 않고, 이미 커밋된 PNG 중
  내용이 최신인 것만 그대로 쓴다 — 빌드 자체는 실패하지 않는다.
- 각 PNG에 입력 문구의 해시(sig)를 심어 두고, 같으면 다시 그리지 않는다.
  Pillow 버전 차이로 바이트만 바뀌는 무의미한 git diff를 막는다.
- 디자인은 DESIGN.md 토큰만 사용: 흰 배경 · 잉크 텍스트 · 블루 포인트 · 헤어라인. 그림자·그라데이션 금지.
"""
import hashlib
import json
import struct
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    from PIL.PngImagePlugin import PngInfo
    HAS_PIL = True
except ImportError:  # pragma: no cover — Pillow 없는 환경
    HAS_PIL = False

# 디자인을 바꾸면 올린다 → 모든 이미지가 다시 그려지고 og:image ?v= 가 바뀐다 (카톡 캐시 무효화)
RENDER_VERSION = 1

FONT_DIR = Path(__file__).resolve().parent / "fonts"
SIG_KEY = "chailji-sig"

# DESIGN.md 색 토큰
BG = "#FFFFFF"
INK = "#191F28"
INK_SECONDARY = "#4E5968"
INK_MUTED = "#8B95A1"
BORDER = "#E5E8EB"
ACCENT = "#1A56DB"

OG_W, OG_H = 1200, 630
PAD = 80


def signature(spec):
    raw = json.dumps({"v": RENDER_VERSION, "spec": spec}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]


def read_png_sig(path):
    """PNG tEXt 청크에서 sig를 읽는다. Pillow 없이도 동작해야 하므로 직접 파싱."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    i = 8
    while i + 8 <= len(data):
        length, ctype = struct.unpack(">I4s", data[i:i + 8])
        if ctype == b"tEXt":
            key, _, val = data[i + 8:i + 8 + length].partition(b"\x00")
            if key.decode("latin-1") == SIG_KEY:
                return val.decode("latin-1")
        if ctype == b"IEND":
            break
        i += 12 + length
    return None


class Renderer:
    def __init__(self, root, site):
        self.root = Path(root)
        base = site.get("baseUrl", "").rstrip("/")
        self.base = base
        self.domain = base.replace("https://", "").replace("http://", "") if base else site["siteName"]
        self.site_name = site["siteName"]
        self.drawn = 0
        self.kept = 0
        self.stale = []
        self._fonts = {}

    # ── 공통 ────────────────────────────────────────────

    def font(self, weight, size):
        key = (weight, size)
        if key not in self._fonts:
            self._fonts[key] = ImageFont.truetype(str(FONT_DIR / f"Pretendard-{weight}.otf"), size)
        return self._fonts[key]

    def _ensure(self, rel_path, sig, draw_fn):
        """sig가 같은 PNG가 있으면 그대로, 아니면 그린다. 사용 가능하면 True."""
        path = self.root / rel_path
        if read_png_sig(path) == sig:
            self.kept += 1
            return True
        if not HAS_PIL:
            if path.exists():
                self.stale.append(rel_path)  # 내용이 낡은 이미지 — 잘못된 금액을 보여줄 수 있어 쓰지 않는다
            return False
        img = draw_fn()
        path.parent.mkdir(parents=True, exist_ok=True)
        info = PngInfo()
        info.add_text(SIG_KEY, sig)
        img.save(path, optimize=True, pnginfo=info)
        self.drawn += 1
        return True

    def report(self):
        msg = f"· 이미지 {self.drawn}개 생성 / {self.kept}개 최신 유지"
        print(msg)
        if not HAS_PIL:
            print("  ! Pillow가 없어 이미지를 새로 그리지 못했습니다 → pip3 install --user pillow 후 다시 빌드")
        if self.stale:
            print(f"  ! 내용이 낡은 이미지 {len(self.stale)}개 (예: {self.stale[0]}) — "
                  "잘못된 금액을 보여줄 수 있어 해당 썸네일은 og:image에서 뺐습니다")

    # ── 공유 썸네일 ─────────────────────────────────────

    def og(self, rel_path, spec, versioned=True):
        """spec을 그린 1200×630 PNG를 보장하고 절대 URL을 돌려준다. 쓸 수 없으면 None.
        versioned: 내용이 바뀌면 URL(?v=)도 바뀌게 해 카카오톡 등의 미리보기 캐시를 우회한다."""
        if not self.base:
            return None
        sig = signature(spec)
        if not self._ensure(rel_path, sig, lambda: self._draw_og(spec)):
            return None
        url = f"{self.base}/{rel_path}"
        return f"{url}?v={sig[:8]}" if versioned else url

    def prune(self, rel_dir, keep_names):
        """빌드 대상에서 빠진 차종의 썸네일 삭제 (rel_dir 아래 PNG만)."""
        d = self.root / rel_dir
        if not d.is_dir():
            return
        for p in d.glob("*.png"):
            if p.name not in keep_names:
                p.unlink()
                print(f"· 사용하지 않는 이미지 삭제: {rel_dir}/{p.name}")

    def _fit(self, draw, text, weight, size, min_size, max_w):
        """max_w 안에 들어갈 때까지 글자 크기를 줄인다. 최소 크기에서도 넘치면 말줄임."""
        while size > min_size and draw.textlength(text, font=self.font(weight, size)) > max_w:
            size -= 2
        f = self.font(weight, size)
        if draw.textlength(text, font=f) > max_w:
            while text and draw.textlength(text + "…", font=f) > max_w:
                text = text[:-1]
            text += "…"
        return text, f

    def _center_glyph(self, draw, box, text, font, fill):
        """글리프의 실제 잉크 영역 기준 중앙 정렬 (anchor="mm"은 폰트 메트릭 기준이라 한글이 위로 뜬다)."""
        l, t, r, b = draw.textbbox((0, 0), text, font=font, anchor="lt")
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        draw.text((cx - (l + r) / 2, cy - (t + b) / 2), text, font=font, fill=fill, anchor="lt")

    def _brand(self, draw, label=None):
        """좌상단 워드마크(블루 사각 '차' + 차일지), 우상단 섹션 라벨."""
        x, y, s = PAD, 64, 52
        draw.rounded_rectangle((x, y, x + s, y + s), radius=12, fill=ACCENT)
        self._center_glyph(draw, (x, y, x + s, y + s), "차", self.font("Bold", 30), BG)
        draw.text((x + s + 16, y + s / 2), self.site_name, font=self.font("Bold", 32), fill=INK, anchor="lm")
        if label:
            draw.text((OG_W - PAD, y + s / 2), label, font=self.font("Medium", 28), fill=INK_MUTED, anchor="rm")

    def _footer(self, draw, left):
        y = OG_H - 104
        draw.line((PAD, y, OG_W - PAD, y), fill=BORDER, width=2)
        ty = y + 48
        draw.text((OG_W - PAD, ty), self.domain, font=self.font("Medium", 28), fill=INK_SECONDARY, anchor="rm")
        if left:
            max_w = OG_W - 2 * PAD - draw.textlength(self.domain, font=self.font("Medium", 28)) - 40
            text, f = self._fit(draw, left, "Medium", 26, 20, max_w)
            draw.text((PAD, ty), text, font=f, fill=INK_MUTED, anchor="lm")

    def _draw_og(self, spec):
        img = Image.new("RGB", (OG_W, OG_H), BG)
        draw = ImageDraw.Draw(img)
        max_w = OG_W - 2 * PAD
        self._brand(draw, spec.get("label"))
        if spec["kind"] == "amount":
            # 차종 페이지: 차종명 → 캡션 → 히어로 금액 → 연납 한 줄 (페이지와 같은 위계)
            name, f = self._fit(draw, spec["name"], "Bold", 60, 40, max_w)
            draw.text((PAD, 206), name, font=f, fill=INK, anchor="ls")
            cap, f = self._fit(draw, spec["caption"], "Medium", 30, 22, max_w)
            draw.text((PAD, 256), cap, font=f, fill=INK_SECONDARY, anchor="ls")
            hero, f = self._fit(draw, spec["hero"], "Bold", 124, 80, max_w)
            draw.text((PAD - 4, 398), hero, font=f, fill=ACCENT, anchor="ls")
            if spec.get("sub"):
                sub, f = self._fit(draw, spec["sub"], "Medium", 34, 24, max_w)
                draw.text((PAD, 458), sub, font=f, fill=INK_SECONDARY, anchor="ls")
        else:
            # 일반 페이지: 큰 제목 + 설명 한 줄
            title, f = self._fit(draw, spec["title"], "Bold", 96, 60, max_w)
            draw.text((PAD - 4, 316), title, font=f, fill=INK, anchor="ls")
            lede, f = self._fit(draw, spec["lede"], "Medium", 38, 26, max_w)
            draw.text((PAD, 392), lede, font=f, fill=INK_SECONDARY, anchor="ls")
        self._footer(draw, spec.get("foot"))
        # 색 수가 적은 그림이라 팔레트 PNG로 줄인다 (차종 200개 × 용량)
        return img.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)

    # ── 앱 아이콘 ───────────────────────────────────────

    def icons(self):
        """홈 화면 아이콘 세트. iOS는 apple-touch-icon(PNG)만 쓰고 SVG data URI는 무시한다."""
        spec = {"kind": "icons", "bg": ACCENT, "fg": BG, "glyph": "차"}
        sig = signature(spec)
        targets = {
            "icons/apple-touch-icon.png": lambda: self._draw_icon(180, rounded=False, scale=0.52),
            "icons/icon-192.png": lambda: self._draw_icon(192, rounded=True, scale=0.52),
            "icons/icon-512.png": lambda: self._draw_icon(512, rounded=True, scale=0.52),
            # 안드로이드 maskable: 전체를 채우고 글자는 안전 영역(지름 80%) 안에
            "icons/icon-maskable-512.png": lambda: self._draw_icon(512, rounded=False, scale=0.40),
        }
        fresh = all(read_png_sig(self.root / p) == sig for p in targets)
        for rel, fn in targets.items():
            self._ensure(rel, sig, fn)
        ico = self.root / "favicon.ico"
        if HAS_PIL and (not fresh or not ico.exists()):
            # 네이버 검색 등 /favicon.ico만 보는 크롤러용
            self._draw_icon(256, rounded=True, scale=0.52).save(ico, sizes=[(16, 16), (32, 32), (48, 48)])

    def _draw_icon(self, size, rounded, scale):
        ss = 4  # 슈퍼샘플링 후 축소 — 둥근 모서리 계단 현상 방지
        S = size * ss
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        if rounded:
            draw.rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 0.2), fill=ACCENT)
        else:
            draw.rectangle((0, 0, S, S), fill=ACCENT)
        self._center_glyph(draw, (0, 0, S, S), "차", self.font("Bold", int(S * scale)), BG)
        img = img.resize((size, size), Image.LANCZOS)
        return img if rounded else img.convert("RGB")
