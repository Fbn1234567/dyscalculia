from flask import Flask, render_template, request, redirect, url_for, session
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL
import random
import pickle
import numpy as np
import os
import MySQLdb

app = Flask(__name__)
app.secret_key = "supersecretkey"

bcrypt = Bcrypt(app)

# -----------------------------
# MYSQL CONFIG
# -----------------------------

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'dyscalculia_db'

mysql = MySQL(app)

# -----------------------------
# LOAD ML MODEL
# -----------------------------

model = None
label_encoder = None
if os.path.exists("model.pkl") and os.path.exists("label_encoder.pkl"):
    try:
        model = pickle.load(open("model.pkl", "rb"))
        label_encoder = pickle.load(open("label_encoder.pkl", "rb"))
    except Exception as e:
        print(f"Warning: Failed to load models: {e}")
else:
    print("Warning: Model files not found. Please train the model first.")

# -----------------------------
# HOME
# -----------------------------

@app.route('/')
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

# -----------------------------
# REGISTER
# -----------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():

    cur = mysql.connection.cursor()

    # Get teachers
    cur.execute("SELECT id, email FROM users WHERE role='Teacher'")
    teachers = cur.fetchall()

    # Get parents
    cur.execute("SELECT id, email FROM users WHERE role='Parent'")
    parents = cur.fetchall()

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        teacher_id = request.form.get("teacher_id")
        parent_id = request.form.get("parent_id")

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        try:
            if role == "Student":
                cur.execute("""
                INSERT INTO users (email, password, role, teacher_id, parent_id)
                VALUES (%s,%s,%s,%s,%s)
                """,(email, hashed_pw, role, teacher_id, parent_id))
            else:
                cur.execute("""
                INSERT INTO users (email, password, role)
                VALUES (%s,%s,%s)
                """,(email, hashed_pw, role))

            mysql.connection.commit()
            return redirect(url_for("login"))
        except MySQLdb.IntegrityError:
            return render_template("register.html", teachers=teachers, parents=parents, error="Email already registered.")
        except Exception as e:
            return render_template("register.html", teachers=teachers, parents=parents, error=f"An error occurred: {str(e)}")

    return render_template("register.html", teachers=teachers, parents=parents)
# -----------------------------
# LOGIN
# -----------------------------

