"""
AI-Powered PDF Data Extraction Script
Uses Google Gemini 1.5 Flash to extract product specifications from datasheets.
Each product/model becomes a separate row with full specifications.
"""

import os
import json
import pdfplumber
import pandas as pd
from tqdm import tqdm
import logging
import google.generativeai as genai
import time

# ============== CONFIGURATION ==============
API_KEY = "AIzaSyB_FmfrGna_rnlrFEECCaiKD0UM40TwK28"
MODEL_NAME = "gemini-2.0-flash"

# Target columns from Q6.xlsx
TARGET_COLUMNS = [
    'SERIES', 'MODEL_CODE', 'MOUNTING HOLE', 'BEZEL STYLE', 'TERMINALS', 
    'BEZEL FINISH', 'TYPE OF ILLUMINATION', 'LED COLOR', 'VOLTAGE', 'SEALING'
]

# ============== SETUP ==============
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

logging.basicConfig(
    filename='errors.txt', 
    level=logging.ERROR, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ============== EXTRACTION PROMPT ==============
EXTRACTION_PROMPT = """
You are a technical datasheet analyzer. Analyze the following PDF text and extract ALL individual products/models listed.

**Instructions:**
1. Identify every distinct product model code mentioned in the datasheet.
2. For each model, extract its complete specifications.
3. If a specification applies to multiple models, repeat it for each model's entry.
4. Return ONLY a valid JSON array. No markdown, no explanation.

**Required fields for each product (use null if not found):**
- MODEL_CODE: The specific model/part number (e.g., "AP1-1VG-24V", "NR1N-1A")
- SERIES: The product series name (e.g., "AP", "NRA")  
- MOUNTING_HOLE: Panel cutout size (e.g., "22mm", "16mm")
- BEZEL_STYLE: Flush, Extended, Raised, etc.
- TERMINALS: Screw, Solder, PCB, Quick-connect, etc.
- BEZEL_FINISH: Material/finish (Chrome, Aluminum, Plastic, etc.)
- TYPE_OF_ILLUMINATION: LED, Incandescent, Neon, None, etc.
- LED_COLOR: Red, Green, Blue, Amber, White, etc.
- VOLTAGE: Operating voltage (e.g., "24V AC/DC", "120V AC")
- SEALING: IP rating (e.g., "IP65", "IP40")

**Example output format:**
[
  {"MODEL_CODE": "AP1-1VG-24V", "SERIES": "AP", "MOUNTING_HOLE": "22mm", "VOLTAGE": "24V AC/DC", ...},
  {"MODEL_CODE": "AP1-1VR-24V", "SERIES": "AP", "MOUNTING_HOLE": "22mm", "VOLTAGE": "24V AC/DC", ...}
]

**PDF Text to analyze:**
{pdf_text}
"""

def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        logging.error(f"PDF extraction error for {pdf_path}: {str(e)}")
        return None
    return text

def extract_products_with_ai(pdf_text, filename):
    """Use Gemini to extract structured product data from PDF text."""
    if not pdf_text or len(pdf_text.strip()) < 50:
        logging.error(f"Insufficient text in {filename}")
        return []
    
    # Truncate if too long (Gemini Flash has 1M context but we'll be conservative)
    max_chars = 100000
    if len(pdf_text) > max_chars:
        pdf_text = pdf_text[:max_chars] + "\n[TRUNCATED]"
    
    # prompt = EXTRACTION_PROMPT.format(pdf_text=pdf_text)
    prompt = EXTRACTION_PROMPT.replace("{pdf_text}", pdf_text)
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,  # Low temperature for consistent extraction
                response_mime_type="application/json"
            )
        )
        
        # Parse JSON response
        json_text = response.text.strip()
        products = json.loads(json_text)
        
        if not isinstance(products, list):
            products = [products]
        
        return products
        
    except json.JSONDecodeError as e:
        logging.error(f"JSON parse error for {filename}: {str(e)}")
        # Try to extract JSON from response
        try:
            import re
            json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return []
    except Exception as e:
        logging.error(f"AI extraction error for {filename}: {str(e)}")
        return []

