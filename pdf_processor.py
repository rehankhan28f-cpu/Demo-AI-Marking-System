import re
from pypdf import PdfReader


def extract_questions_from_pdf(pdf_path):
    """
    Extract questions from a PDF.

    Supports formats like:
        Q1. What is photosynthesis? [2]
        Q2(a). Explain the process. [5 Marks]
        Q2(b) Explain respiration. (3 marks)
        Q3. Define osmosis. [2M]

    Also supports questions spanning multiple lines.
    """

    # ---------------------------------------------------------
    # 1. Read the PDF
    # ---------------------------------------------------------

    reader = PdfReader(pdf_path)

    full_text = ""

    for page_number, page in enumerate(reader.pages, start=1):

        text = page.extract_text()

        if text:
            full_text += text + "\n"

    # ---------------------------------------------------------
    # 2. Clean the extracted text
    # ---------------------------------------------------------

    # Convert different types of spaces into normal spaces
    full_text = full_text.replace("\xa0", " ")

    # Remove excessive spaces
    full_text = re.sub(r"[ \t]+", " ", full_text)

    # ---------------------------------------------------------
    # 3. Regex pattern
    # ---------------------------------------------------------

    pattern = re.compile(
        r"""
        (?P<question>
            Q\s*
            (?P<number>\d+)
            \s*
            (?:\(\s*(?P<subpart>[a-zA-Z])\s*\))?
            \s*
            [\.\:\)]?
        )
        \s*

        (?P<text>.*?)

        \s*
        (?:
            \[
                \s*
                (?P<marks1>\d+)
                \s*
                (?:marks?|m)?
                \s*
            \]
            |
            \(
                \s*
                (?P<marks2>\d+)
                \s*
                marks?
                \s*
            \)
        )

        """,
        re.IGNORECASE | re.DOTALL | re.VERBOSE
    )

    # ---------------------------------------------------------
    # 4. Find all questions
    # ---------------------------------------------------------

    matches = pattern.finditer(full_text)

    questions = []

    for match in matches:

        question_number = int(match.group("number"))

        subpart = match.group("subpart")

        question_text = match.group("text")

        # Marks can come from either [5] or (5 marks)
        marks = match.group("marks1") or match.group("marks2")

        # -----------------------------------------------------
        # 5. Clean question text
        # -----------------------------------------------------

        question_text = clean_question_text(question_text)

        # -----------------------------------------------------
        # 6. Create question ID
        # -----------------------------------------------------

        if subpart:
            question_id = f"Q{question_number}({subpart.lower()})"
        else:
            question_id = f"Q{question_number}"

        # -----------------------------------------------------
        # 7. Store question
        # -----------------------------------------------------

        questions.append({
            "question_id": question_id,
            "question_number": question_number,
            "subpart": subpart.lower() if subpart else None,
            "question_text": question_text,
            "max_marks": int(marks)
        })

    return questions


def clean_question_text(text):
    """
    Clean question text extracted from PDF.
    """

    # Replace line breaks with spaces
    text = re.sub(r"\s+", " ", text)

    # Remove spaces before punctuation
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)

    # Remove unnecessary spaces
    text = text.strip()

    return text


# -------------------------------------------------------------
# Main program
# -------------------------------------------------------------

if __name__ == "__main__":

    pdf_path = "uploads/question_papers/PCB_New_Doc_09-20-2026_16.38.pdf"

    questions = extract_questions_from_pdf(pdf_path)

    for question in questions:
        print(question)