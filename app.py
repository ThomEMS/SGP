from flask import Flask, render_template, redirect, request, session, url_for
from database import init_db, add_user, verify_user
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change_me_dev")

init_db()

@app.route('/')
def index():
    if not session.get("user"):
        return redirect(url_for('login'))
    return render_template('index.html', user=session["user"])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = verify_user(username, password)
        if user:
            session["user"] = user
            return redirect(url_for('index'))
        return render_template('login.html', error="Identifiants invalides")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        from database import add_user, verify_user

        # Check if user already exists
        if verify_user(username, password):
            return render_template('register.html', error="Ce nom d'utilisateur existe déjà.")

        # Add user and redirect to login
        add_user(username, password)
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

from database import get_db_connection  # si tu as déjà une fonction équivalente

@app.route('/compte', methods=['GET', 'POST'])
def compte():
    user = session.get("user")
    if not user:
        return redirect(url_for('login'))

    conn = get_db_connection()
    account = conn.execute(
        "SELECT * FROM accounts WHERE user_id = ?", (user["id"],)
    ).fetchone()

    if request.method == "POST":
        data = {
            "net_income": request.form["net_income"],
            "pay_frequency": request.form["pay_frequency"],
            "next_pay_date": request.form.get("next_pay_date"),
            "fixed_expenses": request.form.get("fixed_expenses") or 0,
            "savings_goal": request.form.get("savings_goal") or 0,
            "debt_payment": request.form.get("debt_payment") or 0,
            "notes": request.form.get("notes", ""),
        }

        if account:
            conn.execute("""
                UPDATE accounts SET
                    net_income = :net_income,
                    pay_frequency = :pay_frequency,
                    next_pay_date = :next_pay_date,
                    fixed_expenses = :fixed_expenses,
                    savings_goal = :savings_goal,
                    debt_payment = :debt_payment,
                    notes = :notes
                WHERE user_id = :user_id
            """, {**data, "user_id": user["id"]})
        else:
            conn.execute("""
                INSERT INTO accounts (user_id, net_income, pay_frequency,
                    next_pay_date, fixed_expenses, savings_goal, debt_payment, notes)
                VALUES (:user_id, :net_income, :pay_frequency,
                    :next_pay_date, :fixed_expenses, :savings_goal, :debt_payment, :notes)
            """, {**data, "user_id": user["id"]})

        conn.commit()
        conn.close()
        return redirect(url_for("compte"))

    conn.close()
    return render_template("compte.html", user=user, account=account)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
