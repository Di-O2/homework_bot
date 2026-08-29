import asyncio
import os
import io
import re
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

# مكتبات تنسيق مستندات Word
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# مكتبات تنسيق مستندات PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

import database as db
import ai_solver

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

session = AiohttpSession(timeout=60)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

ACTIVE_SUPPORT = set()
USER_LAST_TEXT = {}
USER_PENDING_TASKS = {}

# --- دالة توحيد وتطبيع النصوص العربية للتعرف الذكي ---
def normalize_arabic(text: str) -> str:
    """توحيد أشكال الهمزات والتاء المربوطة والألف المقصورة"""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[إأآٱ]", "ا", text)
    text = re.sub(r"ة", "ه", text)
    text = re.sub(r"ى", "ي", text)
    text = re.sub(r"[\u064B-\u065F]", "", text)
    return text

# الكلمات المفتاحية التي تفعّل وضع خدمة العملاء تلقائياً
SUPPORT_KEYWORDS = [
    "دعم", "خدمه العملاء", "مشكل", "مساعد", "استفسار",
    "اداره", "مشرف", "شخص", "اتكلم", "تواصل", "خدمه",
    "support", "help", "admin"
]

# --- دوال استخراج وقراءة الملفات ---
def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        doc = Document(io.BytesIO(file_bytes))
        extracted = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_data = [c.text.strip() for c in row.cells if c.text.strip()]
                if row_data:
                    extracted.append(" | ".join(row_data))
        return "\n".join(extracted)
    except Exception:
        return ""

def create_pro_academic_docx(solution_text: str, custom_title: str, filename: str) -> BufferedInputFile:
    doc = Document()
    for s in doc.sections:
        s.top_margin = Inches(1)
        s.bottom_margin = Inches(1)
        s.left_margin = Inches(1)
        s.right_margin = Inches(1)

    header_para = doc.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_h = header_para.add_run("ACADEMIC REPORT | حل الواجبات الجامعية")
    run_h.font.size = Pt(8.5)
    run_h.font.color.rgb = RGBColor(120, 120, 120)

    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_before = Pt(8)
    title_p.paragraph_format.space_after = Pt(16)
    
    title_run = title_p.add_run(custom_title)
    title_run.font.name = "Arial"
    title_run.font.size = Pt(16)
    title_run.bold = True
    title_run.font.color.rgb = RGBColor(27, 54, 93)

    for line in solution_text.split("\n"):
        raw = line.strip()
        if not raw:
            continue
        cleaned = raw.replace("$$", "").replace("$", "").replace("\\text{", "").replace("}", "")

        if raw.startswith("### ") or raw.startswith("## ") or raw.startswith("# "):
            hp = doc.add_paragraph()
            hp.paragraph_format.space_before = Pt(10)
            hp.paragraph_format.space_after = Pt(3)
            hrun = hp.add_run(raw.lstrip("#").strip().replace("**", ""))
            hrun.font.size = Pt(12)
            hrun.bold = True
            hrun.font.color.rgb = RGBColor(41, 70, 115)
        elif raw.startswith("- ") or raw.startswith("* ") or raw.startswith("• "):
            bp = doc.add_paragraph(style='List Bullet')
            bp.paragraph_format.space_after = Pt(3)
            item_text = cleaned.lstrip("-*• ").strip()
            parts = item_text.split("**")
            for i, part in enumerate(parts):
                brun = bp.add_run(part)
                brun.font.name = "Arial"
                brun.font.size = Pt(10.5)
                if i % 2 == 1:
                    brun.bold = True
                    brun.font.color.rgb = RGBColor(27, 54, 93)
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.15
            parts = cleaned.split("**")
            for i, part in enumerate(parts):
                run = p.add_run(part)
                run.font.name = "Arial"
                run.font.size = Pt(10.5)
                if i % 2 == 1:
                    run.bold = True
                    run.font.color.rgb = RGBColor(27, 54, 93)

    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return BufferedInputFile(file_stream.getvalue(), filename=f"{filename}.docx")

