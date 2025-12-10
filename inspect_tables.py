import pdfplumber

pdf_path = 'XP series datasheet.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    for i, page in enumerate(pdf.pages):
        print(f"--- Page {i+1} Tables ---")
        tables = page.extract_tables()
        for j, table in enumerate(tables):
            print(f"Table {j+1} (first 3 rows):")
            for row in table[:3]:
                print(row)
        print("\n")
