const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const faceImageInput = document.getElementById("faceImageInput");
let stream = null;

// Start webcam
navigator.mediaDevices.getUserMedia({ video: true })
    .then(function(s) {
        stream = s;
        video.srcObject = stream;
    })
    .catch(function(err) {
        console.error("Error accessing webcam: ", err);
    });

function captureImage() {
    // Set canvas size exactly same as video preview
    canvas.width = video.width;
    canvas.height = video.height;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert canvas to base64 string
    const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
    faceImageInput.value = dataUrl;

    // Stop webcam stream
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }

    // Hide video element, show frozen canvas
    video.style.display = "none";
    canvas.style.display = "block";

    alert("Face captured! Now complete form and click Register.");
}
