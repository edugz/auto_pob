"""
Auto-POB Qt Application

This application processes hotel guest data from XML or Excel files,
validates the information, and generates CSV reports for POB (Población flotante de Habitaciones).
It includes license validation, GUI for user interaction, and error logging.

Features:
- Parse XML and Excel hotel reports
- Validate guest data against required fields
- Generate structured CSV output
- Comprehensive error logging with human-readable format
- PySide6-based GUI with custom styling
"""

import sys
import os
import csv
import json
import base64
import datetime
import xml.etree.ElementTree as ET
import pandas as pd

from PySide6.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QFileDialog,
    QMessageBox, QInputDialog
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature


# ==================================================
# Path Utilities
# ==================================================

def get_resource_path(relative_path):
    """Get the absolute path to a resource, works for development and PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def get_app_path(filename):
    """Get the absolute path to an application file."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(os.path.dirname(sys.executable), filename)
    return os.path.join(os.path.abspath("."), filename)


# ==================================================
# License Management
# ==================================================

def validate_license():
    """Validate the application license using digital signature."""

    license_path = get_app_path("license.lic")
    public_key_path = get_resource_path("public_key.pem")

    if not os.path.exists(license_path):
        QMessageBox.critical(None, "License Error", "License file not found.")
        return False

    if not os.path.exists(public_key_path):
        QMessageBox.critical(None, "License Error", "Public key file not found.")
        return False

    with open(license_path, "r", encoding="utf-8") as f:
        license_data = json.load(f)

    with open(public_key_path, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())

    license_info = license_data.get("license")
    signature_b64 = license_data.get("signature")

    license_json = json.dumps(license_info, separators=(",", ":")).encode("utf-8")

    try:
        signature = base64.b64decode(signature_b64)

        public_key.verify(
            signature,
            license_json,
            padding.PKCS1v15(),
            hashes.SHA256()
        )

    except InvalidSignature:
        QMessageBox.critical(None, "License Error", "Invalid license signature.")
        return False

    expiry = datetime.datetime.strptime(
        license_info.get("expires"),
        "%Y-%m-%d"
    ).date()

    if expiry < datetime.date.today():
        QMessageBox.critical(None, "License Error", "License expired.")
        return False

    return True


# ==================================================
# Configuration and Constants
# ==================================================

CONFIG_FILENAME = "output_path.cfg"
LAST_INPUT_PATH_FILE = "last_input_path.cfg"

MERCOSUR_ID_COUNTRIES = {"AR","BO","BR","CL","CO","EC","PY","PE"}


REQUIRED_FIELDS = [
    "documento",
    "idpaisdocumento",
    "tipodocumento",
    "apellido1",
    "nombre1",
    "sexo",
    "idpaisnacionalidad",
    "idpaisresidencia",
    "fechaNacimiento",
    "fechaEntrada",
    "fechaSalida",
    "habitacion"
]


FIELD_ORDER = [
    "documento",
    "idpaisdocumento",
    "tipodocumento",
    "apellido1",
    "apellido2",
    "nombre1",
    "nombre2",
    "sexo",
    "idpaisnacionalidad",
    "idpaisresidencia",
    "fechaNacimiento",
    "fechaEntrada",
    "fechaSalida",
    "habitacion"
]


# ==================================================
# Data Validation Utilities
# ==================================================

def normalize_date(date_str, is_birth=False):
    """Normalize date strings to DD-MM-YYYY format."""

    if not date_str or len(str(date_str)) < 8:
        return ""

    try:
        day, month, year2 = str(date_str).split("-")
        yy = int(year2)

        yyyy = f"20{yy:02d}" if (not is_birth or yy <= 26) else f"19{yy:02d}"

        return f"{day}-{month}-{yyyy}"

    except:
        return ""


def invalid(value):
    """Check if a value is invalid (empty or placeholder)."""

    if not value:
        return True

    v = str(value).strip().upper()

    return v in ["UNKNOWN", "NAN", "NONE"]


# ==================================================
# Data Processing
# ==================================================

