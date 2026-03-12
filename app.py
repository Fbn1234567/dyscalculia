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


# ---------------------------
# LOAD MODEL
# ---------------------------
model = pickle.load(open("model.pkl","rb"))
label_encoder = pickle.load(open("label_encoder.pkl","rb"))


# ---------------------------
# HOME
# ---------------------------
@app.route("/")
def home():

    if "user" in session:
        return redirect("/dashboard")

    return redirect("/login")


# ---------------------------
# LOGIN
# ---------------------------
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

        return render_template("login.html",error="Invalid login")

    return render_template("login.html")


# ---------------------------
# DASHBOARD
# ---------------------------
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    role=session["role"]

    if role=="Student":
        return render_template("student_dashboard.html")

    if role=="Teacher":
        return render_template("teacher_dashboard.html")

    if role=="Parent":
        return render_template("parent_dashboard.html")

    return render_template("admin_dashboard.html")


# ---------------------------
# LOGOUT
# ---------------------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ---------------------------
# START TEST
# ---------------------------
@app.route("/start_cognitive")
def start_cognitive():

    return redirect("/symbolic_test")


# =================================================
# SYMBOLIC TEST
# =================================================

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

    return render_template("symbolic_test.html",left=left,right=right,trial=trial+1)


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

    acc=sum(t["correct"] for t in trials)/len(trials)
    rt=sum(t["rt"] for t in trials)/len(trials)

    session["Accuracy_SymbolicComp"]=acc
    session["RTs_SymbolicComp"]=rt

    return redirect("/ans_test")


# =================================================
# ANS TEST
# =================================================

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

    return render_template("ans_test.html",left=left,right=right,trial=trial+1)


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

    acc=sum(t["correct"] for t in trials)/len(trials)
    rt=sum(t["rt"] for t in trials)/len(trials)

    session["Mean_ACC_ANS"]=acc
    session["Mean_RTs_ANS"]=rt

    return redirect("/fraction_test")


# =================================================
# FRACTION TEST
# =================================================

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

    return render_template("fraction_test.html",
                           left=f"{a}/{b}",
                           right=f"{c}/{d}",
                           trial=trial+1)


@app.route("/submit_fraction",methods=["POST"])
def submit_fraction():

    choice=request.form["choice"]

    a,b=session["frac_left"]
    c,d=session["frac_right"]

    correct="left" if (a/b)>(c/d) else "right"

    correct_val=1 if choice==correct else 0

    session["fraction_data"].append({"correct":correct_val})

    session["fraction_trial"]+=1

    return redirect("/fraction_trial")


@app.route("/finish_fraction")
def finish_fraction():

    trials=session["fraction_data"]

    acc=sum(t["correct"] for t in trials)/len(trials)

    session["Fraction_ACC"]=acc

    return redirect("/wm_test")


# =================================================
# WORKING MEMORY
# =================================================

@app.route("/wm_test")
def wm_test():

    session["wm_level"]=3
    session["wm_data"]=[]

    return redirect("/wm_trial")


@app.route("/wm_trial")
def wm_trial():

    level=session.get("wm_level",3)

    seq=[str(random.randint(1,9)) for _ in range(level)]

    session["sequence"]=seq

    return render_template("wm_test.html",sequence=" ".join(seq))


@app.route("/submit_wm",methods=["POST"])
def submit_wm():

    if "sequence" not in session:
        return redirect("/wm_test")

    answer=request.form.get("answer","").replace(" ","")

    correct_seq="".join(session["sequence"])

    correct=1 if answer==correct_seq else 0

    data=session.get("wm_data",[])
    level=session.get("wm_level",3)

    data.append({"level":level,"correct":correct})

    session["wm_data"]=data

    if correct:
        session["wm_level"]=level+1
        return redirect("/wm_trial")

    return redirect("/finish_wm")


@app.route("/finish_wm")
def finish_wm():

    data=session.get("wm_data",[])

    scores=[d["level"] for d in data if d["correct"]==1]

    session["wm_K"]=max(scores) if scores else 0

    return redirect("/final_prediction")


# =================================================
# FINAL PREDICTION
# =================================================

@app.route("/final_prediction")
def final_prediction():

    if "user" not in session:
        return redirect("/login")

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
        risk="High Risk"
    elif label in ["moderate","medium"]:
        risk="Medium Risk"
    elif label in ["mild","low"]:
        risk="Low Risk"
    else:
        risk="No Dyscalculia"


    conn=get_db_connection()
    cur=conn.cursor()

    cur.execute("""
    INSERT INTO results
    (student_email,ans_acc,ans_rt,wm_k,sym_acc,sym_rt,risk_level)
    VALUES(%s,%s,%s,%s,%s,%s,%s)
    """,(

        session["user"],
        session["Mean_ACC_ANS"],
        session["Mean_RTs_ANS"],
        session["wm_K"],
        session["Accuracy_SymbolicComp"],
        session["RTs_SymbolicComp"],
        risk

    ))

    conn.commit()
    cur.close()
    conn.close()

    return render_template("final_result.html",risk=risk)


# =================================================
# HISTORY
# =================================================

@app.route("/history")
def history():

    if "user" not in session:
        return redirect("/login")

    conn=get_db_connection()
    cur=conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
    SELECT ans_acc,ans_rt,wm_k,sym_acc,sym_rt,risk_level,created_at
    FROM results
    WHERE student_email=%s
    ORDER BY created_at DESC
    """,(session["user"],))

    results=cur.fetchall()

    cur.close()
    conn.close()

    return render_template("history.html",results=results)


if __name__=="__main__":
    app.run(debug=True)