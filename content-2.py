"""
Gemini orqali (internet qidiruvi bilan) mavzu bo'yicha ma'lumot yig'ish, undan
poster uchun qisqa matnlar (sarlavha/subtitle/caption) yaratish, so'ng
image_compose orqali tayyor poster-rasm yig'ish.
"""

import json
import os
import random
import re

from google import genai
from google.genai import types

from image_compose import compose_poster

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")

CHANNEL_HANDLE = os.environ.get("POSTER_HANDLE", "@kamalim")
CHANNEL_SITE_TAG = os.environ.get("POSTER_SITE_TAG", "kamalim.uz")

client = genai.Client(api_key=GEMINI_API_KEY)

TOPICS = [
    "video montaj sohasidagi so'nggi yangiliklar va dasturlar (Premiere Pro, DaVinci Resolve, CapCut)",
    "Canon kameralarining video suratga olish uchun eng yaxshi modellari va sozlamalari",
    "Sony kameralarining video suratga olish uchun eng yaxshi modellari va sozlamalari",
    "Nikon kameralarining video suratga olish uchun eng yaxshi modellari va sozlamalari",
    "to'y va nikoh marosimini sifatli video qilib olish bo'yicha maslahatlar",
    "video suratga olishda yorug'lik (light) va kadr kompozitsiyasi bo'yicha maslahatlar",
    "drone bilan tadbir va to'ylarni suratga olish bo'yicha maslahatlar",
    "video montajda rang korreksiyasi (color grading) asoslari",
]

BACKGROUND_STYLE_PROMPTS = [
    "minimalist 3d clay render, small cute clay figurine character, dark background, "
    "warm orange rim lighting, isometric objects, product photography, cinematic, no text",
    "dark moody studio background, soft orange glow, floating 3d icons related to {topic}, "
    "minimalist clay style render, high detail, no text, no logo",
]


async def _research(topic: str) -> str:
    """Google Search grounding bilan mavzu haqida joriy ma'lumot to'playdi."""
    prompt = (
        f"Mavzu: {topic}\n\n"
        "Shu mavzu bo'yicha internetdan eng so'nggi, aniq faktlar va maslahatlarni qisqacha yig'."
    )
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    return response.text.strip()


async def _structure_for_poster(topic: str, research_notes: str) -> dict:
    """Yig'ilgan ma'lumotni poster uchun qisqa struktura (JSON) ga aylantiradi."""
    prompt = f"""
Quyidagi ma'lumot asosida Telegram kanali uchun "poster-uslubidagi" post matnlarini yoz.
Mavzu: {topic}
Ma'lumot: {research_notes}

Talablar:
- headline: juda qisqa, ta'sirchan, DIQQATNI TORTUVCHI sarlavha (4-8 so'z, Uzbek lotin, savol yoki dadil da'vo shaklida bo'lishi mumkin)
- highlight: headline ichidagi 1 ta so'z yoki qisqa ibora (masalan raqam, foiz, kalit so'z) — bo'sh ham bo'lishi mumkin
- subheadline: headline'ni to'ldiruvchi 1 ta qisqa jumla (8-14 so'z)
- caption: Telegram post pastidagi juda qisqa matn (1-2 jumla, 15-25 so'z, oxirida chaqiriq/emoji)

Faqat quyidagi JSON formatda javob ber, boshqa hech narsa yozma:
{{"headline": "...", "highlight": "...", "subheadline": "...", "caption": "..."}}
""".strip()

    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    text = response.text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    return json.loads(text)


async def generate_post() -> tuple[str, str, bytes]:
    """(mavzu, telegram_caption, poster_rasm_bytes) qaytaradi."""
    topic = random.choice(TOPICS)
    research_notes = await _research(topic)
    parts = await _structure_for_poster(topic, research_notes)

    bg_prompt = random.choice(BACKGROUND_STYLE_PROMPTS).format(topic=topic)

    poster_bytes = await compose_poster(
        handle=CHANNEL_HANDLE,
        site_tag=CHANNEL_SITE_TAG,
        headline=parts.get("headline", topic),
        highlight=parts.get("highlight", ""),
        subheadline=parts.get("subheadline", ""),
        background_prompt=bg_prompt,
    )

    caption = parts.get("caption", "").strip()
    return topic, caption, poster_bytes
