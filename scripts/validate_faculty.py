import csv
import re
import sys

def validate_email(email):
    return re.match(r"^\S+@\S+\.\S+$", email)

def validate_faculty(file_path):
    errors = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for idx, row in enumerate(reader, start=2):
            if not row.get("employee_code") or not row.get("name") or not row.get("email") or not row.get("mobile_number") or not row.get("department"):
                errors.append(f"Row {idx}: Missing mandatory fields")
            elif not validate_email(row["email"]):
                errors.append(f"Row {idx}: Invalid email format")
    return errors

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_faculty.py <csv_file>")
    else:
        errs = validate_faculty(sys.argv[1])
        if errs:
            print("Validation Errors:")
            for e in errs:
                print("-", e)
        else:
            print("All rows valid!")
