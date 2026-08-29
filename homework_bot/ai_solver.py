import os
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPTS = {
    "en": """
You are an expert university professor and teaching assistant. 
Your task is to analyze the uploaded assignment/document and provide an accurate, high-standard solution.

STRICT INSTRUCTIONS:
1. THE VERY FIRST LINE of your response MUST strictly be the main Experiment/Topic Title extracted directly from the assignment in this format:
   TITLE: <Exact Experiment Title or Assignment Topic>
2. Strictly follow any user instructions or specific requested sections (e.g. if the user only asked for Discussion, Conclusion, References, provide ONLY those sections).
3. Do not include unnecessary generic filler or lengthy theoretical essays unless explicitly requested.
4. Format headings clearly using Markdown (##, ###) and clean plain mathematical/chemical symbols for direct Word/PDF export.
""",
    "ar": """
أنت معيد وبروفيسور جامعي خبير.
مهمتك تحليل الواجب والمستند المرفق وإعطاء حل دقيق ومباشر.

التعليمات الصارمة:
1. السطر الأول في إجابتك يجب أن يكون حصراً عنوان ورقم التجربة/الواجب المستخرج من الملف بهذه الصيغة:
   TITLE: <عنوان أو رقم التجربة الدقيق>
2. التزم حرفياً بالأقسام والشروط التي يحددها الطالب في رسالته.
3. قدم إجابات مباشرة ومختصرة حسب المطلوب وتجنب الحشو غير المفيد.
"""
}

def extract_title_and_clean_text(response_text: str) -> tuple[str, str]:
    """استخراج العنوان المخصص وتنظيف النص لبناء الملفات"""
    lines = response_text.strip().split("\n")
    doc_title = "Experiment_Assignment"
    
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
    text_query: str = None, 
    image_bytes: bytes = None, 
    mime_type: str = "image/jpeg",
    lang: str = "en"
) -> tuple[bool, str, str, str]:
    """إرسال السؤال وإرجاع: (حالة النجاح, العنوان, اسم الملف المقترح, نص الحل)"""
    contents = []
    
    if image_bytes:
        contents.append(
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        )
    
    base_prompt = PROMPTS.get(lang, PROMPTS["en"])
    user_instruction = f"\n\nStudent Specific Instructions/Prior Notes:\n{text_query}" if text_query else ""
    contents.append(base_prompt + user_instruction)

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
            )
        )
        title, safe_filename, cleaned_text = extract_title_and_clean_text(response.text)
        return True, title, safe_filename, cleaned_text
    except Exception as e:
        return False, "Error", "Error_Report", f"حدث خطأ أثناء معالجة الطلب: {str(e)}"