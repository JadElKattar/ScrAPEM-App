#!/usr/bin/env python3
"""
PDF Data Extraction Script - Enhanced Version v3
Extracts ALL options with their actual codes from product datasheets.
Includes data cleaning: standardized units, duplicate removal.
"""

import pdfplumber
import pandas as pd
import re
import os
from pathlib import Path


# =============================================================================
# DATA CLEANING FUNCTIONS
# =============================================================================

def standardize_voltage(voltage_str):
    """
    Standardize voltage format: '24VDC' and '24V DC' → '24V DC'
    """
    if not voltage_str:
        return voltage_str
    
    v = voltage_str.strip()
    
    # Normalize spacing and format
    # Handle patterns like "24VDC" → "24V DC"
    v = re.sub(r'(\d+\.?\d*)\s*VDC', r'\1V DC', v, flags=re.IGNORECASE)
    v = re.sub(r'(\d+\.?\d*)\s*VAC', r'\1V AC', v, flags=re.IGNORECASE)
    
    # Normalize "V DC" vs "V  DC" (multiple spaces)
    v = re.sub(r'V\s+DC', 'V DC', v)
    v = re.sub(r'V\s+AC', 'V AC', v)
    
    # Handle ranges like "110/120V AC" - keep as is but normalize
    v = re.sub(r'(\d+)\s*/\s*(\d+)', r'\1/\2', v)
    
    return v


def clean_dimension(dim_str):
    """
    Clean dimension strings: remove 'ø' and 'mm', keep just numbers.
    Example: 'Ø8mm' → '8', 'ø3.2' → '3.2', '1.0 to 5.0mm' → '1.0 to 5.0'
    """
    if not dim_str:
        return dim_str
    
    d = dim_str.strip()
    
    # Remove ø/Ø symbols
    d = re.sub(r'[øØ]\s*', '', d)
    
    # Remove 'mm' suffix
    d = re.sub(r'\s*mm\b', '', d, flags=re.IGNORECASE)
    
    return d.strip()


def remove_duplicates_from_list(values_list):
    """
    Remove duplicates from a list, keeping order.
    Also handles cases like '8' and '8mm' (keeps the more descriptive one).
    """
    if not values_list:
        return values_list
    
    seen = {}
    result = []
    
    for item in values_list:
        # Normalize for comparison
        normalized = item.lower().strip()
        
        # Skip if we've seen an equivalent
        if normalized in seen:
            continue
        
        # Check for numeric equivalents (8 vs 8mm)
        numeric_match = re.match(r'^(\d+\.?\d*)\s*(?:mm)?$', normalized)
        if numeric_match:
            num = numeric_match.group(1)
            # Check if we already have this number
            if num in seen or f"{num}mm" in seen or f"{num} mm" in seen:
                continue
        
        seen[normalized] = True
        result.append(item)
    
    return result


def clean_and_dedupe_values(values_str, value_type='generic'):
    """
    Clean and deduplicate values in a formatted string like {A:Value|B:Value2}.
    value_type: 'voltage', 'dimension', or 'generic'
    """
    if not values_str or values_str == 'N/A':
        return values_str
    
    # Extract content between braces
    match = re.match(r'\{(.+)\}', values_str)
    if not match:
        return values_str
    
    content = match.group(1)
    items = content.split('|')
    
    cleaned_items = []
    seen_values = set()
    
    for item in items:
        item = item.strip()
        if not item:
            continue
        
        # Check if it's a code:value pair or just a value
        if ':' in item:
            parts = item.split(':', 1)
            code = parts[0].strip()
            value = parts[1].strip()
        else:
            code = None
            value = item
        
        # Apply type-specific cleaning
        if value_type == 'voltage':
            value = standardize_voltage(value)
        elif value_type == 'dimension':
            value = clean_dimension(value)
        
        # Skip duplicates (case-insensitive comparison)
        value_lower = value.lower()
        if value_lower in seen_values:
            continue
        seen_values.add(value_lower)
        
        # Rebuild the item
        if code:
            cleaned_items.append(f"{code}:{value}")
        else:
            cleaned_items.append(value)
    
    if not cleaned_items:
        return 'N/A'
    
    return '{' + '|'.join(cleaned_items) + '}'


