"""
Gemini orqali post matni (internet qidiruvi bilan) va rasm generatsiyasi.
"""

import os
import random

from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

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
- Batafsil va foydali ma'lumot bilan (uzun, to'liq post — 150-250 so'z atrofida)
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
    """Mavzuga mos rasm generatsiya qiladi (AI o'zi uslubni tanlaydi: texnika yoki tadbir sahnasi)."""
    image_prompt = (
        f"Professional, yuqori sifatli, jozibali sotsial tarmoq posti uchun rasm. Mavzu: {topic}. "
        "Agar mavzu kamera/texnika haqida bo'lsa — kamera yoki video-jihozning real, studio uslubidagi "
        "fotosurat-sifatidagi tasvirini yarat. Agar mavzu to'y/tadbir haqida bo'lsa — kinematik, iliq "
        "yorug'likdagi to'y/tadbir sahnasini yarat. Matn yoki logotip bo'lmasin."
    )

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=image_prompt,
    )

    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) is not None:
            return part.inline_data.data

    raise RuntimeError("Gemini rasm qaytarmadi — model yoki prompt tekshirilsin.")


async def generate_post() -> tuple[str, str, bytes]:
    """(mavzu, caption, rasm_bytes) qaytaradi."""
    topic = random.choice(TOPICS)
    caption = await generate_caption(topic)
    image_bytes = await generate_image(topic)
    return topic, caption, image_bytes
