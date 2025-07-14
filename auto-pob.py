import sys
import os
import xml.etree.ElementTree as ET
import csv

# Constants
REQUIRED_FIELDS = [
    "documento", "apellido1", "nombre1", "sexo",
    "idpaisnacionalidad", "idpaisresidencia",
    "fechaNacimiento", "fechaEntrada", "fechaSalida", "habitacion"
]

FIELD_ORDER = [
    "documento", "idpaisdocumento", "tipodocumento", "apellido1", "apellido2",
    "nombre1", "nombre2", "sexo", "idpaisnacionalidad", "idpaisresidencia",
    "fechaNacimiento", "fechaEntrada", "fechaSalida", "habitacion"
]

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

    # Validate mapped tipo id
    if raw_tipo and mapped_tipo_id is None:
        errors.append(f"Invalid tipodocumento value: '{raw_tipo}' (only '3' and '5' allowed)")

    if errors:
        guest_name = f"{data.get('apellido1', '')}, {data.get('nombre1', '')}".strip()
        return None, f"Entry #{index}: {guest_name or '[unknown name]'} — " + "; ".join(errors)

    return [data[field] for field in FIELD_ORDER], None

# Main script logic
def main():
# --- Step 1: Get the filename ---
    if len(sys.argv) < 2:
        print('Usage: python script.py file.xml')
        sys.exit(1)

# --- Step 2: Check if the file exists ---
    xml_file = sys.argv[1]
    if not os.path.exists(xml_file):
        print(f'File "{xml_file}" not found')
        sys.exit(1)

# --- Step 3: Parse the XML ---
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError:
        print("The XML file could not be parsed")
        sys.exit(1)


# --- Step 4: Process each guest entry ---
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

# --- Step 5: Output
    base_name = os.path.splitext(xml_file)[0]
    
    if errors:
        log_file = base_name + ".log"
        with open(log_file, "w", encoding="utf-8") as log:
            log.write("Errors found in POB data:\n\n")
            for err in errors:
                log.write(f"- {err}\n")
        print(f"Export failed. Errors written to: {log_file}")
    else:
        csv_file = base_name + ".csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(FIELD_ORDER)
            writer.writerows(valid_rows)
        print(f"CSV export complete: {csv_file}")

if __name__ == "__main__":
    main()
