"""
Poster uslubidagi rasm — AI fon (Pollinations) ustiga Pillow bilan aniq matn chizish.
Matnni diffusion modeliga ishonib topshirmaymiz (u ko'pincha buzib chizadi),
shu sababli matn har doim shrift orqali, dasturiy ravishda, aniq chiziladi.
"""

import os
import textwrap
from io import BytesIO

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = "/tmp/kamalim_fonts"
FONT_URLS = {
    "bold": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Bold.ttf",
    "semibold": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-SemiBold.ttf",
    "regular": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Regular.ttf",
}

W, H = 1024, 1280
MARGIN = 60
ORANGE = (255, 122, 26)
WHITE = (255, 255, 255)
LIGHT_GRAY = (205, 205, 205)
MID_GRAY = (190, 190, 190)


async def _ensure_fonts() -> None:
    os.makedirs(FONT_DIR, exist_ok=True)
    async with httpx.AsyncClient(timeout=30.0) as client:
        for name, url in FONT_URLS.items():
            path = os.path.join(FONT_DIR, f"{name}.ttf")
            if not os.path.exists(path):
                resp = await client.get(url)
                resp.raise_for_status()
                with open(path, "wb") as f:
                    f.write(resp.content)


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(FONT_DIR, f"{name}.ttf"), size)


def _wrap_by_pixel(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        test = (cur + " " + word).strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


async def fetch_background(prompt: str) -> Image.Image:
    """Pollinations.ai orqali fon rasmini oladi (matnsiz, faqat vizual sahna)."""
    import random
    import urllib.parse

    encoded = urllib.parse.quote(prompt)
    seed = random.randint(1, 1_000_000)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={W}&height={H}&nologo=true&model=flux&seed={seed}&enhance=true"
    )
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGB")


def _darken_top_for_readability(img: Image.Image, fraction: float = 0.55) -> Image.Image:
    """Matn o'qilishi uchun rasmning tepa qismini asta-sekin qoraytiradi (gradient overlay)."""
    overlay = Image.new("L", (1, H), 0)
    top_h = int(H * fraction)
    for y in range(H):
        if y < top_h:
            alpha = int(200 * (1 - y / top_h))
        else:
            alpha = 0
        overlay.putpixel((0, y), alpha)
    overlay = overlay.resize((W, H))
    black = Image.new("RGB", (W, H), (0, 0, 0))
    return Image.composite(black, img, overlay)


async def compose_poster(
    handle: str,
    site_tag: str,
    headline: str,
    highlight: str,
    subheadline: str,
    background_prompt: str,
) -> bytes:
    """To'liq posterni yig'adi: AI fon + ustiga chizilgan sarlavha/subtitle/handle."""
    await _ensure_fonts()

    bg = await fetch_background(background_prompt)
    bg = bg.resize((W, H))
    bg = _darken_top_for_readability(bg)

    draw = ImageDraw.Draw(bg)

    semibold_small = _font("semibold", 26)
    bold_headline = _font("bold", 58)
    regular_sub = _font("regular", 30)

    # Handle (chap yuqori) va site tag (o'ng yuqori)
    draw.text((MARGIN, 50), handle, font=semibold_small, fill=WHITE)
    tag_w = draw.textlength(site_tag, font=semibold_small)
    draw.text((W - MARGIN - tag_w, 50), site_tag, font=semibold_small, fill=MID_GRAY)

    # Sarlavha — pastga tushguncha shriftni kichraytirib moslashtiramiz
    size = 58
    while size > 34:
        bold_headline = _font("bold", size)
        lines = _wrap_by_pixel(draw, headline.upper(), bold_headline, W - 2 * MARGIN)
        if len(lines) <= 4:
            break
        size -= 4

    y = 150
    line_height = int(size * 1.18)
    for line in lines:
        if highlight and highlight.upper() in line:
            # highlight so'zini rangli chizamiz, qolganini oq
            idx = line.upper().find(highlight.upper())
            before, mid, after = line[:idx], line[idx:idx + len(highlight)], line[idx + len(highlight):]
            x = MARGIN
            if before:
                draw.text((x, y), before, font=bold_headline, fill=WHITE)
                x += draw.textlength(before, font=bold_headline)
            draw.text((x, y), mid, font=bold_headline, fill=ORANGE)
            x += draw.textlength(mid, font=bold_headline)
            if after:
                draw.text((x, y), after, font=bold_headline, fill=WHITE)
        else:
            draw.text((MARGIN, y), line, font=bold_headline, fill=WHITE)
        y += line_height

    y += 14
    sub_lines = _wrap_by_pixel(draw, subheadline, regular_sub, W - 2 * MARGIN)
    for line in sub_lines[:3]:
        draw.text((MARGIN, y), line, font=regular_sub, fill=LIGHT_GRAY)
        y += 42

    # Nozik rounded border (poster ramkasi)
    border_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(border_layer)
    bdraw.rounded_rectangle([8, 8, W - 8, H - 8], radius=28, outline=(255, 255, 255, 60), width=3)
    bg = Image.alpha_composite(bg.convert("RGBA"), border_layer).convert("RGB")

    buf = BytesIO()
    bg.save(buf, format="PNG")
    return buf.getvalue()
