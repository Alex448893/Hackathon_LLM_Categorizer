import pymupdf  # PyMuPDF
from dotenv import load_dotenv
from ollamaClient import ollamaClient
import json


load_dotenv()

def init_prompt(text):
    prompt = f"""
    Analyze the following document and determine if the doc_type is an AGREEMENT or a LICENSE.

    Rules:
    - If the document mentions terms like 'invoice', 'payment', 'license purchase', or 'subscription', classify it as LICENSE.
    - If the document discusses terms like 'contract', 'agreement', 'terms and conditions', or 'service level agreement', classify it as AGREEMENT.
    - If uncertain, classify it as UNKNOWN.

    Document Text:
    {text}

    Your response must be either 'AGREEMENT', 'LICENSE', or 'UNKNOWN'.
    """
    return prompt

def extract_text_from_pdf(pdf_path):
    """Extrahiert den Text aus einem maschinenlesbaren PDF."""
    doc = pymupdf.open(pdf_path)
    text = "\n".join(page.get_text("text") for page in doc)
    return text

def classify_document(text, model="phi4"):
    """
    Klassifiziert das Dokument als 'AGREEMENT', 'LICENSE' oder 'UNKNOWN' mithilfe 
    des Mistral-Modells über SSH.
    """
    prompt = init_prompt(text)
    try:
        response = ollamaClient(prompt, model=model,doc_type="CLASSIFY")
        classification = json.loads(response).get("doc_type")
        print(classification)
    except Exception as e:
        print(f"Fehler bei der Klassifizierung mit Mistral: {e}")
        classification = "UNKNOWN"

    if classification not in ["AGREEMENT", "LICENSE"]:
        classification = fallback_classification(text)
    
    return classification

def fallback_classification(text):
    """Fallback-Klassifizierung basierend auf einfacher Schlüsselwortsuche."""
    license_keywords = ["invoice", "payment", "license purchase", "subscription"]
    agreement_keywords = ["contract", "agreement", "terms and conditions", "service level agreement"]

    text_lower = text.lower()

    if any(keyword in text_lower for keyword in license_keywords):
        return "LICENSE"
    elif any(keyword in text_lower for keyword in agreement_keywords):
        return "AGREEMENT"
    else:
        return "UNKNOWN"
