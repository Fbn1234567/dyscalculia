from flask import Flask, render_template, request, redirect, url_for, session
from flask_bcrypt import Bcrypt
import random
import pickle
import numpy as np
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

bcrypt = Bcrypt(app)

DATABASE_URL = os.getenv("DATABASE_URL")


# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# -----------------------------
# LOAD ML MODEL
# -----------------------------
model = None
label_encoder = None

try:
    with open("model.pkl","rb") as f:
        model = pickle.load(f)

    with open("label_encoder.pkl","rb") as f:
        label_encoder = pickle.load(f)

except Exception as e:
    print("Model loading error:",e)


# -----------------------------
# HOME
# -----------------------------
@app.route('/')
def home():

    if "user" in session:
        return redirect("/dashboard")

    return redirect("/login")


# -----------------------------
# REGISTER
# -----------------------------
@app.route('/register',methods=["GET","POST"])
def register():

    conn=get_db_connection()
    cur=conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT id,email FROM users WHERE role='Teacher'")
    teachers=cur.fetchall()

    cur.execute("SELECT id,email FROM users WHERE role='Parent'")
    parents=cur.fetchall()

    if request.method=="POST":

        email=request.form["email"]
        password=request.form["password"]
        role=request.form["role"]

        teacher_id=request.form.get("teacher_id")
        parent_id=request.form.get("parent_id")

        hashed=bcrypt.generate_password_hash(password).decode("utf-8")

        try:

            if role=="Student":

                cur.execute("""
                INSERT INTO users(email,password,role,teacher_id,parent_id)
                VALUES(%s,%s,%s,%s,%s)
                """,(email,hashed,role,teacher_id,parent_id))

            else:

                cur.execute("""
                INSERT INTO users(email,password,role)
                VALUES(%s,%s,%s)
                """,(email,hashed,role))

            conn.commit()

            cur.close()
            conn.close()

            return redirect("/login")

        except Exception as e:

            return render_template(
                "register.html",
                teachers=teachers,
                parents=parents,
                error=str(e)
            )

    return render_template("register.html",teachers=teachers,parents=parents)


# -----------------------------
# LOGIN
# -----------------------------
@app.route('/login',methods=["GET","POST"])
def login():

    if request.method=="POST":

        email=request.form["email"]
        password=request.form["password"]

        conn=get_db_connection()
        cur=conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
        "SELECT password,role FROM users WHERE email=%s",(email,)
        )

        user=cur.fetchone()

        cur.close()
        conn.close()

        if user and bcrypt.check_password_hash(user["password"],password):

            session["user"]=email
            session["role"]=user["role"]

            return redirect("/dashboard")

        else:

            return render_template("login.html",error="Invalid credentials")

    return render_template("login.html")


# -----------------------------
# DASHBOARD
# -----------------------------
@app.route('/dashboard')
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
# CREATE TEACHER
# -----------------------------
@app.route('/create_teacher',methods=["GET","POST"])
def create_teacher():

    if session.get("role")!="Admin":
        return redirect("/dashboard")

    if request.method=="POST":

        email=request.form["email"]
        password=request.form["password"]

        hashed=bcrypt.generate_password_hash(password).decode("utf-8")

        conn=get_db_connection()
        cur=conn.cursor()

        cur.execute("""
        INSERT INTO users(email,password,role)
        VALUES(%s,%s,'Teacher')
        """,(email,hashed))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/dashboard")

    return render_template("create_teacher.html")


# -----------------------------
# LOGOUT
# -----------------------------
@app.route('/logout')
def logout():

    session.clear()
    return redirect("/login")


# =================================================
# START TEST
# =================================================
@app.route('/start_cognitive')
def start_cognitive():

    return redirect("/symbolic_test")


# =================================================
# SYMBOLIC TEST
# =================================================
@app.route('/symbolic_test')
def symbolic_test():

    session["symbolic_data"]=[]
    session["symbolic_trial"]=0

    return redirect("/symbolic_trial")


@app.route('/symbolic_trial')
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


