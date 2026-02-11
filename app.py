import random
import time
from flask import Flask, render_template_string, request, redirect, url_for, session
import os

app = Flask(__name__)
app.secret_key = "super_secret_key"

QUESTIONS_FILE = "french_placement_1000_questions.txt"

# Load questions
def load_questions():
    questions = []
    if not os.path.exists(QUESTIONS_FILE):
        return questions

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        blocks = f.read().split("Level:")
        for block in blocks:
            if block.strip() == "":
                continue
            block = "Level:" + block
            lines = block.strip().split("\n")
            level = lines[0].replace("Level:", "").strip()
            qtype = lines[1].replace("Type:", "").strip()
            question_line = lines[2].replace("Question:", "").strip()
            
            options = []
            answer = ""

            for line in lines:
                if line.startswith(("A)", "B)", "C)", "D)")):
                    options.append(line.strip())
                if line.startswith("Answer:"):
                    answer = line.replace("Answer:", "").strip()

            questions.append({
                "level": level,
                "type": qtype,
                "question": question_line,
                "options": options,
                "answer": answer
            })
    return questions


ALL_QUESTIONS = load_questions()

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
let totalTime = 5400;

function startTimers() {
    setInterval(function() {
        questionTime--;
        totalTime--;
        document.getElementById("question_timer").innerHTML = "Question Time: " + questionTime + " sec";
        document.getElementById("total_timer").innerHTML = "Total Time: " + totalTime + " sec";

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
                <input type="radio" name="answer" value="{{ option[0] }}" required> {{ option }}
            </div>
        {% endfor %}
    {% else %}
        <div class="option">
            <input type="radio" name="answer" value="Vrai" required> Vrai
        </div>
        <div class="option">
            <input type="radio" name="answer" value="Faux" required> Faux
        </div>
    {% endif %}

    <button type="submit">Next</button>
</form>

<p>Question {{ current + 1 }} / 40</p>

</div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_answer = request.form.get("answer")
        current = session.get("current", 0)
        score = session.get("score", 0)

        correct_answer = session["selected_questions"][current]["answer"]

        if user_answer == correct_answer:
            score += 1

        session["score"] = score
        session["current"] = current + 1

        if session["current"] >= 40:
            return redirect(url_for("result"))

    if "selected_questions" not in session:
        session["selected_questions"] = random.sample(ALL_QUESTIONS, 40)
        session["current"] = 0
        session["score"] = 0

    current = session["current"]

    if current >= 40:
        return redirect(url_for("result"))

    question = session["selected_questions"][current]

    return render_template_string(
        HTML_TEMPLATE,
        question=question,
        current=current
    )


@app.route("/result")
def result():
    score = session.get("score", 0)
    return f"""
    <h2 style='background-color:#ff6b6b;color:white;padding:20px;text-align:center;'>
    Test Finished<br><br>
    Your Score: {score} / 40
    </h2>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
