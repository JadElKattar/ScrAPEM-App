"""
Deterministic PDF Data Extraction - Enhanced Version
Ported from user's proven extraction logic.
Features: Exhaustive table search, code-value pairs, data cleaning.
"""

import pdfplumber
import pandas as pd
import re
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(filename='errors.txt', level=logging.ERROR)


# =============================================================================
# STANDARD CODE MAPPINGS
# =============================================================================

LED_COLOR_CODES = {
    'red': 'R', 'green': 'G', 'blue': 'B', 'white': 'W',
    'amber': 'A', 'yellow': 'Y', 'orange': 'O', 'clear': 'C',
    'warm white': 'WW', 'cool white': 'CW', 'pink': 'P',
    'purple': 'PR', 'bi-color': 'BC', 'rgb': 'RGB', 'multicolor': 'MC',
}

UPPERCASE_ACRONYMS = ['LED', 'RGB', 'SMD', 'PCB', 'AC', 'DC', 'IP']


# =============================================================================
# DATA CLEANING FUNCTIONS
# =============================================================================

def standardize_voltage(voltage_str):
    """Standardize voltage format: '24VDC' → '24V DC'"""
    if not voltage_str:
        return voltage_str
    v = voltage_str.strip()
    v = re.sub(r'(\d+\.?\d*)\s*VDC', r'\1V DC', v, flags=re.IGNORECASE)
    v = re.sub(r'(\d+\.?\d*)\s*VAC', r'\1V AC', v, flags=re.IGNORECASE)
    v = re.sub(r'V\s+DC', 'V DC', v)
    v = re.sub(r'V\s+AC', 'V AC', v)
    v = re.sub(r'(\d+)\s*/\s*(\d+)', r'\1/\2', v)
    return v


def clean_dimension(dim_str):
    """Clean dimension strings: remove 'ø' and 'mm'."""
    if not dim_str:
        return dim_str
    d = dim_str.strip()
    d = re.sub(r'[øØ]\s*', '', d)
    d = re.sub(r'\s*mm\b', '', d, flags=re.IGNORECASE)
    return d.strip()


def proper_capitalize(value):
    """Capitalize a value but keep acronyms uppercase."""
    if not value:
        return value
    if value.upper() in UPPERCASE_ACRONYMS:
        return value.upper()
    return value.capitalize()


def get_color_code(color_name):
    """Get standard code for a color."""
    color_lower = color_name.lower().strip()
    if color_lower in LED_COLOR_CODES:
        return LED_COLOR_CODES[color_lower]
    return color_name[0].upper() if color_name else 'X'


def clean_and_dedupe_values(values_str, value_type='generic'):
    """Clean and deduplicate values in a formatted string."""
    if not values_str or values_str == 'N/A':
        return values_str
    
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
        
        if ':' in item:
            parts = item.split(':', 1)
            code = parts[0].strip()
            value = parts[1].strip()
        else:
            code = None
            value = item
        
        if value_type == 'voltage':
            value = standardize_voltage(value)
        elif value_type == 'dimension':
            value = clean_dimension(value)
        
        value_lower = value.lower()
        if value_lower in seen_values:
            continue
        seen_values.add(value_lower)
        
        if code:
            cleaned_items.append(f"{code}:{value}")
        else:
            cleaned_items.append(value)
    
    if not cleaned_items:
        return 'N/A'
    
    return '{' + '|'.join(cleaned_items) + '}'


def clean_mounting_hole(value):
    """Clean mounting hole values."""
    if not value or value == 'N/A':
        return value
    
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
# EXHAUSTIVE EXTRACTION HELPERS
# =============================================================================

