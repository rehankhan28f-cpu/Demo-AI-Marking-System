from flask import Flask, render_template, request, redirect, send_from_directory, jsonify
import mysql.connector
import os
from werkzeug.utils import secure_filename
from pdf_processor import extract_questions_from_pdf
import pytesseract
import pypdfium2 as pdfium

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/examiner-login", methods=["GET", "POST"])
def examiner_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="MP6111",
            database="ai_exam_system"
        )

        cursor = db.cursor()

        cursor.execute(
            """
            SELECT * FROM examiner_users
            WHERE email=%s AND password=%s
            """,
            (email, password)
        )

        examiner = cursor.fetchone()

        cursor.close()
        db.close()

        if examiner:
            return redirect("/examiner-dashboard")

        return "Invalid Email or Password"

    return render_template("examiner_login.html")


@app.route("/university-login", methods=["GET", "POST"])
def university_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="MP6111",
            database="ai_exam_system"
        )

        cursor = db.cursor()

        cursor.execute(
            "SELECT * FROM university_users WHERE email=%s AND password=%s",
            (email, password)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user:
            return redirect("/university-dashboard")

        return "Invalid Email or Password"

    return render_template("university_login.html")
    
@app.route("/university-dashboard")
def university_dashboard():

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    # Total subjects
    cursor.execute("SELECT COUNT(*) FROM subjects")
    total_subjects = cursor.fetchone()[0]

    # Total teachers
    cursor.execute("SELECT COUNT(*) FROM teachers")
    total_teachers = cursor.fetchone()[0]

    # Total answer sheets
    cursor.execute("SELECT COUNT(*) FROM answer_sheets")
    total_copies = cursor.fetchone()[0]

    # Pending copies
    cursor.execute("""
        SELECT COUNT(*)
        FROM answer_sheets
        WHERE status = 'Pending'
    """)
    pending_copies = cursor.fetchone()[0]

    # Evaluated copies
    cursor.execute("""
        SELECT COUNT(*)
        FROM answer_sheets
        WHERE status = 'Evaluated'
    """)
    evaluated_copies = cursor.fetchone()[0]

    # Completed copies
    cursor.execute("""
        SELECT COUNT(*)
        FROM answer_sheets
        WHERE status = 'Completed'
    """)
    completed_copies = cursor.fetchone()[0]

    cursor.close()
    db.close()

    return render_template(
        "university_dashboard.html",
        total_subjects=total_subjects,
        total_teachers=total_teachers,
        total_copies=total_copies,
        pending_copies=pending_copies,
        evaluated_copies=evaluated_copies,
        completed_copies=completed_copies
    )


@app.route("/reports")
def reports():

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    # Total copies
    cursor.execute("SELECT COUNT(*) FROM answer_sheets")
    total_copies = cursor.fetchone()[0]

    # Pending
    cursor.execute("""
        SELECT COUNT(*)
        FROM answer_sheets
        WHERE status = 'Pending'
    """)
    pending_copies = cursor.fetchone()[0]

    # Evaluated
    cursor.execute("""
        SELECT COUNT(*)
        FROM answer_sheets
        WHERE status = 'Evaluated'
    """)
    evaluated_copies = cursor.fetchone()[0]

    # Completed
    cursor.execute("""
        SELECT COUNT(*)
        FROM answer_sheets
        WHERE status = 'Completed'
    """)
    completed_copies = cursor.fetchone()[0]

     # Subject-wise progress
    cursor.execute("""
        SELECT
            subject,
            COUNT(*) AS total,
            SUM(CASE
                WHEN status IN ('Evaluated', 'Completed')
                THEN 1 ELSE 0
            END) AS evaluated,
            SUM(CASE
                WHEN status = 'Completed'
                THEN 1 ELSE 0
            END) AS completed
        FROM answer_sheets
        GROUP BY subject
        ORDER BY subject
    """)

    subject_progress = cursor.fetchall()

    # Examiner-wise progress
    cursor.execute("""
        SELECT
            teachers.teacher_name,
            COUNT(answer_sheets.id) AS assigned,
            SUM(
                CASE
                    WHEN answer_sheets.status IN ('Evaluated', 'Completed')
                    THEN 1 ELSE 0
                END
            ) AS evaluated,
            SUM(
                CASE
                    WHEN answer_sheets.status = 'Completed'
                    THEN 1 ELSE 0
                END
            ) AS completed
        FROM teachers
        LEFT JOIN answer_sheets
            ON answer_sheets.assigned_teacher_id = teachers.id
        GROUP BY teachers.id, teachers.teacher_name
        ORDER BY teachers.teacher_name
    """)

    examiner_progress = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "reports.html",
        total_copies=total_copies,
        pending_copies=pending_copies,
        evaluated_copies=evaluated_copies,
        completed_copies=completed_copies,
        subject_progress=subject_progress,
        examiner_progress=examiner_progress
    )

