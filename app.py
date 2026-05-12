from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)

# ─────────────────────────────────────────
# DECORATORS
# ─────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') != role:
                flash('Unauthorized access.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['name']    = user['name']
            session['role']    = user['role']

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'student':
                return redirect(url_for('student_dashboard'))
            elif user['role'] == 'technician':
                return redirect(url_for('technician_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form['name']
        email    = request.form['email']
        password = generate_password_hash(request.form['password'])
        role     = request.form['role']

        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (name, email, password, role)
            )
            mysql.connection.commit()

            # If registering as technician, add to technicians table
            if role == 'technician':
                specialization = request.form.get('specialization', 'General')
                phone          = request.form.get('phone', '0000000000')
                user_id        = cur.lastrowid
                cur.execute(
                    "INSERT INTO technicians (user_id, specialization, phone) VALUES (%s, %s, %s)",
                    (user_id, specialization, phone)
                )
                mysql.connection.commit()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash('Email already exists or error occurred.', 'danger')
        finally:
            cur.close()

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# ─────────────────────────────────────────
# ADMIN ROUTES
# ─────────────────────────────────────────

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) AS total FROM labs")
    total_labs = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS total FROM equipments")
    total_equipment = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS total FROM equipments WHERE status = 'damaged'")
    damaged = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS total FROM maintenance_requests WHERE status = 'pending'")
    pending_repairs = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS total FROM maintenance_requests WHERE status = 'completed'")
    completed_repairs = cur.fetchone()['total']

    cur.execute("""
        SELECT c.complaint_id, u.name AS student_name, e.name AS equipment_name,
               c.status, c.created_at
        FROM complaints c
        JOIN users u ON c.student_id = u.user_id
        JOIN equipments e ON c.equipment_id = e.equipment_id
        ORDER BY c.created_at DESC LIMIT 5
    """)
    recent_complaints = cur.fetchall()
    cur.close()

    return render_template('admin/dashboard.html',
        total_labs=total_labs,
        total_equipment=total_equipment,
        damaged=damaged,
        pending_repairs=pending_repairs,
        completed_repairs=completed_repairs,
        recent_complaints=recent_complaints
    )

# ── Labs ──

@app.route('/admin/labs')
@login_required
@role_required('admin')
def admin_labs():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM labs")
    labs = cur.fetchall()
    cur.close()
    return render_template('admin/labs.html', labs=labs)

@app.route('/admin/labs/add', methods=['POST'])
@login_required
@role_required('admin')
def add_lab():
    lab_name = request.form['lab_name']
    location = request.form['location']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO labs (lab_name, location) VALUES (%s, %s)", (lab_name, location))
    mysql.connection.commit()
    cur.close()
    flash('Lab added successfully.', 'success')
    return redirect(url_for('admin_labs'))

@app.route('/admin/labs/edit/<int:lab_id>', methods=['POST'])
@login_required
@role_required('admin')
def edit_lab(lab_id):
    lab_name = request.form['lab_name']
    location = request.form['location']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE labs SET lab_name=%s, location=%s WHERE lab_id=%s", (lab_name, location, lab_id))
    mysql.connection.commit()
    cur.close()
    flash('Lab updated successfully.', 'success')
    return redirect(url_for('admin_labs'))

@app.route('/admin/labs/delete/<int:lab_id>')
@login_required
@role_required('admin')
def delete_lab(lab_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM labs WHERE lab_id = %s", (lab_id,))
    mysql.connection.commit()
    cur.close()
    flash('Lab deleted.', 'success')
    return redirect(url_for('admin_labs'))

# ── Equipment ──

@app.route('/admin/equipment')
@login_required
@role_required('admin')
def admin_equipment():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT e.*, l.lab_name FROM equipments e
        JOIN labs l ON e.lab_id = l.lab_id
        ORDER BY e.equipment_id DESC
    """)
    equipments = cur.fetchall()
    cur.execute("SELECT * FROM labs")
    labs = cur.fetchall()
    cur.close()
    return render_template('admin/equipment.html', equipments=equipments, labs=labs)

@app.route('/admin/equipment/add', methods=['POST'])
@login_required
@role_required('admin')
def add_equipment():
    lab_id = request.form['lab_id']
    name   = request.form['name']
    etype  = request.form['type']
    status = request.form['status']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO equipments (lab_id, name, type, status) VALUES (%s, %s, %s, %s)",
                (lab_id, name, etype, status))
    mysql.connection.commit()
    cur.close()
    flash('Equipment added.', 'success')
    return redirect(url_for('admin_equipment'))

@app.route('/admin/equipment/edit/<int:equipment_id>', methods=['POST'])
@login_required
@role_required('admin')
def edit_equipment(equipment_id):
    lab_id = request.form['lab_id']
    name   = request.form['name']
    etype  = request.form['type']
    status = request.form['status']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE equipments SET lab_id=%s, name=%s, type=%s, status=%s WHERE equipment_id=%s",
                (lab_id, name, etype, status, equipment_id))
    mysql.connection.commit()
    cur.close()
    flash('Equipment updated.', 'success')
    return redirect(url_for('admin_equipment'))

@app.route('/admin/equipment/delete/<int:equipment_id>')
@login_required
@role_required('admin')
def delete_equipment(equipment_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM equipments WHERE equipment_id = %s", (equipment_id,))
    mysql.connection.commit()
    cur.close()
    flash('Equipment deleted.', 'success')
    return redirect(url_for('admin_equipment'))

# ── Complaints ──

@app.route('/admin/complaints')
@login_required
@role_required('admin')
def admin_complaints():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.*, u.name AS student_name, e.name AS equipment_name
        FROM complaints c
        JOIN users u ON c.student_id = u.user_id
        JOIN equipments e ON c.equipment_id = e.equipment_id
        ORDER BY c.created_at DESC
    """)
    complaints = cur.fetchall()
    cur.execute("SELECT t.technician_id, u.name FROM technicians t JOIN users u ON t.user_id = u.user_id")
    technicians = cur.fetchall()
    cur.close()
    return render_template('admin/complaints.html', complaints=complaints, technicians=technicians)

@app.route('/admin/complaints/assign/<int:complaint_id>', methods=['POST'])
@login_required
@role_required('admin')
def assign_complaint(complaint_id):
    technician_id = request.form['technician_id']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE complaints SET status='assigned' WHERE complaint_id=%s", (complaint_id,))
    cur.execute("""
        INSERT INTO maintenance_requests (complaint_id, technician_id, status)
        VALUES (%s, %s, 'pending')
    """, (complaint_id, technician_id))
    mysql.connection.commit()
    cur.close()
    flash('Complaint assigned to technician.', 'success')
    return redirect(url_for('admin_complaints'))

# ── Technicians ──

@app.route('/admin/technicians')
@login_required
@role_required('admin')
def admin_technicians():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT t.*, u.name, u.email FROM technicians t
        JOIN users u ON t.user_id = u.user_id
    """)
    technicians = cur.fetchall()
    cur.close()
    return render_template('admin/technicians.html', technicians=technicians)

@app.route('/admin/technicians/delete/<int:technician_id>')
@login_required
@role_required('admin')
def delete_technician(technician_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id FROM technicians WHERE technician_id=%s", (technician_id,))
    row = cur.fetchone()
    cur.execute("DELETE FROM technicians WHERE technician_id=%s", (technician_id,))
    cur.execute("DELETE FROM users WHERE user_id=%s", (row['user_id'],))
    mysql.connection.commit()
    cur.close()
    flash('Technician removed.', 'success')
    return redirect(url_for('admin_technicians'))

# ── Maintenance ──

@app.route('/admin/maintenance')
@login_required
@role_required('admin')
def admin_maintenance():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT mr.*, u.name AS technician_name, e.name AS equipment_name,
               c.description, c.created_at AS complaint_date
        FROM maintenance_requests mr
        JOIN technicians t ON mr.technician_id = t.technician_id
        JOIN users u ON t.user_id = u.user_id
        JOIN complaints c ON mr.complaint_id = c.complaint_id
        JOIN equipments e ON c.equipment_id = e.equipment_id
        ORDER BY mr.assigned_at DESC
    """)
    requests = cur.fetchall()
    cur.close()
    return render_template('admin/maintenance.html', requests=requests)

