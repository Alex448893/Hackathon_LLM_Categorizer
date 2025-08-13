import os
import sys
import json
import paramiko
import shlex
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger("paramiko").setLevel(logging.WARNING)


with open("fields.json", "r", encoding="utf-8") as f:
    fields_data = json.load(f)




def ollamaClient(prompt, model="mistral", doc_type=""):
    """
    Stellt über eine SSH-Verbindung einen Curl-Befehl an den lokalen Ollama-Server 
    und gibt die Antwort als Text zurück.
    """
    required_fields = []
    properties = {}
    # ssh_host = "robodev02hhb"
    # # ssh_user = "RMA-DL-JJAVIER"
    # ssh_user = "RMA-DL-AMOEHLENBRUCH"
    # ssh_port = 22
    # ssh_password = os.getenv('PASSWORD')
    ssh_host = "localhost"
    # ssh_user = "RMA-DL-JJAVIER"
    ssh_user = "RMA-DL-AMOEHLENBRUCH"
    ssh_port = 1
    ssh_password = os.getenv('PASSWORD')


    if doc_type == "LICENSE":
        for field in fields_data["license_fields"]:
            field_name = field["field_name"]
            field_type = field["type"]
            properties[field_name] = {"type": field_type}
            if field["required"]:
                required_fields.append(field_name)

    elif doc_type == "AGREEMENT":
        for field in fields_data["agreement_fields"]:
            field_name = field["field_name"]
            field_type = field["type"]
            properties[field_name] = {"type": field_type}
            if field["required"]:
                required_fields.append(field_name)
    
    elif doc_type == "CLASSIFY":
        properties={"doc_type": {
        "type": "string"
        }}
        required_fields.append("doc_type")


    # Dieses Schema landet in "format"
    format_schema = {
    "type": "object",
    "properties": properties,
    "required": required_fields
    }
    
    if properties:
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": format_schema
        }
    else:
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
    
    json_data = json.dumps(data)
    safe_json_data = shlex.quote(json_data)  
    
    curl_command = f"curl -s -S -H 'Content-Type: application/json' http://localhost:11434/api/generate -d {safe_json_data}"
    #curl_command = f"curl -X POST http://localhost:11434/api/generate -d {safe_json_data}"
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    headers = {'content-type': 'application/json'}
    try:
        # client.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_password)
        #stdin, stdout, stderr = client.exec_command(curl_command)
        # response_text = requests.post("http://localhost:11434/api/generate -d", headers={"Content-Type": "application/json"}, data={json_data})
        response_text = requests.post("http://localhost:11434/api/generate", headers=headers, data=json_data)
        #response_text = response_text.read().decode("utf-8")
        #print(response_text)
        response_text = response_text.text
        # JSON-Antwort parsen
        response_json = json.loads(response_text)
        
        # Auf das "response"-Feld zugreifen
        return response_json.get("response", "Keine Antwort erhalten")
    
    except Exception as e:
        logging.error(f"Fehler bei der SSH-Verbindung: {e}")
        return None
    
    finally:
        client.close()