@app.route("/subjects", methods=["GET", "POST"])
def subjects():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    if request.method == "POST":
        subject_name = request.form["subject_name"]
        subject_code = request.form["subject_code"]
        semester = request.form["semester"]

        cursor.execute(
            """
            INSERT INTO subjects (subject_name, subject_code, semester)
            VALUES (%s, %s, %s)
            """,
            (subject_name, subject_code, semester)
        )

        db.commit()

    cursor.execute("SELECT * FROM subjects")
    subject_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "subjects.html",
        subjects=subject_list
    )
@app.route("/teachers", methods=["GET", "POST"])
def teachers():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    if request.method == "POST":
        teacher_name = request.form["teacher_name"]
        email = request.form["email"]
        subject = request.form["subject"]

        cursor.execute(
            """
            INSERT INTO teachers (teacher_name, email, subject)
            VALUES (%s, %s, %s)
            """,
            (teacher_name, email, subject)
        )

        db.commit()

    cursor.execute("SELECT * FROM teachers")
    teacher_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "teachers.html",
        teachers=teacher_list
    )

@app.route("/questions", methods=["GET", "POST"])
def questions():

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    if request.method == "POST":

        subject = request.form["subject"]
        question_text = request.form["question_text"]
        max_marks = request.form["max_marks"]
        model_answer = request.form["model_answer"]

        cursor.execute(
            """
            INSERT INTO questions
            (subject, question_text, max_marks, model_answer)
            VALUES (%s, %s, %s, %s)
            """,
            (subject, question_text, max_marks, model_answer)
        )

        db.commit()

    cursor.execute("SELECT * FROM questions")
    question_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "questions.html",
        questions=question_list
    )    



@app.route("/question-papers", methods=["GET", "POST"])
def question_papers():

    upload_folder = "uploads/question_papers"
    os.makedirs(upload_folder, exist_ok=True)

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    if request.method == "POST":

        subject = request.form["subject"]
        file = request.files["question_paper"]

        filename = secure_filename(file.filename)

        file_path = os.path.join(upload_folder, filename)

        file.save(file_path)

        # Save question paper
        cursor.execute(
            """
            INSERT INTO question_papers
            (subject, file_name)
            VALUES (%s, %s)
            """,
            (subject, filename)
        )

        db.commit()

        # Extract questions from PDF
        questions = extract_questions_from_pdf(file_path)

        # Save extracted questions
        for question in questions:

            cursor.execute(
                """
                INSERT INTO questions
                (subject, question_text, max_marks, model_answer)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    subject,
                    question["question_text"],
                    question["max_marks"],
                    ""
                )
            )

        db.commit()

    cursor.execute(
        "SELECT * FROM question_papers ORDER BY id DESC"
    )

    papers = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "question_papers.html",
        papers=papers
    )


@app.route("/process-question-paper/<int:paper_id>")
def process_question_paper(paper_id):

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    # Get uploaded question paper
    cursor.execute(
        """
        SELECT subject, file_name
        FROM question_papers
        WHERE id = %s
        """,
        (paper_id,)
    )

    paper = cursor.fetchone()

    if not paper:
        cursor.close()
        db.close()
        return "Question paper not found"

    subject = paper[0]
    filename = paper[1]

    file_path = os.path.join(
        "uploads/question_papers",
        filename
    )

    # Extract questions from PDF
    questions = extract_questions_from_pdf(file_path)

    # Save extracted questions
    for question in questions:

        cursor.execute(
            """
            SELECT id
            FROM questions
            WHERE question_paper_id = %s
            AND question_text = %s
            LIMIT 1
            """,
            (
                paper_id,
                question["question_text"]
            )
        )

        existing_question = cursor.fetchone()

        if not existing_question:

            cursor.execute(
                """
                INSERT INTO questions
                (subject, question_text, max_marks, model_answer, question_paper_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    subject,
                    question["question_text"],
                    question["max_marks"],
                    "",
                    paper_id
                )
            )

    db.commit()

    cursor.close()
    db.close()

    return render_template(
    "question_review.html",
    subject=subject,
    questions=questions,
    paper_id=paper_id
)

