
document.getElementById("create-vm-form")
    .addEventListener("submit", async function(event) {

        event.preventDefault();

        const vmData = {
            name: document.getElementById("vm-name").value,
            os_type: document.getElementById("os-type").value,
            ram: Number(document.getElementById("ram").value),
            cpus: Number(document.getElementById("cpus").value),
            disk: Number(document.getElementById("disk").value)
        };

        const message = document.getElementById("result-message");
        message.textContent = "Creating virtual machine...";

        try {
            const response = await fetch("/api/vms/create", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(vmData)
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || "Creation failed.");
            }

            message.textContent = result.message;

        } catch (error) {
            message.textContent = error.message;
        }
    });
