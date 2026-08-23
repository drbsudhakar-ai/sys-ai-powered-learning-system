"""Administrator-only faculty master-data imports."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import database, models
from app.routes.auth import require_roles
from app.services.master_bulk_upload import import_master_records


router = APIRouter(tags=["Master uploads"])


@router.post("/faculty/bulk")
def bulk_create_faculty(
    faculty_list: list[dict],
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(require_roles("admin")),
):
    """Create pending faculty masters without provisioning login accounts."""

    return import_master_records(db, current_admin, faculty_list, role="faculty")
