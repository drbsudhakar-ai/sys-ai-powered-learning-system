import csv
import re
import sys

def validate_email(email):
    return re.match(r"^\S+@\S+\.\S+$", email)

def validate_students(file_path):
    errors = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for idx, row in enumerate(reader, start=2):
            if not row.get("roll_number") or not row.get("name") or not row.get("email") or not row.get("mobile_number"):
                errors.append(f"Row {idx}: Missing mandatory fields")
            elif not validate_email(row["email"]):
                errors.append(f"Row {idx}: Invalid email format")
            elif not row["admission_year"].isdigit() or not row["present_year"].isdigit():
                errors.append(f"Row {idx}: Admission/Present year must be integers")
    return errors

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_students.py <csv_file>")
    else:
        errs = validate_students(sys.argv[1])
        if errs:
            print("Validation Errors:")
            for e in errs:
                print("-", e)
        else:
            print("All rows valid!")
