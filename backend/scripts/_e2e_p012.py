"""
P0-012 E2E: real P0-011 attempt → analyzer → profile → report → notifications.
Run: python scripts/_e2e_p012.py
"""

from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app import models, database

client = TestClient(app)


def email(p):
    return f"{p}_{uuid.uuid4().hex[:8]}@example.com"


def reg(role, extra):
    e = email(role)
    r = client.post(
        "/auth/register",
        json={"name": f"E2E012 {role}", "email": e, "role": role, "password": "TestPass123!", **extra},
    )
    assert r.status_code == 201, r.text
    login = client.post("/auth/login", data={"username": e, "password": "TestPass123!"})
    assert login.status_code == 200
    return login.json()["access_token"], r.json()["id"]


def auth(t):
    return {"Authorization": f"Bearer {t}"}


def main():
    admin_t, _ = reg("admin", {"employee_code": "E2E012A"})
    fac_t, fac_id = reg("faculty", {"employee_code": "E2E012F"})
    stu_t, stu_id = reg("student", {"roll_number": "E2E012S"})

    course = client.post("/courses/", headers=auth(admin_t), json={"title": "E2E012 Course", "description": "e2e"})
    assert course.status_code == 201
    cid = course.json()["id"]
    assert client.post(
        "/admin/course-coordinators", headers=auth(admin_t), json={"faculty_id": fac_id, "course_id": cid}
    ).status_code == 201

    sub = client.post(
        "/admin/subjects", headers=auth(admin_t), json={"name": f"Sub-{uuid.uuid4().hex[:5]}", "course_id": cid}
    )
    sid = sub.json()["id"]
    topic = client.post("/topics", headers=auth(admin_t), json={"name": "T1", "subject_id": sid})
    tid = topic.json()["id"]

    for i, (diff, ans) in enumerate([("EASY", "A"), ("MEDIUM", "B"), ("HARD", "C")]):
        q = client.post(
            "/question-bank/questions",
            headers=auth(admin_t),
            json={
                "stem": f"E2E012 Q{i} {uuid.uuid4().hex[:6]}",
                "difficulty": diff,
                "status": "ACTIVE",
                "course_id": cid,
                "subject_id": sid,
                "topic_id": tid,
                "options": ["A", "B", "C", "D"],
                "correct_answer": ans,
                "explanation": "e",
                "concept_tags": ["Force"],
                "marks": 2,
                "negative_marks": -0.5,
            },
        )
        assert q.status_code == 201, q.text

    a = client.post(
        "/assessments/",
        headers=auth(fac_t),
        json={
            "title": "E2E012 Topic Test",
            "course_id": cid,
            "assessment_type": "TOPIC_TEST",
            "duration_minutes": 40,
            "total_questions": 3,
            "total_marks": 6,
            "marks_correct": 2,
            "marks_incorrect": -0.5,
            "subject_id": sid,
            "topic_id": tid,
            "max_attempts": 1,
        },
    )
    assert a.status_code == 201, a.text
    aid = a.json()["id"]
    assert (
        client.put(
            f"/assessments/{aid}/blueprint",
            headers=auth(fac_t),
            json=[
                {"subject_id": sid, "topic_id": tid, "difficulty": "EASY", "question_count": 1},
                {"subject_id": sid, "topic_id": tid, "difficulty": "MEDIUM", "question_count": 1},
                {"subject_id": sid, "topic_id": tid, "difficulty": "HARD", "question_count": 1},
            ],
        ).status_code
        == 200
    )
    pub = client.post(f"/assessments/{aid}/publish", headers=auth(fac_t))
    assert pub.status_code == 200, pub.text
    version_id = pub.json()["version_id"]

    assert client.post(f"/courses/{cid}/enroll", headers=auth(stu_t)).status_code == 201
    start = client.post(f"/student/assessments/{aid}/start", headers=auth(stu_t))
    assert start.status_code == 201, start.text
    attempt_id = start.json()["attempt_id"]

    # auto-save
    att = client.get(f"/student/attempts/{attempt_id}", headers=auth(stu_t)).json()
    db = database.SessionLocal()
    try:
        snaps = {
            aq.id: aq
            for aq in db.query(models.AssessmentQuestion)
            .filter(models.AssessmentQuestion.version_id == version_id)
            .all()
        }
    finally:
        db.close()

    for q in att["questions"]:
        correct = snaps[q["assessment_question_id"]].correct_answer_snapshot
        assert (
            client.post(
                f"/student/attempts/{attempt_id}/responses",
                headers=auth(stu_t),
                json={"assessment_question_id": q["assessment_question_id"], "selected_answer": correct, "time_spent_delta": 5},
            ).status_code
            == 200
        )

    # resume
    assert client.post(f"/student/assessments/{aid}/start", headers=auth(stu_t)).json()["attempt_id"] == attempt_id

    submit = client.post(f"/student/attempts/{attempt_id}/submit", headers=auth(stu_t))
    assert submit.status_code == 200 and submit.json()["status"] == "EVALUATED"

    analysis = client.get(
        f"/analyzer/students/{stu_id}/courses/{cid}",
        headers=auth(stu_t),
        params={"refresh": True},
    )
    assert analysis.status_code == 200, analysis.text
    body = analysis.json()
    assert body["overall"]["total_assessments"] >= 1
    assert body["profile"]["evidence"]["source"] == "P0-011_EVALUATED_ATTEMPTS"
    assert body["readiness"]["label"] == "ANALYTICAL_ESTIMATE"

    profile = client.get(f"/analyzer/students/{stu_id}/courses/{cid}/profile", headers=auth(stu_t))
    assert profile.status_code == 200 and "ai_lecturer_contract" in profile.json()

    pdf = client.get(f"/analyzer/students/{stu_id}/courses/{cid}/report.pdf", headers=auth(stu_t))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF") and b"SYS" in pdf.content

    inbox = client.get("/inbox/notifications", headers=auth(stu_t))
    assert inbox.status_code == 200 and len(inbox.json()) >= 1

    # coordinator opens report (authz)
    fac_view = client.get(f"/analyzer/students/{stu_id}/courses/{cid}/report", headers=auth(fac_t))
    assert fac_view.status_code == 200

    print("E2E_P012_PASS")
    print(f"student={stu_id} course={cid} attempt={attempt_id} overall={body['overall'].get('average_percentage')}")


if __name__ == "__main__":
    main()
