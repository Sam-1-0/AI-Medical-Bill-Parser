import pytesseract

# For Windows users: explicitly point to the Tesseract executable
# Update this path if you installed Tesseract elsewhere.
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

import re
import json
import sys
from PIL import Image

# --- STEP 1: OCR and Raw Token Extraction ---
def extract_raw_tokens(document_path):
    """
    Performs OCR on a document and extracts raw numeric tokens and currency hints.
    This corresponds to "Step 1- OCR/Text Extraction".
    """
    print("---  STEP 1: Performing OCR and Token Extraction ---")
    try:
        raw_text = pytesseract.image_to_string(Image.open(document_path))
        print(f"✅ Raw OCR Text Extracted:\n{raw_text}")

        # Extract raw numeric tokens from the bill [cite: 7]
        tokens = re.findall(r'[\d,.]+%?', raw_text)

        # Look for a currency hint [cite: 16]
        currency_match = re.search(r'(INR|Rs)', raw_text, re.IGNORECASE)
        currency_hint = "INR" if currency_match else "INR" # Default to INR

        # Guardrail: Check if any amounts were found [cite: 18]
        if not tokens:
            return {"status": "no_amounts_found", "reason": "document too noisy"}

        output = {
            "raw_tokens": tokens, # [cite: 15]
            "currency_hint": currency_hint, # [cite: 16]
            "confidence": 0.95,  # Simulated confidence score
            "full_text": raw_text
        }
        print(f"✅ Step 1 Output: {json.dumps(output, indent=2)}\n")
        return output

    except FileNotFoundError:
        return {"status": "error", "reason": f"File not found at {document_path}"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}

# --- STEP 2: Normalization ---
def normalize_amounts(step1_data):
    """
    Normalizes raw string tokens into clean numerical values.
    This corresponds to "Step 2 - Normalization".
    """
    print("--- STEP 2: Normalizing Extracted Tokens ---")
    raw_tokens = step1_data.get("raw_tokens", [])
    normalized = []

    for token in raw_tokens:
        if '%' in token:
            continue
        clean_token = re.sub(r'[^\d.]', '', token)
        if clean_token:
            try:
                num = float(clean_token)
                normalized.append(int(num) if num.is_integer() else num)
            except ValueError:
                continue

    output = {
        "normalized_amounts": normalized, # [cite: 25]
        "normalization_confidence": 0.98 # [cite: 26]
    }
    print(f"✅ Step 2 Output: {json.dumps(output, indent=2)}\n")
    return output

# --- STEP 3: Classification by Context ---
def classify_by_context(step1_data, step2_data):
    """
    Labels each amount based on surrounding keywords in the text.
    This corresponds to "Step 3 - Classification by Context".
    """
    print("--- STEP 3: Classifying Amounts by Context ---")
    full_text = step1_data.get("full_text", "")
    normalized_amounts = step2_data.get("normalized_amounts", [])
    classified_amounts = []

    context_keywords = {
        "total_bill": ["total", "net amount", "grand total"],
        "paid": ["paid", "cash", "advanced"],
        "due": ["due", "balance", "amount pending"]
    }

    lines = full_text.lower().split('\n')
    used_amounts = set()

    for line in lines:
        for amount_type, keywords in context_keywords.items():
            if any(keyword in line for keyword in keywords):
                numbers_in_line = [int(n) for n in re.findall(r'\d+', line)]
                for num in numbers_in_line:
                    if num in normalized_amounts and num not in used_amounts:
                        classified_amounts.append({"type": amount_type, "value": num})
                        used_amounts.add(num)
                        break
    
    output = {
        "amounts": classified_amounts, # [cite: 32]
        "confidence": 0.90 # [cite: 37]
    }
    print(f"✅ Step 3 Output: {json.dumps(output, indent=2)}\n")
    return output

# --- STEP 4: Final Structured Output ---
def generate_final_output(step1_data, step3_data):
    """
    Assembles the final JSON output with currency, labeled amounts, and provenance.
    This corresponds to "Step 4 - Final Output".
    """
    print("--- STEP 4: Assembling Final Output ---")
    classified_amounts = step3_data.get("amounts", [])
    full_text = step1_data.get("full_text", "")
    final_amounts = []

    for item in classified_amounts:
        val = item['value']
        source_text = "Not found"
        for line in full_text.split('\n'):
            if str(val) in line and any(char.isalpha() for char in line):
                source_text = line.strip()
                break
        
        final_amounts.append({
            "type": item['type'],
            "value": item['value'],
            "source": f"text: '{source_text}'" # [cite: 44]
        })

    output = {
        "currency": step1_data.get("currency_hint", "INR"), # [cite: 42]
        "amounts": final_amounts, # [cite: 43]
        "status": "ok" # [cite: 49]
    }
    return output

def process_bill(image_path):
    """
    Runs the full 4-step pipeline for processing a medical bill.
    """
    # Step 1
    step1_output = extract_raw_tokens(image_path)
    if "error" in step1_output or "status" in step1_output and step1_output["status"] != "ok":
        return step1_output # Exit early on error or guardrail condition

    # Step 2
    step2_output = normalize_amounts(step1_output)
    
    # Step 3
    step3_output = classify_by_context(step1_output, step2_output)
    
    # Step 4
    final_output = generate_final_output(step1_output, step3_output)
    
    return final_output

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_image>")
        sys.exit(1)
        
    document_path = sys.argv[1]
    
    final_result = process_bill(document_path)
    
    print("--- FINAL RESULT ---")
    print(json.dumps(final_result, indent=2))