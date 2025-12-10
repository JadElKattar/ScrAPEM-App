"""
Merge Results Module - Option 2: AI + Python Filter

AI extracts MODEL_CODEs → Python validates each → Stable count
"""


def validate_model_code(code, series_name):
    """
    Python validation rules for MODEL_CODEs.
    Returns True if code looks like a valid orderable part number.
    """
    if not code or not isinstance(code, str):
        return False
    
    code = code.strip().upper()
    series = series_name.upper() if series_name else ""
    
    # Basic length check
    if len(code) < 5 or len(code) > 30:
        return False
    
    # No spaces
    if ' ' in code:
        return False
    
    # Garbage words to reject
    garbage = ['CIRCUIT', 'EXAMPLE', 'NOTE', 'FIGURE', 'TABLE', 'PAGE', 
               'DIMENSION', 'SPECIFICATION', 'MOUNTING', 'TERMINAL']
    for g in garbage:
        if g in code:
            return False
    
    # Should contain at least one letter and one digit
    has_letter = any(c.isalpha() for c in code)
    has_digit = any(c.isdigit() for c in code)
    if not (has_letter and has_digit):
        return False
    
    # Prefer codes that start with series name (but don't require it)
    # This gives higher confidence
    
    return True


def merge_ai_with_python_filter(ai_products, python_specs, series_name):
    """
    Option 2: AI extracts MODEL_CODEs, Python filters them.
    
    - AI finds all potential MODEL_CODEs
    - Python validates each one
    - Python specs applied to all valid codes
    """
    target_columns = [
        'SERIES', 'MODEL_CODE', 'MOUNTING HOLE', 'BEZEL STYLE', 'TERMINALS',
        'BEZEL FINISH', 'TYPE OF ILLUMINATION', 'LED COLOR', 'VOLTAGE', 'SEALING'
    ]
    
    products = []
    seen_codes = set()
    
    # Handle both old and new python_specs formats
    if isinstance(python_specs, dict) and 'specs' in python_specs:
        specs = python_specs.get('specs', {})
    else:
        specs = python_specs
    
    # If AI found products, filter and use them
    if ai_products:
        for ai_prod in ai_products:
            model_code = ai_prod.get('MODEL_CODE')
            
            # Skip if no model code or already seen
            if not model_code or model_code.upper() in seen_codes:
                continue
            
            # Validate with Python rules
            if not validate_model_code(model_code, series_name):
                continue
            
            seen_codes.add(model_code.upper())
            
            # Build product with Python specs + AI data
            product = {}
            for col in target_columns:
                if col == 'MODEL_CODE':
                    product[col] = model_code
                elif col == 'SERIES':
                    product[col] = specs.get('SERIES') or ai_prod.get('SERIES') or series_name
                else:
                    # Prefer Python specs, fallback to AI
                    py_val = specs.get(col)
                    ai_val = ai_prod.get(col)
                    
                    if py_val and py_val not in [None, "", "null", "N/A"]:
                        product[col] = py_val
                    elif ai_val and ai_val not in [None, "", "null", "N/A"]:
                        product[col] = ai_val
                    else:
                        product[col] = None
            
            products.append(product)
    
    # Fallback: if no valid products, create single row from specs
    if not products:
        product = {}
        for col in target_columns:
            val = specs.get(col)
            if val in [None, "", "null", "N/A"]:
                product[col] = None
            else:
                product[col] = val
        if not product.get('MODEL_CODE'):
            product['MODEL_CODE'] = specs.get('SERIES', 'Unknown')
        products.append(product)
    
    return products


def format_for_output(products):
    """Format products for final XLSX output."""
    target_columns = [
        'SERIES', 'MODEL_CODE', 'MOUNTING HOLE', 'BEZEL STYLE', 'TERMINALS',
        'BEZEL FINISH', 'TYPE OF ILLUMINATION', 'LED COLOR', 'VOLTAGE', 'SEALING'
    ]
    
    formatted_products = []
    for product in products:
        formatted = {}
        for col in target_columns:
            val = product.get(col)
            if val is None:
                formatted[col] = None
            elif isinstance(val, list):
                clean_vals = [str(v) for v in val if v]
                if len(clean_vals) == 0:
                    formatted[col] = None
                elif len(clean_vals) == 1:
                    formatted[col] = clean_vals[0]
                else:
                    formatted[col] = "{" + "|".join(clean_vals) + "}"
            else:
                formatted[col] = str(val)
        formatted_products.append(formatted)
    
    return formatted_products


# Legacy function for backwards compatibility
def merge_product_data(ai_products, python_data):
    """Main entry point - uses AI + Python filter approach."""
    # Extract series name
    if isinstance(python_data, dict) and 'specs' in python_data:
        series = python_data.get('specs', {}).get('SERIES', '')
    elif isinstance(python_data, dict):
        series = python_data.get('SERIES', '')
    else:
        series = ''
    
    return merge_ai_with_python_filter(ai_products, python_data, series)
