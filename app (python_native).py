#!/usr/bin/env python3
"""
ScrAPEM - Intelligent Datasheet Extractor (Final Version)
Enhanced extraction logic with exhaustive search and standardized formatting.
"""

import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
from pathlib import Path
import tempfile
import os


# =============================================================================
# STANDARD CODE MAPPINGS FOR LED COLORS
# =============================================================================

LED_COLOR_CODES = {
    'red': 'R',
    'green': 'G',
    'blue': 'B',
    'white': 'W',
    'amber': 'A',
    'yellow': 'Y',
    'orange': 'O',
    'clear': 'C',
    'warm white': 'WW',
    'cool white': 'CW',
    'pink': 'P',
    'purple': 'PR',
    'bi-color': 'BC',
    'rgb': 'RGB',
    'multicolor': 'MC',
}


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


# Acronyms that should stay uppercase
UPPERCASE_ACRONYMS = ['LED', 'RGB', 'SMD', 'PCB', 'AC', 'DC', 'IP']


def proper_capitalize(value):
    """
    Capitalize a value but keep acronyms uppercase.
    'led' -> 'LED', 'red' -> 'Red', 'smd' -> 'SMD'
    """
    if not value:
        return value
    
    # Check if it's an acronym
    if value.upper() in UPPERCASE_ACRONYMS:
        return value.upper()
    
    # Otherwise use standard capitalize
    return value.capitalize()


def get_color_code(color_name):
    """Get standard code for a color. Falls back to first letter."""
    color_lower = color_name.lower().strip()
    if color_lower in LED_COLOR_CODES:
        return LED_COLOR_CODES[color_lower]
    # Fallback: use first letter uppercase
    return color_name[0].upper() if color_name else 'X'


def format_led_colors_with_codes(colors_dict, colors_list):
    """
    Format LED colors ALWAYS as {Code:Value|Code:Value}.
    Uses discovered codes or infers from standard mappings.
    """
    if not colors_dict and not colors_list:
        return "N/A"
    
    formatted_items = []
    used_colors = set()
    
    # First add items with discovered codes
    for code, color in colors_dict.items():
        formatted_items.append(f"{code}:{color}")
        used_colors.add(color.lower())
    
    # Then add colors without codes - ALWAYS generate a code
    for color in colors_list:
        if color.lower() not in used_colors:
            code = get_color_code(color)
            formatted_items.append(f"{code}:{color}")
            used_colors.add(color.lower())
    
    if not formatted_items:
        return "N/A"
    
    return "{" + "|".join(formatted_items) + "}"


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
    """
    Exhaustively search ALL table cells for values.
    Returns: (code_dict, value_list)
    """
    found_codes = {}
    found_values = []
    
    for table in tables:
        if not table:
            continue
        for row in table:
            if not row:
                continue
            
            # Join all cells for text search
            row_text = ' '.join([str(c).lower() if c else '' for c in row])
            
            # Check each value in our list
            for value in value_list:
                if value.lower() in row_text:
                    # Found a match - look for adjacent code
                    for i, cell in enumerate(row):
                        if not cell:
                            continue
                        cell_str = str(cell).strip()
                        
                        if value.lower() in cell_str.lower():
                            # Found the value, check adjacent cells for code
                            if find_codes:
                                # Check previous cell
                                if i > 0 and row[i-1]:
                                    prev = str(row[i-1]).strip()
                                    if len(prev) <= 3 and prev.replace('*', '').isalpha():
                                        found_codes[prev.upper()] = proper_capitalize(value)
                                # Check next cell
                                if i < len(row) - 1 and row[i+1]:
                                    next_cell = str(row[i+1]).strip()
                                    if len(next_cell) <= 3 and next_cell.replace('*', '').isalpha():
                                        found_codes[next_cell.upper()] = proper_capitalize(value)
                            
                            # Add to found values
                            if proper_capitalize(value) not in found_values:
                                found_values.append(proper_capitalize(value))
    
    return found_codes, found_values


def exhaustive_text_search(text, patterns):
    """
    Search entire text with multiple patterns.
    Returns ALL matches found.
    """
    all_matches = []
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]  # Get first group if tuple
            match_clean = match.strip()
            if match_clean and match_clean not in all_matches:
                all_matches.append(match_clean)
    
    return all_matches


