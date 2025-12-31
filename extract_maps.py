"""Extract mission maps from PDF to individual image files."""

import fitz  # PyMuPDF
from pathlib import Path

def extract_mission_maps():
    """Extract each page from the maps PDF as a separate image."""
    pdf_path = Path("references/Lone_U-Boat_-_Maps_only.pdf")
    output_dir = Path("assets/maps")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Open the PDF
    pdf_document = fitz.open(pdf_path)
    
    print(f"Found {len(pdf_document)} pages in PDF")
    
    # Extract each page
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        
        # Render page to an image (300 DPI for good quality)
        mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
        pix = page.get_pixmap(matrix=mat)
        
        # Save as PNG
        output_path = output_dir / f"mission_{page_num + 1}.png"
        pix.save(output_path)
        print(f"Extracted Mission {page_num + 1} to {output_path}")
    
    pdf_document.close()
    print("\nAll maps extracted successfully!")

if __name__ == "__main__":
    extract_mission_maps()
