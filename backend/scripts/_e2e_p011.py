"""
P0-011 live E2E: publish → enroll → start → save → resume → submit → result → answer key.
Run from backend/: python scripts/_e2e_p011.py
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app import models, database

client = TestClient(app)


def _email(p):
    return f"{p}_{uuid.uuid4().hex[:8]}@example.com"


def _reg(role, extra):
    email = _email(role)
    r = client.post(
        "/auth/register",
        json={"name": f"E2E {role}", "email": email, "role": role, "password": "TestPass123!", **extra},
    )
    assert r.status_code == 201, r.text
    login = client.post("/auth/login", data={"username": email, "password": "TestPass123!"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"], r.json()["id"]


def auth(t):
    return {"Authorization": f"Bearer {t}"}


def main():
    admin_t, _ = _reg("admin", {"employee_code": "E2E011A"})
    fac_t, fac_id = _reg("faculty", {"employee_code": "E2E011F"})
    stu_t, _ = _reg("student", {"roll_number": "E2E011S"})

    course = client.post("/courses/", headers=auth(admin_t), json={"title": "E2E011 Course", "description": "e2e"})
    assert course.status_code == 201, course.text
    cid = course.json()["id"]
    assert client.post(
        "/admin/course-coordinators", headers=auth(admin_t), json={"faculty_id": fac_id, "course_id": cid}
    ).status_code == 201

    sub = client.post("/admin/subjects", headers=auth(admin_t), json={"name": f"Sub-{uuid.uuid4().hex[:5]}", "course_id": cid})
    assert sub.status_code == 201
    sid = sub.json()["id"]
    topic = client.post("/topics", headers=auth(admin_t), json={"name": "T1", "subject_id": sid})
    assert topic.status_code == 201
    tid = topic.json()["id"]

    for i, (diff, ans) in enumerate([("EASY", "A"), ("MEDIUM", "B"), ("HARD", "C")]):
        q = client.post(
            "/question-bank/questions",
            headers=auth(admin_t),
            json={
                "stem": f"E2E011 Q{i} {uuid.uuid4().hex[:6]}",
                "difficulty": diff,
                "status": "ACTIVE",
                "course_id": cid,
                "subject_id": sid,
                "topic_id": tid,
                "options": ["A", "B", "C", "D"],
                "correct_answer": ans,
                "explanation": f"Explain {ans}",
                "marks": 2,
                "negative_marks": -0.5,
            },
        )
        assert q.status_code == 201, q.text

    a = client.post(
        "/assessments/",
        headers=auth(fac_t),
        json={
            "title": "E2E011 Assessment",
            "course_id": cid,
            "assessment_type": "TOPIC_TEST",
            "duration_minutes": 45,
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
    bp = client.put(
        f"/assessments/{aid}/blueprint",
        headers=auth(fac_t),
        json=[
            {"subject_id": sid, "topic_id": tid, "difficulty": "EASY", "question_count": 1},
            {"subject_id": sid, "topic_id": tid, "difficulty": "MEDIUM", "question_count": 1},
            {"subject_id": sid, "topic_id": tid, "difficulty": "HARD", "question_count": 1},
        ],
    )
    assert bp.status_code == 200, bp.text
    pub = client.post(f"/assessments/{aid}/publish", headers=auth(fac_t))
    assert pub.status_code == 200, pub.text
    version_id = pub.json()["version_id"]

    en = client.post(f"/courses/{cid}/enroll", headers=auth(stu_t))
    assert en.status_code == 201, en.text

    start = client.post(f"/student/assessments/{aid}/start", headers=auth(stu_t))
    assert start.status_code == 201, start.text
    attempt_id = start.json()["attempt_id"]
    assert start.json()["remaining_seconds"] > 0

    # resume
    start2 = client.post(f"/student/assessments/{aid}/start", headers=auth(stu_t))
    assert start2.json()["attempt_id"] == attempt_id

    att = client.get(f"/student/attempts/{attempt_id}", headers=auth(stu_t))
    assert att.status_code == 200
    questions = att.json()["questions"]
    assert len(questions) == 3

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

    for q in questions:
        snap = snaps[q["assessment_question_id"]]
        # answer first correctly, second wrongly, third leave blank after clear
        pass

    q0, q1, q2 = questions[0], questions[1], questions[2]
    c0 = snaps[q0["assessment_question_id"]].correct_answer_snapshot
    wrong1 = next(
        o
        for o in (snaps[q1["assessment_question_id"]].options_snapshot or [])
        if o != snaps[q1["assessment_question_id"]].correct_answer_snapshot
    )
    assert (
        client.post(
            f"/student/attempts/{attempt_id}/responses",
            headers=auth(stu_t),
            json={"assessment_question_id": q0["assessment_question_id"], "selected_answer": c0, "time_spent_delta": 3},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/student/attempts/{attempt_id}/responses",
            headers=auth(stu_t),
            json={
                "assessment_question_id": q1["assessment_question_id"],
                "selected_answer": wrong1,
                "marked_for_review": True,
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/student/attempts/{attempt_id}/responses",
            headers=auth(stu_t),
            json={"assessment_question_id": q2["assessment_question_id"], "selected_answer": "A"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/student/attempts/{attempt_id}/responses",
            headers=auth(stu_t),
            json={"assessment_question_id": q2["assessment_question_id"], "clear": True},
        ).status_code
        == 200
    )

    # resume again mid-way
    mid = client.get(f"/student/attempts/{attempt_id}", headers=auth(stu_t))
    assert mid.json()["summary"]["answered"] == 2

    submit = client.post(f"/student/attempts/{attempt_id}/submit", headers=auth(stu_t))
    assert submit.status_code == 200, submit.text
    result = submit.json()
    assert result["status"] == "EVALUATED"
    assert result["correct"] == 1 and result["incorrect"] == 1 and result["unanswered"] == 1
    assert abs(result["score"] - 1.5) < 0.01
    assert result["subject_performance"] and result["difficulty_performance"]

    db = database.SessionLocal()
    try:
        perf = db.query(models.PerformanceRecord).filter(models.PerformanceRecord.attempt_id == attempt_id).count()
        assert perf == 3
        at = db.query(models.AssessmentAttempt).get(attempt_id)
        assert at.version_id == version_id
    finally:
        db.close()

    assert client.get(f"/assessments/{aid}/answer-key", headers=auth(stu_t)).status_code == 403
    assert client.post(f"/assessments/{aid}/release-answer-key", headers=auth(fac_t)).status_code == 200
    ak = client.get(f"/assessments/{aid}/answer-key", headers=auth(stu_t))
    assert ak.status_code == 200
    assert len(ak.json()["questions"]) == 3
    pdf = client.get(f"/assessments/{aid}/answer-key.pdf", headers=auth(stu_t))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF") and b"SYS" in pdf.content

    # bank edit must not change answer key
    db = database.SessionLocal()
    try:
        aq = db.query(models.AssessmentQuestion).filter(models.AssessmentQuestion.version_id == version_id).first()
        orig = aq.correct_answer_snapshot
        qrow = db.query(models.Question).get(aq.question_id)
        qrow.correct_answer = "MUTATED"
        db.commit()
    finally:
        db.close()
    ak2 = client.get(f"/assessments/{aid}/answer-key", headers=auth(stu_t)).json()
    assert any(q["correct_answer"] == orig for q in ak2["questions"])
    assert all(q["correct_answer"] != "MUTATED" for q in ak2["questions"])

    print("E2E_P011_PASS")
    print(f"assessment_id={aid} attempt_id={attempt_id} version_id={version_id} score={result['score']}")


if __name__ == "__main__":
    main()
