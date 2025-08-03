// 🌟 Sidebar Toggle
document.addEventListener("DOMContentLoaded", function() {
    const sidebar = document.getElementById("sidebar");
    const toggleBtn = document.getElementById("sidebar-toggle");
    let manuallyExpanded = false;

    toggleBtn.addEventListener("click", function(e) {
        e.stopPropagation();
        manuallyExpanded = !manuallyExpanded;
        sidebar.classList.toggle("expanded", manuallyExpanded);
    });

    sidebar.addEventListener("mouseleave", function() {
        if (!manuallyExpanded) {
            sidebar.classList.remove("expanded");
        }
    });
});

// 🟢 Dashboard & Wallet Logic
document.addEventListener("DOMContentLoaded", () => {
    let remainingSeconds = window.parkingSeconds || 0;
    let timerInterval;

    // Show payment success message if paymentSummary exists
    const successMessage = document.getElementById("payment-success-message");
    if (successMessage && window.paymentSummary) {
        successMessage.textContent = window.paymentSummary;
        successMessage.style.display = "block";
    }

    function formatTime(sec) {
        const hours = String(Math.floor(sec / 3600)).padStart(2, '0');
        const minutes = String(Math.floor((sec % 3600) / 60)).padStart(2, '0');
        const seconds = String(sec % 60).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    }

    function updateTimer() {
        const timerEl = document.getElementById("parking-timer");
        if (timerEl) {
            if (remainingSeconds > 0) {
                timerEl.textContent = formatTime(remainingSeconds);
                remainingSeconds--;
            } else {
                timerEl.textContent = "00:00:00";
                clearInterval(timerInterval);
            }
        }
    }

    // Start timer if parkingSeconds is positive
    if (remainingSeconds > 0) {
        timerInterval = setInterval(updateTimer, 1000);
    }

    // ---------------- Dashboard Form ----------------
    const dashboardForm = document.getElementById("payment-form");
    const dashScanBtn = document.getElementById("face-scan-btn");
    const dashFaceBlock = document.getElementById("face-scan-block");
    const dashVideo = document.getElementById("video");
    const dashCanvas = document.getElementById("canvas");
    const dashStatusText = document.getElementById("status-text");

    if (dashScanBtn && dashboardForm && dashFaceBlock && dashVideo && dashCanvas && dashStatusText) {
        dashScanBtn.addEventListener("click", () => {
            dashFaceBlock.style.display = "block";
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(stream => {
                    dashVideo.srcObject = stream;
                    dashStatusText.textContent = "Scanning face...";
                })
                .catch(err => {
                    alert("Error accessing camera: " + err);
                });

            dashVideo.addEventListener("playing", () => {
                setTimeout(() => {
                    dashCanvas.width = dashVideo.videoWidth;
                    dashCanvas.height = dashVideo.videoHeight;
                    const context = dashCanvas.getContext("2d");
                    context.drawImage(dashVideo, 0, 0, dashCanvas.width, dashCanvas.height);

                    const imageData = dashCanvas.toDataURL("image/png");
                    dashStatusText.textContent = "Verifying face...";

                    fetch("/face_verify", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ image: imageData }),
                    })
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === "success") {
                                dashStatusText.textContent = "Face matched! Making payment...";
                                setTimeout(() => {
                                    dashboardForm.submit();
                                }, 500);
                            } else {
                                dashStatusText.textContent = "Face not recognized. Please try again.";
                            }
                        })
                        .catch(err => {
                            dashStatusText.textContent = "Error during verification.";
                            console.error(err);
                        });
                }, 2000);
            }, { once: true });
        });
    }

    // ---------------- Wallet Form ----------------
    const walletForm = document.getElementById("wallet-form");
    const walletScanBtn = document.getElementById("reload-scan-btn");
    const walletFaceBlock = document.getElementById("face-scan-block");
    const walletVideo = document.getElementById("video");
    const walletCanvas = document.getElementById("canvas");
    const walletStatusText = document.getElementById("status-text");

    if (walletScanBtn && walletForm && walletFaceBlock && walletVideo && walletCanvas && walletStatusText) {
        walletScanBtn.addEventListener("click", () => {
            walletFaceBlock.style.display = "block";
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(stream => {
                    walletVideo.srcObject = stream;
                    walletStatusText.textContent = "Scanning face...";
                })
                .catch(err => {
                    alert("Error accessing camera: " + err);
                });

            walletVideo.addEventListener("playing", () => {
                setTimeout(() => {
                    walletCanvas.width = walletVideo.videoWidth;
                    walletCanvas.height = walletVideo.videoHeight;
                    const context = walletCanvas.getContext("2d");
                    context.drawImage(walletVideo, 0, 0, walletCanvas.width, walletCanvas.height);

                    const imageData = walletCanvas.toDataURL("image/png");
                    walletStatusText.textContent = "Verifying face...";

                    fetch("/face_verify", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ image: imageData }),
                    })
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === "success") {
                                walletStatusText.textContent = "Face matched! Reloading wallet...";
                                setTimeout(() => {
                                    walletForm.submit();
                                }, 500);
                            } else {
                                walletStatusText.textContent = "Face not recognized. Please try again.";
                            }
                        })
                        .catch(err => {
                            walletStatusText.textContent = "Error during verification.";
                            console.error(err);
                        });
                }, 2000);
            }, { once: true });
        });
    }

    // ---------------- Quick Reload Buttons ----------------
    const quickBtns = document.querySelectorAll(".quick-btn");
    quickBtns.forEach(btn => {
    btn.addEventListener("click", () => {
        const amount = btn.getAttribute("data-amount");
        document.getElementById("amount").value = amount;
        });
    });
});

// ✏️ Account Page Edit
document.addEventListener("DOMContentLoaded", function() {
    const editBtn = document.getElementById("edit-btn");
    const saveBtn = document.getElementById("save-btn");
    const usernameInput = document.getElementById("username");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");

    if (editBtn && saveBtn) {
        editBtn.addEventListener("click", function() {
            usernameInput.removeAttribute("readonly");
            emailInput.removeAttribute("readonly");
            passwordInput.removeAttribute("readonly");
            saveBtn.removeAttribute("disabled");
            editBtn.setAttribute("disabled", "true");
        });
    }
});