def search_ordering_info(text, tables):
    """
    Search specifically in 'Ordering Information' or 'Part Number' sections.
    These often contain comprehensive option lists.
    """
    # Find ordering info section
    ordering_patterns = [
        r'ordering\s+information[:\s]*(.*?)(?=\n\n|\Z)',
        r'part\s+number[:\s]*(.*?)(?=\n\n|\Z)',
        r'model\s+number[:\s]*(.*?)(?=\n\n|\Z)',
        r'how\s+to\s+order[:\s]*(.*?)(?=\n\n|\Z)',
    ]
    
    ordering_text = ""
    for pattern in ordering_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            ordering_text += " " + match
    
    return ordering_text


# =============================================================================
# EXTRACTION FUNCTIONS (EXHAUSTIVE)
# =============================================================================

def extract_mounting_hole(text, tables):
    """Extract ALL mounting hole dimensions exhaustively."""
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
                if 5 <= num <= 50:  # Reasonable mounting hole range
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
    return "N/A"


def extract_voltage(text, tables):
    """Extract ALL voltage specifications exhaustively."""
    patterns = [
        r'\d+\.?\d*\s*/\s*\d+\.?\d*\s*V\s*(?:DC|AC)',
        r'\d+\.?\d*\s*V\s*(?:DC|AC)',
        r'\d+\.?\d*\s*(?:VDC|VAC)',
        r'\d+\.?\d*\s*to\s*\d+\.?\d*\s*V\s*(?:DC|AC)',
        r'\d+\.?\d*[-–]\d+\.?\d*\s*V\s*(?:DC|AC)',
    ]
    
    found_voltages = []
    voltage_codes = {}
    
    # Exhaustive text search
    all_matches = exhaustive_text_search(text, patterns)
    for match in all_matches:
        match_clean = standardize_voltage(match)
        if match_clean and not match_clean.startswith('000'):
            if match_clean.lower() not in [v.lower() for v in found_voltages]:
                found_voltages.append(match_clean)
    
    # Exhaustive table search
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
                            
                            # Check for codes in adjacent cells
                            if i > 0 and row[i-1]:
                                prev_cell = str(row[i-1]).strip()
                                if len(prev_cell) <= 3 and prev_cell.isalnum():
                                    voltage_codes[prev_cell.upper()] = match_clean
                            if i < len(row) - 1 and row[i+1]:
                                next_cell = str(row[i+1]).strip()
                                if len(next_cell) <= 3 and next_cell.isalnum():
                                    voltage_codes[next_cell.upper()] = match_clean
    
    # Format output
    if voltage_codes:
        formatted = "|".join([f"{code}:{val}" for code, val in voltage_codes.items()])
        result = "{" + formatted + "}"
    elif found_voltages:
        formatted = "|".join(found_voltages[:12])
        result = "{" + formatted + "}"
    else:
        return "N/A"
    
    return clean_and_dedupe_values(result, 'voltage')


def extract_sealing(text, tables):
    """Extract ALL IP ratings exhaustively."""
    patterns = [r'IP\s*\d{2}[A-Z]?', r'IP\s*\d{2}']
    
    found_ratings = []
    rating_codes = {}
    
    # Exhaustive text search
    all_matches = exhaustive_text_search(text, patterns)
    for match in all_matches:
        rating = match.replace(' ', '').upper()
        if rating and rating not in found_ratings:
            found_ratings.append(rating)
    
    # Exhaustive table search
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
                        
                        # Check for codes
                        if i > 0 and row[i-1]:
                            code = str(row[i-1]).strip()
                            if len(code) <= 2 and code.isalpha():
                                rating_codes[code.upper()] = rating
    
    # Format output
    if rating_codes:
        formatted = "|".join([f"{code}:{val}" for code, val in rating_codes.items()])
        return "{" + formatted + "}"
    elif found_ratings:
        formatted = "|".join([f"E:{r}" for r in found_ratings])
        return "{" + formatted + "}"
    
    return "N/A"


