import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, session, flash
from jinja2 import DictLoader
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "ums.db"

# ======================= DATABASE =======================
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS teachers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    email       TEXT,
    phone       TEXT,
    department  TEXT,
    designation TEXT
);
CREATE TABLE IF NOT EXISTS students (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no    TEXT UNIQUE NOT NULL,
    name       TEXT NOT NULL,
    email      TEXT,
    phone      TEXT,
    department TEXT,
    semester   INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS courses (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    code       TEXT UNIQUE NOT NULL,
    title      TEXT NOT NULL,
    credits    INTEGER DEFAULT 3,
    teacher_id INTEGER REFERENCES teachers(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS enrollments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id  INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    grade      TEXT,
    UNIQUE (student_id, course_id)
);
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    if not db.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone():
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                   ("admin", generate_password_hash("admin123")))
    db.commit()
    db.close()


# ======================= HTML TEMPLATES =======================
BASE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>UMS | {% block title %}University Management{% endblock %}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root { --primary:#4f46e5; --accent:#06b6d4; --bg:#f4f6fb; --muted:#64748b; --radius:16px; }
    * { box-sizing: border-box; }
    body { font-family:'Poppins',sans-serif; background:var(--bg); color:#1e293b; margin:0; }

    .app-wrapper { display:flex; min-height:100vh; }
    .sidebar { width:250px; position:fixed; top:0; bottom:0; left:0; padding:28px 18px;
      background:linear-gradient(180deg,#1e1b4b 0%,#312e81 100%); color:#fff;
      display:flex; flex-direction:column; box-shadow:4px 0 20px rgba(0,0,0,.08); }
    .brand { font-size:1.5rem; font-weight:700; padding:0 12px 28px; letter-spacing:1px; }
    .brand i { color:var(--accent); }
    .sidebar nav a { display:flex; align-items:center; gap:12px; color:#c7d2fe; text-decoration:none;
      padding:12px 16px; border-radius:12px; margin-bottom:6px; font-weight:500; transition:.2s; }
    .sidebar nav a:hover { background:rgba(255,255,255,.1); color:#fff; }
    .sidebar nav a.active { background:linear-gradient(90deg,var(--primary),#7c3aed); color:#fff;
      box-shadow:0 6px 16px rgba(79,70,229,.4); }
    .sidebar .logout { margin-top:auto; color:#fca5a5 !important; }

    .content { margin-left:250px; padding:32px 36px; width:calc(100% - 250px); }
    .page-title { font-weight:700; margin-bottom:4px; }
    .page-sub { color:var(--muted); margin-bottom:28px; }

    .ui-card { background:#fff; border-radius:var(--radius); box-shadow:0 4px 20px rgba(15,23,42,.06);
      padding:24px; margin-bottom:24px; }
    .ui-card h5 { font-weight:600; margin-bottom:18px; }

    .stat-card { border-radius:var(--radius); padding:22px 24px; color:#fff; position:relative;
      overflow:hidden; box-shadow:0 8px 24px rgba(0,0,0,.12); }
    .stat-card .label { font-size:.85rem; opacity:.9; }
    .stat-card .value { font-size:2.2rem; font-weight:700; line-height:1.1; }
    .stat-card .icon { position:absolute; right:18px; bottom:10px; font-size:3.5rem; opacity:.18; }
    .grad-1 { background:linear-gradient(135deg,#6366f1,#8b5cf6); }
    .grad-2 { background:linear-gradient(135deg,#0ea5e9,#06b6d4); }
    .grad-3 { background:linear-gradient(135deg,#10b981,#34d399); }
    .grad-4 { background:linear-gradient(135deg,#f59e0b,#f97316); }

    .form-control, .form-select { border-radius:10px; border:1px solid #e2e8f0; padding:10px 14px; }
    .form-control:focus, .form-select:focus { border-color:var(--primary); box-shadow:0 0 0 .2rem rgba(79,70,229,.15); }
    .btn { border-radius:10px; font-weight:500; }
    .btn-primary { background:linear-gradient(90deg,var(--primary),#7c3aed); border:none; }
    .btn-primary:hover { opacity:.92; }

    .table thead th { font-size:.78rem; text-transform:uppercase; letter-spacing:.6px; color:var(--muted);
      font-weight:600; border-bottom:2px solid #eef2f7; }
    .table tbody td { vertical-align:middle; padding:14px 12px; border-color:#f1f5f9; }
    .table tbody tr:hover { background:#f8faff; }

    .avatar { width:40px; height:40px; border-radius:50%; display:inline-flex; align-items:center;
      justify-content:center; font-weight:600; color:#fff; margin-right:12px; flex-shrink:0;
      background:linear-gradient(135deg,var(--primary),var(--accent)); }
    .badge-soft { padding:6px 12px; border-radius:999px; font-weight:600; font-size:.8rem; }
    .badge-grade { background:#ecfdf5; color:#059669; }
    .badge-none { background:#f1f5f9; color:var(--muted); }
    .alert { border:none; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,.05); }

    .auth-page { min-height:100vh; width:100%; display:flex; align-items:center; justify-content:center;
      background:linear-gradient(135deg,#1e1b4b,#4f46e5,#06b6d4); padding:20px; }
    .login-card { width:100%; max-width:400px; background:#fff; border-radius:20px; padding:40px 34px;
      box-shadow:0 20px 60px rgba(0,0,0,.25); }
    .login-card .logo { width:64px; height:64px; border-radius:18px; display:flex; align-items:center;
      justify-content:center; margin:0 auto 14px; color:#fff; font-size:1.8rem;
      background:linear-gradient(135deg,var(--primary),var(--accent)); }

    @media (max-width:768px) {
      .sidebar { position:relative; width:100%; height:auto; }
      .content { margin-left:0; width:100%; padding:20px; }
      .app-wrapper { flex-direction:column; }
    }
  </style>
</head>
<body>
<div class="{{ 'app-wrapper' if session.get('user') else '' }}">
  {% if session.get('user') %}
  <aside class="sidebar">
    <div class="brand"><i class="bi bi-mortarboard-fill"></i> UMS</div>
    <nav>
      <a href="{{ url_for('dashboard') }}" class="{{ 'active' if request.endpoint == 'dashboard' else '' }}"><i class="bi bi-grid-fill"></i> Dashboard</a>
      <a href="{{ url_for('students') }}" class="{{ 'active' if request.endpoint == 'students' else '' }}"><i class="bi bi-people-fill"></i> Students</a>
      <a href="{{ url_for('teachers') }}" class="{{ 'active' if request.endpoint == 'teachers' else '' }}"><i class="bi bi-person-badge-fill"></i> Teachers</a>
      <a href="{{ url_for('courses') }}" class="{{ 'active' if request.endpoint == 'courses' else '' }}"><i class="bi bi-book-fill"></i> Courses</a>
      <a href="{{ url_for('enrollments') }}" class="{{ 'active' if request.endpoint == 'enrollments' else '' }}"><i class="bi bi-journal-check"></i> Enrollments</a>
    </nav>
    <a href="{{ url_for('logout') }}" class="logout"><i class="bi bi-box-arrow-left"></i> Logout</a>
  </aside>
  {% endif %}

  <main class="{{ 'content' if session.get('user') else 'auth-page' }}">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, message in messages %}
        <div class="alert alert-{{ category }} mb-4">{{ message }}</div>
      {% endfor %}
    {% endwith %}
    {% block content %}{% endblock %}
  </main>
</div>
</body>
</html>"""

LOGIN_HTML = """{% extends "base.html" %}
{% block title %}Login{% endblock %}
{% block content %}
<div class="login-card">
  <div class="logo"><i class="bi bi-mortarboard-fill"></i></div>
  <h4 class="text-center fw-bold mb-1">University Management</h4>
  <p class="text-center text-muted small mb-4">Sign in to your account</p>
  <form method="POST">
    <div class="mb-3">
      <label class="form-label small fw-semibold">Username</label>
      <div class="input-group">
        <span class="input-group-text bg-white"><i class="bi bi-person"></i></span>
        <input type="text" name="username" class="form-control" required>
      </div>
    </div>
    <div class="mb-4">
      <label class="form-label small fw-semibold">Password</label>
      <div class="input-group">
        <span class="input-group-text bg-white"><i class="bi bi-lock"></i></span>
        <input type="password" name="password" class="form-control" required>
      </div>
    </div>
    <button class="btn btn-primary w-100 py-2">Login <i class="bi bi-arrow-right"></i></button>
  </form>
  <p class="text-muted small text-center mt-4 mb-0">Default: admin / admin123</p>
</div>
{% endblock %}"""

DASHBOARD_HTML = """{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}
{% block content %}
<h2 class="page-title">Welcome, {{ session.user }} 👋</h2>
<p class="page-sub">Today's overview</p>
<div class="row g-4 mb-4">
  <div class="col-md-6 col-xl-3"><div class="stat-card grad-1">
    <div class="label">Total Students</div><div class="value">{{ stats.students }}</div>
    <i class="bi bi-people-fill icon"></i></div></div>
  <div class="col-md-6 col-xl-3"><div class="stat-card grad-2">
    <div class="label">Total Teachers</div><div class="value">{{ stats.teachers }}</div>
    <i class="bi bi-person-badge-fill icon"></i></div></div>
  <div class="col-md-6 col-xl-3"><div class="stat-card grad-3">
    <div class="label">Total Courses</div><div class="value">{{ stats.courses }}</div>
    <i class="bi bi-book-fill icon"></i></div></div>
  <div class="col-md-6 col-xl-3"><div class="stat-card grad-4">
    <div class="label">Enrollments</div><div class="value">{{ stats.enrollments }}</div>
    <i class="bi bi-journal-check icon"></i></div></div>
</div>
<div class="ui-card">
  <h5><i class="bi bi-clock-history text-primary"></i> Recent Enrollments</h5>
  <div class="table-responsive">
    <table class="table mb-0">
      <thead><tr><th>Student</th><th>Course</th><th>Grade</th></tr></thead>
      <tbody>
        {% for r in recent %}
        <tr>
          <td>{{ r.student_name }}</td>
          <td>{{ r.code }} - {{ r.title }}</td>
          <td>{% if r.grade %}<span class="badge-soft badge-grade">{{ r.grade }}</span>
              {% else %}<span class="badge-soft badge-none">Pending</span>{% endif %}</td>
        </tr>
        {% else %}
        <tr><td colspan="3" class="text-center text-muted py-4">No enrollments yet.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}"""

STUDENTS_HTML = """{% extends "base.html" %}
{% block title %}Students{% endblock %}
{% block content %}
<h2 class="page-title">Students</h2>
<p class="page-sub">Manage student records</p>
<div class="ui-card">
  <h5><i class="bi bi-person-plus-fill text-primary"></i> New Student</h5>
  <form method="POST" class="row g-2">
    <div class="col-md-2"><input name="roll_no" class="form-control" placeholder="Roll No" required></div>
    <div class="col-md-3"><input name="name" class="form-control" placeholder="Full Name" required></div>
    <div class="col-md-3"><input name="email" type="email" class="form-control" placeholder="Email"></div>
    <div class="col-md-2"><input name="phone" class="form-control" placeholder="Phone"></div>
    <div class="col-md-1"><input name="semester" type="number" min="1" max="8" value="1" class="form-control" title="Semester"></div>
    <div class="col-md-1"><button class="btn btn-primary w-100"><i class="bi bi-plus-lg"></i></button></div>
    <div class="col-md-4"><input name="department" class="form-control" placeholder="Department (e.g. CS)"></div>
  </form>
</div>
<div class="ui-card">
  <div class="table-responsive">
    <table class="table mb-0">
      <thead><tr><th>Roll No</th><th>Name</th><th>Email</th><th>Phone</th><th>Dept</th><th>Sem</th><th></th></tr></thead>
      <tbody>
        {% for s in students %}
        <tr>
          <td class="fw-semibold">{{ s.roll_no }}</td>
          <td><span class="avatar">{{ s.name[0] }}</span>{{ s.name }}</td>
          <td>{{ s.email or '-' }}</td>
          <td>{{ s.phone or '-' }}</td>
          <td>{{ s.department or '-' }}</td>
          <td><span class="badge-soft badge-none">Sem {{ s.semester }}</span></td>
          <td class="text-end">
            <form method="POST" action="{{ url_for('delete_student', student_id=s.id) }}"
                  onsubmit="return confirm('Delete this student?');">
              <button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button>
            </form>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="7" class="text-center text-muted py-4">No students yet.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}"""

TEACHERS_HTML = """{% extends "base.html" %}
{% block title %}Teachers{% endblock %}
{% block content %}
<h2 class="page-title">Teachers</h2>
<p class="page-sub">Manage faculty records</p>
<div class="ui-card">
  <h5><i class="bi bi-person-plus-fill text-primary"></i> New Teacher</h5>
  <form method="POST" class="row g-2">
    <div class="col-md-2"><input name="employee_id" class="form-control" placeholder="Employee ID" required></div>
    <div class="col-md-3"><input name="name" class="form-control" placeholder="Full Name" required></div>
    <div class="col-md-3"><input name="email" type="email" class="form-control" placeholder="Email"></div>
    <div class="col-md-2"><input name="phone" class="form-control" placeholder="Phone"></div>
    <div class="col-md-2"><button class="btn btn-primary w-100"><i class="bi bi-plus-lg"></i> Add</button></div>
    <div class="col-md-4"><input name="department" class="form-control" placeholder="Department (e.g. CS)"></div>
    <div class="col-md-8"><input name="designation" class="form-control" placeholder="Designation (e.g. Assistant Professor)"></div>
  </form>
</div>
<div class="ui-card">
  <div class="table-responsive">
    <table class="table mb-0">
      <thead><tr><th>Employee ID</th><th>Name</th><th>Designation</th><th>Dept</th><th>Email</th><th>Courses</th><th></th></tr></thead>
      <tbody>
        {% for t in teachers %}
        <tr>
          <td class="fw-semibold">{{ t.employee_id }}</td>
          <td><span class="avatar" style="background:linear-gradient(135deg,#f59e0b,#f97316)">{{ t.name[0] }}</span>{{ t.name }}</td>
          <td>{{ t.designation or '-' }}</td>
          <td>{{ t.department or '-' }}</td>
          <td>{{ t.email or '-' }}</td>
          <td><span class="badge-soft badge-grade">{{ t.course_count }} courses</span></td>
          <td class="text-end">
            <form method="POST" action="{{ url_for('delete_teacher', teacher_id=t.id) }}"
                  onsubmit="return confirm('Delete this teacher? Their courses will become unassigned.');">
              <button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button>
            </form>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="7" class="text-center text-muted py-4">No teachers yet.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}"""

COURSES_HTML = """{% extends "base.html" %}
{% block title %}Courses{% endblock %}
{% block content %}
<h2 class="page-title">Courses</h2>
<p class="page-sub">Manage courses and their teachers</p>
<div class="ui-card">
  <h5><i class="bi bi-plus-square-fill text-primary"></i> New Course</h5>
  <form method="POST" class="row g-2">
    <div class="col-md-2"><input name="code" class="form-control" placeholder="Code (CS101)" required></div>
    <div class="col-md-4"><input name="title" class="form-control" placeholder="Course Title" required></div>
    <div class="col-md-2"><input name="credits" type="number" min="1" max="6" value="3" class="form-control" title="Credits"></div>
    <div class="col-md-3">
      <select name="teacher_id" class="form-select">
        <option value="">-- Select Teacher --</option>
        {% for t in teachers %}<option value="{{ t.id }}">{{ t.name }}</option>{% endfor %}
      </select>
    </div>
    <div class="col-md-1"><button class="btn btn-primary w-100"><i class="bi bi-plus-lg"></i></button></div>
  </form>
</div>
<div class="ui-card">
  <div class="table-responsive">
    <table class="table mb-0">
      <thead><tr><th>Code</th><th>Title</th><th>Credits</th><th>Teacher</th><th></th></tr></thead>
      <tbody>
        {% for c in courses %}
        <tr>
          <td><span class="badge-soft" style="background:#eef2ff;color:#4f46e5">{{ c.code }}</span></td>
          <td class="fw-semibold">{{ c.title }}</td>
          <td>{{ c.credits }}</td>
          <td>{% if c.teacher_name %}
                <span class="avatar" style="width:30px;height:30px;font-size:.8rem">{{ c.teacher_name[0] }}</span>{{ c.teacher_name }}
              {% else %}<span class="text-muted">Unassigned</span>{% endif %}</td>
          <td class="text-end">
            <form method="POST" action="{{ url_for('delete_course', course_id=c.id) }}"
                  onsubmit="return confirm('Delete this course?');">
              <button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button>
            </form>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="5" class="text-center text-muted py-4">No courses yet.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}"""

ENROLLMENTS_HTML = """{% extends "base.html" %}
{% block title %}Enrollments{% endblock %}
{% block content %}
<h2 class="page-title">Enrollments & Grades</h2>
<p class="page-sub">Enroll students in courses and assign grades</p>
<div class="ui-card">
  <h5><i class="bi bi-journal-plus text-primary"></i> New Enrollment</h5>
  <form method="POST" class="row g-2">
    <div class="col-md-5">
      <select name="student_id" class="form-select" required>
        <option value="">-- Select Student --</option>
        {% for s in students %}<option value="{{ s.id }}">{{ s.roll_no }} - {{ s.name }}</option>{% endfor %}
      </select>
    </div>
    <div class="col-md-5">
      <select name="course_id" class="form-select" required>
        <option value="">-- Select Course --</option>
        {% for c in courses %}<option value="{{ c.id }}">{{ c.code }} - {{ c.title }}</option>{% endfor %}
      </select>
    </div>
    <div class="col-md-2"><button class="btn btn-primary w-100">Enroll</button></div>
  </form>
</div>
<div class="ui-card">
  <div class="table-responsive">
    <table class="table mb-0">
      <thead><tr><th>Roll No</th><th>Student</th><th>Course</th><th>Teacher</th><th>Grade</th><th>Set Grade</th><th></th></tr></thead>
      <tbody>
        {% for e in enrollments %}
        <tr>
          <td class="fw-semibold">{{ e.roll_no }}</td>
          <td>{{ e.student_name }}</td>
          <td>{{ e.code }} - {{ e.title }}</td>
          <td>{{ e.teacher_name or '-' }}</td>
          <td>{% if e.grade %}<span class="badge-soft badge-grade">{{ e.grade }}</span>
              {% else %}<span class="badge-soft badge-none">-</span>{% endif %}</td>
          <td>
            <form method="POST" action="{{ url_for('set_grade', enrollment_id=e.id) }}" class="d-flex gap-1">
              <input name="grade" class="form-control form-control-sm" style="width:80px" placeholder="A+" required>
              <button class="btn btn-sm btn-success"><i class="bi bi-check-lg"></i></button>
            </form>
          </td>
          <td class="text-end">
            <form method="POST" action="{{ url_for('delete_enrollment', enrollment_id=e.id) }}"
                  onsubmit="return confirm('Remove this enrollment?');">
              <button class="btn btn-sm btn-outline-danger"><i class="bi bi-x-lg"></i></button>
            </form>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="7" class="text-center text-muted py-4">No enrollments yet.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}"""

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret"
app.jinja_loader = DictLoader({
    "base.html": BASE_HTML,
    "login.html": LOGIN_HTML,
    "dashboard.html": DASHBOARD_HTML,
    "students.html": STUDENTS_HTML,
    "teachers.html": TEACHERS_HTML,
    "courses.html": COURSES_HTML,
    "enrollments.html": ENROLLMENTS_HTML,
})


# ======================= AUTH =======================
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?",
                          (request.form["username"].strip(),)).fetchone()
        db.close()
        if user and check_password_hash(user["password"], request.form["password"]):
            session["user"] = user["username"]
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ======================= DASHBOARD =======================
@app.route("/")
@login_required
def dashboard():
    db = get_db()
    stats = {
        "students": db.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        "teachers": db.execute("SELECT COUNT(*) FROM teachers").fetchone()[0],
        "courses": db.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
        "enrollments": db.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0],
    }
    recent = db.execute("""
        SELECT s.name AS student_name, c.code, c.title, e.grade
        FROM enrollments e
        JOIN students s ON s.id = e.student_id
        JOIN courses c ON c.id = e.course_id
        ORDER BY e.id DESC LIMIT 5
    """).fetchall()
    db.close()
    return render_template("dashboard.html", stats=stats, recent=recent)


# ======================= STUDENTS =======================
@app.route("/students", methods=["GET", "POST"])
@login_required
def students():
    db = get_db()
    if request.method == "POST":
        try:
            db.execute(
                """INSERT INTO students (roll_no, name, email, phone, department, semester)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (request.form["roll_no"].strip(), request.form["name"].strip(),
                 request.form.get("email", ""), request.form.get("phone", ""),
                 request.form.get("department", ""), int(request.form.get("semester", 1))))
            db.commit()
            flash("Student added.", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        db.close()
        return redirect(url_for("students"))

    rows = db.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    db.close()
    return render_template("students.html", students=rows)


@app.route("/students/delete/<int:student_id>", methods=["POST"])
@login_required
def delete_student(student_id):
    db = get_db()
    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
    db.close()
    flash("Student deleted.", "info")
    return redirect(url_for("students"))


# ======================= TEACHERS =======================
@app.route("/teachers", methods=["GET", "POST"])
@login_required
def teachers():
    db = get_db()
    if request.method == "POST":
        try:
            db.execute(
                """INSERT INTO teachers (employee_id, name, email, phone, department, designation)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (request.form["employee_id"].strip(), request.form["name"].strip(),
                 request.form.get("email", ""), request.form.get("phone", ""),
                 request.form.get("department", ""), request.form.get("designation", "")))
            db.commit()
            flash("Teacher added.", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        db.close()
        return redirect(url_for("teachers"))

    rows = db.execute("""
        SELECT t.*, (SELECT COUNT(*) FROM courses c WHERE c.teacher_id = t.id) AS course_count
        FROM teachers t ORDER BY t.name
    """).fetchall()
    db.close()
    return render_template("teachers.html", teachers=rows)


@app.route("/teachers/delete/<int:teacher_id>", methods=["POST"])
@login_required
def delete_teacher(teacher_id):
    db = get_db()
    db.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))
    db.commit()
    db.close()
    flash("Teacher deleted. Their courses are now unassigned.", "info")
    return redirect(url_for("teachers"))


# ======================= COURSES =======================
@app.route("/courses", methods=["GET", "POST"])
@login_required
def courses():
    db = get_db()
    if request.method == "POST":
        try:
            db.execute(
                "INSERT INTO courses (code, title, credits, teacher_id) VALUES (?, ?, ?, ?)",
                (request.form["code"].strip().upper(), request.form["title"].strip(),
                 int(request.form.get("credits", 3)), request.form.get("teacher_id") or None))
            db.commit()
            flash("Course added.", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        db.close()
        return redirect(url_for("courses"))

    rows = db.execute("""
        SELECT c.*, t.name AS teacher_name
        FROM courses c LEFT JOIN teachers t ON t.id = c.teacher_id
        ORDER BY c.code
    """).fetchall()
    all_teachers = db.execute("SELECT id, name FROM teachers ORDER BY name").fetchall()
    db.close()
    return render_template("courses.html", courses=rows, teachers=all_teachers)


@app.route("/courses/delete/<int:course_id>", methods=["POST"])
@login_required
def delete_course(course_id):
    db = get_db()
    db.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    db.commit()
    db.close()
    flash("Course deleted.", "info")
    return redirect(url_for("courses"))


# ======================= ENROLLMENTS =======================
@app.route("/enrollments", methods=["GET", "POST"])
@login_required
def enrollments():
    db = get_db()
    if request.method == "POST":
        try:
            db.execute("INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)",
                       (request.form["student_id"], request.form["course_id"]))
            db.commit()
            flash("Student enrolled.", "success")
        except sqlite3.IntegrityError:
            flash("This student is already enrolled in this course.", "warning")
        db.close()
        return redirect(url_for("enrollments"))

    rows = db.execute("""
        SELECT e.id, s.roll_no, s.name AS student_name, c.code, c.title,
               e.grade, t.name AS teacher_name
        FROM enrollments e
        JOIN students s ON s.id = e.student_id
        JOIN courses c ON c.id = e.course_id
        LEFT JOIN teachers t ON t.id = c.teacher_id
        ORDER BY s.roll_no
    """).fetchall()
    all_students = db.execute("SELECT id, roll_no, name FROM students ORDER BY roll_no").fetchall()
    all_courses = db.execute("SELECT id, code, title FROM courses ORDER BY code").fetchall()
    db.close()
    return render_template("enrollments.html", enrollments=rows,
                           students=all_students, courses=all_courses)


@app.route("/enrollments/grade/<int:enrollment_id>", methods=["POST"])
@login_required
def set_grade(enrollment_id):
    db = get_db()
    db.execute("UPDATE enrollments SET grade = ? WHERE id = ?",
               (request.form["grade"].strip().upper(), enrollment_id))
    db.commit()
    db.close()
    flash("Grade updated.", "success")
    return redirect(url_for("enrollments"))


@app.route("/enrollments/delete/<int:enrollment_id>", methods=["POST"])
@login_required
def delete_enrollment(enrollment_id):
    db = get_db()
    db.execute("DELETE FROM enrollments WHERE id = ?", (enrollment_id,))
    db.commit()
    db.close()
    flash("Enrollment removed.", "info")
    return redirect(url_for("enrollments"))


# ======================= RUN =======================
if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)