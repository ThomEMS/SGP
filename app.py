from flask import Flask, render_template, redirect, request, session, url_for
from database import init_db, add_user, verify_user, user_exists
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change_me_dev")

init_db()

@app.route('/')
def index():
    user = session.get("user")
    if not user:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COALESCE(SUM(amount * COALESCE(shared_ratio, 1)), 0) AS total_share,
            COALESCE(SUM(amount), 0) AS total_brut
        FROM expenses
        WHERE user_id = ?
          AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
    """, (user["id"],))
    current_totals = cursor.fetchone()
    current_total = current_totals["total_share"] if current_totals else 0
    current_total_brut = current_totals["total_brut"] if current_totals else 0

    cursor.execute("""
        SELECT
            COALESCE(SUM(amount * COALESCE(shared_ratio, 1)), 0) AS total_share
        FROM expenses
        WHERE user_id = ?
          AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', '-1 month')
    """, (user["id"],))
    previous_totals = cursor.fetchone()
    last_month_total = previous_totals["total_share"] if previous_totals else 0

    delta = current_total - last_month_total
    percent_change = (delta / last_month_total * 100) if last_month_total else None

    cursor.execute("""
        SELECT
            category,
            amount,
            COALESCE(shared_ratio, 1) AS shared_ratio,
            note,
            created_at,
            amount * COALESCE(shared_ratio, 1) AS user_amount
        FROM expenses
        WHERE user_id = ?
        ORDER BY datetime(created_at) DESC
        LIMIT 5
    """, (user["id"],))
    recent_expenses = cursor.fetchall()

    conn.close()

    monthly_summary = {
        "current_total": current_total,
        "current_total_brut": current_total_brut,
        "last_month_total": last_month_total,
        "delta": delta,
        "percent_change": percent_change,
    }

    return render_template(
        'index.html',
        user=user,
        monthly_summary=monthly_summary,
        recent_expenses=recent_expenses,
    )

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
        username = request.form['username'].strip()
        password = request.form['password']

        if user_exists(username):
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
    cursor = conn.cursor()

    # Retrieve main account
    account = cursor.execute(
        "SELECT * FROM accounts WHERE user_id = ?", (user["id"],)
    ).fetchone()

    # Case 1 — update main financial info
    if request.method == "POST" and "add_expense" not in request.form:
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
            cursor.execute("""
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
            cursor.execute("""
                INSERT INTO accounts (user_id, net_income, pay_frequency,
                    next_pay_date, fixed_expenses, savings_goal, debt_payment, notes)
                VALUES (:user_id, :net_income, :pay_frequency,
                    :next_pay_date, :fixed_expenses, :savings_goal, :debt_payment, :notes)
            """, {**data, "user_id": user["id"]})
        conn.commit()
        account = cursor.execute(
            "SELECT * FROM accounts WHERE user_id = ?", (user["id"],)
        ).fetchone()

    # Case 2 — add a fixed expense line
    elif request.method == "POST" and "add_expense" in request.form:
        category = request.form["category"]
        amount = float(request.form["amount"])
        note = request.form.get("note", "")
        cursor.execute("""
            INSERT INTO fixed_expenses (user_id, category, amount, note)
            VALUES (?, ?, ?, ?)
        """, (user["id"], category, amount, note))
        conn.commit()

    # Retrieve all fixed expenses
    cursor.execute("SELECT * FROM fixed_expenses WHERE user_id = ?", (user["id"],))
    fixed_expenses = cursor.fetchall()

    conn.close()
    return render_template("compte.html", user=user, account=account, fixed_expenses=fixed_expenses)



@app.route('/stats')
def stats():
    """Page de statistiques mensuelles"""
    user = session.get("user")
    if not user:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Récupérer les infos de compte (revenu, objectifs, etc.)
    account = cursor.execute(
        "SELECT * FROM accounts WHERE user_id = ?", (user["id"],)
    ).fetchone()

    # 1️⃣ Dépenses fixes
    cursor.execute("""
        SELECT category, SUM(amount) AS total
        FROM fixed_expenses
        WHERE user_id = ?
        GROUP BY category
    """, (user["id"],))
    fixed_expenses = cursor.fetchall()
    total_fixed = sum([row["total"] for row in fixed_expenses]) if fixed_expenses else 0

    # 2️⃣ Dépenses du mois courant (expenses)
    cursor.execute("""
        SELECT category,
               SUM(amount * COALESCE(shared_ratio,1)) AS total,
               SUM(amount) AS total_brut
        FROM expenses
        WHERE user_id = ?
          AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
        GROUP BY category
    """, (user["id"],))
    variable_expenses = cursor.fetchall()
    total_variable = sum([row["total"] for row in variable_expenses]) if variable_expenses else 0

    # 2.5️⃣ Répartition par catégorie
    category_totals = {}
    for row in fixed_expenses or []:
        category = row["category"]
        category_totals.setdefault(category, {"fixed": 0.0, "variable": 0.0})
        category_totals[category]["fixed"] = row["total"]
    for row in variable_expenses or []:
        category = row["category"]
        category_totals.setdefault(category, {"fixed": 0.0, "variable": 0.0})
        category_totals[category]["variable"] = row["total"]

    category_breakdown = [
        {
            "category": category,
            "fixed_total": totals["fixed"],
            "variable_total": totals["variable"],
            "overall_total": totals["fixed"] + totals["variable"],
        }
        for category, totals in sorted(category_totals.items(), key=lambda item: item[0].lower())
    ]

    # 3️⃣ Calculs généraux
    net_income = account["net_income"] if account else 0
    savings_goal = account["savings_goal"] if account else 0
    remaining = net_income - total_fixed - total_variable - savings_goal

    conn.close()

    return render_template(
        "stats.html",
        user=user,
        account=account,
        fixed_expenses=fixed_expenses,
        variable_expenses=variable_expenses,
        total_fixed=total_fixed,
        total_variable=total_variable,
        savings_goal=savings_goal,
        remaining=remaining,
        net_income=net_income,
        category_breakdown=category_breakdown,
    )


@app.route('/ajout', methods=['GET', 'POST'])
def ajout():
    """Ajout de dépenses du mois courant"""
    user = session.get("user")
    if not user:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        category = request.form['category']
        amount = float(request.form['amount'])
        note = request.form.get('note', '')
        shared_type = request.form.get('shared_type')
        shared_ratio = 1.0

        # Si c’est une facture partagée, récupérer la proportion entrée
        if shared_type == 'shared':
            shared_ratio = float(request.form.get('shared_ratio', 1.0))

        cursor.execute("""
            INSERT INTO expenses (user_id, category, amount, note, shared_ratio)
            VALUES (?, ?, ?, ?, ?)
        """, (user['id'], category, amount, note, shared_ratio))
        conn.commit()

    cursor.execute("""
        SELECT *
        FROM expenses
        WHERE user_id = ?
        AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
        ORDER BY created_at DESC
    """, (user['id'],))
    expenses = cursor.fetchall()

    cursor.execute("""
        SELECT category FROM (
            SELECT DISTINCT category FROM fixed_expenses WHERE user_id = ?
            UNION
            SELECT DISTINCT category FROM expenses WHERE user_id = ?
        ) AS categories
        WHERE category IS NOT NULL AND TRIM(category) <> ''
        ORDER BY LOWER(category)
    """, (user['id'], user['id']))
    expense_categories = [row["category"] for row in cursor.fetchall()]

    conn.close()

    return render_template('ajout.html', user=user, expenses=expenses, expense_categories=expense_categories)

@app.route("/ping")
def ping():
    return {"status": "ok"}, 200


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
