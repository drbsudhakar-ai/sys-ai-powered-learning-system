"""Read-only, student-scoped syllabus progress. Never infers mastery from attendance."""
from datetime import timezone
from sqlalchemy import func
from app import models


def _time(value):
    if value is None:
        return 0
    return value.replace(tzinfo=timezone.utc).timestamp() if value.tzinfo is None else value.timestamp()


def summary(db, student_id, course_id):
    topics = db.query(models.Topic).join(models.Subject).filter(
        models.Subject.course_id == course_id, models.Topic.unit_id.isnot(None)
    ).order_by(models.Topic.id).all()
    topic_ids = {t.id for t in topics}
    rows = db.query(models.LearningSession, models.LearningSessionParticipant).join(
        models.LearningSessionParticipant, models.LearningSessionParticipant.session_id == models.LearningSession.id
    ).filter(models.LearningSession.course_id == course_id,
             models.LearningSessionParticipant.user_id == student_id,
             models.LearningSessionParticipant.role == "STUDENT",
             models.LearningSessionParticipant.status != "REMOVED",
             models.LearningSession.status != "CANCELLED").all()
    evidence = dict(db.query(models.LearningEvidence.session_id, func.max(models.LearningEvidence.created_at)).filter(
        models.LearningEvidence.user_id == student_id,
        models.LearningEvidence.session_id.in_([s.id for s, _ in rows] or [-1]),
    ).group_by(models.LearningEvidence.session_id).all())
    full_done, sub_done, started, sub_started = set(), set(), set(), set()
    candidates, topic_sessions = [], {}
    completed_sessions = 0
    for session, participant in rows:
        if session.topic_id not in topic_ids:
            continue
        # A group's completion is not evidence that every student completed it.
        done = participant.status == "COMPLETED" or (session.mode == "INDIVIDUAL" and session.status == "COMPLETED")
        touched = done or session.id in evidence or participant.joined_at is not None
        if done:
            completed_sessions += 1
            (sub_done if session.subtopic_id else full_done).add(session.subtopic_id or session.topic_id)
        if touched:
            started.add(session.topic_id)
            if session.subtopic_id:
                sub_started.add(session.subtopic_id)
        can_resume = not done and session.status in {"DRAFT", "SCHEDULED", "READY", "IN_PROGRESS", "PAUSED"}
        last = max(_time(evidence.get(session.id)), _time(participant.joined_at))
        item = {"session_id": session.id, "topic_id": session.topic_id, "subtopic_id": session.subtopic_id,
                "status": session.status, "can_resume": can_resume,
                "classroom_path": f"/learning-sessions/{session.id}/lecture?course_id={course_id}"}
        previous = topic_sessions.get(session.topic_id)
        if session.subtopic_id is None and (previous is None or (last, session.id) > previous[0]):
            topic_sessions[session.topic_id] = ((last, session.id), item)
        if touched and can_resume:
            candidates.append((last, session.id, item))
    states, sub_states = {}, {}
    for topic in topics:
        children = [s.id for s in topic.subtopics]
        done = topic.id in full_done or (bool(children) and all(s in sub_done for s in children))
        states[topic.id] = "COMPLETED" if done else "IN_PROGRESS" if topic.id in started else "NOT_STARTED"
        # Whole-topic completion does not fabricate separately tracked subtopic evidence.
        for subtopic in topic.subtopics:
            sub_states[subtopic.id] = "COMPLETED" if subtopic.id in sub_done else "IN_PROGRESS" if subtopic.id in sub_started else "NOT_STARTED"
    completed = sum(s == "COMPLETED" for s in states.values())
    total = len(states)
    candidates = [c for c in candidates if states[c[2]["topic_id"]] != "COMPLETED"
                  and c[2]["subtopic_id"] not in sub_done]
    resume = max(candidates, key=lambda c: (c[0], c[1]))[2] if candidates else None
    return {"status": "COMPLETED" if total and completed == total else "IN_PROGRESS" if started else "NOT_STARTED",
            "session_count": len(rows), "active_count": sum(s.status in {"DRAFT", "SCHEDULED", "READY", "IN_PROGRESS", "PAUSED"} for s, _ in rows),
            "completed_count": completed_sessions, "topic_sessions": {k: v[1] for k, v in topic_sessions.items()},
            "topic_states": states, "subtopic_states": sub_states,
            "total_topics": total, "completed_topics": completed,
            "progress_percent": round(100 * completed / total, 1) if total else 0,
            "continue_learning": resume,
            "message": "Continue your most recently used incomplete lesson." if resume else "Select a syllabus topic to begin or review. Completion reflects learning records, not assessment mastery."}


def enrich_syllabus(db, course_id, subjects):
    subject_ids = [s["id"] for s in subjects]
    topic_ids = [t["id"] for s in subjects for u in s["units"] for t in u["topics"]]
    subject_weights = {r.subject_id: r.weight_percent for r in db.query(models.SubjectWeightage).filter_by(course_id=course_id)}
    unit_weights = {r.unit_id: r.weight_percent for r in db.query(models.UnitWeightage).filter(models.UnitWeightage.subject_id.in_(subject_ids or [-1]))}
    topic_weights = {r.topic_id: r.weight_percent for r in db.query(models.TopicWeightage).filter(models.TopicWeightage.subject_id.in_(subject_ids or [-1]))}
    sub_weights = {r.subtopic_id: r.weight_percent for r in db.query(models.SubtopicWeightage).filter(models.SubtopicWeightage.topic_id.in_(topic_ids or [-1]))}
    for subject in subjects:
        subject["weight_percent"] = subject_weights.get(subject["id"])
        for unit in subject["units"]:
            unit["weight_percent"] = unit_weights.get(unit["id"])
            for topic in unit["topics"]:
                topic["weight_percent"] = topic_weights.get(topic["id"])
                for subtopic in topic["subtopics"]:
                    subtopic["weight_percent"] = sub_weights.get(subtopic["id"])
