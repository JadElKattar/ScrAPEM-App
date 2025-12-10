"""
AI-based PDF Data Extraction using OpenAI GPT-4o-mini (Multimodal)
Enhanced with: System/User prompts, JSON schema, Seed for determinism
"""

import json
import time
import base64
import io
import pypdfium2 as pdfium

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Configuration
DEFAULT_PROVIDER = "openai"
OPENAI_MODEL = "gpt-4o-mini"
GOOGLE_MODEL = "gemini-1.5-flash-latest"
SEED = 42  # Fixed seed for determinism

# =============================================================================
# SYSTEM PROMPT (Optimized for GPT-4o-mini)
# =============================================================================

SYSTEM_PROMPT = """You are the "ScrAPEM Datasheet Extractor".

GOAL
From the images of a PDF technical datasheet, extract ALL individual, orderable product models and their specifications into a strict JSON array. Your output will be consumed by another automated system, so it must be exhaustive, consistent, and strictly follow the format below.

INPUT
- You receive one or more images.
- Together, these images represent ALL pages of a single PDF datasheet.
- The images may contain:
  - Tables
  - Text paragraphs
  - Diagrams and callouts
  - Footnotes and legends
- OCR quality may not be perfect (broken words, split lines, strange spacing).

You must:
1. Consider ALL pages before deciding what to output.
2. Identify every distinct orderable product model code appearing anywhere in the datasheet.
3. For each such model, output one JSON object with the specified fields.

────────────────────────────────
1. WHAT COUNTS AS A MODEL_CODE
────────────────────────────────

Treat as a MODEL_CODE any string that is clearly an orderable part number, e.g.:
- Codes like "AP1-1VG-24V", "NR1N-1A", "XB7-EW33B".
- Table rows where each row corresponds to a specific part number.
- Fully specified configuration codes where all option slots are filled.

DO NOT treat as separate models:
- Purely generic series names like "AP Series" or "NRA Series" unless they clearly appear as orderable codes.
- Incomplete templates such as "AP1-□□-□□" or "AP1 - □ □ - □□".
- Pure marketing families or headings that do not look like actual order codes.

If you are uncertain whether something is a real orderable product or just a pattern/template:
- Prefer precision over recall: include it only if it clearly functions as a specific, orderable model.

Each distinct MODEL_CODE must appear in the JSON output exactly once (no duplicates).

────────────────────────────────
2. FIELDS TO EXTRACT FOR EACH MODEL
────────────────────────────────

For each MODEL_CODE, extract these fields (use null if not found):

1. MODEL_CODE: The exact model/part number as written.
2. SERIES: Product series/family name (e.g., "AP", "NRA").
3. MOUNTING_HOLE: Panel cutout size (e.g., "22mm", "16mm").
4. BEZEL_STYLE: Flush, Extended, Raised, etc.
5. TERMINALS: Screw, Solder, PCB, Quick-connect, etc.
6. BEZEL_FINISH: Material/finish (Chrome, Aluminum, Plastic, etc.).
7. TYPE_OF_ILLUMINATION: LED, Incandescent, Neon, None, etc.
8. LED_COLOR: Red, Green, Blue, Amber, White, etc.
9. VOLTAGE: Operating voltage (e.g., "24V AC/DC", "120V AC").
10. SEALING: IP rating or sealing (e.g., "IP65", "IP40", "IP67").

RULES:
- If a specification is given at series-level and applies to multiple models, REPLICATE it for every affected model.
- If there is conflicting info, prefer the most specific source:
  row-level > table-level > general description.
- If you cannot confidently determine a field, set it to null (not "N/A" or "unknown").

────────────────────────────────
3. MULTI-OPTION FORMAT (CRITICAL)
────────────────────────────────

Sometimes a SINGLE model supports multiple valid options for a spec. Examples:
- A model explicitly described as "Red/Green LED".
- A single code that can be supplied with either "24V AC" or "24V DC" under options.

In those cases, use this EXACT format:
- {Red|Green}
- {Red|Green|Blue}
- {24V AC|24V DC}

STRICT RULES:
- Use curly braces `{}` and vertical bars `|`.
- NO spaces around the `|` (e.g., `{Red|Green}`, NOT `{Red | Green}`).
- Normalize obvious separators:
  - "Red/Green" → `{Red|Green}`
  - "Red or Green" → `{Red|Green}`

To reduce randomness, when multiple options exist:
- Order options ALPHABETICALLY by their normalized label
  (e.g., `{Amber|Green|Red}`, `{24V AC|24V DC}`).

Only use this format when the text clearly states that ONE model supports multiple options.  
If the datasheet instead lists different model codes, each with one option:
- Create SEPARATE JSON objects (one per model) with simple single values (e.g., "Red").

────────────────────────────────
4. NORMALIZATION & HYGIENE
────────────────────────────────

- All non-null values must be plain strings.
- Use JSON null, not the string "null".
- Preserve meaningful electrical detail in VOLTAGE (e.g., keep "AC/DC" if written).
- Normalize obvious synonyms when unambiguous:
  - "LED lamp", "LED illumination" → TYPE_OF_ILLUMINATION = "LED"
  - "non-illuminated", "unlit" → TYPE_OF_ILLUMINATION = "None"

Focus on the main product models. If the datasheet includes accessories, spare parts, or mounting hardware:
- Only include them as products if they are clearly treated as orderable models in the same way as the main products.

────────────────────────────────
5. REQUIRED INTERNAL PROCESS (FOR CONSISTENCY)
────────────────────────────────

Before you produce the final JSON:

1. INTERNALLY scan ALL pages and:
   - Collect a complete list of all distinct MODEL_CODE candidates.
   - Deduplicate them.
2. INTERNALLY verify:
   - Every MODEL_CODE in that list appears exactly once in your JSON output.
   - No JSON object uses a MODEL_CODE that is not visible in the images.
3. Only then, produce the final JSON array.

Do NOT output your internal lists or reasoning steps. Only output the final JSON array.

────────────────────────────────
6. OUTPUT FORMAT (STRICT)
────────────────────────────────

- Output MUST be a single valid JSON array of objects.
- NO markdown, NO backticks, NO natural language, NO comments.
- Do NOT mention page counts or product counts in the output.
- Do NOT prefix or suffix the JSON with any text.

Each JSON object must have EXACTLY these 10 keys:

1. "MODEL_CODE"
2. "SERIES"
3. "MOUNTING_HOLE"
4. "BEZEL_STYLE"
5. "TERMINALS"
6. "BEZEL_FINISH"
7. "TYPE_OF_ILLUMINATION"
8. "LED_COLOR"
9. "VOLTAGE"
10. "SEALING"

No extra keys are allowed.

If no valid models are found at all, output: []"""


