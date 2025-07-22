import sys
import os
import xml.etree.ElementTree as ET
import csv
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

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

CONFIG_FILENAME = "output_path.cfg"

# Function to extract guest info and validate
def extract_guest_data(guest, nationality_code, index):
    q_id = guest.find(".//Q_ID")
    raw_tipo = q_id.findtext("ID_TYPE", "").strip() if q_id is not None else ""
    mapped_tipo_id = {"3": "CI", "5": "P"}.get(raw_tipo)

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
            row, error = extract_guest_data(guest, nationality_code, entry_index)
            if row:
                valid_rows.append(row)
            else:
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
