import random
import time
import os
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

QUESTIONS_FILE = "french_placement_1000_questions.txt"

# ---------------------------------------------------
# SAFE QUESTION LOADER (CRASH-PROOF)
# ---------------------------------------------------

def load_questions():
    questions = []

    if not os.path.exists(QUESTIONS_FILE):
        print("ERROR: Questions file not found.")
        return questions

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.split("Level:")

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = [line.strip() for line in block.split("\n") if line.strip()]

        level = None
        qtype = None
        question_line = None
        options = []
        answer = None

        for line in lines:
            if line.startswith("Level:"):
                level = line.replace("Level:", "").strip()
            elif line.startswith("Type:"):
                qtype = line.replace("Type:", "").strip()
            elif line.startswith("Question:"):
                question_line = line.replace("Question:", "").strip()
            elif line.startswith(("A)", "B)", "C)", "D)")):
                options.append(line)
            elif line.startswith("Answer:"):
                answer = line.replace("Answer:", "").strip()

        # Only append valid questions
        if level and qtype and question_line and answer:
            questions.append({
                "level": level,
                "type": qtype,
                "question": question_line,
                "options": options,
                "answer": answer
            })

    print("TOTAL VALID QUESTIONS LOADED:", len(questions))
    return questions


ALL_QUESTIONS = load_questions()

# ---------------------------------------------------
# HTML TEMPLATE
# ---------------------------------------------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<title>French Placement Test</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {
    background-color: #ff6b6b;
    color: white;
    font-family: Arial, sans-serif;
    text-align: center;
    margin: 0;
    padding: 20px;
}
.container {
    max-width: 800px;
    margin: auto;
}
button {
    padding: 10px 20px;
    font-size: 16px;
    margin-top: 20px;
    cursor: pointer;
}
.option {
    margin: 10px;
}
.timer {
    font-size: 18px;
    margin-bottom: 10px;
}
</style>

<script>
let questionTime = 120;
let totalTime = {{ total_time }};

function startTimers() {
    setInterval(function() {
        questionTime--;
        totalTime--;

        document.getElementById("question_timer").innerHTML =
            "Question Time: " + questionTime + " sec";

        document.getElementById("total_timer").innerHTML =
            "Total Time: " + totalTime + " sec";

        if (questionTime <= 0) {
            document.getElementById("quizForm").submit();
        }

        if (totalTime <= 0) {
            window.location.href = "/result";
        }
    }, 1000);
}
</script>
</head>

<body onload="startTimers()">
<div class="container">

<h2>French Placement Test</h2>

<div class="timer" id="question_timer"></div>
<div class="timer" id="total_timer"></div>

<h3>{{ question['question'] }}</h3>

<form method="POST" id="quizForm">
    {% if question['type'] == 'MCQ' %}
        {% for option in question['options'] %}
            <div class="option">
                <input type="radio" name="answer" value="{{ option[0] }}">
                {{ option }}
            </div>
        {% endfor %}
    {% else %}
        <div class="option">
            <input type="radio" name="answer" value="Vrai"> Vrai
        </div>
        <div class="option">
            <input type="radio" name="answer" value="Faux"> Faux
        </div>
    {% endif %}

    <button type="submit">Next</button>
</form>

<p>Question {{ current + 1 }} / {{ total_questions }}</p>

</div>
</body>
</html>
"""

# ---------------------------------------------------
# MAIN ROUTE
# ---------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():

    if not ALL_QUESTIONS:
        return "No valid questions available. Check your file formatting."

    # Initialize session
    if "start_time" not in session:
        session["start_time"] = time.time()
        session["current"] = 0
        session["score"] = 0

        total_available = len(ALL_QUESTIONS)

        if total_available < 1:
            return "No questions available."

        number_to_select = min(40, total_available)

        session["selected_questions"] = random.sample(
            ALL_QUESTIONS,
            number_to_select
        )

    # Total 90-minute timer (server-side enforced)
    elapsed = time.time() - session["start_time"]
    if elapsed >= 5400:
        return redirect(url_for("result"))

    if request.method == "POST":
        current = session["current"]

        if current < len(session["selected_questions"]):
            user_answer = request.form.get("answer")
            correct_answer = session["selected_questions"][current]["answer"]

            if user_answer == correct_answer:
                session["score"] += 1

            session["current"] += 1

        if session["current"] >= len(session["selected_questions"]):
            return redirect(url_for("result"))

    current = session["current"]

    if current >= len(session["selected_questions"]):
        return redirect(url_for("result"))

    question = session["selected_questions"][current]

    remaining_total = int(5400 - (time.time() - session["start_time"]))

    return render_template_string(
        HTML_TEMPLATE,
        question=question,
        current=current,
        total_time=remaining_total,
        total_questions=len(session["selected_questions"])
    )

# ---------------------------------------------------
# RESULT ROUTE
# ---------------------------------------------------

@app.route("/result")
def result():
    score = session.get("score", 0)
    total = len(session.get("selected_questions", []))

    return f"""
    <h2 style='background-color:#ff6b6b;color:white;padding:30px;text-align:center;'>
    Test Finished<br><br>
    Score: {score} / {total}
    </h2>
    """

# ---------------------------------------------------
# RUN (Fly.io compatible)
# ---------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