# =============================================================================
# USER PROMPT (Concise trigger)
# =============================================================================

USER_PROMPT = "You are given all pages of this PDF datasheet as images. Using your system instructions, extract all orderable product models and output the JSON array."


# =============================================================================
# JSON SCHEMA (for structured output)
# =============================================================================

PRODUCT_SCHEMA = {
    "type": "object",
    "properties": {
        "MODEL_CODE": {"type": ["string", "null"]},
        "SERIES": {"type": ["string", "null"]},
        "MOUNTING_HOLE": {"type": ["string", "null"]},
        "BEZEL_STYLE": {"type": ["string", "null"]},
        "TERMINALS": {"type": ["string", "null"]},
        "BEZEL_FINISH": {"type": ["string", "null"]},
        "TYPE_OF_ILLUMINATION": {"type": ["string", "null"]},
        "LED_COLOR": {"type": ["string", "null"]},
        "VOLTAGE": {"type": ["string", "null"]},
        "SEALING": {"type": ["string", "null"]}
    },
    "required": ["MODEL_CODE", "SERIES", "MOUNTING_HOLE", "BEZEL_STYLE", 
                 "TERMINALS", "BEZEL_FINISH", "TYPE_OF_ILLUMINATION", 
                 "LED_COLOR", "VOLTAGE", "SEALING"],
    "additionalProperties": False
}


# =============================================================================
# PDF RENDERING
# =============================================================================

def render_pdf_to_images(pdf_bytes, max_pages=10, scale=4):
    """Render PDF bytes to a list of PIL images."""
    images = []
    try:
        pdf = pdfium.PdfDocument(pdf_bytes)
        num_pages = min(len(pdf), max_pages)
        for p_idx in range(num_pages):
            page = pdf.get_page(p_idx)
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            images.append(pil_image)
    except Exception as e:
        print(f"[PDF] Error rendering: {e}")
    return images


def pil_to_base64(pil_image):
    """Convert PIL image to base64 string."""
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# =============================================================================
# OPENAI EXTRACTION (with seed for determinism)
# =============================================================================

