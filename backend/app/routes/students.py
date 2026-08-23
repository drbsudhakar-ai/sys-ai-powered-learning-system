from fastapi import APIRouter, HTTPException
from app.supabaseClient import supabase
import re
from datetime import datetime

router = APIRouter()

# ✅ Only include columns that actually exist in your Supabase "users" table
ALLOWED_COLUMNS = {
    "name", "email", "role", "roll_number", "employee_code", "photo_url",
    "is_active", "institutional_email", "institutional_mobile", "mobile_number",
    "email_verified", "mobile_verified", "mobile_is_personal", "account_status",
    "session_version", "college", "department",
    "admission_year", "present_year", "academic_status",
    "academic_program"
}

@router.post("/students/bulk")
def bulk_create_students(students: list[dict], admin_user: str = "system"):
    normalized, skipped, invalid = [], [], []

    for student in students:
        roll_number = student.get("roll_number")
        email = student.get("email")

        # ✅ Validation
        if not roll_number or not email:
            invalid.append({"roll_number": roll_number, "reason": "Missing roll_number or email"})
            continue
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            invalid.append({"roll_number": roll_number, "reason": "Invalid email format"})
            continue

        # ✅ Duplicate check
        existing = supabase.table("users").select("id").eq("roll_number", roll_number).execute()
        if existing.data and len(existing.data) > 0:
            skipped.append(roll_number)
            continue

        # ✅ Schema-safe insert
        record = {k: v for k, v in student.items() if k in ALLOWED_COLUMNS}
        record.update({
            "role": "student",
            "is_active": True,
            "account_status": "ACTIVE",
            "session_version": 1,
        })
        normalized.append(record)

    inserted_count = 0
    if normalized:
        try:
            response = supabase.table("users").insert(normalized).execute()
            if not response.data:
                raise HTTPException(status_code=500, detail="No data returned from Supabase")
            inserted_count = len(response.data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ✅ Automatic logging into uploads_log (make sure this table exists!)
    log_entry = None
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "admin_user": admin_user,
            "total_uploaded": len(students),
            "inserted": inserted_count,
            "skipped": len(skipped),
            "invalid": len(invalid),
            "skipped_roll_numbers": skipped,
            "invalid_records": invalid,
        }
        supabase.table("uploads_log").insert(log_entry).execute()
    except Exception as log_err:
        print("Uploads_log insert error:", log_err)

    return {
        "status": "success" if inserted_count > 0 else "skipped",
        "inserted": inserted_count,
        "skipped": len(skipped),
        "invalid": len(invalid),
        "skipped_roll_numbers": skipped,
        "invalid_records": invalid,
        "log_entry": log_entry
    }
