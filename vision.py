import os
import json
import paramiko
import shlex
import logging
import base64
import io
import fitz 
from dotenv import load_dotenv

load_dotenv()


def ollamaClient(prompt, model="llava:7b", image=""):
    """
    Stellt über eine SSH-Verbindung einen Curl-Befehl an den lokalen Ollama-Server 
    und gibt die Antwort als Text zurück.
    """

    ssh_host = "robodev02hhb"
    ssh_user = "RMA-DL-JJAVIER"
    ssh_port = 22
    ssh_password = os.getenv('PASSWORD')

    required_fields = []
    properties = {}

    format_schema = {
    "type": "object",
    "properties": properties,
    "required": required_fields
    }

    data = {
        "model": model,
        "prompt": prompt,
        "images": [image],
        "format": format_schema,
        "stream": False,
    }
    
    json_data = json.dumps(data)
    safe_json_data = shlex.quote(json_data)  
    curl_command = f"curl -s -S -H 'Content-Type: application/json' http://localhost:11434/api/generate -d {safe_json_data}"
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_password)
        stdin, stdout, stderr = client.exec_command(curl_command)
        response_text = stdout.read().decode("utf-8")
        response_json = json.loads(response_text)
        
        return response_json.get("response", "Keine Antwort erhalten")
    
    except Exception as e:
        logging.error(f"Fehler bei der SSH-Verbindung: {e}")
        return None
    
    finally:
        client.close()



def pdf2img_base64(file_path, img_format="jpg"):

    doc = fitz.open(file_path)
    if doc.page_count < 1:
        raise ValueError("Die PDF-Datei enthält keine Seiten.")
    
    page = doc[0]
    pix = page.get_pixmap()
    
    if img_format.lower() == "png":
        img_bytes = pix.tobytes("png")
    elif img_format.lower() in ("jpeg", "jpg"):
        from PIL import Image

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        img_bytes = buffer.getvalue()
    else:
        raise ValueError("Unterstütztes Format ist nur 'png' oder 'jpeg'.")
    
    encoded_str = base64.b64encode(img_bytes).decode("utf-8")
    return encoded_str

    

img_encoded = pdf2img_base64(r"C:\Users\JJavier.Extern\Code\llm\data\4200054593__Docker Team Abo 30 User Subscriptionen.pdf")


prompt="what do you see in the picture?"

result = ollamaClient(prompt=prompt, image=img_encoded)
print(result)