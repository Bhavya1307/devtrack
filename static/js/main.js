// ─── SIDEBAR TOGGLE ──────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

// Close sidebar when clicking outside on mobile
document.addEventListener('click', function (e) {
    const sidebar = document.getElementById('sidebar');
    const menuToggle = document.querySelector('.menu-toggle');
    if (!sidebar) return;
    if (window.innerWidth <= 768) {
        if (!sidebar.contains(e.target) && menuToggle && !menuToggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    }
});

// ─── MODALS ──────────────────────────────────────────────────
function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('open');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('open');
}

function closeModalOutside(event, id) {
    if (event.target.id === id) closeModal(id);
}

// Close modals with Escape key
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.open').forEach(modal => {
            modal.classList.remove('open');
        });
    }
});

// ─── CONFIRM DELETE ───────────────────────────────────────────
function confirmDelete(formId) {
    if (confirm('Are you sure you want to delete this? This action cannot be undone.')) {
        document.getElementById(formId).submit();
    }
}

// ─── PASSWORD TOGGLE ─────────────────────────────────────────
function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon = btn.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}

// ─── OPEN EDIT PROJECT MODAL ──────────────────────────────────
function openEditProject(id, name, description, status, priority, deadline) {
    document.getElementById('editProjectName').value = name;
    document.getElementById('editProjectDesc').value = description;
    document.getElementById('editProjectStatus').value = status;
    document.getElementById('editProjectPriority').value = priority;
    document.getElementById('editProjectDeadline').value = deadline;
    document.getElementById('editProjectForm').action = `/projects/${id}/edit`;
    openModal('editProjectModal');
}

// ─── OPEN EDIT TASK MODAL ─────────────────────────────────────
function openEditTask(id, title, description, status, priority, deadline) {
    document.getElementById('editTaskTitle').value = title;
    document.getElementById('editTaskDesc').value = description;
    document.getElementById('editTaskStatus').value = status;
    document.getElementById('editTaskPriority').value = priority;
    document.getElementById('editTaskDeadline').value = deadline;
    document.getElementById('editTaskForm').action = `/tasks/${id}/edit`;
    openModal('editTaskModal');
}

// ─── CHANGE TASK STATUS (AJAX) ────────────────────────────────
function changeTaskStatus(taskId, newStatus) {
    fetch(`/tasks/${taskId}/update-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            // Reload page to reflect new kanban position
            window.location.reload();
        }
    })
    .catch(err => console.error('Error:', err));
}

// ─── AUTO DISMISS FLASH MESSAGES ─────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-10px)';
            flash.style.transition = 'all 0.4s ease';
            setTimeout(() => flash.remove(), 400);
        }, 4000);
    });
});

// ─── ACTIVE NAV HIGHLIGHT ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });

    if (path === '/dashboard') {
        document.querySelector('a[href="/dashboard"]')?.classList.add('active');
    } else if (path.startsWith('/projects')) {
        document.querySelector('a[href="/projects"]')?.classList.add('active');
    } else if (path.startsWith('/tasks')) {
        document.querySelector('a[href="/tasks"]')?.classList.add('active');
    }
});