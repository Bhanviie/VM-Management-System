
async function loadDashboard() {

    try {

        const response = await fetch("/api/vms");
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error);
        }

        const machines = data.vms;

        const running = machines.filter(
            vm => vm.status === "Running"
        ).length;

        document.getElementById("total-vms").textContent =
            data.total;

        document.getElementById("running-vms").textContent =
            running;

        document.getElementById("stopped-vms").textContent =
            data.total - running;

        const container = document.getElementById("vm-list");

        if (machines.length === 0) {
            container.textContent = "No virtual machines registered.";
        } else {

            container.innerHTML = machines.map(vm => `
                <div class="vm-card">

                    <div class="vm-top">
                        <div class="vm-name">${escapeHTML(vm.name)}</div>

                        <span class="status ${vm.status}">
                            ${vm.status}
                        </span>
                    </div>

                    <p class="vm-id">ID: ${escapeHTML(vm.id)}</p>
                    <div class="actions">
                        <button class="start-btn"
                            ${vm.status === "Running" ? "disabled" : ""}
                            onclick="controlVM('${vm.id}', 'start')">Start</button>

                        <button class="stop-btn"
                            ${vm.status === "Stopped" ? "disabled" : ""}
                            onclick="controlVM('${vm.id}', 'stop')">Stop</button>

                        <button class="restart-btn"
                            ${vm.status === "Stopped" ? "disabled" : ""}
                            onclick="controlVM('${vm.id}', 'restart')">Restart</button>
                    </div>
                    
                </div>
            `).join("");
        }

    } catch (error) {

        console.error(error);
        showToast("Unable to load virtual machines.");

    }

}


function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[character]);
}


async function controlVM(id, action) {

    if (action === "stop") {
        const confirmed = confirm(
            "Send a graceful shutdown request to this VM?"
        );

        if (!confirmed) return;
    }

    try {

        const response = await fetch(
            `/api/vms/${id}/${action}`,
            { method: "POST" }
        );

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.error || "Operation failed");
        }

        showToast(result.message);

        setTimeout(loadDashboard, 1500);

    } catch (error) {

        showToast(error.message);

    }

}


async function loadMetrics() {

    try {

        const response = await fetch("/api/metrics");
        const data = await response.json();

        document.getElementById("cpu-usage").textContent =
            data.cpu + "%";

        updateResource("cpu", data.cpu);
        updateResource("ram", data.ram);
        updateResource("storage", data.storage);

    } catch (error) {

        console.error("Metrics error:", error);

    }

}


function updateResource(name, value) {

    const percentage = Math.max(0, Math.min(100, value));

    document.getElementById(name + "-label").textContent =
        percentage + "%";

    document.getElementById(name + "-bar").style.width =
        percentage + "%";

}


function showToast(message) {

    const toast = document.getElementById("toast");

    toast.textContent = message;
    toast.style.display = "block";

    setTimeout(() => {
        toast.style.display = "none";
    }, 3500);

}


// Initial dashboard load
loadDashboard();
loadMetrics();

// Refresh information periodically
setInterval(loadDashboard, 10000);
setInterval(loadMetrics, 3000);

async function loadActivityLogs() {
    try {
        const response = await fetch("/api/activity-logs");
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "Unable to load logs.");
        }

        const container = document.getElementById("activity-log-list");

        if (data.logs.length === 0) {
            container.innerHTML =
                '<tr><td colspan="5">No activity recorded yet.</td></tr>';
            return;
        }

        container.innerHTML = data.logs.map(log => `
            <tr>
                <td>${escapeHTML(log.username)}</td>
                <td>${escapeHTML(log.action)}</td>
                <td>${escapeHTML(log.vm_name || "-")}</td>
                <td>${escapeHTML(log.details || "-")}</td>
                <td>${escapeHTML(log.timestamp)}</td>
            </tr>
        `).join("");

    } catch (error) {
        console.error(error);
        showToast(error.message);
    }
}