def process_guest(g, index):
    """Process a single guest record and return validated data or error."""

    raw_tipo = g["ID_TYPE"]
    doc_number = g["ID_NUMBER"]
    nationality_code = g["NATIONALITY"]

    mapped_tipo_id = None

    if raw_tipo == "3":
        mapped_tipo_id = "CI"

    elif raw_tipo == "5":

        normalized = doc_number.replace(".", "").replace("-", "").upper()

        if nationality_code in MERCOSUR_ID_COUNTRIES:
            mapped_tipo_id = "PA" if any(c.isalpha() for c in normalized) else "OTR"
        else:
            mapped_tipo_id = "PA"

    data = {

        "documento": doc_number,
        "idpaisdocumento": nationality_code,
        "tipodocumento": mapped_tipo_id,

        "apellido1": g["LAST"],
        "apellido2": g["ALTERNATE_LAST_NAME"],

        "nombre1": g["FIRST"],
        "nombre2": g["ALTERNATE_FIRST_NAME"],

        "sexo": g["GENDER"],

        "idpaisnacionalidad": nationality_code,
        "idpaisresidencia": nationality_code,

        "fechaNacimiento": normalize_date(g["BIRTH_DATE"], True),
        "fechaEntrada": normalize_date(g["ARRIVAL"]),
        "fechaSalida": normalize_date(g["DEPARTURE"]),

        "habitacion": g["ROOM"]
    }

    errors = []

    for field in REQUIRED_FIELDS:

        if invalid(data[field]):
            errors.append(f"Missing {field}")

    if data["sexo"] not in ["M", "F"]:
        errors.append("Invalid sexo (must be M or F)")

    for field in [
        "idpaisdocumento",
        "idpaisnacionalidad",
        "idpaisresidencia"
    ]:
        if invalid(data[field]) or len(data[field]) != 2:
            errors.append(f"Invalid country code in {field}")

    if errors:

        guest_name = f"{data['apellido1']}, {data['nombre1']}".strip(", ")

        return None, (
            f"Entry #{index} (Room {data['habitacion']}): "
            f"{guest_name or '[unknown]'} —\n  - "
            + "\n  - ".join(errors)
        )

    return [data[field] for field in FIELD_ORDER], None


# ==================================================
# File Parsers
# ==================================================

def parse_xml(file):
    """Parse guest data from XML file."""

    guests = []

    tree = ET.parse(file)
    root = tree.getroot()

    for nat in root.findall(".//G_NATIONALITY"):

        nat_code = nat.findtext("NATIONALITY","")

        for guest in nat.findall(".//G_FIRST"):

            guests.append({

                "FIRST": guest.findtext("FIRST",""),
                "LAST": guest.findtext("LAST",""),

                "ALTERNATE_FIRST_NAME": guest.findtext("ALTERNATE_FIRST_NAME",""),
                "ALTERNATE_LAST_NAME": guest.findtext("ALTERNATE_LAST_NAME",""),

                "GENDER": guest.findtext("GENDER",""),

                "BIRTH_DATE": guest.findtext("BIRTH_DATE",""),

                "ROOM": guest.findtext("ROOM",""),

                "ID_TYPE": guest.findtext("ID_TYPE",""),
                "ID_NUMBER": guest.findtext("ID_NUMBER",""),

                "NATIONALITY": nat_code,

                "ARRIVAL": guest.findtext("TO_CHAR_RGV_TRUNC_ARRIVAL_PMS_",""),
                "DEPARTURE": guest.findtext("TO_CHAR_RGV_TRUNC_DEPARTURE_PM",""),

                "RESV_STATUS": guest.findtext("RESV_STATUS","")
            })

    return guests


def parse_xlsx(file):
    """Parse guest data from Excel file."""

    df = pd.read_excel(file).fillna("")

    guests = []

    for _, r in df.iterrows():

        guests.append({

            "FIRST": str(r.get("FIRST","")).strip(),
            "LAST": str(r.get("LAST","")).strip(),

            "ALTERNATE_FIRST_NAME": str(r.get("ALTERNATE_FIRST_NAME","")).strip(),
            "ALTERNATE_LAST_NAME": str(r.get("ALTERNATE_LAST_NAME","")).strip(),

            "GENDER": str(r.get("GENDER","")).strip(),

            "BIRTH_DATE": str(r.get("BIRTH_DATE","")).strip(),

            "ROOM": str(r.get("ROOM","")).strip(),

            "ID_TYPE": str(r.get("ID_TYPE","")).strip(),
            "ID_NUMBER": str(r.get("ID_NUMBER","")).strip(),

            "NATIONALITY": str(r.get("NATIONALITY","")).strip(),

            "ARRIVAL": str(r.get("TO_CHAR_RGV_TRUNC_ARRIVAL_PMS_","")).strip(),
            "DEPARTURE": str(r.get("TO_CHAR_RGV_TRUNC_DEPARTURE_PM","")).strip(),

            "RESV_STATUS": str(r.get("RESV_STATUS","")).strip()

        })

    return guests


# ==================================================
# User Interface
# ==================================================

