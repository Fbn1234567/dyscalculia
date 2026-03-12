from flask import Flask, render_template, request, redirect, session
from flask_bcrypt import Bcrypt
import random
import pickle
import numpy as np
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY","supersecretkey")

bcrypt = Bcrypt(app)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# -----------------------------
# LOAD MODEL
# -----------------------------
model = pickle.load(open("model.pkl","rb"))
label_encoder = pickle.load(open("label_encoder.pkl","rb"))


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login",methods=["GET","POST"])
def login():

    if request.method=="POST":

        email=request.form["email"]
        password=request.form["password"]

        conn=get_db_connection()
        cur=conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT * FROM users WHERE email=%s",(email,))
        user=cur.fetchone()

        cur.close()
        conn.close()

        if user and bcrypt.check_password_hash(user["password"],password):

            session["user"]=user["email"]
            session["role"]=user["role"]

            return redirect("/dashboard")

        return render_template("login.html",error="Invalid credentials")

    return render_template("login.html")


# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    role=session["role"]

    if role=="Student":
        return render_template("student_dashboard.html",user=session["user"])

    if role=="Teacher":
        return render_template("teacher_dashboard.html",user=session["user"])

    if role=="Parent":
        return render_template("parent_dashboard.html",user=session["user"])

    if role=="Admin":
        return render_template("admin_dashboard.html",user=session["user"])


# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# -----------------------------
# START TEST
# -----------------------------
@app.route("/start_cognitive")
def start_cognitive():
    return redirect("/symbolic_test")


# =====================================================
# SYMBOLIC NUMBER COMPARISON TEST
# =====================================================

@app.route("/symbolic_test")
def symbolic_test():

    session["symbolic_data"]=[]
    session["symbolic_trial"]=0

    return redirect("/symbolic_trial")


@app.route("/symbolic_trial")
def symbolic_trial():

    trial=session.get("symbolic_trial",0)

    if trial>=10:
        return redirect("/finish_symbolic")

    left=random.randint(1,50)
    right=random.randint(1,50)

    while left==right:
        right=random.randint(1,50)

    session["left"]=left
    session["right"]=right

    return render_template(
        "symbolic_test.html",
        left=left,
        right=right,
        trial=trial+1
    )


@app.route("/submit_symbolic",methods=["POST"])
def submit_symbolic():

    choice=request.form["choice"]
    rt=float(request.form["response_time"])

    left=session["left"]
    right=session["right"]

    correct="left" if left>right else "right"
    correct_val=1 if choice==correct else 0

    session["symbolic_data"].append({"correct":correct_val,"rt":rt})
    session["symbolic_trial"]+=1

    return redirect("/symbolic_trial")


@app.route("/finish_symbolic")
def finish_symbolic():

    trials=session["symbolic_data"]

    accuracy=sum(t["correct"] for t in trials)/len(trials)
    mean_rt=sum(t["rt"] for t in trials)/len(trials)

    session["Accuracy_SymbolicComp"]=accuracy
    session["RTs_SymbolicComp"]=mean_rt

    return redirect("/ans_test")


# =====================================================
# ANS DOT COMPARISON TEST
# =====================================================

@app.route("/ans_test")
def ans_test():

    session["ans_data"]=[]
    session["ans_trial"]=0

    return redirect("/ans_trial")


@app.route("/ans_trial")
def ans_trial():

    trial=session["ans_trial"]

    if trial>=10:
        return redirect("/finish_ans")

    left=random.randint(5,20)
    right=random.randint(5,20)

    while left==right:
        right=random.randint(5,20)

    session["ans_left"]=left
    session["ans_right"]=right

    return render_template(
        "ans_test.html",
        left=left,
        right=right,
        trial=trial+1
    )


@app.route("/submit_ans",methods=["POST"])
def submit_ans():

    choice=request.form["choice"]
    rt=float(request.form["response_time"])

    left=session["ans_left"]
    right=session["ans_right"]

    correct="left" if left>right else "right"
    correct_val=1 if choice==correct else 0

    session["ans_data"].append({"correct":correct_val,"rt":rt})
    session["ans_trial"]+=1

    return redirect("/ans_trial")