@app.route("/approve-questions/<int:paper_id>", methods=["POST"])
def approve_questions(paper_id):

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    # Is question paper ke questions nikalo
    cursor.execute(
        """
        SELECT id
        FROM questions
        WHERE question_paper_id = %s
        ORDER BY id
        """,
        (paper_id,)
    )

    question_rows = cursor.fetchall()

    # Model answers save karo
    for index, row in enumerate(question_rows):

        model_answer = request.form.get(
            f"model_answer_{index}",
            ""
        ).strip()

        cursor.execute(
            """
            UPDATE questions
            SET model_answer = %s
            WHERE id = %s
            """,
            (model_answer, row[0])
        )

    # Question paper approve karo
    cursor.execute(
        """
        UPDATE question_papers
        SET status = 'Approved'
        WHERE id = %s
        """,
        (paper_id,)
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect("/question-papers")

@app.route("/answer-sheets", methods=["GET", "POST"])
def answer_sheets():

    upload_folder = "uploads"
    os.makedirs(upload_folder, exist_ok=True)

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    if request.method == "POST":

        student_name = request.form["student_name"]
        roll_no = request.form["roll_no"]
        subject = request.form["subject"]
        teacher_id = request.form["teacher_id"]

        file = request.files["answer_file"]

        filename = secure_filename(file.filename)
        file.save(os.path.join(upload_folder, filename))

        cursor.execute(
            """
            INSERT INTO answer_sheets
            (student_name, roll_no, subject, file_name, assigned_teacher_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (student_name, roll_no, subject, filename, teacher_id)
        )

        db.commit()

    cursor.execute("SELECT * FROM answer_sheets")
    sheet_list = cursor.fetchall()

    cursor.execute("SELECT * FROM teachers")
    teacher_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "answer_sheets.html",
        answer_sheets=sheet_list,
        teachers=teacher_list
    )

    return render_template(
        "answer_sheets.html",
        answer_sheets=sheet_list
    )



@app.route("/examiner-dashboard")
def examiner_dashboard():
    return render_template("examiner_dashboard.html")

@app.route("/completed-copies")
def completed_copies():

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            answer_sheets.id,
            answer_sheets.student_name,
            answer_sheets.roll_no,
            answer_sheets.subject,
            evaluations.total_marks
        FROM answer_sheets
        INNER JOIN evaluations
            ON evaluations.id = (
                SELECT MAX(e.id)
                FROM evaluations e
                WHERE e.answer_sheet_id = answer_sheets.id
            )
        WHERE answer_sheets.status = 'Completed'
        ORDER BY evaluations.id DESC
    """)

    completed = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "completed_copies.html",
        completed=completed
    )

