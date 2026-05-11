"""XLSX Writer - Write Question objects back to XLSX format for round-trip testing."""

from openpyxl import Workbook

from exam_mockup_agent.models import Question


def write_xlsx(questions: list[Question], file_path: str) -> None:
    """Write a list of Question objects to an XLSX file."""
    wb = Workbook()
    ws = wb.active

    # Determine if any questions use Option_E or Option_F
    has_e = any("E" in q.options for q in questions)
    has_f = any("F" in q.options for q in questions)

    headers = [
        "Question",
        "Option_A",
        "Option_B",
        "Option_C",
        "Option_D",
    ]
    if has_e:
        headers.append("Option_E")
    if has_f:
        headers.append("Option_F")
    headers.extend(["Correct_Answer", "Question_Type"])

    ws.append(headers)

    for q in questions:
        row = [
            q.text,
            q.options.get("A", ""),
            q.options.get("B", ""),
            q.options.get("C", ""),
            q.options.get("D", ""),
        ]
        if has_e:
            row.append(q.options.get("E", ""))
        if has_f:
            row.append(q.options.get("F", ""))

        if q.question_type == "multiple":
            correct_str = ",".join(q.correct_answers)
        else:
            correct_str = q.correct_answers[0] if q.correct_answers else ""

        row.extend([correct_str, q.question_type])
        ws.append(row)

    wb.save(file_path)
