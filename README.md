# AutoPOB

AutoPOB is a purpose-built desktop application that automates the preparation of guest reporting data for Uruguay’s **POB (Policía de Hospedajes)** system.

It processes **Opera Cloud XML reports**, applies reporting rules and data validation, and produces **POB-compliant CSV files** ready for bulk upload—eliminating repetitive manual entry while preserving existing hotel workflows.

The tool is designed for **Front Desk and Night Shift operations**, prioritizing reliability, clarity, and compliance over unnecessary complexity.

---

## Key Features

- Converts Opera Cloud XML reports into POB-compatible CSV files  
- Applies field validation and normalization based on official POB requirements  
- Supports full-property or room-specific report generation  
- Prevents common formatting and data-entry errors before upload  
- Desktop-based, offline-first execution  
- License validation to ensure controlled distribution  

---

## Why AutoPOB Exists

In many hotel environments, guest data must be entered manually into both the PMS and the national reporting platform. AutoPOB removes this duplication by acting as a **controlled transformation layer** between systems—reducing operational load while maintaining data integrity and compliance.

This is not a generic file converter.  
AutoPOB encodes domain-specific rules and safeguards that reflect real-world hotel reporting constraints.

---

## Technology Overview

- Python 3  
- Qt (PySide6) for the user interface  
- XML parsing and structured CSV generation  
- Cryptographic license validation  
- Packaged as a single executable via PyInstaller  

---

## Status

AutoPOB is actively used and maintained as a production tool.  
Future updates focus on incremental improvements, stability, and usability—rather than feature expansion for its own sake.

---

## Author

**Eduardo González**  
Project Lead & Developer  
Pacific Fern