def clean_mounting_hole(value):
    """Clean mounting hole values - remove symbols, dedupe."""
    if not value or value == 'N/A':
        return value
    
    # Split by pipe and clean each
    parts = value.split('|')
    cleaned = []
    seen = set()
    
    for part in parts:
        cleaned_part = clean_dimension(part.strip())
        if cleaned_part and cleaned_part.lower() not in seen:
            seen.add(cleaned_part.lower())
            cleaned.append(cleaned_part)
    
    return '|'.join(cleaned) if cleaned else 'N/A'


# =============================================================================
# EXTRACTION HELPER FUNCTIONS
# =============================================================================

def extract_series_from_filename(filename):
    """Extract series name from PDF filename."""
    basename = Path(filename).stem
    match = re.match(r'^([A-Z0-9]+)', basename, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return basename.split()[0].upper() if basename else "N/A"


def extract_code_value_pairs_from_tables(tables, value_list):
    """
    Extract code-value pairs from tables.
    Looks for patterns like "Red | R" or "R | Red" in table cells.
    """
    pairs = {}
    
    for table in tables:
        if not table:
            continue
        for row in table:
            if not row or len(row) < 2:
                continue
            
            for i in range(len(row) - 1):
                cell1 = str(row[i]).strip() if row[i] else ""
                cell2 = str(row[i+1]).strip() if row[i+1] else ""
                
                if not cell1 or not cell2:
                    continue
                
                for value in value_list:
                    # Pattern 1: "Value | Code"
                    if cell1.lower() == value.lower() and len(cell2) <= 3:
                        pairs[cell2.upper()] = value.capitalize()
                    # Pattern 2: "Code | Value"
                    elif cell2.lower() == value.lower() and len(cell1) <= 3:
                        pairs[cell1.upper()] = value.capitalize()
                    # Pattern 3: Value contains match
                    elif value.lower() in cell1.lower() and len(cell2) == 1 and cell2.isalpha():
                        pairs[cell2.upper()] = value.capitalize()
                    elif value.lower() in cell2.lower() and len(cell1) == 1 and cell1.isalpha():
                        pairs[cell1.upper()] = value.capitalize()
    
    return pairs


def format_pairs(pairs, found_values):
    """Format extracted pairs as {Code:Value|Code:Value}."""
    if not pairs and not found_values:
        return "N/A"
    
    formatted_items = []
    used_values = set()
    
    for code, value in pairs.items():
        formatted_items.append(f"{code}:{value}")
        used_values.add(value.lower())
    
    for value in found_values:
        if value.lower() not in used_values:
            formatted_items.append(value)
            used_values.add(value.lower())
    
    if not formatted_items:
        return "N/A"
    
    return "{" + "|".join(formatted_items) + "}"


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def extract_mounting_hole(text, tables):
    """
    Extract ALL mounting hole dimensions.
    Enhanced with fallback search for 'Panel Cutout' and mechanical drawing dimensions.
    """
    # Primary patterns for mounting holes
    patterns = [
        r'[Øø]\s*\d+\.?\d*\s*mm',      # Ø8mm, ø 10mm
        r'[Øø]\s*\d+\.?\d*',            # Ø8, ø 22 (with or without space)
        r'\d+\.?\d*\s*mm\s*[Xx×]\s*\d+\.?\d*\s*mm',  # 10mm x 10mm
        r'\d+\.?\d*\s*to\s*\d+\.?\d*\s*mm',  # 1.0 to 5.0mm
        r'\d+\.?\d*\s*to\s*\d+\.?\d*',  # 1.0 to 5.0
    ]
    
    # Keywords that indicate panel cutout / mounting hole context
    mounting_keywords = [
        'panel cut-out', 'panel cutout', 'panel cut out',
        'mounting hole', 'mounting', 'cut-out', 'cutout',
        'panel hole', 'hole diameter', 'hole size'
    ]
    
    found_values = []
    seen_normalized = set()  # For deduplication
    
    def add_value(val):
        """Add value if not duplicate."""
        # Normalize for comparison (just the number)
        norm = re.sub(r'[øØ\s]', '', val.lower()).replace('mm', '')
        if norm and norm not in seen_normalized:
            seen_normalized.add(norm)
            found_values.append(val)
    
    # PASS 1: Search near mounting keywords in text
    text_lower = text.lower()
    for keyword in mounting_keywords:
        if keyword in text_lower:
            # Find all occurrences
            idx = 0
            while True:
                idx = text_lower.find(keyword, idx)
                if idx == -1:
                    break
                # Extract context around keyword (200 chars after)
                context = text[idx:min(len(text), idx+200)]
                for pattern in patterns:
                    matches = re.findall(pattern, context, re.IGNORECASE)
                    for m in matches:
                        add_value(m)
                idx += 1
    
    # PASS 2: Search entire text for ø dimensions (common in mechanical drawings)
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            # Filter out very small values (likely not mounting holes)
            num_match = re.search(r'(\d+\.?\d*)', m)
            if num_match:
                num = float(num_match.group(1))
                # Typical mounting holes are 8-30mm, allow some range
                if 5 <= num <= 50:
                    add_value(m)
    
    # PASS 3: Search tables for dimensions near mounting keywords
    for table in tables:
        if not table:
            continue
        for row in table:
            if not row:
                continue
            
            row_text = ' '.join([str(c).lower() if c else '' for c in row])
            
            # Check if row has mounting-related keywords
            has_keyword = any(kw in row_text for kw in mounting_keywords)
            
            for cell in row:
                if not cell:
                    continue
                cell_str = str(cell)
                
                for pattern in patterns:
                    matches = re.findall(pattern, cell_str, re.IGNORECASE)
                    for m in matches:
                        # If near keyword, prioritize; otherwise filter by size
                        if has_keyword:
                            add_value(m)
                        else:
                            num_match = re.search(r'(\d+\.?\d*)', m)
                            if num_match:
                                num = float(num_match.group(1))
                                if 8 <= num <= 35:  # Stricter range for non-keyword matches
                                    add_value(m)
    
    # Clean and dedupe
    if found_values:
        result = '|'.join(found_values[:5])
        return clean_mounting_hole(result)
    return "N/A"


def extract_voltage(text, tables):
    """Extract ALL voltage specifications."""
    print("\n=== VOLTAGE EXTRACTION DEBUG ===")
    
    patterns = [
        r'\d+\.?\d*\s*/\s*\d+\.?\d*\s*V\s*(?:DC|AC)',
        r'\d+\.?\d*\s*V\s*(?:DC|AC)',
        r'\d+\.?\d*\s*(?:VDC|VAC)',
        r'\d+\.?\d*\s*to\s*\d+\.?\d*\s*V\s*(?:DC|AC)',
    ]
    
    found_voltages = []
    voltage_pairs = {}
    
    # Search entire text
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            match_clean = standardize_voltage(match.strip())
            if match_clean and not match_clean.startswith('000'):
                if match_clean.lower() not in [v.lower() for v in found_voltages]:
                    found_voltages.append(match_clean)
    
    # Search tables
    for table in tables:
        if not table:
            continue
        for row in table:
            if not row:
                continue
            for i, cell in enumerate(row):
                if not cell:
                    continue
                cell_text = str(cell)
                
                for pattern in patterns:
                    matches = re.findall(pattern, cell_text, re.IGNORECASE)
                    for match in matches:
                        match_clean = standardize_voltage(match.strip())
                        if match_clean and not match_clean.startswith('000'):
                            if match_clean.lower() not in [v.lower() for v in found_voltages]:
                                found_voltages.append(match_clean)
                            
                            # Check for codes
                            if i > 0 and row[i-1]:
                                prev_cell = str(row[i-1]).strip()
                                if len(prev_cell) <= 3 and prev_cell.isalnum():
                                    voltage_pairs[prev_cell.upper()] = match_clean
                            if i < len(row) - 1 and row[i+1]:
                                next_cell = str(row[i+1]).strip()
                                if len(next_cell) <= 3 and next_cell.isalnum():
                                    voltage_pairs[next_cell.upper()] = match_clean
    
    print(f"Found voltages (cleaned): {found_voltages[:10]}")
    
    # Format output
    if voltage_pairs:
        formatted = "|".join([f"{code}:{val}" for code, val in voltage_pairs.items()])
        result = "{" + formatted + "}"
    elif found_voltages:
        formatted = "|".join(found_voltages[:10])
        result = "{" + formatted + "}"
    else:
        return "N/A"
    
    # Final cleanup
    return clean_and_dedupe_values(result, 'voltage')


def extract_sealing(text, tables):
    """Extract ALL IP ratings."""
    print("\n=== SEALING EXTRACTION DEBUG ===")
    
    patterns = [r'IP\s*\d{2}[A-Z]?']
    
    found_ratings = []
    rating_pairs = {}
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            rating = match.replace(' ', '').upper()
            if rating and rating.lower() not in [r.lower() for r in found_ratings]:
                found_ratings.append(rating)
    
    for table in tables:
        if not table:
            continue
        for row in table:
            if not row:
                continue
            for i, cell in enumerate(row):
                if not cell:
                    continue
                for pattern in patterns:
                    matches = re.findall(pattern, str(cell), re.IGNORECASE)
                    for match in matches:
                        rating = match.replace(' ', '').upper()
                        if rating and rating.lower() not in [r.lower() for r in found_ratings]:
                            found_ratings.append(rating)
                        
                        if i > 0 and row[i-1]:
                            code = str(row[i-1]).strip()
                            if len(code) <= 2 and code.isalpha():
                                rating_pairs[code.upper()] = rating
    
    print(f"Found IP ratings (deduped): {found_ratings}")
    
    if rating_pairs:
        formatted = "|".join([f"{code}:{val}" for code, val in rating_pairs.items()])
        return "{" + formatted + "}"
    elif found_ratings:
        formatted = "|".join([f"E:{r}" for r in found_ratings])
        return "{" + formatted + "}"
    
    return "N/A"


def extract_led_color(text, tables):
    """Extract ALL LED colors with their actual codes."""
    colors = ['red', 'green', 'amber', 'yellow', 'white', 'blue', 'orange', 'clear', 'warm white']
    
    pairs = extract_code_value_pairs_from_tables(tables, colors)
    
    found_colors = []
    text_lower = text.lower()
    for color in colors:
        if color in text_lower and color.capitalize() not in found_colors:
            found_colors.append(color.capitalize())
    
    for table in tables:
        if not table:
            continue
        for row in table:
            if not row:
                continue
            for cell in row:
                if not cell:
                    continue
                cell_lower = str(cell).lower()
                for color in colors:
                    if color in cell_lower and color.capitalize() not in found_colors:
                        found_colors.append(color.capitalize())
    
    result = format_pairs(pairs, found_colors)
    return clean_and_dedupe_values(result, 'generic')


def extract_illumination_type(text, tables):
    """Extract ALL illumination types."""
    types = ['LED', 'Neon', 'Incandescent', 'Halogen', 'Lamp', 'Fluorescent']
    
    pairs = extract_code_value_pairs_from_tables(tables, types)
    
    found_types = []
    text_upper = text.upper()
    for illum_type in types:
        if illum_type.upper() in text_upper and illum_type not in found_types:
            found_types.append(illum_type)
    
    result = format_pairs(pairs, found_types)
    return clean_and_dedupe_values(result, 'generic')


def extract_bezel_style(text, tables):
    """Extract ALL bezel styles."""
    styles = ['Dome', 'Flat', 'Round', 'Square', 'Rectangular', 'Flush', 'Projected', 
              'Extended', 'Raised', 'Recessed', 'Convex']
    
    pairs = extract_code_value_pairs_from_tables(tables, styles)
    
    found_styles = []
    text_lower = text.lower()
    for style in styles:
        if style.lower() in text_lower and style not in found_styles:
            found_styles.append(style)
    
    result = format_pairs(pairs, found_styles)
    return clean_and_dedupe_values(result, 'generic')


def extract_terminals(text, tables):
    """Extract ALL terminal types."""
    terminal_types = ['Solder', 'Screw', 'Quick-connect', 'Quick Connect', 'Spring', 
                      'Crimp', 'Wire', 'Tab', 'PCB', 'Through-hole', 'SMD', 'Plug-in']
    
    pairs = extract_code_value_pairs_from_tables(tables, terminal_types)
    
    found_types = []
    text_lower = text.lower()
    for term_type in terminal_types:
        if term_type.lower() in text_lower:
            normalized = term_type.replace('Quick Connect', 'Quick-connect')
            if normalized not in found_types:
                found_types.append(normalized)
    
    result = format_pairs(pairs, found_types)
    return clean_and_dedupe_values(result, 'generic')


def extract_bezel_finish(text, tables):
    """Extract ALL bezel finishes."""
    finishes = ['Chrome', 'Plastic', 'Metal', 'Aluminum', 'Stainless', 'Nickel', 
                'Black', 'Silver', 'Brass', 'Zinc', 'Painted', 'Anodized']
    
    pairs = extract_code_value_pairs_from_tables(tables, finishes)
    
    found_finishes = []
    text_lower = text.lower()
    for finish in finishes:
        if finish.lower() in text_lower and finish not in found_finishes:
            found_finishes.append(finish)
    
    result = format_pairs(pairs, found_finishes)
    return clean_and_dedupe_values(result, 'generic')


# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

def parse_pdf(file_path):
    """Main extraction function."""
    print(f"\n{'='*60}")
    print(f"Processing: {file_path}")
    print(f"{'='*60}")
    
    result = {
        'SERIES': 'N/A',
        'MOUNTING HOLE': 'N/A',
        'BEZEL STYLE': 'N/A',
        'TERMINALS': 'N/A',
        'BEZEL FINISH': 'N/A',
        'TYPE OF ILLUMINATION': 'N/A',
        'LED COLOR': 'N/A',
        'VOLTAGE': 'N/A',
        'SEALING': 'N/A'
    }
    
    try:
        result['SERIES'] = extract_series_from_filename(file_path)
        
        pdf = pdfplumber.open(file_path)
        
        all_text = ""
        all_tables = []
        
        print(f"Scanning {len(pdf.pages)} pages...")
        
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n"
            
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)
        
        print(f"Total tables found: {len(all_tables)}")
        
        result['MOUNTING HOLE'] = extract_mounting_hole(all_text, all_tables)
        result['VOLTAGE'] = extract_voltage(all_text, all_tables)
        result['SEALING'] = extract_sealing(all_text, all_tables)
        result['LED COLOR'] = extract_led_color(all_text, all_tables)
        result['TYPE OF ILLUMINATION'] = extract_illumination_type(all_text, all_tables)
        result['BEZEL STYLE'] = extract_bezel_style(all_text, all_tables)
        result['TERMINALS'] = extract_terminals(all_text, all_tables)
        result['BEZEL FINISH'] = extract_bezel_finish(all_text, all_tables)
        
        pdf.close()
        
        print("\n--- EXTRACTED VALUES (CLEANED) ---")
        for key, value in result.items():
            print(f"{key}: {value}")
        
    except Exception as e:
        print(f"ERROR processing {file_path}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return result


def main():
    """Main execution function."""
    print("PDF Data Extraction Script - v3 (with Data Cleaning)")
    print("=" * 60)
    print("Features: Standardized units, duplicate removal")
    print("=" * 60)
    
    current_dir = os.getcwd()
    pdf_files = [f for f in os.listdir(current_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("No PDF files found in current directory!")
        return
    
    print(f"Found {len(pdf_files)} PDF files:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file}")
    
    results = []
    for pdf_file in pdf_files:
        pdf_path = os.path.join(current_dir, pdf_file)
        data = parse_pdf(pdf_path)
        results.append(data)
    
    df = pd.DataFrame(results)
    
    column_order = [
        'SERIES',
        'MOUNTING HOLE',
        'BEZEL STYLE',
        'TERMINALS',
        'BEZEL FINISH',
        'TYPE OF ILLUMINATION',
        'LED COLOR',
        'VOLTAGE',
        'SEALING'
    ]
    df = df[column_order]
    
    output_file = 'Project_ScrAPEM_Output.xlsx'
    df.to_excel(output_file, index=False)
    
    print(f"\n{'='*60}")
    print(f"SUCCESS! Data exported to: {output_file}")
    print(f"{'='*60}")
    print(f"\nProcessed {len(results)} PDF files")
    print(f"\nPreview of output:")
    print(df.to_string())


if __name__ == "__main__":
    main()
