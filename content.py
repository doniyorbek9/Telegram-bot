"""
Gemini orqali post matni (internet qidiruvi bilan) va rasm generatsiyasi.
"""

import os
import random
import urllib.parse

import httpx
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")

client = genai.Client(api_key=GEMINI_API_KEY)

# Kanal mavzulari — "Kamalim" (video studio / Sadaf Media): video montaj, kameralar, to'y videolari
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

STYLE_GUIDE = """
Post matnini quyidagi uslubda yoz:
- Hikoyaviy, samimiy, ta'sirchan ohangda, lekin mavzu kameralar/video-montaj/to'y-video sohasida bo'lishi shart
- Qisqa jumlalar, izchil fikr rivoji
- Qisqa va ixcham (60-90 so'z atrofida) — uzun paragraflardan qoch
- Oxirida bitta kuchli xulosa yoki chaqiriq (call-to-action) bilan tugasin
- Emoji o'rinli ishlatilsin (ortiqcha bo'lmasin), matn Uzbekcha (lotin yozuvida) bo'lsin
- Telegram uchun HTML formatlash ishlatilsin: <b>qalin</b>, kerak bo'lsa <i>qiya</i>
""".strip()


async def generate_caption(topic: str) -> str:
    """Google Search grounding yordamida joriy ma'lumot asosida uzun caption yaratadi."""
    prompt = (
        f"Mavzu: {topic}\n\n"
        "Shu mavzu bo'yicha internetdan eng so'nggi va aniq ma'lumotlarni topib, "
        "Telegram kanali uchun post matni yoz.\n\n" + STYLE_GUIDE
    )

    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    return response.text.strip()


async def generate_image(topic: str) -> bytes:
    """Mavzuga mos rasm generatsiya qiladi (bepul Pollinations.ai, flux model, karta/kalit kerak emas)."""
    image_prompt = (
        f"professional photograph about {topic}, "
        "if about camera/equipment: realistic studio product photography, sharp focus, softbox lighting, "
        "if about wedding/event: cinematic warm-lit wedding videography scene, shallow depth of field, "
        "photorealistic, highly detailed, 8k, sharp focus, professional color grading, "
        "no text, no logo, no watermark, no blurry, no distorted, no cartoon"
    )
    encoded_prompt = urllib.parse.quote(image_prompt)
    seed = random.randint(1, 1_000_000)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width=1024&height=1024&nologo=true&model=flux&seed={seed}&enhance=true"
    )

    async with httpx.AsyncClient(timeout=90.0) as http_client:
        response = await http_client.get(url)
        response.raise_for_status()
        return response.content


async def generate_post() -> tuple[str, str, bytes]:
    """(mavzu, caption, rasm_bytes) qaytaradi."""
    topic = random.choice(TOPICS)
    caption = await generate_caption(topic)
    image_bytes = await generate_image(topic)
    return topic, caption, image_bytes
    