@app.route("/finish_ans")
def finish_ans():

    trials=session["ans_data"]

    accuracy=sum(t["correct"] for t in trials)/len(trials)
    mean_rt=sum(t["rt"] for t in trials)/len(trials)

    session["Mean_ACC_ANS"]=accuracy
    session["Mean_RTs_ANS"]=mean_rt

    return redirect("/fraction_test")


# =====================================================
# FRACTION TEST
# =====================================================

@app.route("/fraction_test")
def fraction_test():

    session["fraction_data"]=[]
    session["fraction_trial"]=0

    return redirect("/fraction_trial")


@app.route("/fraction_trial")
def fraction_trial():

    trial=session["fraction_trial"]

    if trial>=10:
        return redirect("/finish_fraction")

    a=random.randint(1,9)
    b=random.randint(2,10)

    c=random.randint(1,9)
    d=random.randint(2,10)

    session["frac_left"]=(a,b)
    session["frac_right"]=(c,d)

    return render_template(
        "fraction_test.html",
        left=f"{a}/{b}",
        right=f"{c}/{d}",
        trial=trial+1
    )


@app.route("/submit_fraction",methods=["POST"])
def submit_fraction():

    choice=request.form["choice"]
    rt=float(request.form["response_time"])

    a,b=session["frac_left"]
    c,d=session["frac_right"]

    correct="left" if (a/b)>(c/d) else "right"
    correct_val=1 if choice==correct else 0

    session["fraction_data"].append({"correct":correct_val,"rt":rt})
    session["fraction_trial"]+=1

    return redirect("/fraction_trial")


@app.route("/finish_fraction")
def finish_fraction():

    trials=session["fraction_data"]

    accuracy=sum(t["correct"] for t in trials)/len(trials)

    session["Fraction_ACC"]=accuracy

    return redirect("/wm_test")


# =====================================================
# WORKING MEMORY TEST
# =====================================================

@app.route("/wm_test")
def wm_test():

    session["wm_level"]=3
    session["wm_data"]=[]

    return redirect("/wm_trial")


@app.route("/wm_trial")
def wm_trial():

    level=session["wm_level"]

    sequence=[str(random.randint(1,9)) for _ in range(level)]
    session["sequence"]=sequence

    return render_template(
        "wm_test.html",
        sequence=" ".join(sequence)
    )


@app.route("/submit_wm",methods=["POST"])
def submit_wm():

    answer=request.form["answer"].replace(" ","")
    correct_seq="".join(session["sequence"])

    correct=1 if answer==correct_seq else 0

    session["wm_data"].append({"level":session["wm_level"],"correct":correct})

    if correct:
        session["wm_level"]+=1
        return redirect("/wm_trial")

    return redirect("/finish_wm")


@app.route("/finish_wm")
def finish_wm():

    data=session["wm_data"]
    scores=[d["level"] for d in data if d["correct"]==1]

    session["wm_K"]=max(scores) if scores else 0

    return redirect("/final_prediction")


# =====================================================
# FINAL ML PREDICTION
# =====================================================

@app.route("/final_prediction")
def final_prediction():

    features=np.array([[

        session["Mean_ACC_ANS"],
        session["Mean_RTs_ANS"],
        session["wm_K"],
        session["Accuracy_SymbolicComp"],
        session["RTs_SymbolicComp"]

    ]])

    prediction=model.predict(features)

    label=label_encoder.inverse_transform(prediction)[0].lower()

    if label in ["dd","severe","high"]:
        risk="Highest Risk"
        rec="Immediate professional evaluation recommended."

    elif label in ["moderate","medium"]:
        risk="Medium Risk"
        rec="Provide additional math practice and monitoring."

    elif label in ["mild","low"]:
        risk="Lowest Risk"
        rec="Provide reinforcement activities."

    else:
        risk="No Dyscalculia Detected"
        rec="Continue normal learning."

    return render_template(
        "final_result.html",
        risk=risk,
        recommendations=rec
    )


if __name__=="__main__":
    app.run(debug=True)