def extract_led_color(text, tables):
    """
    Extract LED colors with comprehensive approach.
    1. Tables: Look for color+code pairs OR colors in LED-context rows
    2. Text: Strict LED context patterns
    ALWAYS returns {Code:Value} format.
    """
    colors = ['red', 'green', 'amber', 'yellow', 'white', 'blue', 
              'orange', 'warm white', 'cool white', 'pink', 
              'purple', 'bi-color', 'rgb', 'multicolor']
    
    # Keywords that indicate a LED-related table row
    table_context_keywords = [
        'led', 'color', 'colour', 'lamp', 'lens', 'indicator', 
        'cap', 'light', 'backlight', 'illumination'
    ]
    
    found_codes = {}
    found_colors = []
    
    # Helper to validate codes (1-2 letters, optionally with *)
    def is_valid_color_code(code_str):
        clean = code_str.replace('*', '').replace('-', '')
        return 1 <= len(clean) <= 2 and clean.isalpha() and clean.isupper()
    
    # 1. Search ALL tables
    for table in tables:
        if not table:
            continue
        
        # Check if table has LED-context in header (first row)
        table_header = ' '.join([str(c).lower() if c else '' for c in table[0]]) if table else ''
        table_has_context = any(kw in table_header for kw in table_context_keywords)
        
        for row in table:
            if not row or len(row) < 2:
                continue
            
            # Check if current row has context
            row_text = ' '.join([str(c).lower() if c else '' for c in row])
            row_has_context = any(kw in row_text for kw in table_context_keywords)
            
            for i in range(len(row)):
                cell = row[i]
                if not cell:
                    continue
                cell_str = str(cell).strip()
                cell_lower = cell_str.lower()
                
                for color in colors:
                    # Match exact color or color within cell
                    if cell_lower == color or cell_lower == color.replace(' ', '') or \
                       (color in cell_lower and len(cell_lower) <= len(color) + 5):
                        
                        # Look for code in adjacent cells
                        code = None
                        
                        # Check previous cell
                        if i > 0 and row[i-1]:
                            prev = str(row[i-1]).strip().upper()
                            if is_valid_color_code(prev):
                                code = prev
                        
                        # Check next cell  
                        if not code and i < len(row) - 1 and row[i+1]:
                            next_c = str(row[i+1]).strip().upper()
                            if is_valid_color_code(next_c):
                                code = next_c
                        
                        # Add if: has code OR table/row has LED context
                        if code or table_has_context or row_has_context:
                            if code:
                                found_codes[code] = proper_capitalize(color)
                            if proper_capitalize(color) not in found_colors:
                                found_colors.append(proper_capitalize(color))
    
    # 2. Search text with strict LED context patterns
    text_lower = text.lower()
    
    for color in colors:
        # Very specific patterns - must have LED-related word adjacent
        patterns = [
            rf'\b{color}\s+led\b',                    # "Red LED"
            rf'\bled\s+{color}\b',                    # "LED red"  
            rf'\bbacklight\s+{color}\b',              # "Backlight White"
            rf'\b{color}\s+backlight\b',              # "White backlight"
            rf'\b{color}\s+indicator\b',              # "Red indicator"
            rf'\b{color}\s+lamp\b',                   # "Red lamp"
            rf'\b{color}\s+lens\b',                   # "Red lens"
            rf'\billuminat\w+.*?\b{color}\b',         # "Illumination... Red"
            rf'\bcolor[:\s]+{color}\b',               # "Color: Red"
            rf'\b{color}\s+cap\b',                    # "Red cap" (for NRA style)
            rf'colored\s+cap.*?{color}',              # "Colored Cap Red"
        ]
        
        for pattern in patterns:
            if re.search(pattern, text_lower):
                if proper_capitalize(color) not in found_colors:
                    found_colors.append(proper_capitalize(color))
                break
    
    # 3. Check ordering information section
    ordering_text = search_ordering_info(text, tables).lower()
    if ordering_text:
        for color in colors:
            if re.search(rf'\b{color}\b', ordering_text):
                if proper_capitalize(color) not in found_colors:
                    found_colors.append(proper_capitalize(color))
    
    # ALWAYS format with codes (auto-generate if needed)
    return format_led_colors_with_codes(found_codes, found_colors)


def extract_illumination_type(text, tables):
    """Extract ALL illumination types exhaustively."""
    types = ['LED', 'Neon', 'Incandescent', 'Halogen', 'Lamp', 'Fluorescent', 'Filament']
    
    found_codes, found_types = exhaustive_table_search(tables, types, find_codes=True)
    
    # Also search text
    text_upper = text.upper()
    for illum_type in types:
        if illum_type.upper() in text_upper:
            if illum_type not in found_types:
                found_types.append(illum_type)
    
    # Format output
    if not found_codes and not found_types:
        return "N/A"
    
    formatted_items = []
    used = set()
    
    for code, value in found_codes.items():
        formatted_items.append(f"{code}:{value}")
        used.add(value.lower())
    
    for value in found_types:
        if value.lower() not in used:
            formatted_items.append(value)
            used.add(value.lower())
    
    return "{" + "|".join(formatted_items) + "}" if formatted_items else "N/A"


