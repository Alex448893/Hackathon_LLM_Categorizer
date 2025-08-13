import os
import json
import csv
import logging
from dotenv import load_dotenv
from collections import Counter
from document_classifier import classify_document
from text_extractor import extract_text_from_file
from ollamaClient import ollamaClient
from tqdm import tqdm


# Load environment variables
load_dotenv()

model="mistral"

# Configure logging
logging.basicConfig(
    filename='processing.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load field definitions
def load_fields(filepath="fields.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

fields_data = load_fields("fields.json")
license_fields_data = fields_data.get("license_fields", [])
agreement_fields_data = fields_data.get("agreement_fields", [])

LICENSE_FIELDNAMES = [f["field_name"] for f in license_fields_data]
AGREEMENT_FIELDNAMES = [f["field_name"] for f in agreement_fields_data]

LICENSE_CSV = "classified_data_license.csv"
AGREEMENT_CSV = "classified_data_agreement.csv"
REPORT_FILE = "file_report.csv"

def log_file_report(file_name, is_readable, classification="UNKNOWN", completed=False):
    file_exists = os.path.exists(REPORT_FILE)
    fieldnames = ["file", "readable", "classification", "completed"]
    with open(REPORT_FILE, 'a', newline='', encoding='utf-8') as report:
        writer = csv.DictWriter(report, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "file": file_name,
            "readable": "YES" if is_readable else "NO",
            "classification": classification,
            "completed": "YES" if completed else "NO"
        })

def append_to_csv(file_name, doc_type, extracted_data):
    if doc_type == "LICENSE":
        csv_file = LICENSE_CSV
        fieldnames = ["file"] + LICENSE_FIELDNAMES
    else:
        csv_file = AGREEMENT_CSV
        fieldnames = ["file"] + AGREEMENT_FIELDNAMES

    file_exists = os.path.exists(csv_file)

    with open(csv_file, 'a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
        if not file_exists:
            writer.writeheader()
        row = {field: "" for field in fieldnames}
        row["file"] = file_name
        for k, v in extracted_data.items():
            if k in row:
                row[k] = v
        writer.writerow(row)

def refine_extraction_with_mistral(text, doc_type, relevant_fields):
    prompt = f"""Extract structured {doc_type} details from the following document and return them in JSON format.

Document text:
{text}

Required fields:
"""
    for f in relevant_fields:
        prompt += f"- {f['field_name']}: {f['description']} (Example: {f['example']})\n"

    prompt += "\nEnsure the JSON contains all listed fields, even if empty."

    try:
        response = ollamaClient(prompt, model=model, doc_type=doc_type)
        return json.loads(response)
    except Exception as e:
        logging.error(f"❌ Mistral extraction failed: {e}")
        return {}

def extract_stable_fields(text, doc_type):
    logging.info(f"🔄 Starting field extraction for {doc_type}...")
    relevant = license_fields_data if doc_type == "LICENSE" else agreement_fields_data
    results = []

    for i in range(1):
        result = refine_extraction_with_mistral(text, doc_type, relevant)
        results.append(result)
        logging.info(f"🔍 Run {i + 1} result:\n{json.dumps(result, indent=2)}")

    all_keys = set().union(*[r.keys() for r in results])
    final_result = {}

    for key in all_keys:
        values = [r.get(key) for r in results if r.get(key)]
        count = Counter(values)
        most_common, freq = count.most_common(1)[0] if count else (None, 0)
        if freq >= 2:
            final_result[key] = most_common

    logging.info(f"✅ Field extraction complete for {doc_type}")
    return final_result

# Main Processing
def main():
    data_folder = "data"
    readable_files, unreadable_files = [], []

    logging.info("🚀 Starting document processing...")

    # Alle Dateien aus Haupt- und Unterordnern sammeln
    all_files = []
    for root, dirs, files in os.walk(data_folder):
        for file in files:
            all_files.append(os.path.join(root, file))

    # Fortschrittsanzeige beim Durchlauf aller Dateien
    for file_path in tqdm(all_files, desc="Processing files"):
        file = os.path.basename(file_path)
        logging.info(f"📄 Processing file: {file_path}")

        # Step 1: Text Extraction
        text = extract_text_from_file(file_path)
        if not text:
            logging.warning(f"⚠️ Could not read or extract text from: {file_path}")
            unreadable_files.append(file_path)
            log_file_report(file_path, False, classification="UNKNOWN", completed=False)
            continue
        else:
            logging.info(f"✅ Successfully extracted text from: {file_path}")
      

        # Step 2: Document Classification
        try:
            logging.info(f"🚀 Starting classification for: {file_path}")
            classification = classify_document(text, model=model)
            logging.info(f"📂 Classification result: {classification}")
        except Exception as e:
            logging.error(f"❌ Classification failed for {file_path}: {e}")
            classification = "UNKNOWN"

        if classification == "UNKNOWN":
            logging.warning(f"⚠️ Classification UNKNOWN for: {file_path}")
            log_file_report(file_path, True, classification="UNKNOWN", completed=False)
            unreadable_files.append(file_path)
            continue

        # Step 3: Field Extraction
        extracted_data = extract_stable_fields(text, classification)

        # Step 4: Check Required Fields
        required_fields = [
            f["field_name"]
            for f in (license_fields_data if classification == "LICENSE" else agreement_fields_data)
            if f["required"]
        ]
        missing_fields = [f for f in required_fields if not extracted_data.get(f)]

        if missing_fields:
            logging.warning(f"⚠️ Missing fields in {file_path}: {missing_fields}")

        # Step 5: Write to CSV
        append_to_csv(file_path, classification, extracted_data)

        if not missing_fields:
            logging.info(f"✅ File written to CSV (complete): {file_path}")
        else:
            logging.warning(f"⚠️ File written to CSV (incomplete): {file_path}, missing fields: {missing_fields}")

        log_file_report(file_path, True, classification, completed=(not missing_fields))
        readable_files.append(file_path)


    logging.info("🧾 Document processing finished.")
    logging.info("======== SUMMARY ========")
    logging.info(f"✅ Readable files: {readable_files}")
    logging.info(f"❌ Unreadable files: {unreadable_files}")
    logging.info("======== END ========")

if __name__ == "__main__":
    main()
