import pdfplumber
import re

pdf_path = 'XP series datasheet.pdf'

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if text and (re.search(r'(?i)ordering information', text) or re.search(r'(?i)part number', text)):
            print(f"--- Page {i+1} Match ---")
            print(text)
