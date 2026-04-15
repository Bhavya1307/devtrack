from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os

app = Flask(__name__)
import os
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devtrack-secret-key-2024')
import os
database_url = os.environ.get('DATABASE_URL', 'sqlite:///devtrack.db')
# Fix URL format for psycopg3
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
elif database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


# ─────────────────────────── MODELS ───────────────────────────

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    projects = db.relationship('Project', backref='owner', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='Active')       # Active, Completed, On Hold
    priority = db.Column(db.String(50), default='Medium')     # Low, Medium, High
    deadline = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')

    @property
    def total_tasks(self):
        return len(self.tasks)

    @property
    def completed_tasks(self):
        return len([t for t in self.tasks if t.status == 'Done'])

    @property
    def progress(self):
        if self.total_tasks == 0:
            return 0
        return int((self.completed_tasks / self.total_tasks) * 100)

    @property
    def is_overdue(self):
        if self.deadline and self.status != 'Completed':
            return self.deadline < date.today()
        return False


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='To Do')        # To Do, In Progress, Done
    priority = db.Column(db.String(50), default='Medium')     # Low, Medium, High
    deadline = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─────────────────────────── AUTH ROUTES ───────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'error')
            return render_template('register.html')

        hashed_pw = generate_password_hash(password)
        user = User(name=name, email=email, password=hashed_pw)
        db.session.add(user)
        db.session.commit()

        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ─────────────────────────── DASHBOARD ───────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    projects = Project.query.filter_by(user_id=current_user.id).all()
    tasks = Task.query.join(Project).filter(Project.user_id == current_user.id).all()

    stats = {
        'total_projects': len(projects),
        'active_projects': len([p for p in projects if p.status == 'Active']),
        'completed_projects': len([p for p in projects if p.status == 'Completed']),
        'total_tasks': len(tasks),
        'todo_tasks': len([t for t in tasks if t.status == 'To Do']),
        'inprogress_tasks': len([t for t in tasks if t.status == 'In Progress']),
        'done_tasks': len([t for t in tasks if t.status == 'Done']),
        'overdue_projects': len([p for p in projects if p.is_overdue]),
    }

    recent_projects = Project.query.filter_by(
        user_id=current_user.id
    ).order_by(Project.created_at.desc()).limit(5).all()

    recent_tasks = Task.query.join(Project).filter(
        Project.user_id == current_user.id
    ).order_by(Task.created_at.desc()).limit(8).all()

    return render_template('dashboard.html',
                           stats=stats,
                           recent_projects=recent_projects,
                           recent_tasks=recent_tasks)


# ─────────────────────────── PROJECTS ───────────────────────────

@app.route('/projects')
@login_required
def projects():
    status_filter = request.args.get('status', 'All')
    priority_filter = request.args.get('priority', 'All')

    query = Project.query.filter_by(user_id=current_user.id)

    if status_filter != 'All':
        query = query.filter_by(status=status_filter)
    if priority_filter != 'All':
        query = query.filter_by(priority=priority_filter)

    all_projects = query.order_by(Project.created_at.desc()).all()

    return render_template('projects.html',
                           projects=all_projects,
                           status_filter=status_filter,
                           priority_filter=priority_filter)


