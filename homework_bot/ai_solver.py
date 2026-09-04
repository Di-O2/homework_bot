import os
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPTS = {
    "en": """
You are an expert university professor and technical academic specialist.
Your task is to analyze the uploaded document/assignment and generate a flawless, professional, and ready-to-submit solution.

STRICT INSTRUCTIONS:
1. THE VERY FIRST LINE of your output MUST strictly be the document title in this exact format:
   TITLE: <Exact Experiment Title or Document Title>
2. STRICT WHITE-LABEL POLICY: Do NOT include any filler remarks, introductory greetings, concluding self-references, or any mention of AI, models, or bot assistance anywhere.
3. TABLE FORMATTING RULE: Whenever presenting structured data, metadata, document headers, or comparison lists, you MUST format them as strict Markdown tables with complete enclosing pipes on every row:
   | Parameter | Description |
   |---|---|
   | Item 1 | Value 1 |
   Never split table keys and values onto separate text lines.
4. Strictly follow any user instructions or requested sections provided in prior notes.
5. Format academic headings using Markdown (##, ###) and clean plain mathematical/chemical symbols for direct Word/PDF export.
""",
    "ar": """
أنت بروفيسور وأكاديمي جامعي خبير.
مهمتك دراسة المستند أو الواجب المرفق وتقديم حل أكاديمي احترافي وجاهز للتسليم الفوري.

التعليمات الصارمة:
1. السطر الأول في مخرجاتك يجب أن يكون حصراً عنوان الموضوع أو المستند بالصيغة التالية:
   TITLE: <عنوان أو رقم الواجب الدقيق>
2. منع الإشارة للذكاء الاصطناعي: لا تضع أي ترحيب، أو اعتذار، أو ختام يذكر البوت أو الذكاء الاصطناعي نهائياً؛ اجعل الملف يبدو وكأنه من إعداد الطالب بالكامل.
3. قاعدة الجداول الصارمة: أي بيانات وصفية، ترويسات تحكم (Document Control)، أو مقارنات يجب صياغتها كجدول Markdown قياسي كامل ومغلق بالأعمدة:
   | العنصر | التفاصيل |
   |---|---|
   | العنوان | القيمة |
   ممنوع منعاً باتاً وضع اسم الحقل في سطر والقيمة في سطر منفصل.
4. التزم حرفياً بالشروط والأقسام التي يطلبها الطالب في رسالته.
5. نسق العناوين بوضوح باستخدام الماركداون (##, ###).
"""
}

def extract_title_and_clean_text(response_text: str) -> tuple[str, str]:
    """استخراج العنوان المخصص وتنظيف النص لبناء الملفات"""
    lines = response_text.strip().split("\n")
    doc_title = "Assignment_Report"
    
    if lines and lines[0].startswith("TITLE:"):
        doc_title = lines[0].replace("TITLE:", "").strip()
        cleaned_text = "\n".join(lines[1:]).strip()
    else:
        cleaned_text = response_text

    # تنظيف العنوان ليكون صالحاً كاسم ملف في نظام التشغيل
    safe_filename = re.sub(r'[\\/*?:"<>|]', "", doc_title).strip().replace(" ", "_")
    safe_filename = safe_filename[:45] if len(safe_filename) > 45 else safe_filename

    return doc_title, safe_filename, cleaned_text

async def solve_homework(
    text_query: str = "",
    image_bytes: bytes = None,
    mime_type: str = "image/jpeg",
    lang: str = "ar"
):
    contents = []

    # 1. فحص وتصحيح نوع الملف تلقائياً لضمان قبوله في Gemini 2.0
    if image_bytes:
        # كشف نوع الملف من ترويسة البايتات إذا كان غير مدعوم
        if mime_type not in ["image/jpeg", "image/png", "image/webp", "application/pdf"]:
            if image_bytes.startswith(b"%PDF"):
                mime_type = "application/pdf"
            elif image_bytes.startswith(b"\x89PNG"):
                mime_type = "image/png"
            else:
                mime_type = "image/jpeg"

        contents.append(
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type
            )
        )

    base_prompt = PROMPTS.get(lang, PROMPTS.get("en", ""))
    user_instruction = f"\n\nStudent Specific Instructions/Prior Notes:\n{text_query}" if text_query else ""
    contents.append(base_prompt + user_instruction)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
            )
        )
        title, safe_filename, cleaned_text = extract_title_and_clean_text(response.text)
        return True, title, safe_filename, cleaned_text

    except Exception as e:
        err_str = str(e)
        print(f"❌ AI Solver Error: {err_str}")  # طباعة سبب الخطأ الحقيقي في السيرفر فوراً
        
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            friendly_err = (
                "⚠️ **يوجد ضغط مؤقت على محرك الذكاء الاصطناعي.**\n"
                "💡 رصيدك محفوظ بالكامل ولم يُخصم منه شيء.\n"
                "يرجى الانتظار لمدة دقيقة واحدة ثم إعادة إرسال الملف."
            )
        else:
            friendly_err = (
                "❌ **تعذر إكمال معالجة الملف في الوقت الحالي.**\n\n"
                "💡 رصيدك لم يُخصم، يرجى إعادة المحاولة بعد قليل أو مراسلة الدعم عبر /support."
            )
        return False, "Error", "Error_Report", friendly_err