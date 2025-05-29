// Replace localhost with your Render backend URL
const API_URL = "https://your-flask-backend.onrender.com";

let imageFile = null;

// Handle file selection
document.getElementById('imageInput').addEventListener('change', function (e) {
  imageFile = e.target.files[0];
});

// Handle form submission
document.getElementById('uploadForm').addEventListener('submit', async function (e) {
  e.preventDefault();

  if (!imageFile) {
    alert("Please select an image file.");
    return;
  }

  try {
    const formData = new FormData();
    formData.append('image', imageFile);

    const response = await fetch(`${API_URL}/upload`, {
      method: 'POST',
      body: formData
    });

    const result = await response.json();
    console.log(result);

    if (response.ok) {
      alert("Image uploaded successfully!");
      document.getElementById('uploadForm').reset();
      imageFile = null;
    } else {
      alert(result.error || "Image upload failed.");
    }
  } catch (error) {
    console.error("Upload error:", error);
    alert("An error occurred during upload.");
  }
});
