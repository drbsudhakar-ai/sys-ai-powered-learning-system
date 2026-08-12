"""
Admin Student / Faculty / Academic Responsibility routes (P0-008)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas, database, utils
from app.routes.auth import require_roles

router = APIRouter(prefix="/admin", tags=["Admin"])
_admin = require_roles("admin")


def _user_out(user: models.User) -> schemas.UserOut:
    return schemas.UserOut.model_validate(user)


def _coordinator_out(row: models.FacultyCourseAssignment) -> schemas.CourseCoordinatorOut:
    return schemas.CourseCoordinatorOut(
        id=row.id,
        faculty_id=row.faculty_id,
        faculty_name=row.faculty.name if row.faculty else "",
        faculty_email=row.faculty.email if row.faculty else "unknown@example.com",
        course_id=row.course_id,
        course_title=row.course.title if row.course else "",
        assigned_at=row.assigned_at,
    )


def _expert_out(row: models.SubjectExpertAssignment) -> schemas.SubjectExpertOut:
    return schemas.SubjectExpertOut(
        id=row.id,
        faculty_id=row.faculty_id,
        faculty_name=row.faculty.name if row.faculty else "",
        faculty_email=row.faculty.email if row.faculty else "unknown@example.com",
        subject_id=row.subject_id,
        subject_name=row.subject.name if row.subject else "",
        assigned_at=row.assigned_at,
    )


def _get_role_user(db: Session, user_id: int, role: str) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or (user.role or "").lower() != role:
        raise HTTPException(status_code=404, detail=f"{role.capitalize()} not found")
    return user


# =========================
# Students
# =========================
@router.get("/students", response_model=List[schemas.UserOut])
def list_students(
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    return (
        db.query(models.User)
        .filter(models.User.role == "student")
        .order_by(models.User.name)
        .all()
    )


@router.get("/students/{student_id}", response_model=schemas.UserOut)
def get_student(
    student_id: int,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    return _get_role_user(db, student_id, "student")


@router.post("/students", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: schemas.AdminUserCreate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    if not payload.roll_number:
        raise HTTPException(status_code=422, detail="roll_number is required for students")
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = models.User(
        name=payload.name,
        email=payload.email,
        hashed_password=utils.hash_password(payload.password),
        role="student",
        roll_number=payload.roll_number,
        photo_url=payload.photo_url,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/students/{student_id}", response_model=schemas.UserOut)
def update_student(
    student_id: int,
    payload: schemas.AdminUserUpdate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    user = _get_role_user(db, student_id, "student")
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    if "email" in data and data["email"] != user.email:
        if db.query(models.User).filter(models.User.email == data["email"]).first():
            raise HTTPException(status_code=409, detail="Email already registered")
    for key, value in data.items():
        setattr(user, key, value)
    if password:
        user.hashed_password = utils.hash_password(password)
    db.commit()
    db.refresh(user)
    return user


@router.post("/students/{student_id}/deactivate", response_model=schemas.UserOut)
def deactivate_student(
    student_id: int,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    user = _get_role_user(db, student_id, "student")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.post("/students/{student_id}/activate", response_model=schemas.UserOut)
def activate_student(
    student_id: int,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    user = _get_role_user(db, student_id, "student")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


# =========================
# Faculty
# =========================
@router.get("/faculty", response_model=List[schemas.UserOut])
def list_faculty(
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    return (
        db.query(models.User)
        .filter(models.User.role == "faculty")
        .order_by(models.User.name)
        .all()
    )


@router.get("/faculty/{faculty_id}", response_model=schemas.FacultyResponsibilitiesOut)
def get_faculty(
    faculty_id: int,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    user = _get_role_user(db, faculty_id, "faculty")
    coords = (
        db.query(models.FacultyCourseAssignment)
        .filter(models.FacultyCourseAssignment.faculty_id == faculty_id)
        .all()
    )
    experts = (
        db.query(models.SubjectExpertAssignment)
        .filter(models.SubjectExpertAssignment.faculty_id == faculty_id)
        .all()
    )
    return schemas.FacultyResponsibilitiesOut(
        faculty=_user_out(user),
        course_coordinator_assignments=[_coordinator_out(r) for r in coords],
        subject_expert_assignments=[_expert_out(r) for r in experts],
    )


@router.post("/faculty", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_faculty(
    payload: schemas.AdminUserCreate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    if not payload.employee_code:
        raise HTTPException(status_code=422, detail="employee_code is required for faculty")
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = models.User(
        name=payload.name,
        email=payload.email,
        hashed_password=utils.hash_password(payload.password),
        role="faculty",
        employee_code=payload.employee_code,
        photo_url=payload.photo_url,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/faculty/{faculty_id}", response_model=schemas.UserOut)
def update_faculty(
    faculty_id: int,
    payload: schemas.AdminUserUpdate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    user = _get_role_user(db, faculty_id, "faculty")
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    if "email" in data and data["email"] != user.email:
        if db.query(models.User).filter(models.User.email == data["email"]).first():
            raise HTTPException(status_code=409, detail="Email already registered")
    for key, value in data.items():
        setattr(user, key, value)
    if password:
        user.hashed_password = utils.hash_password(password)
    db.commit()
    db.refresh(user)
    return user


@router.post("/faculty/{faculty_id}/deactivate", response_model=schemas.UserOut)
def deactivate_faculty(
    faculty_id: int,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    user = _get_role_user(db, faculty_id, "faculty")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.post("/faculty/{faculty_id}/activate", response_model=schemas.UserOut)
def activate_faculty(
    faculty_id: int,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    user = _get_role_user(db, faculty_id, "faculty")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


# =========================
# Subjects (minimal)
# =========================
@router.get("/subjects", response_model=List[schemas.SubjectOut])
def list_subjects(
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    return db.query(models.Subject).order_by(models.Subject.name).all()


@router.post("/subjects", response_model=schemas.SubjectOut, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: schemas.SubjectCreate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    if payload.course_id is not None:
        course = db.query(models.Course).filter(models.Course.id == payload.course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
    if db.query(models.Subject).filter(models.Subject.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Subject name already exists")
    subject = models.Subject(
        name=payload.name,
        description=payload.description,
        course_id=payload.course_id,
    )
    db.add(subject)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Subject name already exists")
    db.refresh(subject)
    return subject


# =========================
# Course Coordinator (uses FacultyCourseAssignment)
# =========================
@router.get("/course-coordinators", response_model=List[schemas.CourseCoordinatorOut])
def list_course_coordinators(
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    rows = db.query(models.FacultyCourseAssignment).all()
    return [_coordinator_out(r) for r in rows]


@router.post(
    "/course-coordinators",
    response_model=schemas.CourseCoordinatorOut,
    status_code=status.HTTP_201_CREATED,
)
def assign_course_coordinator(
    payload: schemas.CourseCoordinatorCreate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    faculty = _get_role_user(db, payload.faculty_id, "faculty")
    if not faculty.is_active:
        raise HTTPException(status_code=400, detail="Faculty account is inactive")
    course = db.query(models.Course).filter(models.Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    existing = (
        db.query(models.FacultyCourseAssignment)
        .filter(
            models.FacultyCourseAssignment.faculty_id == payload.faculty_id,
            models.FacultyCourseAssignment.course_id == payload.course_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Course Coordinator assignment already exists")
    row = models.FacultyCourseAssignment(
        faculty_id=payload.faculty_id,
        course_id=payload.course_id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Course Coordinator assignment already exists")
    db.refresh(row)
    # ensure relationships loaded
    db.refresh(row)
    row = (
        db.query(models.FacultyCourseAssignment)
        .filter(models.FacultyCourseAssignment.id == row.id)
        .first()
    )
    return _coordinator_out(row)


@router.delete("/course-coordinators/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_course_coordinator(
    assignment_id: int,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    row = (
        db.query(models.FacultyCourseAssignment)
        .filter(models.FacultyCourseAssignment.id == assignment_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(row)
    db.commit()
    return None


# =========================
# Subject Expert
# =========================
@router.get("/subject-experts", response_model=List[schemas.SubjectExpertOut])
def list_subject_experts(
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    rows = db.query(models.SubjectExpertAssignment).all()
    return [_expert_out(r) for r in rows]


@router.post(
    "/subject-experts",
    response_model=schemas.SubjectExpertOut,
    status_code=status.HTTP_201_CREATED,
)
def assign_subject_expert(
    payload: schemas.SubjectExpertCreate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    faculty = _get_role_user(db, payload.faculty_id, "faculty")
    if not faculty.is_active:
        raise HTTPException(status_code=400, detail="Faculty account is inactive")
    subject = db.query(models.Subject).filter(models.Subject.id == payload.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    existing = (
        db.query(models.SubjectExpertAssignment)
        .filter(
            models.SubjectExpertAssignment.faculty_id == payload.faculty_id,
            models.SubjectExpertAssignment.subject_id == payload.subject_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Subject Expert assignment already exists")
    row = models.SubjectExpertAssignment(
        faculty_id=payload.faculty_id,
        subject_id=payload.subject_id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Subject Expert assignment already exists")
    db.refresh(row)
    row = (
        db.query(models.SubjectExpertAssignment)
        .filter(models.SubjectExpertAssignment.id == row.id)
        .first()
    )
    return _expert_out(row)


@router.delete("/subject-experts/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_subject_expert(
    assignment_id: int,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    row = (
        db.query(models.SubjectExpertAssignment)
        .filter(models.SubjectExpertAssignment.id == assignment_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(row)
    db.commit()
    return None