def extract_bezel_style(text, tables):
    """Extract ALL bezel styles exhaustively."""
    styles = ['Dome', 'Flat', 'Round', 'Square', 'Rectangular', 'Flush', 
              'Projected', 'Extended', 'Raised', 'Recessed', 'Convex', 'Mushroom']
    
    found_codes, found_styles = exhaustive_table_search(tables, styles, find_codes=True)
    
    # Also search text
    text_lower = text.lower()
    for style in styles:
        if style.lower() in text_lower:
            if style not in found_styles:
                found_styles.append(style)
    
    # Format output
    if not found_codes and not found_styles:
        return "N/A"
    
    formatted_items = []
    used = set()
    
    for code, value in found_codes.items():
        formatted_items.append(f"{code}:{value}")
        used.add(value.lower())
    
    for value in found_styles:
        if value.lower() not in used:
            formatted_items.append(value)
            used.add(value.lower())
    
    return "{" + "|".join(formatted_items) + "}" if formatted_items else "N/A"


def extract_terminals(text, tables):
    """Extract ALL terminal types exhaustively."""
    terminal_types = ['Solder', 'Screw', 'Quick-connect', 'Quick Connect', 
                      'Spring', 'Crimp', 'Wire', 'Tab', 'PCB', 'Through-hole', 
                      'SMD', 'Plug-in', 'Faston', 'Blade', 'Pin']
    
    found_codes, found_types = exhaustive_table_search(tables, terminal_types, find_codes=True)
    
    # Also search text
    text_lower = text.lower()
    for term_type in terminal_types:
        if term_type.lower() in text_lower:
            normalized = term_type.replace('Quick Connect', 'Quick-connect')
            if normalized not in found_types:
                found_types.append(normalized)
    
    # Format output
    if not found_codes and not found_types:
        return "N/A"
    
    formatted_items = []
    used = set()
    
    for code, value in found_codes.items():
        formatted_items.append(f"{code}:{value}")
        used.add(value.lower())
    
    for value in found_types:
        if value.lower() not in used:
            formatted_items.append(value)
            used.add(value.lower())
    
    return "{" + "|".join(formatted_items) + "}" if formatted_items else "N/A"


def extract_bezel_finish(text, tables):
    """Extract ALL bezel finishes exhaustively."""
    finishes = ['Chrome', 'Plastic', 'Metal', 'Aluminum', 'Stainless', 
                'Nickel', 'Black', 'Silver', 'Brass', 'Zinc', 'Painted', 
                'Anodized', 'Polished', 'Satin', 'Matte']
    
    found_codes, found_finishes = exhaustive_table_search(tables, finishes, find_codes=True)
    
    # Also search text
    text_lower = text.lower()
    for finish in finishes:
        if finish.lower() in text_lower:
            if finish not in found_finishes:
                found_finishes.append(finish)
    
    # Format output
    if not found_codes and not found_finishes:
        return "N/A"
    
    formatted_items = []
    used = set()
    
    for code, value in found_codes.items():
        formatted_items.append(f"{code}:{value}")
        used.add(value.lower())
    
    for value in found_finishes:
        if value.lower() not in used:
            formatted_items.append(value)
            used.add(value.lower())
    
    return "{" + "|".join(formatted_items) + "}" if formatted_items else "N/A"


# =============================================================================
# MAIN PDF PARSING FUNCTION
# =============================================================================

def parse_pdf(file_path, filename):
    """Main extraction function - exhaustive search."""
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
        result['SERIES'] = extract_series_from_filename(filename)
        
        pdf = pdfplumber.open(file_path)
        
        all_text = ""
        all_tables = []
        
        # Extract from ALL pages
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n"
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)
        
        # Run exhaustive extraction
        result['MOUNTING HOLE'] = extract_mounting_hole(all_text, all_tables)
        result['VOLTAGE'] = extract_voltage(all_text, all_tables)
        result['SEALING'] = extract_sealing(all_text, all_tables)
        result['LED COLOR'] = extract_led_color(all_text, all_tables)
        result['TYPE OF ILLUMINATION'] = extract_illumination_type(all_text, all_tables)
        result['BEZEL STYLE'] = extract_bezel_style(all_text, all_tables)
        result['TERMINALS'] = extract_terminals(all_text, all_tables)
        result['BEZEL FINISH'] = extract_bezel_finish(all_text, all_tables)
        
        pdf.close()
        
    except Exception as e:
        pass  # Silent fail, return N/A values
    
    return result


