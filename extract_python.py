#!/usr/bin/env python3
"""
ScrAPEM Python Extraction Module
Enhanced extraction logic with exhaustive search, multi-product support, and confidence tracking.
"""

import pdfplumber
import re
from pathlib import Path


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
# EXTRACTION METADATA - CONFIDENCE & SOURCE TRACKING
# =============================================================================

class ExtractionResult:
    """Stores extracted value with confidence and source metadata."""
    def __init__(self, value, confidence='medium', page=None, source=None, matched_text=None):
        self.value = value
        self.confidence = confidence  # 'high', 'medium', 'low'
        self.page = page
        self.source = source  # e.g., 'LED Color Table', 'Ordering Information'
        self.matched_text = matched_text  # The actual text that was matched
    
    def to_dict(self):
        return {
            'value': self.value,
            'confidence': self.confidence,
            'page': self.page,
            'source': self.source,
            'matched_text': self.matched_text
        }


def get_confidence_icon(confidence):
    """Return emoji icon for confidence level."""
    icons = {
        'high': '🟢',
        'medium': '🟡', 
        'low': '🔴'
    }
    return icons.get(confidence, '⚪')


def create_validation_metadata():
    """Create empty validation metadata dict for a result."""
    return {
        '_validation': {}  # Will store field -> ExtractionResult.to_dict()
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
# PRODUCT TYPE DETECTION
# =============================================================================

PRODUCT_TYPES = {
    'led_indicator': {
        'description': 'Pilot Lights, Switches & Indicators - Panel mount LED illuminated devices',
        'keywords': ['indicator', 'pilot light', 'pushbutton', 'illuminated', 'LED lens', 'panel mount indicator'],
        'columns': ['SERIES', 'MOUNTING HOLE', 'BEZEL STYLE', 'TERMINALS', 'BEZEL FINISH', 
                    'TYPE OF ILLUMINATION', 'LED COLOR', 'VOLTAGE', 'SEALING']
    },
    'paddle_joystick': {
        'description': 'Paddle Joystick Controllers - Hall effect non-contacting technology',
        'keywords': ['paddle joystick', 'paddle controller', 'BHN series'],
        'columns': ['SERIES', 'CONFIGURATION', 'GAIN', 'LEVER OPERATION', 'HANDLE', 
                    'DETAIL COLOR', 'SWITCHING POINTS', 'MODIFIER']
    },
    'thumbstick_joystick': {
        'description': 'Multi-function Hand Grip Controllers - Proportional joystick with buttons',
        'keywords': ['hand grip controller', 'CJ series', 'multi-function hand grip', 'fingertip joystick'],
        'columns': ['SERIES', 'LOWER FACE BUTTONS', 'UPPER FACE BUTTONS', 'OPERATOR PRESENCE PADDLE',
                    'LIMITER PLATE', 'SPRING TENSION', 'OUTPUT OPTIONS', 'ADDITIONAL OPTIONS']
    },
    'fingertip_joystick': {
        'description': 'Fingertip Controllers - Low profile proportional Hall effect joysticks',
        'keywords': ['fingertip controller', 'XS series', 'proportional fingertip'],
        'columns': ['SERIES', 'CONFIGURATION', 'AXIS', 'OUTPUT', 'VOLTAGE', 'SEALING', 
                    'MOUNTING', 'OPTIONS']
    },
    'terminal_block': {
        'description': 'Terminal Blocks - DIN rail mounted wiring connection blocks',
        'keywords': ['terminal block', 'BN-W', 'BNH-W', 'touch-down terminal'],
        'columns': ['SERIES', 'TERMINAL TYPE', 'WIRE RANGE', 'RATING', 'MOUNTING', 
                    'CERTIFICATIONS', 'MATERIAL', 'MARKING']
    }
}


def detect_product_type(text, filename):
    """
    Detect product type from PDF content and filename.
    Returns: 'led_indicator', 'paddle_joystick', 'thumbstick_joystick', or 'unknown'
    """
    text_lower = text.lower()
    filename_lower = filename.lower()
    
    # Check specific series names first (most reliable)
    if 'bhn' in filename_lower or 'bhn series' in text_lower:
        return 'paddle_joystick'
    
    if 'cj' in filename_lower.split('_')[0] or 'cj series' in text_lower:
        return 'thumbstick_joystick'
    
    # XS series - fingertip controller
    if 'xs' in filename_lower.split()[0].lower() or 'xs series' in text_lower:
        return 'fingertip_joystick'
    
    # FT1J/FT2J - Controller with Operator Interface (check before terminal block)
    if 'ft1j' in filename_lower or 'ft2j' in filename_lower or 'controller with operator interface' in text_lower:
        return 'led_indicator'  # Use LED indicator schema for now (has similar fields)
    
    # HS1T - Interlock Switch with Solenoid
    if 'hs1t' in filename_lower or 'interlock switch' in text_lower:
        return 'led_indicator'  # Use LED indicator schema for now
    
    # BN series - terminal blocks (specific filename check only)
    if 'bn-w' in filename_lower or 'bnh-w' in filename_lower:
        return 'terminal_block'
    
    # Check for paddle joystick keywords
    if 'paddle joystick' in text_lower or 'paddle controller' in text_lower:
        return 'paddle_joystick'
    
    # Check for thumbstick/hand grip joystick keywords  
    if 'hand grip' in text_lower or 'fingertip joystick' in text_lower:
        return 'thumbstick_joystick'
    
    # Check for fingertip controller keywords
    if 'fingertip controller' in text_lower or 'proportional fingertip' in text_lower:
        return 'fingertip_joystick'
    
    # Check for LED indicator keywords
    for keyword in PRODUCT_TYPES['led_indicator']['keywords']:
        if keyword.lower() in text_lower:
            return 'led_indicator'
    
    # Default to LED indicator for unknown products  
    return 'led_indicator'


# =============================================================================
# PADDLE JOYSTICK (BHN) EXTRACTION
# =============================================================================

def extract_paddle_joystick_data(text, tables, filename):
    """Extract data for paddle joystick products like BHN."""
    result = {col: 'N/A' for col in PRODUCT_TYPES['paddle_joystick']['columns']}
    result['SERIES'] = extract_series_from_filename(filename)
    result['_PRODUCT_TYPE'] = 'Paddle Joystick'
    
    # Extract Configuration (Standard Dual Outputs, Inverse Dual Outputs, PWM)
    config_patterns = [
        (r'1[:\s]*Standard\s*Dual\s*Outputs?', '1: Standard Dual Outputs'),
        (r'2[:\s]*Inverse\s*Dual\s*Outputs?', '2: Inverse Dual Outputs'),
        (r'3[:\s]*PWM', '3: PWM'),
    ]
    configs = []
    for pattern, label in config_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            configs.append(label)
    if configs:
        result['CONFIGURATION'] = '{\n' + '|\n'.join(configs) + '\n}'
    
    # Extract Gain options
    gain_patterns = re.findall(r'(\d+)[:\s]*[±]?(\d+)%\s*[xX×]?\s*V', text)
    if gain_patterns:
        gains = [f"{g[0]}: ±{g[1]}%xV" for g in gain_patterns]
        result['GAIN'] = '{\n' + '|\n'.join(gains) + '\n}'
    
    # Extract Lever Operation (Detents, Sprung)
    lever_ops = []
    detent_patterns = [
        (r'D0?1[:\s]*Centre\s*Detent', 'D01: Centre Detent'),
        (r'D0?2[:\s]*15°?\s*Detents?', 'D02: 15° Detents'),
        (r'D0?3[:\s]*15°?\s*&\s*30°?\s*Detents?', 'D03: 15° & 30° Detents'),
        (r'D0?4[:\s]*30°?\s*Detents?', 'D04: 30° Detents'),
        (r'SD1[:\s]*Sprung\s*to\s*Centre', 'SD1: Sprung to Centre with D1'),
        (r'SD2[:\s]*Sprung\s*to\s*Centre', 'SD2: Sprung to Centre with D2'),
        (r'SD3[:\s]*Sprung\s*to\s*Centre', 'SD3: Sprung to Centre with D3'),
        (r'SD4[:\s]*Sprung\s*to\s*Centre', 'SD4: Sprung to Centre with D4'),
    ]
    for pattern, label in detent_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            lever_ops.append(label)
    if lever_ops:
        result['LEVER OPERATION'] = '{\n' + '|\n'.join(lever_ops) + '\n}'
    
    # Extract Handle colors
    handle_colors = []
    color_patterns = [
        (r'BK[:\s]*Black', 'BK: Black'),
        (r'RE[:\s]*Red', 'RE: Red'),
        (r'BL[:\s]*Blue', 'BL: Blue'),
        (r'YE[:\s]*Yellow', 'YE: Yellow'),
        (r'GR[:\s]*Green', 'GR: Green'),
    ]
    for pattern, label in color_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            handle_colors.append(label)
    if handle_colors:
        result['DETAIL COLOR'] = '{\n' + '|\n'.join(handle_colors) + '\n}'
    
    # Extract Handle (typically just Black)
    if re.search(r'handle.*black|black.*handle', text, re.IGNORECASE):
        result['HANDLE'] = '{BK: Black}'
    
    # Extract Switching Points
    switch_pts = []
    switch_patterns = [
        (r'00[:\s]*No\s*Switch', '00: No Switches'),
        (r'05[:\s]*[±]?5\s*Degrees?', '05: ±5 Degrees'),
        (r'15[:\s]*[±]?15\s*Degrees?', '15: ±15 Degrees'),
        (r'30[:\s]*[±]?30\s*Degrees?', '30: ±30 Degrees'),
    ]
    for pattern, label in switch_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            switch_pts.append(label)
    if switch_pts:
        result['SWITCHING POINTS'] = '{\n' + '|\n'.join(switch_pts) + '\n}'
    
    # Extract Modifier
    result['MODIFIER'] = '{00: None}'
    
    return result


# =============================================================================
# THUMBSTICK JOYSTICK (CJ) EXTRACTION
# =============================================================================

def extract_thumbstick_data(text, tables, filename):
    """Extract data for thumbstick joystick products like CJ."""
    result = {col: 'N/A' for col in PRODUCT_TYPES['thumbstick_joystick']['columns']}
    result['SERIES'] = extract_series_from_filename(filename)
    result['_PRODUCT_TYPE'] = 'Thumbstick Joystick'
    
    # Extract Lower Face Buttons
    lower_buttons = []
    lower_patterns = [
        (r'N[:\s]*None', 'N: None'),
        (r'A[:\s]*One\s*switch\s*in\s*position\s*A', 'A: One switch in position A'),
        (r'B[:\s]*One\s*switch\s*in\s*position\s*B', 'B: One switch in position B'),
        (r'C[:\s]*One\s*switch\s*in\s*center', 'C: One switch in center'),
        (r'W[:\s]*Two\s*switches', 'W: Two switches'),
        (r'X[:\s]*Custom', 'X: Custom¹'),
    ]
    for pattern, label in lower_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            lower_buttons.append(label)
    if lower_buttons:
        result['LOWER FACE BUTTONS'] = '{\n' + '|\n'.join(lower_buttons) + '\n}'
    
    # Extract Upper Face Buttons
    upper_buttons = []
    upper_patterns = [
        (r'0[:\s]*None', '0: None'),
        (r'1[:\s]*One\b', '1: One'),
        (r'2[:\s]*Two\b', '2: Two'),
        (r'3[:\s]*Three', '3: Three'),
        (r'4[:\s]*Four', '4: Four'),
        (r'5[:\s]*Five', '5: Five'),
        (r'6[:\s]*Six', '6: Six'),
    ]
    for pattern, label in upper_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            upper_buttons.append(label)
    if upper_buttons:
        result['UPPER FACE BUTTONS'] = '{\n' + '|\n'.join(upper_buttons) + '\n}'
    
    # Extract Operator Presence Paddle
    if re.search(r'operator\s*presence\s*paddle', text, re.IGNORECASE):
        result['OPERATOR PRESENCE PADDLE'] = '{\nN: None|\nD: Operator presence paddle\n}'
    
    # Extract Limiter Plate shapes
    plates = []
    plate_patterns = [
        (r'S[:\s]*Square', 'S: Square'),
        (r'R[:\s]*Round', 'R: Round'),
        (r'X[:\s]*Slotted\s*horizontal', 'X: Slotted horizontal'),
        (r'Y[:\s]*Slotted\s*vertical', 'Y: Slotted vertical'),
        (r'P[:\s]*Plus', 'P: Plus'),
        (r'D[:\s]*Diamond', 'D: Diamond'),
        (r'G[:\s]*Guided\s*feel\s*square', 'G: Guided feel square'),
        (r'H[:\s]*Guided\s*feel\s*round', 'H: Guided feel round'),
    ]
    for pattern, label in plate_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            plates.append(label)
    if plates:
        result['LIMITER PLATE'] = '{\n' + '|\n'.join(plates) + '\n}'
    
    # Extract Spring Tension
    result['SPRING TENSION'] = '{\n0: Standard\n}'
    
    # Extract Output Options
    outputs = []
    output_patterns = [
        (r'00[:\s]*0V\s*to\s*5V\b', '00: 0V to 5V'),
        (r'01[:\s]*0\.5V\s*to\s*4\.5V', '01: 0.5V to 4.5V'),
        (r'02[:\s]*0\.25V\s*to\s*4\.75V', '02: 0.25V to 4.75V'),
        (r'03[:\s]*1V\s*to\s*4V', '03: 1V to 4V'),
        (r'13[:\s]*USB', '13: USB'),
        (r'14[:\s]*Cursor', '14: Cursor emulation'),
        (r'15[:\s]*CAN\s*bus\s*J1939', '15: CAN bus J1939'),
        (r'16[:\s]*CANopen', '16: CANopen'),
    ]
    for pattern, label in output_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            outputs.append(label)
    if outputs:
        result['OUTPUT OPTIONS'] = '{\n' + '|\n'.join(outputs) + '\n}'
    
    # Extract Additional Options
    addl_opts = []
    addl_patterns = [
        (r'N[:\s]*None', 'N: None'),
        (r'V[:\s]*Voltage\s*regulator', 'V: Voltage regulator²'),
        (r'E[:\s]*Environmental\s*sealing', 'E: Environmental sealing*'),
    ]
    for pattern, label in addl_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            addl_opts.append(label)
    if addl_opts:
        result['ADDITIONAL OPTIONS'] = '{\n' + '|\n'.join(addl_opts) + '\n}'
    
    return result


# =============================================================================
# FINGERTIP JOYSTICK (XS) EXTRACTION
# =============================================================================

def extract_fingertip_joystick_data(text, tables, filename):
    """Extract data for fingertip controller products like XS series."""
    result = {col: 'N/A' for col in PRODUCT_TYPES['fingertip_joystick']['columns']}
    result['SERIES'] = extract_series_from_filename(filename)
    result['_PRODUCT_TYPE'] = 'Fingertip Joystick'
    
    # Extract Configuration
    configs = []
    config_patterns = [
        (r'1[:\s]*One\s*axis', '1: One axis'),
        (r'2[:\s]*Two\s*axis', '2: Two axis'),
        (r'5V\s*operation', '5V operation'),
        (r'3\.3\s*V', '3.3V operation'),
    ]
    for pattern, label in config_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            configs.append(label)
    if configs:
        result['CONFIGURATION'] = '{\\n' + '|\\n'.join(configs) + '\\n}'
    
    # Extract Axis options
    if 'one axis' in text.lower() and 'two axis' in text.lower():
        result['AXIS'] = '{1: One axis|2: Two axis}'
    elif 'two axis' in text.lower():
        result['AXIS'] = '{2: Two axis}'
    elif 'one axis' in text.lower():
        result['AXIS'] = '{1: One axis}'
    
    # Extract Output options (Analog, PWM)
    outputs = []
    if 'analog' in text.lower():
        outputs.append('Analog')
    if 'pwm' in text.lower():
        outputs.append('PWM')
    if outputs:
        result['OUTPUT'] = '{' + '|'.join(outputs) + '}'
    
    # Extract Voltage
    voltages = []
    if '5 v' in text.lower() or '5v' in text.lower():
        voltages.append('5V')
    if '3.3 v' in text.lower() or '3.3v' in text.lower():
        voltages.append('3.3V')
    if voltages:
        result['VOLTAGE'] = '{' + '|'.join(voltages) + '}'
    
    # Extract Sealing
    sealing = re.search(r'IP\d+', text, re.IGNORECASE)
    if sealing:
        result['SEALING'] = '{' + sealing.group() + '}'
    
    # Extract Mounting 
    if 'panel' in text.lower():
        result['MOUNTING'] = '{Panel Mount}'
    
    # Extract Options
    options = []
    if 'pushbutton' in text.lower():
        options.append('Pushbutton')
    if 'boot' in text.lower():
        options.append('Boot')
    if options:
        result['OPTIONS'] = '{' + '|'.join(options) + '}'
    
    return result


# =============================================================================
# TERMINAL BLOCK (BN) EXTRACTION
# =============================================================================

def extract_terminal_block_data(text, tables, filename):
    """Extract data for terminal block products like BN series."""
    result = {col: 'N/A' for col in PRODUCT_TYPES['terminal_block']['columns']}
    result['SERIES'] = extract_series_from_filename(filename)
    result['_PRODUCT_TYPE'] = 'Terminal Block'
    
    # Extract Terminal Type
    types = []
    if 'touch-down' in text.lower() or 'touchdown' in text.lower():
        types.append('Touch-down')
    if 'screw' in text.lower():
        types.append('Screw')
    if 'stud' in text.lower():
        types.append('Stud')
    if types:
        result['TERMINAL TYPE'] = '{' + '|'.join(types) + '}'
    
    # Extract Wire Range (AWG patterns)
    wire_patterns = re.findall(r'(\d+)\s*(?:to|~|-)\s*(\d+)\s*AWG', text, re.IGNORECASE)
    if wire_patterns:
        ranges = [f"{p[0]}-{p[1]} AWG" for p in wire_patterns]
        result['WIRE RANGE'] = '{' + '|'.join(set(ranges)) + '}'
    
    # Extract Rating (Voltage/Current)
    ratings = []
    voltage_match = re.search(r'(\d+)\s*V(?:AC|DC)?', text)
    current_match = re.search(r'(\d+)\s*A\b', text)
    if voltage_match:
        ratings.append(voltage_match.group())
    if current_match:
        ratings.append(current_match.group() + 'A')
    if ratings:
        result['RATING'] = '{' + '|'.join(ratings) + '}'
    
    # Extract Mounting
    mounting = []
    if 'din rail' in text.lower():
        mounting.append('DIN Rail')
    if '35' in text and 'mm' in text.lower():
        mounting.append('35mm DIN Rail')
    if 'iec' in text.lower():
        mounting.append('IEC Type C Rail')
    if mounting:
        result['MOUNTING'] = '{' + '|'.join(mounting) + '}'
    
    # Extract Certifications
    certs = []
    if 'ul' in text.lower():
        certs.append('UL')
    if 'csa' in text.lower():
        certs.append('CSA')
    if 'tüv' in text.lower() or 'tuv' in text.lower():
        certs.append('TÜV')
    if certs:
        result['CERTIFICATIONS'] = '{' + '|'.join(certs) + '}'
    
    # Extract Material
    if 'ul94v-0' in text.lower() or 'ul 94v-0' in text.lower():
        result['MATERIAL'] = '{UL94V-0}'
    
    # Extract Marking
    if 'marking strip' in text.lower():
        result['MARKING'] = '{Marking strip available}'
    
    return result


# =============================================================================
# LED INDICATOR EXTRACTION (EXISTING)
# =============================================================================

def extract_led_indicator_data(text, tables, filename):
    """Extract data for LED indicator products (original extraction logic)."""
    result = {col: 'N/A' for col in PRODUCT_TYPES['led_indicator']['columns']}
    result['SERIES'] = extract_series_from_filename(filename)
    result['_PRODUCT_TYPE'] = 'LED Indicator'
    
    result['MOUNTING HOLE'] = extract_mounting_hole(text, tables)
    result['VOLTAGE'] = extract_voltage(text, tables)
    result['SEALING'] = extract_sealing(text, tables)
    result['LED COLOR'] = extract_led_color(text, tables)
    result['TYPE OF ILLUMINATION'] = extract_illumination_type(text, tables)
    result['BEZEL STYLE'] = extract_bezel_style(text, tables)
    result['TERMINALS'] = extract_terminals(text, tables)
    result['BEZEL FINISH'] = extract_bezel_finish(text, tables)
    
    return result


def analyze_extraction_confidence(result, text, pages_text=None):
    """
    Analyze extraction results and assign confidence levels.
    Returns validation metadata dict with confidence and source for each field.
    
    Confidence levels:
    - high: Value has proper {Code:Value} format with multiple options
    - medium: Value found but incomplete format or single option
    - low: Value is N/A or potentially incorrect
    """
    validation = {}
    
    for field, value in result.items():
        if field.startswith('_'):
            continue
            
        if value == 'N/A':
            validation[field] = {
                'confidence': 'low',
                'icon': '🔴',
                'reason': 'Value not found in PDF',
                'source': None,
                'page': None
            }
        elif field == 'SERIES':
            # SERIES from filename is always high confidence
            validation[field] = {
                'confidence': 'high',
                'icon': '🟢',
                'reason': 'Extracted from filename',
                'source': 'Filename',
                'page': None
            }
        elif '{' in str(value) and ':' in str(value):
            # Proper {Code:Value} format - high confidence
            num_options = str(value).count('|') + 1 if '|' in str(value) else 1
            if num_options >= 2:
                validation[field] = {
                    'confidence': 'high',
                    'icon': '🟢',
                    'reason': f'Found {num_options} options with code format',
                    'source': 'Table/Ordering Info',
                    'page': find_value_page(value, pages_text) if pages_text else None
                }
            else:
                validation[field] = {
                    'confidence': 'medium',
                    'icon': '🟡',
                    'reason': 'Single option found',
                    'source': 'Table/Text',
                    'page': find_value_page(value, pages_text) if pages_text else None
                }
        elif '{' in str(value):
            # Has format but no code - medium confidence
            validation[field] = {
                'confidence': 'medium',
                'icon': '🟡',
                'reason': 'Value found but no code mapping',
                'source': 'Text search',
                'page': find_value_page(value, pages_text) if pages_text else None
            }
        else:
            # Basic value - medium confidence
            validation[field] = {
                'confidence': 'medium',
                'icon': '🟡',
                'reason': 'Basic value extracted',
                'source': 'Text',
                'page': None
            }
    
    return validation


def find_value_page(value, pages_text):
    """Find which page contains the extracted value."""
    if not pages_text or not value:
        return None
    
    # Clean value for search
    search_terms = []
    if '{' in str(value):
        # Extract actual values from format
        clean = str(value).replace('{', '').replace('}', '').replace('\n', ' ')
        parts = clean.split('|')
        for p in parts[:2]:  # Check first 2 options
            if ':' in p:
                search_terms.append(p.split(':')[-1].strip())
            else:
                search_terms.append(p.strip())
    else:
        search_terms.append(str(value))
    
    for page_num, page_text in enumerate(pages_text, 1):
        for term in search_terms:
            if term.lower() in page_text.lower():
                return page_num
    
    return None


def calculate_overall_confidence(validation):
    """Calculate overall confidence score from validation metadata."""
    if not validation:
        return 0, 'low'
    
    scores = {'high': 3, 'medium': 2, 'low': 1}
    total_score = 0
    count = 0
    
    for field, meta in validation.items():
        conf = meta.get('confidence', 'low')
        total_score += scores.get(conf, 1)
        count += 1
    
    if count == 0:
        return 0, 'low'
    
    avg_score = total_score / count
    
    if avg_score >= 2.5:
        return int((avg_score / 3) * 100), 'high'
    elif avg_score >= 1.8:
        return int((avg_score / 3) * 100), 'medium'
    else:
        return int((avg_score / 3) * 100), 'low'


# =============================================================================
# MAIN PDF PARSING FUNCTION
# =============================================================================

def parse_pdf(file_path, filename):
    """Main extraction function with auto product type detection."""
    try:
        pdf = pdfplumber.open(file_path)
        
        all_text = ""
        all_tables = []
        pages_text = []  # Track text per page for source reference
        
        # Extract from ALL pages
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n"
                pages_text.append(page_text)
            else:
                pages_text.append("")
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)
        
        pdf.close()
        
        # Detect product type
        product_type = detect_product_type(all_text, filename)
        
        # Extract based on product type
        if product_type == 'paddle_joystick':
            result = extract_paddle_joystick_data(all_text, all_tables, filename)
        elif product_type == 'thumbstick_joystick':
            result = extract_thumbstick_data(all_text, all_tables, filename)
        elif product_type == 'fingertip_joystick':
            result = extract_fingertip_joystick_data(all_text, all_tables, filename)
        elif product_type == 'terminal_block':
            result = extract_terminal_block_data(all_text, all_tables, filename)
        else:
            result = extract_led_indicator_data(all_text, all_tables, filename)
        
        # Add validation metadata
        validation = analyze_extraction_confidence(result, all_text, pages_text)
        overall_score, overall_conf = calculate_overall_confidence(validation)
        result['_validation'] = validation
        result['_confidence_score'] = overall_score
        result['_confidence_level'] = overall_conf
        
        return result
        
    except Exception as e:
        # Return basic result on error
        return {
            'SERIES': extract_series_from_filename(filename),
            '_PRODUCT_TYPE': 'Unknown',
            '_validation': {},
            '_confidence_score': 0,
            '_confidence_level': 'low',
            'ERROR': str(e)
        }


