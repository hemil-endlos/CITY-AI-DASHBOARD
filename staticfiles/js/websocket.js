const wsStatusBadge = document.getElementById("ws-status");
const tableBody = document.querySelector("#detections-table tbody");

function toIST(utcStr) {
    const d = new Date(utcStr);
    return d.toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        day: "2-digit", month: "short", year: "numeric",
        hour: "2-digit", minute: "2-digit", hour12: true
    });
}

function buildRow(d) {
    const tr = document.createElement("tr");
    tr.setAttribute("data-id", d.id);
    tr.className = d.violation_type ? "violation-row" : "";
    const imgSrc = d.image || "https://via.placeholder.com/160x90?text=No+Image";
    const modelLabel = d.model_type === "helmet" ? "Helmet Detection" : "Cart Detection";
    const violationLabel = d.violation_type === "no_helmet"
        ? `<span class="badge bg-danger">NO HELMET</span>`
        : `<span class="text-muted">-</span>`;
    const lat = d.latitude;
    const lng = d.longitude;
    const locationCell = (lat != null && lng != null)
        ? `<a href="https://www.google.com/maps?q=${lat},${lng}" target="_blank">
               📍 ${parseFloat(lat).toFixed(4)}, ${parseFloat(lng).toFixed(4)}
           </a>`
        : `<span class="text-muted">—</span>`;
    tr.innerHTML = `
        <td>
            <a href="${imgSrc}" target="_blank">
                <img src="${imgSrc}" class="thumb-img"
                     onerror="this.onerror=null; this.src='https://via.placeholder.com/160x90?text=No+Image';">
            </a>
        </td>
        <td>${d.name}</td>
        <td>${modelLabel}</td>
        <td>${toIST(d.detected_at)}</td>
        <td>${locationCell}</td>
        <td>${violationLabel}</td>
        <td>
            <span class="badge status-badge ${statusClass(d.status)}">${d.status}</span>
        </td>
        <td>
            <button class="btn btn-sm btn-outline-success me-1"
                    onclick="updateStatus(${d.id}, 'approved')">Approve</button>
            <button class="btn btn-sm btn-outline-danger"
                    onclick="updateStatus(${d.id}, 'rejected')">Reject</button>
        </td>
    `;
    return tr;
}

function statusClass(status) {
    if (status === "approved") return "bg-success";
    if (status === "rejected") return "bg-danger";
    return "bg-warning text-dark";
}

function upsertRow(d) {
    const existing = tableBody.querySelector(`tr[data-id="${d.id}"]`);
    const row = buildRow(d);
    if (existing) {
        tableBody.replaceChild(row, existing);
    } else {
        tableBody.insertBefore(row, tableBody.firstChild);
    }
}

function updateStatus(id, status) {
    fetch(`/api/detections/${id}/status/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ status }),
    })
        .then((resp) => resp.json())
        .then((data) => {
            if (data && data.id) {
                upsertRow(data);
            } else {
                console.error("Failed to update status", data);
            }
        })
        .catch((err) => console.error("Update status error", err));
}

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://${window.location.host}/ws/detections/`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        if (wsStatusBadge) {
            wsStatusBadge.className = "badge bg-success";
            wsStatusBadge.textContent = "WebSocket: connected";
        }
    };

    socket.onclose = () => {
        if (wsStatusBadge) {
            wsStatusBadge.className = "badge bg-danger";
            wsStatusBadge.textContent = "WebSocket: disconnected (retrying...)";
        }
        setTimeout(connectWebSocket, 3000);
    };

    socket.onerror = (err) => {
        console.error("WebSocket error", err);
    };

    socket.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg && msg.detection) {
                upsertRow(msg.detection);
            }
        } catch (e) {
            console.error("WS message parse error", e);
        }
    };
}

connectWebSocket();