def create_pro_academic_pdf(solution_text: str, custom_title: str, filename: str) -> BufferedInputFile:
    pdf_stream = io.BytesIO()
    doc = SimpleDocTemplate(pdf_stream, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=colors.HexColor('#1B365D'), alignment=1, spaceAfter=12)
    heading_style = ParagraphStyle('H', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor('#294673'), spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle('B', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor('#252525'), spaceAfter=5)
    
    story = [Paragraph(custom_title, title_style), Spacer(1, 6)]
    for line in solution_text.split('\n'):
        raw = line.strip()
        if not raw:
            continue
        cleaned = raw.replace("$$", "").replace("$", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        if raw.startswith("### ") or raw.startswith("## ") or raw.startswith("# "):
            h_text = raw.lstrip("#").strip().replace("**", "")
            story.append(Paragraph(f"<b>{h_text}</b>", heading_style))
        else:
            parts = cleaned.split("**")
            formatted = "".join([f"<b>{p}</b>" if i % 2 == 1 else p for i, p in enumerate(parts)])
            story.append(Paragraph(formatted, body_style))
        
    doc.build(story)
    pdf_stream.seek(0)
    return BufferedInputFile(pdf_stream.getvalue(), filename=f"{filename}.pdf")

# --- لوحات الأزرار ---
def get_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 خدمة العملاء والدعم", callback_data="btn_support"),
        ]
    ])

def get_options_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 Word (.docx)", callback_data="opt_en_docx"),
            InlineKeyboardButton(text="🇬🇧 PDF (.pdf)", callback_data="opt_en_pdf"),
        ],
        [
            InlineKeyboardButton(text="🇸🇦 وورد (.docx)", callback_data="opt_ar_docx"),
            InlineKeyboardButton(text="🇸🇦 بي دي إف (.pdf)", callback_data="opt_ar_pdf"),
        ],
        [
            InlineKeyboardButton(text="💬 نص مباشر", callback_data="opt_en_txt"),
        ]
    ])

# --- معالجة الأوامر ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    ACTIVE_SUPPORT.discard(user_id)
    credits = await db.get_or_create_user(user_id)
    
    welcome_text = (
        f"يا هلا والله بـ **{message.from_user.first_name}**، نوّرت! 🎓✨\n\n"
        "أنا مساعدك الجامعي الذكي، موجود هنا عشان أسهّل عليك مشوارك وأساعدك في إنجاز الواجبات، تقارير اللاب، وتكاليفك الجامعية أول بأول.\n\n"
        "ولا تشيل هم التنسيق، حلك يوصلك مرتب وجاهز بملف **Word** أو **PDF** للتسليم فوراً! 😉\n\n"
        "────────────────\n"
        "📌 **كيف تبدأ بـ 3 خطوات بس؟**\n"
        "1️⃣ **اكتب شروطك** (اختياري) مثل: *إنجليزي فقط، ركز على الخاتمة والمراجع*.\n"
        "2️⃣ **أرسل ملف الواجب** على طول (صورة، PDF، أو Word).\n"
        "3️⃣ **اختر الصيغة** (**Word** أو **PDF**) واستلم ملفك فوراً!\n"
        "────────────────\n\n"
        f"🔹 **رصيدك الحالي:** {credits} نقاط.\n"
        "🎁 *(شحنا لك رصيد تجريبي مجاني عشان تجرب أول حل وتشوف الجودة بنفسك)*"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    await db.add_credits(message.from_user.id, 10)
    await message.answer("🎁 تم شحن 10 نقاط في حسابك للتجربة!")

# --- أمر خاص بالأدمن لشحن رصيد لأي مستخدم ---
@dp.message(Command("give"))
async def cmd_give_credits(message: types.Message):
    user_id = message.from_user.id
    
    # التحقق من أن المرسل هو الأدمن فقط
    if user_id != ADMIN_ID:
        return  # تجاهل الأمر إذا كان المرسل طالباً عادياً

    # تقسيم نص الأمر: /give 12345678 100
    args = message.text.split()
    if len(args) != 3:
        await message.answer(
            "⚠️ **طريقة الاستخدام:**\n"
            "`/give <Telegram_ID> <النقاط>`\n\n"
            "📌 **مثال:**\n"
            "`/give 769764499 50`\n"
            "*(أو 9999 لرصيد مفتوح/VIP)*",
            parse_mode="Markdown"
        )
        return

    try:
        target_id = int(args[1])
        amount = int(args[2])
        
        # إضافة الرصيد في قاعدة البيانات
        await db.add_credits(target_id, amount)
        
        await message.answer(
            f"✅ **تم بنجاح!**\n"
            f"تمت إضافة **{amount}** نقطة للمستخدم: `{target_id}`.",
            parse_mode="Markdown"
        )
        
        # إرسال إشعار لطيف للشخص في محادثة البوت
        try:
            await bot.send_message(
                chat_id=target_id,
                text=f"🎁 **مبروك!** تمت إضافة **{amount}** نقطة رصيد إلى حسابك في البوت 🎓✨\nيمكنك الآن حل تكاليفك بكل حرية!"
            )
        except Exception:
            pass

    except ValueError:
        await message.answer("❌ خطأ: يرجى التأكد من كتابة الآيدي وعدد النقاط كأرقام صحيحة.")

# --- إدارة خدمة العملاء ---
@dp.callback_query(F.data == "btn_support")
@dp.message(Command("support"))
async def trigger_support(event: types.CallbackQuery | types.Message):
    user = event.from_user
    ACTIVE_SUPPORT.add(user.id)
    
    msg_text = (
        "💬 **أنت الآن في محادثة مباشرة مع خدمة العملاء.**\n\n"
        "اكتب مشكلتك أو استفسارك وسيقوم المشرف بالرد عليك هنا مباشرة.\n\n"
        "🔙 للخروج من المحادثة والعودة لحل الواجبات اكتب: `/exit`"
    )
    
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        await event.message.answer(msg_text, parse_mode="Markdown")
    else:
        await event.answer(msg_text, parse_mode="Markdown")

    if ADMIN_ID:
        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔔 **طلب دعم فني جديد!**\n\nالطالب: {user.full_name}\nالمعرف: `ID:{user.id}`\n\n(للرد عليه اضغط Reply على رسائله)",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Admin Notify Error: {e}")