def normalize_product(product):
    """Normalize AI output to match target columns."""
    normalized = {}
    
    # Mapping from possible AI response keys to target columns
    # Using lowercase for matching
    key_mapping = {
        'model_code': 'MODEL_CODE',
        'modelcode': 'MODEL_CODE',
        'model': 'MODEL_CODE',
        'part_number': 'MODEL_CODE',
        'partnumber': 'MODEL_CODE',
        'series': 'SERIES',
        'mounting_hole': 'MOUNTING HOLE',
        'mountinghole': 'MOUNTING HOLE',
        'mounting hole': 'MOUNTING HOLE',
        'panel_cutout': 'MOUNTING HOLE',
        'bezel_style': 'BEZEL STYLE',
        'bezelstyle': 'BEZEL STYLE',
        'bezel style': 'BEZEL STYLE',
        'terminals': 'TERMINALS',
        'terminal': 'TERMINALS',
        'bezel_finish': 'BEZEL FINISH',
        'bezelfinish': 'BEZEL FINISH',
        'bezel finish': 'BEZEL FINISH',
        'finish': 'BEZEL FINISH',
        'type_of_illumination': 'TYPE OF ILLUMINATION',
        'illumination': 'TYPE OF ILLUMINATION',
        'light_type': 'TYPE OF ILLUMINATION',
        'led_color': 'LED COLOR',
        'ledcolor': 'LED COLOR',
        'led color': 'LED COLOR',
        'color': 'LED COLOR',
        'voltage': 'VOLTAGE',
        'operating_voltage': 'VOLTAGE',
        'sealing': 'SEALING',
        'ip_rating': 'SEALING',
        'iprating': 'SEALING',
        'protection': 'SEALING'
    }
    
    # Initialize all target columns to None
    for col in TARGET_COLUMNS:
        normalized[col] = None
    
    # Map AI response to target columns
    for key, value in product.items():
        if value is None or value == "null" or value == "" or value == "N/A":
            continue
        
        # Try to match key (case-insensitive)
        key_lower = key.lower().replace(' ', '_')
        target_col = key_mapping.get(key_lower)
        
        if not target_col:
            # Try without underscores
            key_lower_no_underscore = key_lower.replace('_', '')
            target_col = key_mapping.get(key_lower_no_underscore)
        
        if not target_col:
            # Try with spaces
            key_with_spaces = key.lower()
            target_col = key_mapping.get(key_with_spaces)
        
        if target_col:
            normalized[target_col] = str(value)
    
    return normalized


def main():
    print("=" * 60)
    print("AI-Powered PDF Data Extraction")
    print("Using Google Gemini 1.5 Flash")
    print("=" * 60)
    
    # SAFETY LIMIT: Default to processing only 3 files to prevent accidental costs
    # Change this to None or a larger number when ready for full batch
    MAX_FILES_LIMIT = 3
    
    # Find all PDFs
    # pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
    pdf_files = ["XP series datasheet.pdf"]
    print(f"\nFound {len(pdf_files)} PDF files.")
    
    if MAX_FILES_LIMIT and len(pdf_files) > MAX_FILES_LIMIT:
        print(f"⚠️  SAFETY MODE: Only processing first {MAX_FILES_LIMIT} files.")
        print(f"   To process all {len(pdf_files)} files, edit the script and set MAX_FILES_LIMIT = None")
        pdf_files = pdf_files[:MAX_FILES_LIMIT]
    
    input("Press Enter to continue with extraction (Ctrl+C to cancel)...")
    print("\n")
    
    all_products = []
    
    for filename in tqdm(pdf_files, desc="Processing PDFs"):
        # Extract text
        pdf_text = extract_text_from_pdf(filename)
        if not pdf_text:
            continue
        
        # Extract products with AI
        products = extract_products_with_ai(pdf_text, filename)
        print(f"DEBUG: Extracted products type: {type(products)}")
        print(f"DEBUG: Extracted products content: {products}")
        
        # Normalize and add source file
        for idx, product in enumerate(products):
            print(f"DEBUG: Processing product {idx} type: {type(product)}")
            normalized = normalize_product(product)
            normalized['SOURCE_FILE'] = filename
            all_products.append(normalized)
        
        # Rate limiting (Gemini has 15 RPM on free tier)
        time.sleep(0.5)
    
    # Save to Excel
    if all_products:
        df = pd.DataFrame(all_products)
        
        # Reorder columns
        columns_order = TARGET_COLUMNS + ['SOURCE_FILE']
        existing_cols = [c for c in columns_order if c in df.columns]
        df = df[existing_cols]
        
        output_file = 'Project_ScrAPEM_Master.xlsx'
        df.to_excel(output_file, index=False)
        print(f"\n✅ Successfully extracted {len(all_products)} products to {output_file}")
    else:
        print("\n❌ No products extracted.")

if __name__ == "__main__":
    main()
