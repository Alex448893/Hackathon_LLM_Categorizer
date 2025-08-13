import fitz  # PyMuPDF
import os
import logging
import docx
import extract_msg
from email import policy
from email.parser import BytesParser
import chardet
import string

try:
    import pyth  # RTF reading library
except ImportError:
    pyth = None  # We'll handle missing library gracefully

logging.basicConfig(
    filename='processing.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def is_text_readable(text, min_ratio=0.5):
    """
    Checks if the extracted text is likely readable text vs. binary gibberish.
    :param text: The extracted text (string).
    :param min_ratio: The minimum ratio of 'printable' characters vs. total length.
                     0.5 is arbitrary; adjust if you're too strict/lenient.
    :return: True if the text is probably readable, False otherwise.
    """
    # Remove extremely short results (like 1-2 random chars)
    if len(text) < 5:
        return False

    total_chars = len(text)
    # Count "printable" ASCII characters, including punctuation/whitespace
    printable_set = set(string.printable)  # digits, ascii_letters, punctuation, whitespace
    printable_count = sum(ch in printable_set for ch in text)

    ratio = printable_count / total_chars
    return ratio >= min_ratio


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a machine-readable PDF.
    """
    try:
        doc = fitz.open(pdf_path)
        extracted_text = []
        for page in doc:
            extracted_text.append(page.get_text("text"))
        text = "\n".join(extracted_text).strip()
        if text and is_text_readable(text):
            return text
        return None
    except Exception as e:
        logging.error(f"PDF extraction failed for {pdf_path}: {e}")
        return None


def extract_text_from_txt(txt_path):
    """
    Extract text from a .txt file, auto-detecting encoding.
    """
    try:
        # Detect encoding to handle varied text files
        with open(txt_path, 'rb') as raw_file:
            raw_data = raw_file.read()
        enc_guess = chardet.detect(raw_data).get('encoding', 'utf-8')

        with open(txt_path, 'r', encoding=enc_guess, errors='replace') as f:
            text = f.read().strip()
        if text and is_text_readable(text):
            return text
        return None
    except Exception as e:
        logging.error(f"TXT extraction failed for {txt_path}: {e}")
        return None


def extract_text_from_docx(docx_path):
    """
    Extract text from a .docx file.
    """
    try:
        document = docx.Document(docx_path)
        paragraphs = [para.text for para in document.paragraphs]
        text = "\n".join(paragraphs).strip()
        if text and is_text_readable(text):
            return text
        return None
    except Exception as e:
        logging.error(f"DOCX extraction failed for {docx_path}: {e}")
        return None


def extract_text_from_eml(eml_path):
    """
    Extract text from an .eml file (email message).
    """
    try:
        with open(eml_path, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)
        lines = []
        if msg['Subject']:
            lines.append("Subject: " + msg['Subject'])

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    lines.append(part.get_content())
        else:
            lines.append(msg.get_content())

        text = "\n".join(line.strip() for line in lines if line).strip()
        if text and is_text_readable(text):
            return text
        return None
    except Exception as e:
        logging.error(f"EML extraction failed for {eml_path}: {e}")
        return None


def extract_text_from_msg(msg_path):
    """
    Extract text from an .msg file (Outlook message).
    """
    try:
        msg = extract_msg.Message(msg_path)
        lines = []
        if msg.subject:
            lines.append("Subject: " + msg.subject)
        if msg.body:
            lines.append(msg.body)
        text = "\n".join(lines).strip()
        if text and is_text_readable(text):
            return text
        return None
    except Exception as e:
        logging.error(f"MSG extraction failed for {msg_path}: {e}")
        return None


def extract_text_from_rtf(rtf_path):
    """
    Extract text from an .rtf file using the 'pyth' library if installed.
    """
    if pyth is None:
        logging.error("RTF extraction requested but 'pyth' is not installed.")
        return None
    try:
        with open(rtf_path, 'rb') as f:
            data = f.read()
        from pyth.plugins.rtf15.reader import Rtf15Reader
        from pyth.plugins.plaintext.writer import PlaintextWriter
        doc = Rtf15Reader.read(data)
        text = PlaintextWriter.write(doc).getvalue()
        text = text.strip()
        if text and is_text_readable(text):
            return text
        return None
    except Exception as e:
        logging.error(f"RTF extraction failed for {rtf_path}: {e}")
        return None


def extract_text_from_file(file_path):
    """
    Attempts to extract text from any recognized file type.
    Returns extracted text or None if failed/unrecognized or invalid (gibberish).
    """
    ext = os.path.splitext(file_path)[1].lower()

    # Decide how to extract based on extension
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".txt":
        return extract_text_from_txt(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    elif ext == ".eml":
        return extract_text_from_eml(file_path)
    elif ext == ".msg":
        return extract_text_from_msg(file_path)
    elif ext == ".rtf":
        return extract_text_from_rtf(file_path)
    else:
        # Attempt a generic text read fallback (some files might be plain text, or .log, etc.)
        try:
            with open(file_path, 'rb') as raw_file:
                raw_data = raw_file.read()
            enc_guess = chardet.detect(raw_data).get('encoding', 'utf-8')
            with open(file_path, 'r', encoding=enc_guess, errors='replace') as f:
                text = f.read().strip()
            if text and is_text_readable(text):
                return text
            return None
        except Exception:
            return None
