# AutoPOB

AutoPOB is a lightweight desktop application that automates the preparation of guest reporting data for Uruguay’s **POB (Población flotante de Habitaciones)** system.

It ingests hotel reports (XML **and Excel** formats), applies reporting rules and extensive data validation, and outputs **POB‑compliant CSV files** ready for bulk upload. By integrating with existing property management workflows, it eliminates repetitive manual entry while safeguarding data integrity.

The tool is intended for **Front Desk, Night Audit and management use**; reliability, transparency, and compliance are prioritized over feature bloat.

---

## Key Features

- Converts Opera Cloud XML reports (and exported Excel spreadsheets) into POB‑compatible CSV files
- Built‑in validation for required fields, country codes, gender values, date normalization, etc.
- Option to process all rooms or a user‑specified subset
- Error logging with human‑readable, numbered reports when records fail validation
- Remembers last input folder and lets user save default output directory via config files
- License validation using RSA signatures; supports machine‑locked and BETA licenses
- Desktop‑based, offline‑first execution with a PySide6 GUI

---

## Why AutoPOB Exists

In many hotel environments, guest data must be entered manually into both the PMS and the national reporting platform. AutoPOB removes this duplication by acting as a **controlled transformation layer** between systems—reducing operational load while maintaining data integrity and compliance.

This is not a generic file converter.  
AutoPOB encodes domain-specific rules and safeguards that reflect real-world hotel reporting constraints.

---

## Technology Overview

- Python 3.11+ (runs under a virtualenv or bundled executable)
- PySide6 (Qt) user interface with custom styling
- XML/Excel parsing via `xml.etree.ElementTree` and `pandas`
- CSV output with configurable delimiter and sorted room numbers
- RSA‑based license verification (public key stored as resource)
- PyInstaller build script (`autopob.spec`) for single‑file distribution

---

## Status

AutoPOB is actively used and maintained in production environments. Bug fixes, validation enhancements, and build/process improvements are the primary focus; new features are added only when they provide clear operational value.

---

## Author

**Eduardo González**  
Project Lead & Developer  
Pacific Fern
