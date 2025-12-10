"""
Debug script to test Gemini API response
"""
import pdfplumber
import google.generativeai as genai
import json
import traceback

API_KEY = "AIzaSyB_FmfrGna_rnlrFEECCaiKD0UM40TwK28"
MODEL_NAME = "gemini-2.0-flash"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

# Extract text from one PDF
pdf_path = "XP series datasheet.pdf"
with pdfplumber.open(pdf_path) as pdf:
    text = ""
    for page in pdf.pages[:2]:
        t = page.extract_text()
        if t:
            text += t + "\n"

print(f"Extracted {len(text)} chars from PDF")
print("=" * 50)

prompt = f"""
Analyze this datasheet and extract ALL products/models listed.
Return ONLY a valid JSON array with objects containing these fields:
MODEL_CODE, SERIES, MOUNTING_HOLE, VOLTAGE, SEALING, LED_COLOR

PDF Text:
{text[:20000]}
"""

print("Sending to Gemini...")
try:
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
    )
    print("Response received!")
    print("=" * 50)
    print("Raw response text:")
    print(response.text[:3000])
    print("=" * 50)
    
    # Try to parse
    data = json.loads(response.text)
    print(f"Parsed {len(data)} products")
    print("Type of data:", type(data))
    for i, p in enumerate(data[:3]):
        print(f"Product {i}: {type(p)}")
        print(p)
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    traceback.print_exc()
