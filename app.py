
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
import subprocess
import psutil
import re
import os
import uuid
import time
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "vm_nexus_secret_key_change_later"

DATABASE = "auth.db"
def init_db():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Create a default Admin account
    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, role)
        VALUES (?, ?, ?)
    """, (
        "admin",
        generate_password_hash("Admin@12345"),
        "Admin"
    ))

    # Create a default normal User account
    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, role)
        VALUES (?, ?, ?)
    """, (
        "user",
        generate_password_hash("User@12345"),
        "User"
    ))
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        action TEXT NOT NULL,
        vm_name TEXT,
        details TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")

    connection.commit()
    connection.close()
def log_activity(username, action, vm_name="", details=""):
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO activity_logs
        (username, action, vm_name, details)
        VALUES (?, ?, ?, ?)
    """, (username, action, vm_name, details))

    connection.commit()
    connection.close()

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )

        user = cursor.fetchone()
        connection.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        error = "Invalid username or password."

    return render_template("login.html", error=error)
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.before_request
def require_login():

    if request.endpoint in ("login", "static"):
        return None

    if "user_id" not in session:

        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "error": "Please log in first."
            }), 401

        return redirect(url_for("login"))

from functools import wraps

def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        if session.get("role") != "Admin":
            return jsonify({
                "success": False,
                "error": "Admin access required."
            }), 403

        return function(*args, **kwargs)

    return wrapper
# VirtualBox installation location
VBOX = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"


# Function to execute VirtualBox commands
def run_vbox_command(arguments):

    if not os.path.isfile(VBOX):
        raise FileNotFoundError("VirtualBox executable not found.")

    result = subprocess.run(
        [VBOX] + arguments,
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "VirtualBox command failed.")

    return result.stdout


# Get all registered virtual machines
def get_virtual_machines():

    all_vms = run_vbox_command(["list", "vms"])
    running_vms = run_vbox_command(["list", "runningvms"])

    running_ids = set(re.findall(
        r"\{([a-fA-F0-9-]+)\}", running_vms
    ))

    machines = []

    for line in all_vms.splitlines():

        match = re.match(r'"(.*)"\s+\{([a-fA-F0-9-]+)\}', line)

        if match:
            name = match.group(1)
            vm_id = match.group(2)

            machines.append({
                "name": name,
                "id": vm_id,
                "status": (
                    "Running" if vm_id in running_ids else "Stopped"
                )
            })

    return machines


# Main dashboard route
@app.route("/")
def home():

    return render_template(
        "index.html",
        username=session.get("username"),
        role=session.get("role")
    )

@app.route("/create-vm")
def create_vm_page():

    if session.get("role") != "Admin":
        return "Admin access required.", 403

    return render_template("create_vm.html")

@app.route("/api/activity-logs")
def get_activity_logs():

    if session.get("role") != "Admin":
        return jsonify({
            "success": False,
            "error": "Admin access required."
        }), 403

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM activity_logs
        ORDER BY id DESC
        LIMIT 100
    """)

    logs = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return jsonify({
        "success": True,
        "logs": logs
    })

# API to retrieve all virtual machines
@app.route("/api/vms")
def list_vms():

    try:
        machines = get_virtual_machines()

        return jsonify({
            "success": True,
            "total": len(machines),
            "vms": machines
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# API to monitor host resources
@app.route("/api/metrics")
def metrics():

    return jsonify({
        "cpu": psutil.cpu_percent(interval=0.3),
        "ram": psutil.virtual_memory().percent,
        "storage": psutil.disk_usage("C:\\").percent
    })


# API to start a virtual machine

# Helper function to validate VM IDs
def find_vm(vm_id):
    machines = get_virtual_machines()

    for vm in machines:
        if vm["id"].lower() == vm_id.lower():
            return vm

    return None


# START VM
@app.route("/api/vms/<vm_id>/start", methods=["POST"])
def start_vm(vm_id):

    try:
        vm = find_vm(vm_id)

        if not vm:
            return jsonify({
                "success": False,
                "error": "Virtual machine not found."
            }), 404

        if vm["status"] == "Running":
            return jsonify({
                "success": False,
                "error": f"{vm['name']} is already running."
            }), 409

        run_vbox_command([
            "startvm", vm["id"], "--type", "gui"
        ])

        log_activity(
    session["username"],
    "START",
    vm["name"],
    "Virtual machine started successfully."
)

        return jsonify({
            "success": True,
            "message": f"{vm['name']} started successfully."
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 500
    log_activity(
    session["username"],
    "START",
    vm["name"],
    "Virtual machine started."
    )

# STOP VM
@app.route("/api/vms/<vm_id>/stop", methods=["POST"])
def stop_vm(vm_id):

    try:
        vm = find_vm(vm_id)

        if not vm:
            return jsonify({
                "success": False,
                "error": "Virtual machine not found."
            }), 404

        if vm["status"] == "Stopped":
            return jsonify({
                "success": False,
                "error": f"{vm['name']} is already stopped."
            }), 409

        run_vbox_command([
            "controlvm", vm["id"], "acpipowerbutton"
        ])

        log_activity(
    session["username"],
    "STOP",
    vm["name"],
    "Shutdown request sent."
)

        return jsonify({
            "success": True,
            "message": f"Shutdown request sent to {vm['name']}."
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 500
    log_activity(
    session["username"],
    "STOP",
    vm["name"],
    "Shutdown requested."
)

# RESTART VM
@app.route("/api/vms/<vm_id>/restart", methods=["POST"])
def restart_vm(vm_id):
    try:
        vm = find_vm(vm_id)

        if not vm:
            return jsonify({
                "success": False,
                "error": "Virtual machine not found."
            }), 404

        if vm["status"] == "Stopped":
            return jsonify({
                "success": False,
                "error": "Cannot restart a stopped VM."
            }), 409

        # Step 1: Request graceful shutdown
        run_vbox_command([
            "controlvm", vm["id"], "acpipowerbutton"
        ])

        # Step 2: Wait until the VM stops
        timeout = time.monotonic() + 90

        while time.monotonic() < timeout:
            current_vm = find_vm(vm["id"])

            if current_vm and current_vm["status"] == "Stopped":
                break

            time.sleep(2)
        else:
            return jsonify({
                "success": False,
                "error": "VM did not shut down within 90 seconds. Please check the VM manually."
            }), 504

        # Step 3: Start the VM again
        run_vbox_command([
            "startvm", vm["id"], "--type", "gui"
        ])

        return jsonify({
            "success": True,
            "message": f"{vm['name']} restarted successfully."
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 500
    log_activity(
    session["username"],
    "RESTART",
    vm["name"],
    "Virtual machine restarted."
)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

