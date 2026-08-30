"""Generate disposable export QA fixtures; never connects to the development DB."""
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import json
from app.services.syllabus_pdf import build_approved_pdf
from app.services.syllabus_workbook import build_workbook, contract


def generate(destination):
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=True)
    nodes = []
    for s, subject in enumerate(("Arithmetic", "General Science"), 1):
        nodes.append(dict(key=f"subject:{s}", level="subject", parent=None, name=subject,
            description="A reviewed instructional subject with clear learning expectations.", sequence=s, learning_outcome=""))
        nodes.append(dict(key=f"unit:{s}", level="unit", parent=f"subject:{s}", name="Core concepts",
            description="Build understanding through worked examples, practice and recap.", sequence=1,
            learning_outcome="Explain the concept, solve a worked example and identify common mistakes."))
        for t in range(1, 5):
            topic = s * 10 + t
            nodes.append(dict(key=f"topic:{topic}", level="topic", parent=f"unit:{s}", name=f"Topic {t}: Concept and application",
                description="Understand the principle and apply it in intermediate-standard examination questions.", sequence=t, learning_outcome=""))
            for st in range(1, 3):
                nodes.append(dict(key=f"subtopic:{topic*10+st}", level="subtopic", parent=f"topic:{topic}",
                    name=f"Worked example {st}", description="Explain each step, verify the result and review a common misconception.", sequence=st, learning_outcome=""))
    version = SimpleNamespace(number=1, course_title="SYS Police Constable Pilot - QA sample", programme_code="QA-ONLY",
        created_at=datetime.now(timezone.utc))
    proposal = SimpleNamespace(id=1, base_hash="test-baseline", version=1, proposed_nodes=nodes)
    course = SimpleNamespace(title=version.course_title)
    (destination / "approved.pdf").write_bytes(build_approved_pdf(version, nodes, "QA Course Coordinator"))
    (destination / "review.xlsx").write_bytes(build_workbook(proposal, course))
    (destination / "contract.json").write_text(json.dumps(contract(proposal)), encoding="utf-8")
    print(f"QA samples: {len(nodes)} nodes")


if __name__ == "__main__":
    import sys
    generate(sys.argv[1])