def extract_series_from_filename(filename):
    """Extract series name from PDF filename."""
    basename = Path(filename).stem
    match = re.match(r'^([A-Z0-9]+)', basename, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return basename.split()[0].upper() if basename else "N/A"


def exhaustive_table_search(tables, value_list, find_codes=True):
    """Exhaustively search ALL table cells for values."""
    found_codes = {}
    found_values = []
    
    for table in tables:
        if not table:
            continue
        for row in table:
            if not row:
                continue
            
            row_text = ' '.join([str(c).lower() if c else '' for c in row])
            
            for value in value_list:
                if value.lower() in row_text:
                    for i, cell in enumerate(row):
                        if not cell:
                            continue
                        cell_str = str(cell).strip()
                        
                        if value.lower() in cell_str.lower():
                            if find_codes:
                                if i > 0 and row[i-1]:
                                    prev = str(row[i-1]).strip()
                                    if len(prev) <= 3 and prev.replace('*', '').isalpha():
                                        found_codes[prev.upper()] = proper_capitalize(value)
                                if i < len(row) - 1 and row[i+1]:
                                    next_cell = str(row[i+1]).strip()
                                    if len(next_cell) <= 3 and next_cell.replace('*', '').isalpha():
                                        found_codes[next_cell.upper()] = proper_capitalize(value)
                            
                            if proper_capitalize(value) not in found_values:
                                found_values.append(proper_capitalize(value))
    
    return found_codes, found_values


def exhaustive_text_search(text, patterns):
    """Search entire text with multiple patterns."""
    all_matches = []
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            match_clean = match.strip()
            if match_clean and match_clean not in all_matches:
                all_matches.append(match_clean)
    
    return all_matches


def format_with_codes(codes_dict, values_list, always_code=False, code_generator=None):
    """Format values with codes as {Code:Value|Code:Value}."""
    if not codes_dict and not values_list:
        return "N/A"
    
    formatted_items = []
    used = set()
    
    for code, value in codes_dict.items():
        formatted_items.append(f"{code}:{value}")
        used.add(value.lower())
    
    for value in values_list:
        if value.lower() not in used:
            if always_code and code_generator:
                code = code_generator(value)
                formatted_items.append(f"{code}:{value}")
            else:
                formatted_items.append(value)
            used.add(value.lower())
    
    return "{" + "|".join(formatted_items) + "}" if formatted_items else "N/A"


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def extract_mounting_hole(text, tables):
    """Extract ALL mounting hole dimensions."""
    patterns = [
        r'[Øø]\s*\d+\.?\d*\s*mm',
        r'[Øø]\s*\d+\.?\d*',
        r'\d+\.?\d*\s*mm\s*[Xx×]\s*\d+\.?\d*\s*mm',
        r'\d+\.?\d*\s*to\s*\d+\.?\d*\s*mm',
        r'\d+\.?\d*\s*to\s*\d+\.?\d*',
        r'panel\s*cut[- ]?out[:\s]*([Øø]?\s*\d+\.?\d*)',
    ]
    
    mounting_keywords = [
        'panel cut-out', 'panel cutout', 'panel cut out',
        'mounting hole', 'mounting', 'cut-out', 'cutout',
        'panel hole', 'hole diameter', 'hole size'
    ]
    
    found_values = []
    seen_normalized = set()
    
    def add_value(val):
        norm = re.sub(r'[øØ\s]', '', val.lower()).replace('mm', '')
        if norm and norm not in seen_normalized:
            seen_normalized.add(norm)
            found_values.append(val)
    
    # Search entire text
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                m = m[0]
            num_match = re.search(r'(\d+\.?\d*)', str(m))
            if num_match:
                num = float(num_match.group(1))
                if 5 <= num <= 50:
                    add_value(str(m))
    
    # Search all tables
    for table in tables:
        if not table:
            continue
        for row in table:
            if not row:
                continue
            row_text = ' '.join([str(c).lower() if c else '' for c in row])
            has_keyword = any(kw in row_text for kw in mounting_keywords)
            
            for cell in row:
                if not cell:
                    continue
                cell_str = str(cell)
                for pattern in patterns:
                    matches = re.findall(pattern, cell_str, re.IGNORECASE)
                    for m in matches:
                        if isinstance(m, tuple):
                            m = m[0]
                        num_match = re.search(r'(\d+\.?\d*)', str(m))
                        if num_match:
                            num = float(num_match.group(1))
                            if has_keyword or (8 <= num <= 35):
                                add_value(str(m))
    
    if found_values:
        result = '|'.join(found_values[:8])
        return clean_mounting_hole(result)
    return None


def extract_voltage(text, tables):
    """Extract ALL voltage specifications."""
    patterns = [
        r'\d+\.?\d*\s*/\s*\d+\.?\d*\s*V\s*(?:DC|AC)',
        r'\d+\.?\d*\s*V\s*(?:DC|AC)',
        r'\d+\.?\d*\s*(?:VDC|VAC)',
        r'\d+\.?\d*\s*to\s*\d+\.?\d*\s*V\s*(?:DC|AC)',
        r'\d+\.?\d*[-–]\d+\.?\d*\s*V\s*(?:DC|AC)',
    ]
    
    found_voltages = []
    voltage_codes = {}
    
    all_matches = exhaustive_text_search(text, patterns)
    for match in all_matches:
        match_clean = standardize_voltage(match)
        if match_clean and not match_clean.startswith('000'):
            if match_clean.lower() not in [v.lower() for v in found_voltages]:
                found_voltages.append(match_clean)
    
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
                            
                            if i > 0 and row[i-1]:
                                prev_cell = str(row[i-1]).strip()
                                if len(prev_cell) <= 3 and prev_cell.isalnum():
                                    voltage_codes[prev_cell.upper()] = match_clean
                            if i < len(row) - 1 and row[i+1]:
                                next_cell = str(row[i+1]).strip()
                                if len(next_cell) <= 3 and next_cell.isalnum():
                                    voltage_codes[next_cell.upper()] = match_clean
    
    if voltage_codes:
        formatted = "|".join([f"{code}:{val}" for code, val in voltage_codes.items()])
        result = "{" + formatted + "}"
    elif found_voltages:
        formatted = "|".join(found_voltages[:12])
        result = "{" + formatted + "}"
    else:
        return None
    
    return clean_and_dedupe_values(result, 'voltage')


def extract_sealing(text, tables):
    """Extract ALL IP ratings."""
    patterns = [r'IP\s*\d{2}[A-Z]?', r'IP\s*\d{2}']
    
    found_ratings = []
    rating_codes = {}
    
    all_matches = exhaustive_text_search(text, patterns)
    for match in all_matches:
        rating = match.replace(' ', '').upper()
        if rating and rating not in found_ratings:
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
                cell_text = str(cell)
                
                for pattern in patterns:
                    matches = re.findall(pattern, cell_text, re.IGNORECASE)
                    for match in matches:
                        rating = match.replace(' ', '').upper()
                        if rating and rating not in found_ratings:
                            found_ratings.append(rating)
                        
                        if i > 0 and row[i-1]:
                            code = str(row[i-1]).strip()
                            if len(code) <= 2 and code.isalpha():
                                rating_codes[code.upper()] = rating
    
    if rating_codes:
        formatted = "|".join([f"{code}:{val}" for code, val in rating_codes.items()])
        return "{" + formatted + "}"
    elif found_ratings:
        formatted = "|".join([f"E:{r}" for r in found_ratings])
        return "{" + formatted + "}"
    
    return None


def extract_led_color(text, tables):
    """Extract LED colors with codes."""
    colors = ['red', 'green', 'amber', 'yellow', 'white', 'blue', 
              'orange', 'warm white', 'cool white', 'pink', 
              'purple', 'bi-color', 'rgb', 'multicolor']
    
    table_context_keywords = [
        'led', 'color', 'colour', 'lamp', 'lens', 'indicator', 
        'cap', 'light', 'backlight', 'illumination'
    ]
    
    found_codes = {}
    found_colors = []
    
    def is_valid_color_code(code_str):
        clean = code_str.replace('*', '').replace('-', '')
        return 1 <= len(clean) <= 2 and clean.isalpha() and clean.isupper()
    
    # Search tables
    for table in tables:
        if not table:
            continue
        
        table_header = ' '.join([str(c).lower() if c else '' for c in table[0]]) if table else ''
        table_has_context = any(kw in table_header for kw in table_context_keywords)
        
        for row in table:
            if not row or len(row) < 2:
                continue
            
            row_text = ' '.join([str(c).lower() if c else '' for c in row])
            row_has_context = any(kw in row_text for kw in table_context_keywords)
            
            for i in range(len(row)):
                cell = row[i]
                if not cell:
                    continue
                cell_str = str(cell).strip()
                cell_lower = cell_str.lower()
                
                for color in colors:
                    if cell_lower == color or cell_lower == color.replace(' ', '') or \
                       (color in cell_lower and len(cell_lower) <= len(color) + 5):
                        
                        code = None
                        
                        if i > 0 and row[i-1]:
                            prev = str(row[i-1]).strip().upper()
                            if is_valid_color_code(prev):
                                code = prev
                        
                        if not code and i < len(row) - 1 and row[i+1]:
                            next_c = str(row[i+1]).strip().upper()
                            if is_valid_color_code(next_c):
                                code = next_c
                        
                        if code or table_has_context or row_has_context:
                            if code:
                                found_codes[code] = proper_capitalize(color)
                            if proper_capitalize(color) not in found_colors:
                                found_colors.append(proper_capitalize(color))
    
    # Search text with LED context
    text_lower = text.lower()
    for color in colors:
        patterns = [
            rf'\b{color}\s+led\b',
            rf'\bled\s+{color}\b',
            rf'\b{color}\s+indicator\b',
            rf'\b{color}\s+lamp\b',
            rf'\b{color}\s+lens\b',
            rf'\bcolor[:\s]+{color}\b',
        ]
        
        for pattern in patterns:
            if re.search(pattern, text_lower):
                if proper_capitalize(color) not in found_colors:
                    found_colors.append(proper_capitalize(color))
                break
    
    # Always format with codes
    if not found_codes and not found_colors:
        return None
    
    formatted_items = []
    used_colors = set()
    
    for code, color in found_codes.items():
        formatted_items.append(f"{code}:{color}")
        used_colors.add(color.lower())
    
    for color in found_colors:
        if color.lower() not in used_colors:
            code = get_color_code(color)
            formatted_items.append(f"{code}:{color}")
            used_colors.add(color.lower())
    
    return "{" + "|".join(formatted_items) + "}" if formatted_items else None


def extract_illumination_type(text, tables):
    """Extract ALL illumination types."""
    types = ['LED', 'Neon', 'Incandescent', 'Halogen', 'Lamp', 'Fluorescent', 'Filament']
    
    found_codes, found_types = exhaustive_table_search(tables, types, find_codes=True)
    
    text_upper = text.upper()
    for illum_type in types:
        if illum_type.upper() in text_upper:
            if illum_type not in found_types:
                found_types.append(illum_type)
    
    return format_with_codes(found_codes, found_types)


def extract_bezel_style(text, tables):
    """Extract ALL bezel styles."""
    styles = ['Dome', 'Flat', 'Round', 'Square', 'Rectangular', 'Flush', 
              'Projected', 'Extended', 'Raised', 'Recessed', 'Convex', 'Mushroom']
    
    found_codes, found_styles = exhaustive_table_search(tables, styles, find_codes=True)
    
    text_lower = text.lower()
    for style in styles:
        if style.lower() in text_lower:
            if style not in found_styles:
                found_styles.append(style)
    
    return format_with_codes(found_codes, found_styles)


def extract_terminals(text, tables):
    """Extract ALL terminal types."""
    terminal_types = ['Solder', 'Screw', 'Quick-connect', 'Quick Connect', 
                      'Spring', 'Crimp', 'Wire', 'Tab', 'PCB', 'Through-hole', 
                      'SMD', 'Plug-in', 'Faston', 'Blade', 'Pin']
    
    found_codes, found_types = exhaustive_table_search(tables, terminal_types, find_codes=True)
    
    text_lower = text.lower()
    for term_type in terminal_types:
        if term_type.lower() in text_lower:
            normalized = term_type.replace('Quick Connect', 'Quick-connect')
            if normalized not in found_types:
                found_types.append(normalized)
    
    return format_with_codes(found_codes, found_types)


def extract_bezel_finish(text, tables):
    """Extract ALL bezel finishes."""
    finishes = ['Chrome', 'Plastic', 'Metal', 'Aluminum', 'Stainless', 
                'Nickel', 'Black', 'Silver', 'Brass', 'Zinc', 'Painted', 
                'Anodized', 'Polished', 'Satin', 'Matte']
    
    found_codes, found_finishes = exhaustive_table_search(tables, finishes, find_codes=True)
    
    text_lower = text.lower()
    for finish in finishes:
        if finish.lower() in text_lower:
            if finish not in found_finishes:
                found_finishes.append(finish)
    
    return format_with_codes(found_codes, found_finishes)


# =============================================================================
# MODEL_CODE EXTRACTION (DETERMINISTIC)
# =============================================================================

def extract_model_codes(text, tables, series_name):
    """
    Extract orderable MODEL_CODEs from PDF - STRICT VALIDATION.
    
    Only matches codes that:
    1. Start with the series name (e.g., "HS1T-")
    2. Contain letters and numbers after the hyphen  
    3. Don't contain spaces or garbage prefixes
    4. Are between 8-25 characters
    
    Args:
        text: All text from PDF
        tables: All tables from PDF
        series_name: The series name (e.g., "HS1T", "AP")
    
    Returns:
        List of unique MODEL_CODE strings
    """
    model_codes = []
    seen = set()
    
    # STRICT pattern: must start with series name + hyphen + alphanumeric segment(s)
    # Examples: HS1T-V44ZM-G, AP1-1VG-24V, NRA-11A-G
    strict_pattern = rf'\b{series_name}[-][A-Z0-9]{{2,}}(?:[-][A-Z0-9]+)*\b'
    
    # Words that indicate garbage (not real model codes)
    garbage_words = [
        'CIRCUIT', 'EXAMPLE', 'CONDITIONAL', 'SHORT', 'CURRENT', 
        'NOTE', 'FIGURE', 'TABLE', 'PAGE', 'SPECIFICATION',
        'DIMENSION', 'MOUNTING', 'TERMINAL', 'VOLTAGE', 'SEALING'
    ]
    
    def is_valid_model_code(code):
        """STRICT validation for model codes."""
        if not code:
            return False
        
        code = code.strip().upper()
        
        # Must be reasonable length
        if len(code) < 8 or len(code) > 25:
            return False
        
        # Must start with series name
        if not code.startswith(series_name.upper()):
            return False
        
        # Must have hyphen after series name
        if len(code) <= len(series_name) or code[len(series_name)] != '-':
            return False
        
        # No spaces allowed
        if ' ' in code:
            return False
        
        # No garbage words
        for garbage in garbage_words:
            if garbage in code:
                return False
        
        # Must contain at least one digit after the series name
        suffix = code[len(series_name)+1:]
        if not any(c.isdigit() for c in suffix):
            return False
        
        # Only alphanumeric and hyphens allowed
        valid_chars = all(c.isalnum() or c == '-' for c in code)
        if not valid_chars:
            return False
        
        return True
    
    def add_code(code):
        """Add code if valid and not seen."""
        code = code.strip().upper()
        if is_valid_model_code(code) and code not in seen:
            seen.add(code)
            model_codes.append(code)
    
    # Pass 1: Search with strict regex pattern in text
    matches = re.findall(strict_pattern, text, re.IGNORECASE)
    for match in matches:
        add_code(match)
    
    # Pass 2: Search tables
    for table in tables:
        if not table:
            continue
        
        for row in table:
            if not row:
                continue
            
            for cell in row:
                if not cell:
                    continue
                cell_str = str(cell).strip()
                
                # Apply strict pattern
                matches = re.findall(strict_pattern, cell_str, re.IGNORECASE)
                for match in matches:
                    add_code(match)
                
                # Also check if cell itself is a valid code
                if is_valid_model_code(cell_str):
                    add_code(cell_str)
    
    # Sort for consistent ordering
    model_codes.sort()
    
    return model_codes


# =============================================================================
# MAIN EXTRACTION FUNCTION (for Streamlit integration)
# =============================================================================

def extract_from_buffer(pdf_buffer, filename):
    """
    Extract data from a PDF buffer (for Streamlit file uploads).
    Returns a dict with:
        - 'specs': dict of extracted field values
        - 'model_codes': list of extracted MODEL_CODEs
    """
    specs = {}
    model_codes = []
    
    try:
        series = extract_series_from_filename(filename)
        specs['SERIES'] = series
        
        with pdfplumber.open(pdf_buffer) as pdf:
            all_text = ""
            all_tables = []
            
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text += page_text + "\n"
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
            
            # Extract field specs
            specs['MOUNTING HOLE'] = extract_mounting_hole(all_text, all_tables)
            specs['VOLTAGE'] = extract_voltage(all_text, all_tables)
            specs['SEALING'] = extract_sealing(all_text, all_tables)
            specs['LED COLOR'] = extract_led_color(all_text, all_tables)
            specs['TYPE OF ILLUMINATION'] = extract_illumination_type(all_text, all_tables)
            specs['BEZEL STYLE'] = extract_bezel_style(all_text, all_tables)
            specs['TERMINALS'] = extract_terminals(all_text, all_tables)
            specs['BEZEL FINISH'] = extract_bezel_finish(all_text, all_tables)
            
            # Extract MODEL_CODEs (deterministic)
            model_codes = extract_model_codes(all_text, all_tables, series)
    
    except Exception as e:
        logging.error(f"Error processing buffer {filename}: {str(e)}")
    
    return {
        'specs': specs,
        'model_codes': model_codes
    }


# =============================================================================
# LEGACY FUNCTIONS (for backwards compatibility)
# =============================================================================

def extract_from_pdf_heuristic(pdf_path):
    """Legacy function for file-based extraction."""
    with open(pdf_path, 'rb') as f:
        return [extract_from_buffer(f, pdf_path)]


def main():
    """Standalone execution."""
    import os
    
    target_columns = ['SERIES', 'MODEL_CODE', 'MOUNTING HOLE', 'BEZEL STYLE', 
                      'TERMINALS', 'BEZEL FINISH', 'TYPE OF ILLUMINATION', 
                      'LED COLOR', 'VOLTAGE', 'SEALING']
    
    pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
    print(f"Found {len(pdf_files)} PDF files.")
    
    results = []
    for filename in pdf_files:
        with open(filename, 'rb') as f:
            data = extract_from_buffer(f, filename)
            data['MODEL_CODE'] = data.get('SERIES', 'Unknown')
            results.append(data)
    
    if results:
        df = pd.DataFrame(results)
        df = df.reindex(columns=target_columns)
        df.to_excel('Project_ScrAPEM_Master.xlsx', index=False)
        print(f"Saved {len(results)} entries.")


if __name__ == "__main__":
    main()