# ─────────────────────────────────────────
# STUDENT ROUTES
# ─────────────────────────────────────────

@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM complaints WHERE student_id=%s", (session['user_id'],))
    total = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM complaints WHERE student_id=%s AND status='open'", (session['user_id'],))
    open_count = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM complaints WHERE student_id=%s AND status='resolved'", (session['user_id'],))
    resolved = cur.fetchone()['total']
    cur.close()
    return render_template('student/dashboard.html',
        total=total, open_count=open_count, resolved=resolved)

@app.route('/student/report', methods=['GET', 'POST'])
@login_required
@role_required('student')
def report_issue():
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        equipment_id = request.form['equipment_id']
        description  = request.form['description']
        cur.execute(
            "INSERT INTO complaints (student_id, equipment_id, description) VALUES (%s, %s, %s)",
            (session['user_id'], equipment_id, description)
        )
        mysql.connection.commit()
        cur.close()
        flash('Issue reported successfully.', 'success')
        return redirect(url_for('my_complaints'))

    cur.execute("""
        SELECT e.equipment_id, e.name, e.type, l.lab_name
        FROM equipments e JOIN labs l ON e.lab_id = l.lab_id
    """)
    equipments = cur.fetchall()
    cur.close()
    return render_template('student/report_issue.html', equipments=equipments)

