import pymupdf

def is_machine_readable(pdf_path, min_text_ratio=0.01):
    """
    Checks if a PDF file is machine-readable based on the presence of text.
    Args:
        pdf_path (str): Path to the PDF file.
        min_text_ratio (float): Minimum ratio of text to consider the document readable.
    Returns:
        bool: True if machine-readable, False otherwise.
    """
    try:
        doc = pymupdf.open(pdf_path)
        total_text = ""
        total_pages = len(doc)
        
        for page in doc:
            total_text += page.get_text("text")
        
        text_ratio = len(total_text) / (total_pages * 1000) 
        
        return text_ratio > min_text_ratio
    
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return False
