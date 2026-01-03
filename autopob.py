import sys
import os
import xml.etree.ElementTree as ET
import csv
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinter.simpledialog as simpledialog
import socket
import json
import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature


# ===============================
# PyInstaller-safe resource path
# ===============================
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# ===============================
# License Validation
# ===============================
def get_app_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(os.path.dirname(sys.executable), filename)
    return os.path.join(os.path.abspath("."), filename)

def validate_license():
    license_path = get_app_path("license.lic")
    public_key_path = get_resource_path("public_key.pem")

    if not os.path.exists(license_path):
        messagebox.showerror("License Error", "License file not found.")
        return False

    if not os.path.exists(public_key_path):
        messagebox.showerror("License Error", "Public key file not found.")
        return False

    # Load license file
    try:
        with open(license_path, "r", encoding="utf-8") as f:
            license_data = json.load(f)
    except Exception as e:
        messagebox.showerror("License Error", f"Failed to read license file:\n{e}")
        return False

    # Load public key
    try:
        with open(public_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
    except Exception as e:
        messagebox.showerror("License Error", f"Failed to load public key:\n{e}")
        return False

    license_info = license_data.get("license")
    signature_b64 = license_data.get("signature")

    if not license_info or not signature_b64:
        messagebox.showerror("License Error", "License file is missing required fields.")
        return False

    # Rebuild signed payload
    license_json = json.dumps(
        license_info,
        separators=(',', ':')
    ).encode("utf-8")

    try:
        signature = base64.b64decode(signature_b64)
    except Exception:
        messagebox.showerror("License Error", "Invalid signature encoding.")
        return False

    # Verify cryptographic signature
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

    # ===============================
    # License rules
    # ===============================

    # Beta check (FIXED)
    is_beta = license_info.get("type") == "BETA"

    # Machine binding (non-beta only)
    if not is_beta:
        current_machine = socket.gethostname()
        if license_info.get("machine_id", "").lower() != current_machine.lower():
            messagebox.showerror(
                "License Error",
                "License is bound to another machine.\nPlease request a new license."
            )
            return False

    # Expiration check
    try:
        expiry_str = license_info.get("expires")
        expiry_date = datetime.datetime.strptime(
            expiry_str, "%Y-%m-%d"
        ).date()

        if expiry_date < datetime.date.today():
            messagebox.showerror(
                "License Error",
                f"License expired on {expiry_str}."
            )
            return False
    except Exception as e:
        messagebox.showerror(
            "License Error",
            f"Invalid expiration date in license:\n{e}"
        )
        return False

    return True


# ===============================
# Constants
# ===============================
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

MERCOSUR_ID_COUNTRIES = {
    "AR", "BO", "BR", "CL", "CO", "EC", "PY", "PE"
}

CONFIG_FILENAME = "output_path.cfg"


# ===============================
# Helpers
# ===============================
def normalize_date(date_str, is_birth=False):
    if not date_str or len(date_str) < 8:
        return date_str

    try:
        day, month, year2 = date_str.split("-")
        yy = int(year2)

        if is_birth:
            yyyy = f"20{yy:02d}" if yy <= 26 else f"19{yy:02d}"
        else:
            yyyy = f"20{yy:02d}"

        return f"{day}-{month}-{yyyy}"
    except Exception:
        return date_str


def extract_guest_data(guest, nationality_code, index):
    q_id = guest.find(".//Q_ID")
    raw_tipo = q_id.findtext("ID_TYPE", "").strip() if q_id is not None else ""
    doc_number = q_id.findtext("ID_NUMBER", "").strip() if q_id is not None else ""

    mapped_tipo_id = None

    if raw_tipo == "3":
        mapped_tipo_id = "CI"
    elif raw_tipo == "5":
        normalized_doc = doc_number.replace(".", "").replace("-", "").upper()
        if nationality_code in MERCOSUR_ID_COUNTRIES:
            if any(c.isalpha() for c in normalized_doc) and any(c.isdigit() for c in normalized_doc):
                mapped_tipo_id = "PA"
            else:
                mapped_tipo_id = "OTR"
        else:
            mapped_tipo_id = "PA"

    data = {
        "documento": doc_number,
        "idpaisdocumento": nationality_code,
        "tipodocumento": mapped_tipo_id,
        "apellido1": guest.findtext("LAST", "").strip(),
        "apellido2": guest.findtext("ALTERNATE_LAST_NAME", "").strip(),
        "nombre1": guest.findtext("FIRST", "").strip(),
        "nombre2": guest.findtext("ALTERNATE_FIRST_NAME", "").strip(),
        "sexo": guest.findtext("GENDER", "").strip(),
        "idpaisnacionalidad": nationality_code,
        "idpaisresidencia": guest.findtext("GUEST_COUNTRY", "").strip(),
        "fechaNacimiento": normalize_date(
            guest.findtext("BIRTH_DATE", "").strip(), is_birth=True
        ),
        "fechaEntrada": normalize_date(
            guest.findtext("TO_CHAR_RGV_TRUNC_ARRIVAL_PMS_", "").strip()
        ),
        "fechaSalida": normalize_date(
            guest.findtext("TO_CHAR_RGV_TRUNC_DEPARTURE_PM", "").strip()
        ),
        "habitacion": guest.findtext("ROOM", "").strip(),
    }

    errors = []

    for field in REQUIRED_FIELDS:
        if not data[field]:
            errors.append(f"Missing required field: {field}")

    if raw_tipo and mapped_tipo_id is None:
        errors.append(f"Invalid tipodocumento value: '{raw_tipo}'")

    if errors:
        guest_name = f"{data.get('apellido1','')}, {data.get('nombre1','')}".strip()
        return None, f"Entry #{index}: {guest_name or '[unknown]'} — " + "; ".join(errors)

    return [data[field] for field in FIELD_ORDER], None


def get_output_folder():
    if os.path.exists(CONFIG_FILENAME):
        with open(CONFIG_FILENAME, "r", encoding="utf-8") as f:
            path = f.read().strip()
            if os.path.isdir(path):
                return path

    folder = filedialog.askdirectory(title="Select output folder")
    if folder:
        with open(CONFIG_FILENAME, "w", encoding="utf-8") as f:
            f.write(folder)
        return folder

    return None


# ===============================
# Mode Selector
# ===============================
def ask_all_or_select():
    result = {"choice": None}

    def choose(val):
        result["choice"] = val
        popup.destroy()

    popup = tk.Toplevel()
    popup.title("Conversion Mode")

    popup.protocol("WM_DELETE_WINDOW", lambda: choose(None))

    tk.Label(popup, text="Choose conversion mode:").pack(padx=20, pady=10)

    frame = tk.Frame(popup)
    frame.pack(pady=10)

    tk.Button(frame, text="All", width=10, command=lambda: choose("all")).pack(side="left", padx=5)
    tk.Button(frame, text="Select Rooms", width=15, command=lambda: choose("select")).pack(side="left", padx=5)

    popup.grab_set()
    popup.wait_window()

    return result["choice"]


# ===============================
# Main
# ===============================
def main():
    if not validate_license():
        return

    root = tk.Tk()
    root.withdraw()

    mode = ask_all_or_select()
    if mode is None:
        return

    selected_rooms = None
    if mode == "select":
        rooms = simpledialog.askstring("Select Rooms", "Enter room numbers separated by commas:")
        if not rooms:
            return
        selected_rooms = ["0" + r.strip() for r in rooms.split(",") if r.strip().isdigit()]

    xml_file = filedialog.askopenfilename(
        title="Select XML file",
        filetypes=[("XML files", "*.xml")]
    )
    if not xml_file:
        return

    output_folder = get_output_folder()
    if not output_folder:
        return

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        messagebox.showerror("XML Error", str(e))
        return

    valid_rows = []
    errors = []
    index = 1

    for nat in root.findall(".//G_NATIONALITY"):
        nat_code = nat.findtext("NATIONALITY", "").strip()
        for guest in nat.findall(".//G_FIRST"):
            if guest.findtext("RESV_STATUS", "").strip().upper() != "CKIN":
                continue

            room = guest.findtext("ROOM", "").strip()
            if selected_rooms and room not in selected_rooms:
                continue

            row, err = extract_guest_data(guest, nat_code, index)
            if row:
                row[FIELD_ORDER.index("habitacion")] = row[-1].lstrip("0")
                valid_rows.append(row)
            else:
                errors.append(err)
            index += 1

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if errors:
        log_path = os.path.join(output_folder, f"POB Error Log {timestamp}.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(errors))
        messagebox.showwarning("Errors Found", f"See log:\n{log_path}")
    else:
        csv_path = os.path.join(output_folder, f"POB {timestamp}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f, delimiter=";").writerows(valid_rows)
        messagebox.showinfo("Success", f"CSV created:\n{csv_path}")


if __name__ == "__main__":
    main()