def extract_with_openai(images, api_key, max_retries=3):
    """Extract product data using OpenAI GPT-4o-mini with seed for determinism."""
    if not OPENAI_AVAILABLE:
        print("[AI] OpenAI library not installed. Run: pip install openai")
        return []
    
    if not images:
        return []
    
    client = OpenAI(api_key=api_key)
    
    # Build user content with images
    user_content = [{"type": "text", "text": USER_PROMPT}]
    for img in images:
        b64 = pil_to_base64(img)
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })
    
    for attempt in range(max_retries):
        try:
            print(f"[AI] Calling OpenAI GPT-4o-mini with {len(images)} images (seed={SEED})...")
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "scrapem_models",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "products": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["MODEL_CODE", "SERIES", "MOUNTING_HOLE", "BEZEL_STYLE", 
                                                     "TERMINALS", "BEZEL_FINISH", "TYPE_OF_ILLUMINATION", 
                                                     "LED_COLOR", "VOLTAGE", "SEALING"],
                                        "properties": {
                                            "MODEL_CODE": {"type": "string"},
                                            "SERIES": {"type": ["string", "null"]},
                                            "MOUNTING_HOLE": {"type": ["string", "null"]},
                                            "BEZEL_STYLE": {"type": ["string", "null"]},
                                            "TERMINALS": {"type": ["string", "null"]},
                                            "BEZEL_FINISH": {"type": ["string", "null"]},
                                            "TYPE_OF_ILLUMINATION": {"type": ["string", "null"]},
                                            "LED_COLOR": {"type": ["string", "null"]},
                                            "VOLTAGE": {"type": ["string", "null"]},
                                            "SEALING": {"type": ["string", "null"]}
                                        },
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["products"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                temperature=0.0,
                max_tokens=4096,
                seed=SEED  # Fixed seed for determinism
            )
            
            json_text = response.choices[0].message.content.strip()
            print(f"[AI] Response received: {len(json_text)} chars")
            
            result = json.loads(json_text)
            # Handle if API returns {"products": [...]} wrapper
            if isinstance(result, dict):
                products = result.get("products", result.get("data", [result]))
                if not isinstance(products, list):
                    products = [result]
            else:
                products = result if isinstance(result, list) else [result]
            
            print(f"[AI] Parsed {len(products)} products")
            return products
            
        except Exception as e:
            print(f"[AI] Attempt {attempt+1} Error: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    return []


# =============================================================================
# GOOGLE EXTRACTION (fallback)
# =============================================================================

def extract_with_google(images, api_key, max_retries=3):
    """Extract product data using Google Gemini."""
    if not GOOGLE_AVAILABLE:
        print("[AI] Google library not installed. Run: pip install google-generativeai")
        return []
    
    if not images:
        return []

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GOOGLE_MODEL)
    
    # Combine system + user prompt for Gemini (no separate system message)
    full_prompt = SYSTEM_PROMPT + "\n\n" + USER_PROMPT
    content = [full_prompt] + images
    
    for attempt in range(max_retries):
        try:
            print(f"[AI] Calling Google Gemini with {len(images)} images...")
            response = model.generate_content(
                content,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            json_text = response.text.strip()
            print(f"[AI] Response received: {len(json_text)} chars")
            products = json.loads(json_text)
            if not isinstance(products, list):
                products = [products]
            print(f"[AI] Parsed {len(products)} products")
            return products
            
        except google_exceptions.ResourceExhausted:
            wait_time = 2 ** (attempt + 1)
            print(f"[AI] Quota hit (429). Retrying in {wait_time}s...")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"[AI] Attempt {attempt+1} Error: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    return []


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def extract_with_ai(images, api_key, provider="openai"):
    """Main entry point for AI extraction."""
    if provider == "openai":
        return extract_with_openai(images, api_key)
    else:
        return extract_with_google(images, api_key)


# =============================================================================
# NORMALIZATION
# =============================================================================

def normalize_ai_output(products):
    """Normalize AI output to match target column names."""
    target_columns = [
        'SERIES', 'MODEL_CODE', 'MOUNTING HOLE', 'BEZEL STYLE', 'TERMINALS',
        'BEZEL FINISH', 'TYPE OF ILLUMINATION', 'LED COLOR', 'VOLTAGE', 'SEALING'
    ]
    
    key_mapping = {
        'MODEL_CODE': 'MODEL_CODE',
        'SERIES': 'SERIES',
        'MOUNTING_HOLE': 'MOUNTING HOLE',
        'BEZEL_STYLE': 'BEZEL STYLE',
        'TERMINALS': 'TERMINALS',
        'BEZEL_FINISH': 'BEZEL FINISH',
        'TYPE_OF_ILLUMINATION': 'TYPE OF ILLUMINATION',
        'LED_COLOR': 'LED COLOR',
        'VOLTAGE': 'VOLTAGE',
        'SEALING': 'SEALING'
    }
    
    normalized_products = []
    for product in products:
        normalized = {col: None for col in target_columns}
        for key, value in product.items():
            if value in [None, "null", "", "N/A"]:
                continue
            target_col = key_mapping.get(key)
            if target_col:
                normalized[target_col] = str(value)
        normalized_products.append(normalized)
    
    return normalized_products