@app.route("/view-evaluation/<int:copy_id>")
def view_evaluation(copy_id):

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            answer_sheets.student_name,
            answer_sheets.roll_no,
            answer_sheets.subject,
            evaluations.q1_marks,
            evaluations.q2_marks,
            evaluations.q3_marks,
            evaluations.total_marks,
            evaluations.question_marks
        FROM answer_sheets
        INNER JOIN evaluations
            ON evaluations.id = (
                SELECT MAX(e.id)
                FROM evaluations e
                WHERE e.answer_sheet_id = answer_sheets.id
            )
        WHERE answer_sheets.id = %s
    """, (copy_id,))

    evaluation = cursor.fetchone()

    import json

    question_marks = []

    if evaluation and evaluation[7]:
        question_marks = json.loads(evaluation[7])

    cursor.close()
    db.close()

    if not evaluation:
        return "Evaluation not found"

    return render_template(
        "view_evaluation.html",
        evaluation=evaluation,
        question_marks=question_marks
    )


@app.route("/assigned-copies")
def assigned_copies():

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            answer_sheets.id,
            answer_sheets.student_name,
            answer_sheets.roll_no,
            answer_sheets.subject,
            answer_sheets.file_name,
            answer_sheets.status
        FROM answer_sheets
        INNER JOIN examiner_users
        ON answer_sheets.assigned_teacher_id = examiner_users.teacher_id
        WHERE examiner_users.email = %s
    """, ("rahul@university.com",))

    copies = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "assigned_copies.html",
        copies=copies
    )


@app.route("/next-copy/<int:copy_id>")
def next_copy(copy_id):

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    # Check current copy status
    cursor.execute("""
        SELECT status, assigned_teacher_id
        FROM answer_sheets
        WHERE id = %s
    """, (copy_id,))

    current_copy = cursor.fetchone()

    if not current_copy:
        cursor.close()
        db.close()
        return "Answer sheet not found"

    # Next copy only after current copy is completed
    if current_copy[0] != "Completed":
        cursor.close()
        db.close()
        return "Please complete the current copy before opening the next copy."

    assigned_teacher_id = current_copy[1]

    # Find next assigned copy
    cursor.execute("""
        SELECT id
        FROM answer_sheets
        WHERE assigned_teacher_id = %s
          AND id > %s
        ORDER BY id ASC
        LIMIT 1
    """, (assigned_teacher_id, copy_id))

    next_copy_row = cursor.fetchone()

    cursor.close()
    db.close()

    if not next_copy_row:
        return "No next copy available."

    return redirect(f"/open-copy/{next_copy_row[0]}")

@app.route("/previous-copy/<int:copy_id>")
def previous_copy(copy_id):

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    # Current copy ki information
    cursor.execute("""
        SELECT assigned_teacher_id
        FROM answer_sheets
        WHERE id = %s
    """, (copy_id,))

    current_copy = cursor.fetchone()

    if not current_copy:
        cursor.close()
        db.close()
        return "Answer sheet not found"

    assigned_teacher_id = current_copy[0]

    # Previous assigned copy
    cursor.execute("""
        SELECT id
        FROM answer_sheets
        WHERE assigned_teacher_id = %s
          AND id < %s
        ORDER BY id DESC
        LIMIT 1
    """, (assigned_teacher_id, copy_id))

    previous_copy_row = cursor.fetchone()

    cursor.close()
    db.close()

    if not previous_copy_row:
        return "No previous copy available."

    return redirect(f"/open-copy/{previous_copy_row[0]}")

@app.route("/open-copy/<int:copy_id>")
def open_copy(copy_id):

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    # Answer sheet
    cursor.execute(
        "SELECT * FROM answer_sheets WHERE id=%s",
        (copy_id,)
    )

    copy = cursor.fetchone()

    if not copy:
        cursor.close()
        db.close()
        return "Answer sheet not found"

    # Questions for this subject
    cursor.execute(
        """
        SELECT id, question_text, max_marks, model_answer
        FROM questions
        WHERE subject=%s
        AND question_paper_id IS NOT NULL
        ORDER BY id
        """,
        (copy[3],)
    )

    questions = cursor.fetchall()
    total_max_marks = sum(question[2] for question in questions)

    print("QUESTIONS:", questions)
    print("TOTAL MAX:", total_max_marks)

    # Latest evaluation
    cursor.execute(
        """
        SELECT q1_marks, q2_marks, q3_marks,
               total_marks, question_marks
        FROM evaluations
        WHERE answer_sheet_id=%s
        ORDER BY id DESC
        LIMIT 1
        """,
        (copy_id,)
    )

    evaluation = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "open_copy.html",
        copy=copy,
        questions=questions,
        evaluation=evaluation,
        total_max_marks=total_max_marks
    )

