import sys
import os
import xml.etree.ElementTree as ET
import csv

# --- Step 1: Get the filename ---
if len(sys.argv) < 2:
    print('Please provide an XML file to convert.')
    sys.exit(1)

xml_file = sys.argv[1]

# --- Step 2: Check if the file exists ---
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

# --- Step 4: Prepare the output CSV ---
output_file = xml_file.replace(".xml", ".csv")

# --- Step 5: Open the CSV file for writing ---
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)

    writer.writerow([
    "documento", "idpaisdocumento", "tipodocumento", "apellido1", "apellido2", 
    "nombre1", "nombre2", "sexo", "idpaisnacionalidad", "idpaisresidencia",
    "fechaNacimiento", "fechaEntrada", "fechaSalida", "habitacion"
    ])

    for person in root.findall("person"):
        required_fields = ["documento", "idpaisdocumento", "tipodocumento", "apellido1", 
    "nombre1", "sexo", "idpaisnacionalidad", "idpaisresidencia",
    "fechaNacimiento", "fechaEntrada", "fechaSalida", "habitacion"]

        missing = [field for field in required_fields if not person.findtext(field, default="").strip()]
        if missing:
            print(f"ERROR: Falta(n) campo(s) requerido(s): {', '.join(missing)} in one <person> entry.")
            sys.exit(1)

        writer.writerow([
            person.findtext("documento"),
            person.findtext("idpaisdocumento"),
            person.findtext("tipodocumento"),
            person.findtext("apellido1"),
            person.findtext("apellido2", default=""),
            person.findtext("nombre1"),
            person.findtext("nombre2", default=""),
            person.findtext("sexo"),
            person.findtext("idpaisnacionalidad"),
            person.findtext("idpaisresidencia"),
            person.findtext("fechaNacimiento"),
            person.findtext("fechaEntrada"),
            person.findtext("fechaSalida"),
            person.findtext("habitacion")
        ])

print(f"CSV export complete: {output_file}")