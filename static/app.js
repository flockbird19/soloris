/**
 * GriefOS Client-Side Controller
 * Handles async transitions and UI updates.
 */

async function uploadIdentity() {
    const fileInput = document.getElementById("fileInput");
    if (!fileInput.files[0]) return alert("Please select a file.");

    let formData = new FormData();
    formData.append("file", fileInput.files[0]);

    // Matches the FastAPI endpoint: @app.post("/upload-identity")
    try {
        let res = await fetch("/upload-identity", {
            method: "POST",
            body: formData
        });

        if (res.ok) {
            window.location.reload(); // Refresh to update GlobalContext
        } else {
            console.error("Upload failed");
        }
    } catch (err) {
        console.error("Connection error:", err);
    }
}

async function triggerGmailScan() {
    const scanBtn = document.getElementById("scanBtn");
    if (scanBtn) scanBtn.innerText = "SCANNING...";

    // Matches the FastAPI endpoint: @app.post("/run-scan")
    try {
        let res = await fetch("/run-scan", { method: "POST" });
        if (res.ok) {
            window.location.reload(); // Refresh to show found assets/tasks
        }
    } catch (err) {
        console.error("Scan error:", err);
    } finally {
        if (scanBtn) scanBtn.innerText = "RUN SCAN";
    }
}

// Logic for the Agent Console "Execute" button
async function executeAgentCommand(event) {
    event.preventDefault();
    const input = document.getElementById("agentInput");
    const formData = new FormData();
    formData.append("user_input", input.value);

    // Matches @app.post("/agent-execute")
    let res = await fetch("/agent-execute", {
        method: "POST",
        body: formData
    });

    if (res.redirected) {
        window.location.href = res.url;
    }
}