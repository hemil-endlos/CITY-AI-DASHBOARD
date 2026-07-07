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
    tr.setAttribute("data-model", d.model_type || "cart");
    tr.setAttribute("data-status", d.status || "pending");
    tr.setAttribute("data-violation", d.violation_type ? "1" : "0");
    tr.setAttribute("data-name", (d.name || "").toLowerCase());
    tr.setAttribute("data-loc", (d.latitude != null && d.longitude != null) ? `${d.latitude},${d.longitude}` : "");
    tr.className = "det-row";

    const placeholder = "data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22118%22 height=%2270%22%3E%3Crect width=%22100%25%22 height=%22100%25%22 fill=%22%23eef1f6%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 font-family=%22sans-serif%22 font-size=%2211%22 fill=%22%238c94a8%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22%3ENo Image%3C/text%3E%3C/svg%3E";

    // ─────────────────────────────────────────────────────────────────────────
    // FIX: Image is rendered as plain <img> with NO wrapping <a href="..."> tag.
    // Previously: <a href="${imgSrc}" target="_blank"><img ...></a>
    // That <a> caused the image to open as a full page whenever the row was
    // replaced by upsertRow() (called after every Approve / Reject action),
    // because the freshly-injected <a> had no preventDefault on it yet.
    // Solution: remove <a> entirely. The dashboard's lightbox handles previews.
    // ─────────────────────────────────────────────────────────────────────────
    const imgSrc = d.image || placeholder;

    const modelBadge = d.model_type === "helmet"
        ? `<span class="badge-pill b-helmet">Helmet</span>`
        : `<span class="badge-pill b-cart">Cart</span>`;

    const violationCell = d.violation_type === "no_helmet"
        ? `<span class="badge-pill b-viol">
               <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                   <path d="M10.3 3.3 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.3a2 2 0 0 0-3.4 0Z"/>
                   <path d="M12 9v4M12 17h.01"/>
               </svg>
               No helmet
           </span>`
        : `<span class="dash">—</span>`;

    const locationCell = (d.latitude != null && d.longitude != null)
        ? `<a class="loc-link" href="https://www.google.com/maps?q=${d.latitude},${d.longitude}" target="_blank" rel="noopener">
               <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                   <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/>
                   <circle cx="12" cy="10" r="3"/>
               </svg>
               ${parseFloat(d.latitude).toFixed(4)}, ${parseFloat(d.longitude).toFixed(4)}
           </a>`
        : `<span class="dash">—</span>`;

    const statusBadge = d.status === "approved"
        ? `<span class="status s-approved"><span class="sdot"></span>Approved</span>`
        : d.status === "rejected"
            ? `<span class="status s-rejected"><span class="sdot"></span>Rejected</span>`
            : `<span class="status s-pending"><span class="sdot"></span>Pending</span>`;

    tr.innerHTML = `
        <td>
            <img src="${imgSrc}"
                 class="thumb"
                 alt="${d.name || 'Detection'}"
                 data-full="${imgSrc}"
                 data-meta="${d.name || 'Detection'}"
                 onerror="this.onerror=null; this.src='${placeholder}';">
        </td>
        <td>
            <span class="cell-name">
                <span class="nm">${d.name || '—'}</span>
                <span class="id-chip">#${d.id}</span>
            </span>
        </td>
        <td>${modelBadge}</td>
        <td><span class="ts">${toIST(d.detected_at)}</span></td>
        <td>${locationCell}</td>
        <td>${violationCell}</td>
        <td>${statusBadge}</td>
        <td>
            <div class="actions">
                <button class="btn-act btn-approve" type="button"
                        onclick="event.preventDefault();event.stopPropagation();reviewDetection(${d.id}, 'approved', this, event)">Approve</button>
                <button class="btn-act btn-reject" type="button"
                        onclick="event.preventDefault();event.stopPropagation();reviewDetection(${d.id}, 'rejected', this, event)">Reject</button>
            </div>
        </td>
    `;
    return tr;
}

function upsertRow(d) {
    const existing = tableBody.querySelector(`tr[data-id="${d.id}"]`);
    const row = buildRow(d);
    if (existing) {
        tableBody.replaceChild(row, existing);
    } else {
        tableBody.insertBefore(row, tableBody.firstChild);
        row.classList.add("flash"); // highlight new arrivals
    }
    // Trigger recompute + filter refresh on the dashboard
    if (typeof recompute === "function") recompute();
    if (typeof applyFilters === "function") applyFilters();
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
            wsStatusBadge.textContent = "WebSocket: connected";
        }
    };

    socket.onclose = () => {
        if (wsStatusBadge) {
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