@app.route('/student/complaints')
@login_required
@role_required('student')
def my_complaints():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.*, e.name AS equipment_name, l.lab_name
        FROM complaints c
        JOIN equipments e ON c.equipment_id = e.equipment_id
        JOIN labs l ON e.lab_id = l.lab_id
        WHERE c.student_id = %s
        ORDER BY c.created_at DESC
    """, (session['user_id'],))
    complaints = cur.fetchall()
    cur.close()
    return render_template('student/my_complaints.html', complaints=complaints)

# ─────────────────────────────────────────
# TECHNICIAN ROUTES
# ─────────────────────────────────────────

@app.route('/technician/dashboard')
@login_required
@role_required('technician')
def technician_dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT technician_id FROM technicians WHERE user_id=%s", (session['user_id'],))
    tech = cur.fetchone()
    tech_id = tech['technician_id']

    cur.execute("SELECT COUNT(*) AS total FROM maintenance_requests WHERE technician_id=%s", (tech_id,))
    total = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM maintenance_requests WHERE technician_id=%s AND status='pending'", (tech_id,))
    pending = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM maintenance_requests WHERE technician_id=%s AND status='completed'", (tech_id,))
    completed = cur.fetchone()['total']
    cur.close()

    return render_template('technician/dashboard.html',
        total=total, pending=pending, completed=completed)

@app.route('/technician/tasks')
@login_required
@role_required('technician')
def my_tasks():
    cur = mysql.connection.cursor()
    cur.execute("SELECT technician_id FROM technicians WHERE user_id=%s", (session['user_id'],))
    tech = cur.fetchone()

    cur.execute("""
        SELECT mr.*, e.name AS equipment_name, c.description, c.created_at AS complaint_date,
               l.lab_name, u.name AS student_name
        FROM maintenance_requests mr
        JOIN complaints c ON mr.complaint_id = c.complaint_id
        JOIN equipments e ON c.equipment_id = e.equipment_id
        JOIN labs l ON e.lab_id = l.lab_id
        JOIN users u ON c.student_id = u.user_id
        WHERE mr.technician_id = %s
        ORDER BY mr.assigned_at DESC
    """, (tech['technician_id'],))
    tasks = cur.fetchall()
    cur.close()
    return render_template('technician/my_tasks.html', tasks=tasks)

@app.route('/technician/update/<int:request_id>', methods=['GET', 'POST'])
@login_required
@role_required('technician')
def update_repair(request_id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        status  = request.form['status']
        remarks = request.form['remarks']
        cur.execute("UPDATE maintenance_requests SET status=%s, remarks=%s WHERE request_id=%s",
                    (status, remarks, request_id))

        if status == 'completed':
            cur.execute("""
                UPDATE complaints SET status='resolved'
                WHERE complaint_id = (
                    SELECT complaint_id FROM maintenance_requests WHERE request_id=%s
                )
            """, (request_id,))

        mysql.connection.commit()
        cur.close()
        flash('Repair status updated.', 'success')
        return redirect(url_for('my_tasks'))

    cur.execute("""
        SELECT mr.*, e.name AS equipment_name, c.description, l.lab_name
        FROM maintenance_requests mr
        JOIN complaints c ON mr.complaint_id = c.complaint_id
        JOIN equipments e ON c.equipment_id = e.equipment_id
        JOIN labs l ON e.lab_id = l.lab_id
        WHERE mr.request_id = %s
    """, (request_id,))
    task = cur.fetchone()
    cur.close()
    return render_template('technician/update_repair.html', task=task)

# ─────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True)