# =============================================================================
# STREAMLIT APP - POLISHED UI/UX
# =============================================================================

def main():
    # Page configuration
    st.set_page_config(
        page_title="ScrAPEM - Intelligent Datasheet Extractor",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 50%, #4a90b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #5a6c7d;
        margin-bottom: 1.5rem;
    }
    
    .step-badge {
        display: inline-block;
        background: linear-gradient(135deg, #2d5a87 0%, #4a90b8 100%);
        color: white;
        padding: 0.25rem 0.7rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #2d5a87 0%, #4a90b8 100%);
        color: white;
        font-weight: 600;
        padding: 0.6rem 1.5rem;
        border: none;
        border-radius: 10px;
        transition: all 0.3s ease;
    }
    
    .stDownloadButton > button {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        color: white;
        font-weight: 600;
        font-size: 1.1rem;
        padding: 0.75rem 2rem;
        border: none;
        border-radius: 10px;
    }
    
    .success-banner {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border-left: 4px solid #059669;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .processing-status {
        background: #f0f9ff;
        border-left: 4px solid #2d5a87;
        padding: 0.75rem 1rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        font-size: 0.95rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ==========================================================================
    # SIDEBAR WITH LOGO
    # ==========================================================================
    with st.sidebar:
        # APEM Logo at top of sidebar
        logo_path = Path(__file__).parent / "apem_logo.png"
        if logo_path.exists():
            st.image(str(logo_path), width=200)
        else:
            st.markdown("## 🏢 APEM")
        
        st.markdown("---")
        
        st.markdown("### 📋 About ScrAPEM")
        st.markdown("""
        Extracts technical specifications from PDF datasheets and exports to Excel.
        
        **Extracted Fields:**
        - Series
        - Mounting Hole
        - Bezel Style
        - Terminals
        - Bezel Finish
        - Illumination Type
        - LED Color
        - Voltage
        - Sealing (IP Rating)
        """)
        
        st.markdown("---")
        st.markdown("### 📐 Output Format")
        st.markdown("""
        All values formatted as:
        ```
        {Code:Value|Code:Value}
        ```
        Example:
        `{R:Red|G:Green|B:Blue}`
        """)
        
        st.markdown("---")
        st.caption("ScrAPEM v4.0 | Final Release")
    
    # ==========================================================================
    # MAIN CONTENT
    # ==========================================================================
    
    # Header
    col_logo, col_title = st.columns([1, 5])
    with col_title:
        st.markdown('<h1 class="main-title">📄 ScrAPEM</h1>', unsafe_allow_html=True)
        st.markdown(
            '<p class="subtitle">Intelligent Datasheet Extractor — Extract technical specifications with exhaustive search</p>',
            unsafe_allow_html=True
        )
    
    # Step 1: Upload
    st.markdown('<span class="step-badge">Step 1</span> **Upload PDF Datasheets**', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "Drag and drop PDF files here, or click to browse",
        type=['pdf'],
        accept_multiple_files=True,
        help="Upload one or more PDF product datasheets"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded and ready")
        with st.expander("📁 View uploaded files"):
            for i, f in enumerate(uploaded_files, 1):
                st.write(f"{i}. {f.name}")
    
    st.markdown("---")
    
    # Step 2: Process
    st.markdown('<span class="step-badge">Step 2</span> **Run Extraction**', unsafe_allow_html=True)
    
    # Session state
    if 'results_df' not in st.session_state:
        st.session_state.results_df = None
    if 'extraction_complete' not in st.session_state:
        st.session_state.extraction_complete = False
    if 'individual_results' not in st.session_state:
        st.session_state.individual_results = []
    
    # Process button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        start_btn = st.button(
            "🚀 Start Extraction",
            type="primary",
            use_container_width=True,
            disabled=not uploaded_files
        )
    
    # Processing logic with DYNAMIC PROGRESS BAR
    if start_btn and uploaded_files:
        st.session_state.extraction_complete = False
        st.session_state.results_df = None
        st.session_state.individual_results = []  # Store individual results
        
        st.markdown("---")
        st.markdown("### ⏳ Processing Files...")
        
        # Progress bar
        progress_bar = st.progress(0)
        
        # Status text
        status_placeholder = st.empty()
        
        results = []
        individual_results = []  # List of (filename, series, data_dict)
        total = len(uploaded_files)
        
        for i, uploaded_file in enumerate(uploaded_files):
            current = i + 1
            
            # Update status text with filename and count
            status_placeholder.markdown(
                f'<div class="processing-status">'
                f'📄 Processing file <strong>{uploaded_file.name}</strong> ({current} of {total})...'
                f'</div>',
                unsafe_allow_html=True
            )
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            try:
                data = parse_pdf(tmp_path, uploaded_file.name)
                results.append(data)
                # Store individual result with filename
                individual_results.append({
                    'filename': uploaded_file.name,
                    'series': data.get('SERIES', 'Unknown'),
                    'data': data
                })
            finally:
                os.unlink(tmp_path)
            
            # Update progress bar
            progress_bar.progress(current / total)
        
        # Clear status
        status_placeholder.empty()
        
        # Create DataFrame
        df = pd.DataFrame(results)
        column_order = [
            'SERIES', 'MOUNTING HOLE', 'BEZEL STYLE', 'TERMINALS',
            'BEZEL FINISH', 'TYPE OF ILLUMINATION', 'LED COLOR', 
            'VOLTAGE', 'SEALING'
        ]
        df = df[column_order]
        
        st.session_state.results_df = df
        st.session_state.individual_results = individual_results
        st.session_state.extraction_complete = True
        
        # Success
        progress_bar.progress(1.0)
        st.markdown(
            '<div class="success-banner">'
            '<h3 style="color: #059669; margin: 0;">✅ Extraction Complete! 🚀</h3>'
            f'<p style="color: #047857; margin: 0.5rem 0 0 0;">Successfully extracted data from {len(results)} file(s)</p>'
            '</div>',
            unsafe_allow_html=True
        )
    
    # Step 3 & 4: Results and Download
    if st.session_state.extraction_complete and st.session_state.results_df is not None:
        st.markdown("---")
        st.markdown('<span class="step-badge">Step 3</span> **Results Preview**', unsafe_allow_html=True)
        
        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("📄 Files", len(st.session_state.results_df))
        with c2:
            st.metric("📊 Columns", 9)
        with c3:
            non_na = (st.session_state.results_df != 'N/A').sum().sum()
            total = st.session_state.results_df.size
            pct = int((non_na / total) * 100)
            st.metric("✅ Coverage", f"{pct}%")
        with c4:
            st.metric("🔧 Status", "Ready")
        
        # Table
        st.dataframe(st.session_state.results_df, use_container_width=True, height=300)
        
        st.markdown("---")
        
        # Step 4: Download Options
        st.markdown('<span class="step-badge">Step 4</span> **Download Results**', unsafe_allow_html=True)
        
        # Combined Download
        st.markdown("##### 📦 Download All (Combined)")
        output_all = io.BytesIO()
        with pd.ExcelWriter(output_all, engine='openpyxl') as writer:
            st.session_state.results_df.to_excel(writer, index=False, sheet_name='All Extracted Data')
        output_all.seek(0)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.download_button(
                label="Download All - ScrAPEM_Output.xlsx",
                data=output_all,
                file_name="ScrAPEM_Output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="download_all"
            )
        
        # Individual Downloads
        if len(st.session_state.individual_results) > 1:
            st.markdown("---")
            st.markdown("##### 📄 Download Individual Files (by Series)")
            
            # Create columns for download buttons (3 per row)
            individual_results = st.session_state.individual_results
            cols_per_row = 3
            
            for i in range(0, len(individual_results), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    idx = i + j
                    if idx < len(individual_results):
                        result = individual_results[idx]
                        series_name = result['series']
                        filename = result['filename']
                        data = result['data']
                        
                        # Create individual Excel file
                        individual_output = io.BytesIO()
                        individual_df = pd.DataFrame([data])
                        column_order = [
                            'SERIES', 'MOUNTING HOLE', 'BEZEL STYLE', 'TERMINALS',
                            'BEZEL FINISH', 'TYPE OF ILLUMINATION', 'LED COLOR', 
                            'VOLTAGE', 'SEALING'
                        ]
                        individual_df = individual_df[column_order]
                        
                        with pd.ExcelWriter(individual_output, engine='openpyxl') as writer:
                            individual_df.to_excel(writer, index=False, sheet_name=series_name[:31])
                        individual_output.seek(0)
                        
                        with col:
                            st.download_button(
                                label=f"📄 {series_name}",
                                data=individual_output,
                                file_name=f"{series_name}_Output.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key=f"download_{idx}"
                            )
    
    # Footer
    st.markdown("---")
    st.caption("ScrAPEM - Intelligent Datasheet Extractor | Built with Streamlit")


if __name__ == "__main__":
    main()