@dp.message(Command("exit"))
async def exit_support(message: types.Message):
    user_id = message.from_user.id
    if user_id in ACTIVE_SUPPORT:
        ACTIVE_SUPPORT.remove(user_id)
        await message.answer("✅ تم إنهاء محادثة الدعم الفني، وعاد البوت للوضع التلقائي لحل الواجبات.")
        if ADMIN_ID:
            await bot.send_message(ADMIN_ID, f"🔒 تم إغلاق جلسة الدعم مع الطالب: `ID:{user_id}`")
    else:
        await message.answer("أنت لست في محادثة دعم حالياً.")

# رد المشرف عبر ميزة Reply
@dp.message(F.chat.id == ADMIN_ID, F.reply_to_message)
async def handle_admin_reply(message: types.Message):
    reply_text = message.reply_to_message.text or message.reply_to_message.caption or ""
    match = re.search(r"ID:(\d+)", reply_text)
    if match:
        target_user_id = int(match.group(1))
        try:
            if message.text:
                await bot.send_message(target_user_id, f"👨‍💼 **خدمة العملاء:**\n\n{message.text}", parse_mode="Markdown")
            elif message.photo:
                await bot.send_photo(target_user_id, photo=message.photo[-1].file_id, caption=f"👨‍💼 **خدمة العملاء:**\n\n{message.caption or ''}")
            elif message.document:
                await bot.send_document(target_user_id, document=message.document.file_id, caption=f"👨‍💼 **خدمة العملاء:**\n\n{message.caption or ''}")
            elif message.voice:
                await bot.send_voice(target_user_id, voice=message.voice.file_id, caption="👨‍💼 **تسجيل صوتي من الدعم الفني**")

            await message.reply("✅ تم إيصال ردك للطالب بنجاح.")
        except Exception as e:
            await message.reply(f"❌ تعذر إرسال الرد: {str(e)}")

# --- معالجة النصوص والملفات ---
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    raw_text = message.text.strip()
    norm_text = normalize_arabic(raw_text)

    # 1. إذا كان الطالب في وضع الدعم مسبقاً
    if user_id in ACTIVE_SUPPORT:
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"📩 **رسالة من الطالب:** {message.from_user.full_name} (`ID:{user_id}`)\n\n{raw_text}"
            )
            await message.answer("📨 تم إيصال رسالتك للدعم الفني، يرجى انتظار الرد...")
        return

    # 2. الفحص الذكي للكلمات المفتاحية
    if any(k in norm_text for k in SUPPORT_KEYWORDS):
        await trigger_support(message)
        return

    # 3. حفظ الملاحظات للواجب القادم
    USER_LAST_TEXT[user_id] = raw_text
    await message.answer("📝 **تم حفظ ملاحظاتك!**\nالآن أرسل ملف الواجب لتطبيقها على الحل فوراً.")

