import sys
import os
import csv
import json
import base64
import socket
import datetime
import xml.etree.ElementTree as ET

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
# PyInstaller-safe resource path
# ==================================================
def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_app_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(os.path.dirname(sys.executable), filename)
    return os.path.join(os.path.abspath("."), filename)


# ==================================================
# License Validation
# ==================================================
def validate_license():
    license_path = get_app_path("license.lic")
    public_key_path = get_resource_path("public_key.pem")

    if not os.path.exists(license_path):
        QMessageBox.critical(None, "License Error", "License file not found.")
        return False

    if not os.path.exists(public_key_path):
        QMessageBox.critical(None, "License Error", "Public key file not found.")
        return False

    try:
        with open(license_path, "r", encoding="utf-8") as f:
            license_data = json.load(f)
    except Exception as e:
        QMessageBox.critical(None, "License Error", f"Failed to read license:\n{e}")
        return False

    try:
        with open(public_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
    except Exception as e:
        QMessageBox.critical(None, "License Error", f"Failed to load public key:\n{e}")
        return False

    license_info = license_data.get("license")
    signature_b64 = license_data.get("signature")

    if not license_info or not signature_b64:
        QMessageBox.critical(None, "License Error", "Invalid license format.")
        return False

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
    except Exception as e:
        QMessageBox.critical(None, "License Error", str(e))
        return False

    if license_info.get("type") != "BETA":
        if license_info.get("machine_id", "").lower() != socket.gethostname().lower():
            QMessageBox.critical(
                None,
                "License Error",
                "License is bound to another machine."
            )
            return False

    expiry = datetime.datetime.strptime(
        license_info.get("expires"), "%Y-%m-%d"
    ).date()

    if expiry < datetime.date.today():
        QMessageBox.critical(
            None,
            "License Error",
            f"License expired on {license_info.get('expires')}"
        )
        return False

    return True


# ==================================================
# Constants
# ==================================================
REQUIRED_FIELDS = [
    "documento", "idpaisdocumento", "tipodocumento",
    "apellido1", "nombre1", "sexo",
    "idpaisnacionalidad", "idpaisresidencia",
    "fechaNacimiento", "fechaEntrada", "fechaSalida", "habitacion"
]

FIELD_ORDER = [
    "documento", "idpaisdocumento", "tipodocumento",
    "apellido1", "apellido2",
    "nombre1", "nombre2",
    "sexo", "idpaisnacionalidad", "idpaisresidencia",
    "fechaNacimiento", "fechaEntrada", "fechaSalida", "habitacion"
]

MERCOSUR_ID_COUNTRIES = {"AR", "BO", "BR", "CL", "CO", "EC", "PY", "PE"}
CONFIG_FILENAME = "output_path.cfg"


# ==================================================
# Helpers
# ==================================================
def normalize_date(date_str, is_birth=False):
    if not date_str or len(date_str) < 8:
        return date_str
    day, month, year2 = date_str.split("-")
    yy = int(year2)
    yyyy = f"20{yy:02d}" if (not is_birth or yy <= 26) else f"19{yy:02d}"
    return f"{day}-{month}-{yyyy}"

def extract_guest_data(guest, nationality_code, index):
    q_id = guest.find(".//Q_ID")
    raw_tipo = q_id.findtext("ID_TYPE", "").strip() if q_id is not None else ""
    doc_number = q_id.findtext("ID_NUMBER", "").strip() if q_id is not None else ""

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
        "apellido1": guest.findtext("LAST", "").strip(),
        "apellido2": guest.findtext("ALTERNATE_LAST_NAME", "").strip(),
        "nombre1": guest.findtext("FIRST", "").strip(),
        "nombre2": guest.findtext("ALTERNATE_FIRST_NAME", "").strip(),
        "sexo": guest.findtext("GENDER", "").strip(),
        "idpaisnacionalidad": nationality_code,
        "idpaisresidencia": nationality_code,
        "fechaNacimiento": normalize_date(guest.findtext("BIRTH_DATE", ""), True),
        "fechaEntrada": normalize_date(guest.findtext("TO_CHAR_RGV_TRUNC_ARRIVAL_PMS_", "")),
        "fechaSalida": normalize_date(guest.findtext("TO_CHAR_RGV_TRUNC_DEPARTURE_PM", "")),
        "habitacion": guest.findtext("ROOM", "").strip(),
    }

    for field in REQUIRED_FIELDS:
        if not data[field]:
            return None, f"Entry #{index}: Missing {field}"

    return [data[field] for field in FIELD_ORDER], None


# ==================================================
# Mode Dialog (Qt)
# ==================================================
class ModeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.choice = None

        self.setWindowTitle("Generate POB Report")
        self.setModal(True)
        self.setFixedSize(420, 175)

        # ---------- Title ----------
        title = QLabel("Choose rooms")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: #111827;
            }
        """)

        # ---------- Buttons ----------
        btn_all = QPushButton("All rooms")
        btn_specific = QPushButton("Specific rooms")

        btn_all.setFixedSize(160, 46)
        btn_specific.setFixedSize(160, 46)

        # Primary button
        btn_all.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1e4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)

        # Secondary button
        btn_specific.setStyleSheet("""
            QPushButton {
                background-color: #f9fafb;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
                border-color: #9ca3af;
            }
            QPushButton:pressed {
                background-color: #d1d5db;
                border-color: #6b7280;
            }
        """)

        btn_all.clicked.connect(lambda: self._select("all"))
        btn_specific.clicked.connect(lambda: self._select("select"))

        # ---------- Layout ----------
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

    def _select(self, value):
        self.choice = value
        self.accept()


# ==================================================
# Main
# ==================================================
def main():
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
            None, "Select Rooms",
            "Enter room numbers separated by commas:"
        )
        if not ok or not text:
            sys.exit(0)
        selected_rooms = ["0" + r.strip() for r in text.split(",") if r.strip().isdigit()]

    xml_file, _ = QFileDialog.getOpenFileName(
        None, "Select XML file", "", "XML Files (*.xml)"
    )
    if not xml_file:
        sys.exit(0)

    if os.path.exists(CONFIG_FILENAME):
        with open(CONFIG_FILENAME) as f:
            output_folder = f.read().strip()
    else:
        output_folder = QFileDialog.getExistingDirectory(
            None, "Select output folder"
        )
        if not output_folder:
            sys.exit(0)
        with open(CONFIG_FILENAME, "w") as f:
            f.write(output_folder)

    tree = ET.parse(xml_file)
    root_xml = tree.getroot()

    rows, errors, idx = [], [], 1

    for nat in root_xml.findall(".//G_NATIONALITY"):
        nat_code = nat.findtext("NATIONALITY", "")
        for guest in nat.findall(".//G_FIRST"):
            if guest.findtext("RESV_STATUS", "").upper() != "CKIN":
                continue

            room = guest.findtext("ROOM", "")
            if selected_rooms and room not in selected_rooms:
                continue

            row, err = extract_guest_data(guest, nat_code, idx)
            if row:
                row[-1] = row[-1].lstrip("0")
                rows.append(row)
            else:
                errors.append(err)
            idx += 1

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if errors:
        log = os.path.join(output_folder, f"POB Error Log {timestamp}.log")
        with open(log, "w") as f:
            f.write("\n".join(errors))
        QMessageBox.warning(None, "Errors Found", f"See log:\n{log}")
    else:
        csv_path = os.path.join(output_folder, f"POB {timestamp}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f, delimiter=";").writerows(rows)
        QMessageBox.information(None, "Success", f"CSV created:\n{csv_path}")


if __name__ == "__main__":
    main()
