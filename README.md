# 🏨 POB Automation Script

This project automates the process of generating valid `.csv` files for mass guest entry into the **POB (Población Flotante)** system in Uruguay, using guest data exported from **Opera Cloud**, the property management system used by The Grand Hotel – Punta del Este (TGHPDE).

---

## 📌 Context

In Uruguay, hotels are legally required to register all guests residing on their property. This is managed through a government platform known as **POB**, which tracks the *floating population* in each area.

POB allows data entry in two ways:
- Manual entry (one guest at a time)
- Mass upload via a properly formatted `.csv` file

At TGHPDE, guest information is already entered manually into **Opera Cloud**, a hotel management system. However, the same data must also be re-entered manually into POB — a process that is:
- Time-consuming  
- Error-prone  
- Redundant

---

## 🎯 Goal

Create a Python script that:
- Takes an exported `.xml` report from Opera Cloud (containing guest reservation data)
- Converts it into a `.csv` file with the structure required by POB
- Enables batch uploading of guest data, eliminating the need for duplicate manual entry

---

## ⚙️ How It Works

1. A customized XML report is generated from Opera Cloud containing all checked-in guest information.
2. The script parses the XML and extracts the relevant fields (e.g., guest name, document number, check-in/check-out dates, nationality, etc.).
3. It outputs a `.csv` file that matches the official POB format.
4. This file is then uploaded to the POB platform.

---

## ✅ Benefits

- **Faster Check-In Processing**  
  Receptionists no longer need to input POB data during Check-In (~20 seconds saved per guest).

- **Streamlined Auditing**  
  Night Auditors verify only Opera Cloud. The POB file is generated and uploaded afterward.

- **Reduces Redundancy**  
  Guest data is entered once — no more duplicated work between systems.

- **Minimizes Human Error**  
  Automation reduces the risk of typos and inconsistencies between databases.

- **Improves Operational Flow**  
  Front Desk staff are freed to focus on guest service and incident management, especially during peak periods.

---

## 💼 Use Case at TGHPDE

The script is designed to fit into the **night audit routine**:
- After verifying that all reservations are properly recorded in Opera Cloud,  
- The Auditor generates the XML report,  
- Runs the script to convert it to CSV,  
- And uploads the final file to POB — completing the legal obligation in a single, efficient step.

---

## 📂 Future Improvements

- GUI version for non-technical users
- Intelligent error handling: if required fields like the guest’s document number are missing, the script will halt and return a clear error message including the line number and full guest entry, making it easier to identify and fix data issues before uploading to POB

---

## 🖥️ Author

**Eduardo González**  
POB Automation Project Lead<br>
@ Pacific Fern

---