@dp.message(F.photo | F.document | F.voice)
async def handle_files(message: types.Message):
    user_id = message.from_user.id

    if user_id in ACTIVE_SUPPORT:
        if ADMIN_ID:
            caption = f"📎 **ملف من الطالب:** {message.from_user.full_name} (`ID:{user_id}`)\n{message.caption or ''}"
            if message.photo:
                await bot.send_photo(ADMIN_ID, photo=message.photo[-1].file_id, caption=caption)
            elif message.document:
                await bot.send_document(ADMIN_ID, document=message.document.file_id, caption=caption)
            elif message.voice:
                await bot.send_voice(ADMIN_ID, voice=message.voice.file_id, caption=caption)
            await message.answer("📨 تم إرسال المرفق للدعم الفني.")
        return

    credits = await db.get_or_create_user(user_id)
    if credits <= 0:
        await message.answer("⚠️ رصيدك 0 نقاط. تواصل مع الدعم أو اشحن رصيدك للمتابعة.")
        return

    file_bytes = None
    mime_type = "image/jpeg"
    caption = message.caption or ""
    prior_text = USER_LAST_TEXT.pop(user_id, "")
    text_query = f"{prior_text}\n{caption}".strip()

    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        f_io = io.BytesIO()
        await bot.download_file(file.file_path, destination=f_io)
        file_bytes = f_io.getvalue()
        mime_type = "image/jpeg"

    elif message.document:
        doc = message.document
        file = await bot.get_file(doc.file_id)
        f_io = io.BytesIO()
        await bot.download_file(file.file_path, destination=f_io)
        raw_bytes = f_io.getvalue()

        if (doc.file_name or "").lower().endswith(".docx"):
            docx_content = extract_text_from_docx(raw_bytes)
            text_query = f"{text_query}\n\n[Docx Content]:\n{docx_content}"
            file_bytes = None
        else:
            mime_type = doc.mime_type or "application/pdf"
            file_bytes = raw_bytes

    USER_PENDING_TASKS[user_id] = {
        "file_bytes": file_bytes,
        "mime_type": mime_type,
        "text_query": text_query
    }

    await message.answer("📥 **تم استلام الواجب!**\nحدد الصيغة المطلوبة لاستلام الحل:", reply_markup=get_options_keyboard())

@dp.callback_query(F.data.startswith("opt_"))
async def process_solution_options(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    task = USER_PENDING_TASKS.get(user_id)

    if not task:
        await callback.answer("⚠️ أعد إرسال الملف من فضلك.", show_alert=True)
        return

    _, lang, out_type = callback.data.split("_")
    await callback.answer()
    
    wait_msg = await callback.message.edit_text("⏳ **جاري قراءة الملف وتجهيز المستند المطلوب...**")

    success, doc_title, safe_filename, solution = await ai_solver.solve_homework(
        text_query=task["text_query"],
        image_bytes=task["file_bytes"],
        mime_type=task["mime_type"],
        lang=lang
    )

    if not success:
        await wait_msg.edit_text(solution)
        return

    await db.deduct_credit(user_id)
    credits = await db.get_or_create_user(user_id)
    await wait_msg.delete()

    if out_type == "docx":
        file_obj = create_pro_academic_docx(solution, custom_title=doc_title, filename=safe_filename)
        await callback.message.answer_document(
            file_obj,
            caption=f"📄 **تم إعداد ملف Word باسم:** `{safe_filename}.docx`\n\n✅ الرصيد المتبقي: **{credits}** نقاط.",
            parse_mode="Markdown"
        )
    elif out_type == "pdf":
        file_obj = create_pro_academic_pdf(solution, custom_title=doc_title, filename=safe_filename)
        await callback.message.answer_document(
            file_obj,
            caption=f"📑 **تم إعداد ملف PDF باسم:** `{safe_filename}.pdf`\n\n✅ الرصيد المتبقي: **{credits}** نقاط.",
            parse_mode="Markdown"
        )
    else:
        if len(solution) > 4000:
            for chunk in [solution[i:i+4000] for i in range(0, len(solution), 4000)]:
                await callback.message.answer(chunk)
        else:
            await callback.message.answer(solution)
        await callback.message.answer(f"✅ الرصيد المتبقي: **{credits}** نقاط.")

    USER_PENDING_TASKS.pop(user_id, None)

async def main():
    await db.init_db()
    print("🤖 البوت يعمل بنظام الدعم الفني المباشر والفحص الذكي للكلمات...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())