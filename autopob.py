import sys
import os
import xml.etree.ElementTree as ET
import csv
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import socket
import json
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

# Get Public Key
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller bundled """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# License Validation
def validate_license():
    license_path = "license.lic"

    public_key_path = get_resource_path("public_key.pem")

    if not os.path.exists(license_path):
        messagebox.showerror("License Error", "License file not found.")
        return False
    if not os.path.exists(public_key_path):
        messagebox.showerror("License Error", "Public key file not found.")
        return False

    try:
        # Load license JSON
        with open(license_path, "r", encoding="utf-8") as f:
            license_data = json.load(f)
    except Exception as e:
        messagebox.showerror("License Error", f"Failed to read license file:\n{e}")
        return False

    try:
        # Load public key
        with open(public_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
    except Exception as e:
        messagebox.showerror("License Error", f"Failed to load public key:\n{e}")
        return False

    # Extract license info and signature
    license_info = license_data.get("license")
    signature_b64 = license_data.get("signature")

    if not license_info or not signature_b64:
        messagebox.showerror("License Error", "License file is missing required fields.")
        return False

    # Prepare data for verification
    license_json = json.dumps(license_info, separators=(',', ':')).encode('utf-8')
    signature = base64.b64decode(signature_b64)

    # Verify signature
    try:
        public_key.verify(
            signature,
            license_json,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    except InvalidSignature:
        messagebox.showerror("License Error", "Invalid license signature.")
        return False
    except Exception as e:
        messagebox.showerror("License Error", f"Signature verification failed:\n{e}")
        return False

    # Check machine binding
    current_machine = socket.gethostname()
    if license_info.get("machine_id") != current_machine:
        messagebox.showerror("License Error", "License is not valid for this machine.")
        return False

    # Check expiration date
    try:
        expiry_str = license_info.get("expires")
        expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d").date()
        if expiry_date < datetime.date.today():
            messagebox.showerror("License Error", f"License expired on {expiry_str}.")
            return False
    except Exception as e:
        messagebox.showerror("License Error", f"Invalid expiration date in license:\n{e}")
        return False

    # If all checks pass
    return True

# Constants
REQUIRED_FIELDS = [
    "documento", "idpaisdocumento", "tipodocumento", "apellido1",
    "nombre1", "sexo", "idpaisnacionalidad", "idpaisresidencia",
    "fechaNacimiento", "fechaEntrada", "fechaSalida", "habitacion"
]

FIELD_ORDER = [
    "documento", "idpaisdocumento", "tipodocumento", "apellido1", "apellido2",
    "nombre1", "nombre2", "sexo", "idpaisnacionalidad", "idpaisresidencia",
    "fechaNacimiento", "fechaEntrada", "fechaSalida", "habitacion"
]

MERCOSUR_ID_COUNTRIES = {"AR", "BO", "BR", "CL", "CO", "EC", "PY", "PE"}

CONFIG_FILENAME = "output_path.cfg"

# Function to extract guest info and validate
def extract_guest_data(guest, nationality_code, index):
    q_id = guest.find(".//Q_ID")
    raw_tipo = q_id.findtext("ID_TYPE", "").strip() if q_id is not None else ""
    doc_number = q_id.findtext("ID_NUMBER", "").strip() if q_id is not None else ""
    
    mapped_tipo_id = None
    if raw_tipo == "3":
        mapped_tipo_id = "CI"  # Uruguayan National ID
    elif raw_tipo == "5":
        normalized_doc = doc_number.replace(".", "").replace("-", "").upper()
        if nationality_code in MERCOSUR_ID_COUNTRIES:
            # Passport check: letters + digits, length >= 8
            if any(c.isalpha() for c in normalized_doc) and any(c.isdigit() for c in normalized_doc) and len(normalized_doc) >= 6:
                mapped_tipo_id = "PA"  # Passport
            else:
                mapped_tipo_id = "OTR"  # Default to Otros
        else:
            mapped_tipo_id = "PA"  # Default: Passport
    else:
        mapped_tipo_id = None  # Invalid

    data = {
        "documento": q_id.findtext("ID_NUMBER", "").strip() if q_id is not None else "",
        "idpaisdocumento": nationality_code,
        "tipodocumento": mapped_tipo_id,
        "apellido1": guest.findtext("LAST", "").strip(),
        "apellido2": guest.findtext("ALTERNATE_LAST_NAME", "").strip(),
        "nombre1": guest.findtext("FIRST", "").strip(),
        "nombre2": guest.findtext("ALTERNATE_FIRST_NAME", "").strip(),
        "sexo": guest.findtext("GENDER", "").strip(),
        "idpaisnacionalidad": nationality_code,
        "idpaisresidencia": guest.findtext("GUEST_COUNTRY", "").strip(),
        "fechaNacimiento": guest.findtext("BIRTH_DATE", "").strip(),
        "fechaEntrada": guest.findtext("TO_CHAR_RGV_TRUNC_ARRIVAL_PMS_", "").strip(),
        "fechaSalida": guest.findtext("TO_CHAR_RGV_TRUNC_DEPARTURE_PM", "").strip(),
        "habitacion": guest.findtext("ROOM", "").strip(),
    }

    # Validate required fields
    errors = []
    for field in REQUIRED_FIELDS:
        if not data[field]:
            errors.append(f"Missing required field: {field}")

    if raw_tipo and mapped_tipo_id is None:
        errors.append(f"Invalid tipodocumento value: '{raw_tipo}' (only '3' and '5' allowed)")

    if errors:
        guest_name = f"{data.get('apellido1', '')}, {data.get('nombre1', '')}".strip()
        return None, f"Entry #{index}: {guest_name or '[unknown name]'} — " + "; ".join(errors)

    return [data[field] for field in FIELD_ORDER], None

# Read or Prompy for output folder
def get_output_folder():
    if os.path.exists(CONFIG_FILENAME):
        with open(CONFIG_FILENAME, "r", encoding="utf-8") as f:
            saved_path = f.read().strip()
            if os.path.isdir(saved_path):
                return saved_path

    folder = filedialog.askdirectory(title="Select folder to save the output files")
    if folder:
        with open(CONFIG_FILENAME, "w", encoding="utf-8") as f:
            f.write(folder)
        return folder

    return None

# Main script logic
def main():
    if not validate_license():
        return  # Exit early if license is invalid

    root = tk.Tk()
    root.withdraw()

    # --- Step 1: Ask for XML file ---
    xml_file = filedialog.askopenfilename(
        title="Select XML file to convert",
        filetypes=[("XML files", "*.xml")]
    )    
    if not xml_file:
        messagebox.showwarning("Cancelled", "No file was selected.")
        return

    # --- Step 2: Ask for (or retrieve) output folder
    output_folder = get_output_folder()
    if not output_folder:
        messagebox.showerror("Error", "No output folder selected.")
        return
    
    # --- Step 3: Parse the XML ---
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        messagebox.showerror("Parsing Error", f"The XML file could not be parsed:\n{str(e)}")
        return


    # --- Step 4: Process data ---
    valid_rows = []
    errors = []
    entry_index = 1

    for g_nationality in root.findall(".//G_NATIONALITY"):
        nationality_code = g_nationality.findtext("NATIONALITY", "").strip()
        for guest in g_nationality.findall(".//G_FIRST"):
            resv_status = guest.findtext("RESV_STATUS", "").strip().upper()
            if resv_status != "CKIN":
                # Skip guests who didn't check in (e.g., "RS")
                continue

            row, error = extract_guest_data(guest, nationality_code, entry_index)
            if row:
                valid_rows.append(row)
            elif error:
                errors.append(error)
            entry_index += 1



    # --- Step 5: Export
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    try:
        if errors:
            log_filename = f"POB Error Log {timestamp}.log"
            log_path = os.path.join(output_folder, log_filename)
            with open(log_path, "w", encoding="utf-8") as log:
                log.write(f"Errors found in POB data on {timestamp}\n\n")
                for err in errors:
                    entry_line, *error_parts = err.split(" — ")
                    log.write(f"- {entry_line} —\n")
                    for part in error_parts:
                        for line in part.split(";"):
                            if line.strip():
                                log.write(f"{line.strip()};\n")
                    log.write("\n")
            messagebox.showwarning("Errors Found", f"Some data was invalid.\nSee log:\n{log_path}")
        else:
            csv_filename = f"POB {timestamp}.csv"
            csv_path = os.path.join(output_folder, csv_filename)
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(FIELD_ORDER)
                writer.writerows(valid_rows)
            messagebox.showinfo("Success", f"CSV export complete:\n{csv_path}")

    except Exception as e:
        messagebox.showerror("File Error", f"Failed to write output files:\n{str(e)}")


if __name__ == "__main__":
    main()