@app.route('/login', methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT password,role FROM users WHERE email=%s",(email,))
            user = cur.fetchone()
            cur.close()
        except Exception as e:
            return render_template("login.html", error=f"Database error: {str(e)}")

        if user and bcrypt.check_password_hash(user[0],password):

            session["user"] = email
            session["role"] = user[1]

            return redirect(url_for("dashboard"))

        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

# -----------------------------
# DASHBOARD
# -----------------------------

@app.route('/dashboard')
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    role = session["role"]

    if role == "Student":
        return render_template("student_dashboard.html",user=session["user"])

    if role == "Teacher":
        return render_template("teacher_dashboard.html")

    if role == "Parent":
        return render_template("parent_dashboard.html")

    if role == "Admin":
        return render_template("admin_dashboard.html")

# -----------------------------
# LOGOUT
# -----------------------------

@app.route('/logout')
def logout():

    session.clear()
    return redirect(url_for("login"))

# =========================================================
# SYMBOLIC COMPARISON TEST
# =========================================================

@app.route('/symbolic_test')
def symbolic_test():

    session["symbolic_data"] = []
    session["symbolic_trial"] = 0

    return redirect('/symbolic_trial')


@app.route('/symbolic_trial')
def symbolic_trial():

    if "symbolic_trial" not in session:
        return redirect('/start_cognitive')

    trial = session["symbolic_trial"]

    if trial >= 10:
        return redirect('/finish_symbolic')

    left = random.randint(1,50)
    right = random.randint(1,50)

    while left == right:
        right = random.randint(1,50)

    session["left"] = left
    session["right"] = right

    return render_template("symbolic_test.html",
                           left=left,
                           right=right,
                           trial=trial+1)


@app.route('/submit_symbolic',methods=["POST"])
def submit_symbolic():

    choice = request.form.get("choice")
    try:
        rt = float(request.form.get("response_time", 0))
    except ValueError:
        rt = 0.0

    left = session.get("left", 0)
    right = session.get("right", 0)

    correct_side = "left" if left > right else "right"
    correct = 1 if choice == correct_side else 0

    session["symbolic_data"].append({
        "correct":correct,
        "rt":rt
    })

    session["symbolic_trial"] += 1

    return redirect('/symbolic_trial')


@app.route('/finish_symbolic')
def finish_symbolic():

    if "symbolic_data" not in session or len(session["symbolic_data"]) == 0:
        return redirect('/start_cognitive')

    trials = session["symbolic_data"]

    accuracy = sum(t["correct"] for t in trials)/len(trials)
    mean_rt = sum(t["rt"] for t in trials)/len(trials)

    session["Accuracy_SymbolicComp"] = accuracy
    session["RTs_SymbolicComp"] = mean_rt

    return redirect('/ans_test')

# =========================================================
# ANS TEST
# =========================================================

@app.route('/ans_test')
def ans_test():

    session["ans_data"] = []
    session["ans_trial"] = 0

    return redirect('/ans_trial')


@app.route('/ans_trial')
def ans_trial():

    if "ans_trial" not in session:
        return redirect('/start_cognitive')

    trial = session["ans_trial"]

    if trial >= 10:
        return redirect('/finish_ans')

    left = random.randint(5,20)
    right = random.randint(5,20)

    while left == right:
        right = random.randint(5,20)

    session["ans_left"] = left
    session["ans_right"] = right

    return render_template("ans_test.html",
                           left=left,
                           right=right,
                           trial=trial+1)


@app.route('/submit_ans',methods=["POST"])
def submit_ans():

    choice = request.form.get("choice")
    try:
        rt = float(request.form.get("response_time", 0))
    except (ValueError, TypeError):
        rt = 0.0

    left = session.get("ans_left", 0)
    right = session.get("ans_right", 0)

    correct_side = "left" if left > right else "right"
    correct = 1 if choice == correct_side else 0

    session["ans_data"].append({
        "correct":correct,
        "rt":rt
    })

    session["ans_trial"] += 1

    return redirect('/ans_trial')


@app.route('/finish_ans')
def finish_ans():

    if "ans_data" not in session or len(session["ans_data"]) == 0:
        return redirect('/start_cognitive')

    trials = session["ans_data"]

    accuracy = sum(t["correct"] for t in trials)/len(trials)
    mean_rt = sum(t["rt"] for t in trials)/len(trials)

    session["Mean_ACC_ANS"] = accuracy
    session["Mean_RTs_ANS"] = mean_rt

    return redirect('/wm_test')

# =========================================================
# WORKING MEMORY TEST
# =========================================================

@app.route('/wm_test')
def wm_test():

    session["wm_level"] = 3
    session["wm_data"] = []

    return redirect('/wm_trial')


@app.route('/wm_trial')
def wm_trial():

    if "wm_level" not in session:
        return redirect('/start_cognitive')

    level = session["wm_level"]

    sequence = [str(random.randint(1,9)) for _ in range(level)]

    session["sequence"] = sequence

    return render_template("wm_test.html",
                           sequence=" ".join(sequence),
                           level=level)


@app.route('/submit_wm',methods=["POST"])
def submit_wm():

    answer = request.form.get("answer", "").replace(" ","")
    correct_sequence = "".join(session.get("sequence", []))

    if not correct_sequence:
        return redirect('/start_cognitive')

    correct = 1 if answer == correct_sequence else 0

    session["wm_data"].append({
        "level":session["wm_level"],
        "correct":correct
    })

    if correct:
        session["wm_level"] += 1
    else:
        return redirect('/finish_wm')

    return redirect('/wm_trial')


@app.route('/finish_wm')
def finish_wm():

    data = session["wm_data"]

    scores = [d["level"] for d in data if d["correct"]==1]

    wm_K = max(scores) if scores else 0

    session["wm_K"] = wm_K

    return redirect('/final_prediction')

# =========================================================
# FINAL ML PREDICTION
# =========================================================

@app.route('/final_prediction')
def final_prediction():

    required_keys = ["Mean_ACC_ANS", "Mean_RTs_ANS", "wm_K", "Accuracy_SymbolicComp", "RTs_SymbolicComp"]
    if any(k not in session for k in required_keys):
        return redirect('/start_cognitive')

    Mean_ACC_ANS = session["Mean_ACC_ANS"]
    Mean_RTs_ANS = session["Mean_RTs_ANS"]
    wm_K = session["wm_K"]
    Accuracy_SymbolicComp = session["Accuracy_SymbolicComp"]
    RTs_SymbolicComp = session["RTs_SymbolicComp"]

    if model is None or label_encoder is None:
        return "Internal Error: ML Model not found. Cannot generate prediction."

    features = np.array([[ 
        Mean_ACC_ANS,
        Mean_RTs_ANS,
        wm_K,
        Accuracy_SymbolicComp,
        RTs_SymbolicComp
    ]])

    prediction = model.predict(features)
    risk = label_encoder.inverse_transform(prediction)[0]

    # Better readable labels
    risk_labels = {
        "DD": "High Risk of Dyscalculia",
        "Medium": "Moderate Risk of Dyscalculia",
        "contr": "No Dyscalculia Risk"
    }

    display_risk = risk_labels.get(risk, risk)

    # Recommendation System
    if risk == "DD":

        recommendations = """
• High risk detected.
• Consult a learning specialist or psychologist.
• Use visual math tools and number line exercises.
• Practice symbolic comparison games.
• Improve working memory training.
"""

    elif risk == "Medium":

        recommendations = """
• Moderate difficulty detected.
• Practice arithmetic exercises regularly.
• Use number comparison activities.
• Improve working memory through memory games.
• Teacher supervision recommended.
"""

    elif risk == "contr":

        recommendations = """
• No dyscalculia risk detected.
• Continue normal learning activities.
• Encourage logical problem solving.
• Maintain regular math practice.
"""

    else:
        recommendations = "Continue practicing mathematical skills."

    # Save to database
    try:
        cur = mysql.connection.cursor()

        cur.execute("""
            INSERT INTO cognitive_results 
            (student_email, Mean_ACC_ANS, Mean_RTs_ANS, wm_K,
             Accuracy_SymbolicComp, RTs_SymbolicComp, risk_level)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,(
            session["user"],
            Mean_ACC_ANS,
            Mean_RTs_ANS,
            wm_K,
            Accuracy_SymbolicComp,
            RTs_SymbolicComp,
            display_risk
        ))

        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"Warning: Failed to save results to database: {e}")

    return render_template(
        "final_result.html",
        risk=display_risk,
        recommendations=recommendations
    )

@app.route('/start_cognitive')
def start_cognitive():

    if "user" not in session or session["role"] != "Student":
        return "Access Denied"

    # reset all test data
    session["symbolic_data"] = []
    session["ans_data"] = []
    session["wm_data"] = []

    session["symbolic_trial"] = 0
    session["ans_trial"] = 0
    session["wm_level"] = 3

    return redirect('/symbolic_test')

@app.route('/history')
def history():

    if "user" not in session:
        return redirect('/login')

    try:
        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT Mean_ACC_ANS, Mean_RTs_ANS, wm_K,
                   Accuracy_SymbolicComp, RTs_SymbolicComp,
                   risk_level, test_date
            FROM cognitive_results
            WHERE student_email = %s
            ORDER BY test_date DESC
        """, (session["user"],))

        results = cur.fetchall()
        cur.close()
    except Exception as e:
        results = []
        print(f"Database error in history: {e}")

    return render_template("history.html", results=results)



@app.route('/teacher_results')
def teacher_results():

    try:
        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT student_email, risk_level
            FROM cognitive_results
        """)

        results = cur.fetchall()
        cur.close()
    except Exception as e:
        results = []
        print(f"Database error in teacher_results: {e}")

    return render_template("teacher_results.html", results=results)
# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)