@app.route("/save-evaluation/<int:copy_id>", methods=["POST"])
def save_evaluation(copy_id):

    # Get all approved questions for this answer sheet
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    cursor.execute(
        """
        SELECT questions.max_marks
        FROM answer_sheets
        INNER JOIN questions
            ON answer_sheets.subject = questions.subject
        INNER JOIN question_papers
            ON questions.question_paper_id = question_papers.id
        WHERE answer_sheets.id = %s
          AND question_papers.status = 'Approved'
        ORDER BY questions.id
        """,
        (copy_id,)
    )

    question_limits = cursor.fetchall()

    marks = []

    for i, question in enumerate(question_limits, start=1):

        field_name = f"q{i}_marks"

        value = int(request.form.get(field_name, 0) or 0)

        max_marks = question[0]

        if value < 0:
            value = 0

        if value > max_marks:
            value = max_marks

        marks.append(value)

    total_marks = sum(marks)

    # Keep old columns working for compatibility
    q1_marks = marks[0] if len(marks) > 0 else 0
    q2_marks = marks[1] if len(marks) > 1 else 0
    q3_marks = marks[2] if len(marks) > 2 else 0

    import json

    question_marks = json.dumps(marks)

    cursor.execute(
        """
        INSERT INTO evaluations
        (answer_sheet_id, q1_marks, q2_marks, q3_marks,
         total_marks, question_marks)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            copy_id,
            q1_marks,
            q2_marks,
            q3_marks,
            total_marks,
            question_marks
        )
    )

    db.commit()

    cursor.execute(
        """
        UPDATE answer_sheets
        SET status = 'Evaluated'
        WHERE id = %s
        """,
        (copy_id,)
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect(f"/open-copy/{copy_id}")


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory("uploads", filename)

@app.route("/analyze-ai/<int:copy_id>")
def analyze_ai(copy_id):

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    cursor.execute(
        """
        SELECT file_name
        FROM answer_sheets
        WHERE id=%s
        """,
        (copy_id,)
    )

    result = cursor.fetchone()
    # Questions fetch karo
    cursor.execute(
        """
        SELECT id, question_text, max_marks, model_answer
        FROM questions
        WHERE subject = (
            SELECT subject
            FROM answer_sheets
            WHERE id = %s
        )
        AND question_paper_id IS NOT NULL
        ORDER BY id
        """,
        (copy_id,)
    )

    questions = cursor.fetchall()

    cursor.close()
    db.close()

    if not result:
        return "Answer sheet not found"

    filename = result[0]

    file_path = os.path.join(
        "uploads",
        filename
    )

    if not os.path.exists(file_path):
        return f"Answer sheet file not found: {filename}"

    # PDF open karo
    pdf = pdfium.PdfDocument(file_path)

    all_text = ""

    # Har page ka OCR
    for page_number in range(len(pdf)):

        page = pdf[page_number]

        image = page.render(scale=2).to_pil()

        text = pytesseract.image_to_string(image)

        all_text += f"\n--- Page {page_number + 1} ---\n"
        all_text += text

    # OCR text ko questions ke according divide karne ki koshish
    student_answers = []

    for i, question in enumerate(questions):
        student_answers.append({
            "question_number": i + 1,
            "answer": all_text
        })
    # Student answers list
    student_answers = []

    for i, question in enumerate(questions):
        student_answers.append({
            "question_number": i + 1,
            "answer": all_text
        })
        
    return render_template(
    "ai_analysis.html",
    copy_id=copy_id,
    filename=filename,
    ocr_text=all_text,
    questions=questions,
    student_answers=student_answers
)

@app.route("/finalize-evaluation/<int:copy_id>", methods=["POST"])
def finalize_evaluation(copy_id):
    print("FINALIZE ROUTE HIT:", copy_id)

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MP6111",
        database="ai_exam_system"
    )

    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE answer_sheets
        SET status = 'Completed'
        WHERE id = %s
        """,
        (copy_id,)
    )

    print("FINALIZE COPY ID:", copy_id)
    print("UPDATED ROWS:", cursor.rowcount)

    db.commit()

    cursor.close()
    db.close()

    return redirect("/completed-copies")

if __name__ == "__main__":
    app.run(debug=True)