def extract_from_buffer(pdf_buffer, filename):
    """
    Extract data from a PDF file buffer (for Streamlit uploads).
    
    Args:
        pdf_buffer: File-like object (e.g., Streamlit UploadedFile)
        filename: Original filename for series detection
        
    Returns:
        dict with extracted data and confidence metadata
    """
    try:
        pdf = pdfplumber.open(pdf_buffer)
        
        all_text = ""
        all_tables = []
        pages_text = []
        
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n"
                pages_text.append(page_text)
            else:
                pages_text.append("")
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)
        
        pdf.close()
        
        # Detect product type
        product_type = detect_product_type(all_text, filename)
        
        # Extract based on product type
        if product_type == 'paddle_joystick':
            result = extract_paddle_joystick_data(all_text, all_tables, filename)
        elif product_type == 'thumbstick_joystick':
            result = extract_thumbstick_data(all_text, all_tables, filename)
        elif product_type == 'fingertip_joystick':
            result = extract_fingertip_joystick_data(all_text, all_tables, filename)
        elif product_type == 'terminal_block':
            result = extract_terminal_block_data(all_text, all_tables, filename)
        else:
            result = extract_led_indicator_data(all_text, all_tables, filename)
        
        # Add validation metadata
        validation = analyze_extraction_confidence(result, all_text, pages_text)
        overall_score, overall_conf = calculate_overall_confidence(validation)
        result['_validation'] = validation
        result['_confidence_score'] = overall_score
        result['_confidence_level'] = overall_conf
        result['_raw_text'] = all_text  # Include for AI enhancement
        result['_pages_text'] = pages_text
        
        return result
        
    except Exception as e:
        return {
            'SERIES': extract_series_from_filename(filename),
            '_PRODUCT_TYPE': 'Unknown',
            '_validation': {},
            '_confidence_score': 0,
            '_confidence_level': 'low',
            'ERROR': str(e)
        }


def get_low_confidence_fields(result):
    """
    Get list of fields that need AI enhancement.
    Returns fields with 'low' confidence or N/A values.
    """
    low_conf_fields = []
    validation = result.get('_validation', {})
    
    for field, meta in validation.items():
        if meta.get('confidence') == 'low' or meta.get('source') is None:
            value = result.get(field, 'N/A')
            low_conf_fields.append({
                'field': field,
                'current_value': value,
                'reason': meta.get('reason', 'Unknown'),
                'confidence': meta.get('confidence', 'low')
            })
    
    return low_conf_fields