@app.route('/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'Active')
        priority = request.form.get('priority', 'Medium')
        deadline_str = request.form.get('deadline', '')

        if not name:
            flash('Project name is required.', 'error')
            return redirect(url_for('projects'))

        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        project = Project(
            name=name,
            description=description,
            status=status,
            priority=priority,
            deadline=deadline,
            user_id=current_user.id
        )
        db.session.add(project)
        db.session.commit()
        flash(f'Project "{name}" created successfully!', 'success')
        return redirect(url_for('project_detail', project_id=project.id))

    return redirect(url_for('projects'))


@app.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    tasks = Task.query.filter_by(project_id=project_id).order_by(Task.created_at.desc()).all()
    return render_template('project_detail.html', project=project, tasks=tasks)


@app.route('/projects/<int:project_id>/edit', methods=['POST'])
@login_required
def edit_project(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()

    project.name = request.form.get('name', project.name).strip()
    project.description = request.form.get('description', project.description).strip()
    project.status = request.form.get('status', project.status)
    project.priority = request.form.get('priority', project.priority)

    deadline_str = request.form.get('deadline', '')
    if deadline_str:
        try:
            project.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    else:
        project.deadline = None

    db.session.commit()
    flash('Project updated successfully!', 'success')
    return redirect(url_for('project_detail', project_id=project_id))


@app.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    name = project.name
    db.session.delete(project)
    db.session.commit()
    flash(f'Project "{name}" deleted.', 'success')
    return redirect(url_for('projects'))


# ─────────────────────────── TASKS ───────────────────────────

@app.route('/tasks')
@login_required
def tasks():
    status_filter = request.args.get('status', 'All')
    priority_filter = request.args.get('priority', 'All')

    query = Task.query.join(Project).filter(Project.user_id == current_user.id)

    if status_filter != 'All':
        query = query.filter(Task.status == status_filter)
    if priority_filter != 'All':
        query = query.filter(Task.priority == priority_filter)

    all_tasks = query.order_by(Task.created_at.desc()).all()
    user_projects = Project.query.filter_by(user_id=current_user.id).all()

    return render_template('tasks.html',
                           tasks=all_tasks,
                           projects=user_projects,
                           status_filter=status_filter,
                           priority_filter=priority_filter)


@app.route('/projects/<int:project_id>/tasks/new', methods=['POST'])
@login_required
def new_task(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    status = request.form.get('status', 'To Do')
    priority = request.form.get('priority', 'Medium')
    deadline_str = request.form.get('deadline', '')

    if not title:
        flash('Task title is required.', 'error')
        return redirect(url_for('project_detail', project_id=project_id))

    deadline = None
    if deadline_str:
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    task = Task(
        title=title,
        description=description,
        status=status,
        priority=priority,
        deadline=deadline,
        project_id=project_id
    )
    db.session.add(task)
    db.session.commit()
    flash(f'Task "{title}" added!', 'success')
    return redirect(url_for('project_detail', project_id=project_id))


@app.route('/tasks/<int:task_id>/update-status', methods=['POST'])
@login_required
def update_task_status(task_id):
    task = Task.query.join(Project).filter(
        Task.id == task_id,
        Project.user_id == current_user.id
    ).first_or_404()

    data = request.get_json()
    new_status = data.get('status')
    if new_status in ['To Do', 'In Progress', 'Done']:
        task.status = new_status
        db.session.commit()
        return jsonify({'success': True, 'status': new_status})
    return jsonify({'success': False}), 400


@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.join(Project).filter(
        Task.id == task_id,
        Project.user_id == current_user.id
    ).first_or_404()

    project_id = task.project_id
    title = task.title
    db.session.delete(task)
    db.session.commit()
    flash(f'Task "{title}" deleted.', 'success')

    ref = request.form.get('ref', 'project')
    if ref == 'tasks':
        return redirect(url_for('tasks'))
    return redirect(url_for('project_detail', project_id=project_id))


@app.route('/tasks/<int:task_id>/edit', methods=['POST'])
@login_required
def edit_task(task_id):
    task = Task.query.join(Project).filter(
        Task.id == task_id,
        Project.user_id == current_user.id
    ).first_or_404()

    task.title = request.form.get('title', task.title).strip()
    task.description = request.form.get('description', task.description or '').strip()
    task.status = request.form.get('status', task.status)
    task.priority = request.form.get('priority', task.priority)

    deadline_str = request.form.get('deadline', '')
    if deadline_str:
        try:
            task.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    else:
        task.deadline = None

    db.session.commit()
    flash('Task updated!', 'success')

    ref = request.form.get('ref', 'project')
    if ref == 'tasks':
        return redirect(url_for('tasks'))
    return redirect(url_for('project_detail', project_id=task.project_id))


# ─────────────────────────── API ───────────────────────────

@app.route('/api/chart-data')
@login_required
def chart_data():
    projects = Project.query.filter_by(user_id=current_user.id).all()
    tasks = Task.query.join(Project).filter(Project.user_id == current_user.id).all()

    return jsonify({
        'projects': {
            'Active': len([p for p in projects if p.status == 'Active']),
            'Completed': len([p for p in projects if p.status == 'Completed']),
            'On Hold': len([p for p in projects if p.status == 'On Hold']),
        },
        'tasks': {
            'To Do': len([t for t in tasks if t.status == 'To Do']),
            'In Progress': len([t for t in tasks if t.status == 'In Progress']),
            'Done': len([t for t in tasks if t.status == 'Done']),
        },
        'priority': {
            'Low': len([p for p in projects if p.priority == 'Low']),
            'Medium': len([p for p in projects if p.priority == 'Medium']),
            'High': len([p for p in projects if p.priority == 'High']),
        }
    })



with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=False)