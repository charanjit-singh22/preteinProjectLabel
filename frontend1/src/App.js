import React, { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState("");
  const [loading, setLoading] = useState(false); // State for loading

  // Handle file selection
  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  // Handle file upload
  const handleUpload = async () => {
    if (!file) {
      alert("Please select a file first.");
      return;
    }

    setLoading(true); // Show loading indicator
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(
        "http://127.0.0.1:5000/upload",
        formData,
        {
          responseType: "blob",
        }
      );
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      setDownloadUrl(url); // Set the download URL for the user
    } catch (error) {
      console.error("Error during file upload:", error);
      alert("Error uploading file. Please try again.");
    } finally {
      setLoading(false); // Hide loading indicator once done
    }
  };

  return (
    <div className="container">
      <h1>Protein Content Calculator</h1>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleUpload} disabled={loading}>
        {loading ? "Processing..." : "Upload File"}
      </button>

      <div className={`loading ${loading ? "active" : ""}`}>
        Processing... Please wait!
      </div>

      {downloadUrl && (
        <div>
          <a href={downloadUrl} download="result.xlsx">
            Download Result
          </a>
        </div>
      )}
    </div>
  );
}

export default App;