@app.route('/submit_symbolic',methods=["POST"])
def submit_symbolic():

    choice=request.form.get("choice")
    rt=float(request.form.get("response_time",0))

    left=session["left"]
    right=session["right"]

    correct="left" if left>right else "right"

    correct_val=1 if choice==correct else 0

    session["symbolic_data"].append({"correct":correct_val,"rt":rt})

    session["symbolic_trial"]+=1

    return redirect("/symbolic_trial")


@app.route('/finish_symbolic')
def finish_symbolic():

    trials=session["symbolic_data"]

    accuracy=sum(t["correct"] for t in trials)/len(trials)
    mean_rt=sum(t["rt"] for t in trials)/len(trials)

    session["Accuracy_SymbolicComp"]=accuracy
    session["RTs_SymbolicComp"]=mean_rt

    return redirect("/ans_test")


# =================================================
# ANS TEST
# =================================================
@app.route('/ans_test')
def ans_test():

    session["ans_data"]=[]
    session["ans_trial"]=0

    return redirect("/ans_trial")


@app.route('/ans_trial')
def ans_trial():

    trial=session.get("ans_trial",0)

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


@app.route('/submit_ans',methods=["POST"])
def submit_ans():

    choice=request.form.get("choice")
    rt=float(request.form.get("response_time",0))

    left=session["ans_left"]
    right=session["ans_right"]

    correct="left" if left>right else "right"

    correct_val=1 if choice==correct else 0

    session["ans_data"].append({"correct":correct_val,"rt":rt})

    session["ans_trial"]+=1

    return redirect("/ans_trial")


@app.route('/finish_ans')
def finish_ans():

    trials=session["ans_data"]

    accuracy=sum(t["correct"] for t in trials)/len(trials)
    mean_rt=sum(t["rt"] for t in trials)/len(trials)

    session["Mean_ACC_ANS"]=accuracy
    session["Mean_RTs_ANS"]=mean_rt

    return redirect("/wm_test")


# =================================================
# WORKING MEMORY TEST
# =================================================
@app.route('/wm_test')
def wm_test():

    session["wm_level"]=3
    session["wm_data"]=[]

    return redirect("/wm_trial")


@app.route('/wm_trial')
def wm_trial():

    level=session["wm_level"]

    sequence=[str(random.randint(1,9)) for _ in range(level)]

    session["sequence"]=sequence

    return render_template(
        "wm_test.html",
        sequence=" ".join(sequence),
        level=level
    )


@app.route('/submit_wm',methods=["POST"])
def submit_wm():

    answer=request.form.get("answer","").replace(" ","")

    correct_seq="".join(session["sequence"])

    correct=1 if answer==correct_seq else 0

    session["wm_data"].append({"level":session["wm_level"],"correct":correct})

    if correct:

        session["wm_level"]+=1
        return redirect("/wm_trial")

    else:

        return redirect("/finish_wm")


@app.route('/finish_wm')
def finish_wm():

    data=session["wm_data"]

    scores=[d["level"] for d in data if d["correct"]==1]

    session["wm_K"]=max(scores) if scores else 0

    return redirect("/final_prediction")


# =================================================
# FINAL PREDICTION
# =================================================
@app.route('/final_prediction')
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

        recommendations="""
Immediate professional assessment recommended.
Use structured numeracy training.
Provide visual math tools and manipulatives.
Increase teacher supervision.
"""

    elif label in ["moderate","medium"]:

        risk="Medium Risk"

        recommendations="""
Provide additional practice.
Use step-by-step math instruction.
Monitor progress regularly.
"""

    elif label in ["mild","low"]:

        risk="Lowest Risk"

        recommendations="""
Provide reinforcement activities.
Encourage regular math exercises.
"""

    else:

        risk="No Dyscalculia Detected"

        recommendations="""
Continue normal learning activities.
Maintain regular practice.
"""

    return render_template(
        "final_result.html",
        risk=risk,
        recommendations=recommendations
    )


if __name__=="__main__":
    app.run()