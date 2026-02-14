import random
import time
import os
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

QUESTIONS_FILE = os.path.join(os.path.dirname(__file__), "french_placement_1000_questions.txt")


# ---------------------------------------------------
# SAFE QUESTION LOADER (CRASH-PROOF)
# ---------------------------------------------------

def load_questions():
    questions = []

    if not os.path.exists(QUESTIONS_FILE):
        print("ERROR: Questions file not found.")
        return questions

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    for line in lines:
        q = {}

        # Extract Level
        if "Level:" in line:
            try:
                level_part = line.split("Level:")[1].split("Type:")[0].strip()
                q["level"] = level_part
            except:
                continue

        # Extract Type
        if "Type:" in line:
            try:
                type_part = line.split("Type:")[1].split("Question:")[0].strip()
                q["type"] = type_part
            except:
                continue

        # Extract Question
        if "Question:" in line:
            try:
                question_part = line.split("Question:")[1].split("A)")[0].strip()
                q["question"] = question_part
            except:
                continue

        # Extract Options (A) ... D))
        options = []
        for opt in ["A)", "B)", "C)", "D)"]:
            if f"{opt} " in line:
                part = line.split(f"{opt} ")[1]
                # For next option, split by next option letter
                for next_opt in ["A)", "B)", "C)", "D)"]:
                    if next_opt != opt and f"{next_opt} " in part:
                        part = part.split(f"{next_opt} ")[0].strip()
                options.append(f"{opt} {part.strip()}")
        q["options"] = options

        # Extract Answer
        if "Answer:" in line:
            answer_part = line.split("Answer:")[1].strip()
            q["answer"] = answer_part

        # Only append if question, type, answer exist
        if "question" in q and "type" in q and "answer" in q:
            questions.append(q)

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

            # MCQ answers: compare first letter
            if session["selected_questions"][current]["type"] == "MCQ":
                user_answer = user_answer.upper().strip()
                correct_answer = correct_answer[0].upper().strip()

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

    session.clear()  # <-- Clear session after finishing test

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
