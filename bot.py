import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from upstash_redis import Redis

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Fetch credentials safely from Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
UPSTASH_URL = os.getenv("UPSTASH_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_TOKEN")

# Initialize API clients
groq_client = Groq(api_key=GROQ_API_KEY)
redis_client = Redis(url=UPSTASH_URL, token=UPSTASH_TOKEN)

SYLLABUS = [
    {
        "lesson_id": 1,
        "title": "IP Addresses vs MAC Addresses",
        "concepts": "IP addresses identify a device on a network (like a house address), while MAC addresses are physical hardware IDs baked into the network card (like a National ID).",
        "quiz": "If a hacker changes their IP address, does their MAC address automatically change? (Jibu na Yes au No)"
    },
    {
        "lesson_id": 2,
        "title": "Understanding Ports",
        "concepts": "IP is the main apartment building address, but Ports are individual door numbers where specific traffic enters (e.g., Port 80/443 for web traffic, Port 22 for SSH).",
        "quiz": "Ni port number gani inatumiwa kwa secure web traffic (HTTPS)?"
    }
]

SYSTEM_PROMPT = """
You are a friendly, expert IT and Ethical Hacking teacher for absolute beginners.
Your job is to explain lessons using clear, beginner-friendly language mixed with high-energy Sheng/Swahili slang and local street analogies.
Keep explanations concise (under 4 short paragraphs). Always end your response with the lesson's exact quiz question.
"""

def get_user_progress(user_id: str) -> int:
    progress = redis_client.get(f"user:{user_id}:lesson")
    return int(progress) if progress is not None else 0

def set_user_progress(user_id: str, lesson_idx: int):
    redis_client.set(f"user:{user_id}:lesson", lesson_idx)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    set_user_progress(user_id, 0)
    await update.message.reply_text("Sasa msee! 👋 Karibu kwa class ya IT na Ethical Hacking!\n\nTuma /lesson kupata topic yako ya leo!")

async def send_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    lesson_idx = get_user_progress(user_id)
    
    if lesson_idx >= len(SYLLABUS):
        await update.message.reply_text("Maze umefanya job safi! Umetuliza syllabus yote ya kwanza. Standby kwa modules zingine! 🔥")
        return

    current_lesson = SYLLABUS[lesson_idx]
    prompt = f"Lesson Topic: {current_lesson['title']}\nCore Concepts: {current_lesson['concepts']}\nQuiz Question: {current_lesson['quiz']}"

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )
    
    await update.message.reply_text(response.choices[0].message.content)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text.lower()
    lesson_idx = get_user_progress(user_id)

    if user_text in ["/next", "next"]:
        lesson_idx += 1
        set_user_progress(user_id, lesson_idx)
        await send_lesson(update, context)
        return

    await update.message.reply_text("Kama uko tayari kwa next topic, tuma 'next' au click /next!")

if __name__ == "__main__":
    print("Bot starting up...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lesson", send_lesson))
    app.add_handler(CommandHandler("next", send_lesson))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    app.run_polling()
