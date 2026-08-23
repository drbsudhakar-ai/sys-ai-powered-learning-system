from fastapi import APIRouter, HTTPException
from app.supabaseClient import supabase
import re
from datetime import datetime

router = APIRouter()

FACULTY_ALLOWED_COLUMNS = {
    "name", "email", "role", "employee_code", "photo_url",
    "is_active", "institutional_email", "institutional_mobile", "mobile_number",
    "email_verified", "mobile_verified", "mobile_is_personal", "account_status",
    "session_version", "college", "department", "designation",
    "joining_year", "employment_status", "academic_status"
}

@router.post("/faculty/bulk")
def bulk_create_faculty(faculty_list: list[dict], admin_user: str = "system"):
    normalized, skipped, invalid = [], [], []

    for faculty in faculty_list:
        employee_code = faculty.get("employee_code")
        email = faculty.get("email")

        # ✅ Validation
        if not employee_code or not email:
            invalid.append({"employee_code": employee_code, "reason": "Missing employee_code or email"})
            continue
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            invalid.append({"employee_code": employee_code, "reason": "Invalid email format"})
            continue

        # ✅ Duplicate check
        existing = supabase.table("users").select("id").eq("employee_code", employee_code).execute()
        if existing.data and len(existing.data) > 0:
            skipped.append(employee_code)
            continue

        # ✅ Schema-safe insert
        record = {k: v for k, v in faculty.items() if k in FACULTY_ALLOWED_COLUMNS}
        record.update({
            "role": "faculty",
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

    # ✅ Logging
    log_entry = None
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "admin_user": admin_user,
            "total_uploaded": len(faculty_list),
            "inserted": inserted_count,
            "skipped": len(skipped),
            "invalid": len(invalid),
            "skipped_employee_codes": skipped,
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
        "skipped_employee_codes": skipped,
        "invalid_records": invalid,
        "log_entry": log_entry
    }