class ModeDialog(QDialog):
    """Dialog for selecting room processing mode."""

    def __init__(self):

        super().__init__()

        self.choice = None

        self.setWindowTitle("Generate POB Report")
        self.setModal(True)
        self.setFixedSize(420,175)

        title = QLabel("Choose Rooms")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: #111827;
            }
        """)

        btn_all = QPushButton("All rooms")
        btn_specific = QPushButton("Specific rooms")

        btn_all.setFixedSize(160, 46)
        btn_specific.setFixedSize(160, 46)

        # Primary button
        btn_all.setStyleSheet("""
            QPushButton {
                background-color: #1e4ed8;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)

        # Secondary button
        btn_specific.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f9fafb;
                border-color: #9ca3af;
            }
            QPushButton:pressed {
                background-color: #d1d5db;
                border-color: #6b7280;
            }
        """)

        btn_all.clicked.connect(lambda:self._select("all"))
        btn_specific.clicked.connect(lambda:self._select("select"))

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(btn_all)
        button_layout.addSpacing(16)
        button_layout.addWidget(btn_specific)
        button_layout.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)
        main_layout.addWidget(title)
        main_layout.addLayout(button_layout)

        # Keyboard defaults
        btn_all.setDefault(True)
        btn_all.setAutoDefault(True)

    def _select(self,val):
        self.choice = val
        self.accept()


# ==================================================
# Main Application Logic
# ==================================================

def main():
    """Main application entry point."""

    app = QApplication(sys.argv)
    icon_path = get_resource_path("icon.ico")
    app.setWindowIcon(QIcon(icon_path))

    if not validate_license():
        sys.exit(1)

    dlg = ModeDialog()
    screen = dlg.screen().availableGeometry()
    dlg.move(
        (screen.width() - dlg.width()) // 2,
        (screen.height() - dlg.height()) // 2
    )

    if dlg.exec() != QDialog.Accepted:
        sys.exit(0)

    selected_rooms = None

    if dlg.choice == "select":

        text, ok = QInputDialog.getText(
            None,
            "Select Rooms",
            "Enter room numbers separated by commas:"
        )

        if not ok or not text:
            sys.exit(0)

        selected_rooms = ["0"+r.strip() for r in text.split(",") if r.strip().isdigit()]

    start_dir=""

    if os.path.exists(LAST_INPUT_PATH_FILE):
        with open(LAST_INPUT_PATH_FILE) as f:
            start_dir=f.read().strip()

    input_file,_=QFileDialog.getOpenFileName(
        None,
        "Select Hotel Report (XML or Excel)",
        start_dir,
        "Hotel Reports (*.xml *.xlsx *.xls)"
    )

    if not input_file:
        sys.exit(0)

    with open(LAST_INPUT_PATH_FILE,"w") as f:
        f.write(os.path.dirname(input_file))

    ext=os.path.splitext(input_file)[1].lower()

    guests=[]

    if ext==".xml":
        guests=parse_xml(input_file)

    elif ext in [".xlsx",".xls"]:
        guests=parse_xlsx(input_file)

    else:
        QMessageBox.critical(None,"Error","Unsupported file format.")
        sys.exit(1)

    rows=[]
    errors=[]
    idx=1

    for g in guests:

        status=g["RESV_STATUS"].upper()

        if status not in ["CKIN","CKOUT"]:
            continue

        room=g["ROOM"]

        if selected_rooms and room not in selected_rooms:
            continue

        row,err=process_guest(g,idx)

        if row:
            row[-1]=row[-1].lstrip("0")
            rows.append(row)
        else:
            errors.append(err)

        idx+=1

    timestamp=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if os.path.exists(CONFIG_FILENAME):
        with open(CONFIG_FILENAME) as f:
            output_folder=f.read().strip()
    else:
        output_folder=QFileDialog.getExistingDirectory(None,"Select output folder")
        if not output_folder:
            sys.exit(0)
        with open(CONFIG_FILENAME,"w") as f:
            f.write(output_folder)

    if errors:

        log=os.path.join(output_folder,f"POB Error Log {timestamp}.log")

        with open(log,"w") as f:
            header = f"POB Error Log\nGenerated: {timestamp.replace('_', ' ')}\nTotal Errors: {len(errors)}\n\n"
            numbered_errors = [f"{i+1}. {error}" for i, error in enumerate(errors)]
            f.write(header + "\n\n".join(numbered_errors))

        QMessageBox.warning(None,"Errors Found",f"See log:\n{log}")

    else:

        rows.sort(key=lambda r:int(r[-1]) if r[-1].isdigit() else 0)

        csv_path=os.path.join(output_folder,f"POB {timestamp}.csv")

        with open(csv_path,"w",newline="",encoding="utf-8") as f:
            csv.writer(f,delimiter=";").writerows(rows)

        QMessageBox.information(None,"Success",f"CSV created:\n{csv_path}")


# ==================================================
# Application Entry Point
# ==================================================

if __name__=="__main__":
    main()