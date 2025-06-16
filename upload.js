document.addEventListener('DOMContentLoaded', function() {
    const optimizeButton = document.getElementById('optimize');
    const resumeInput = document.getElementById('resume');
    const statusDiv = document.getElementById('status');
  
    optimizeButton.addEventListener('click', async function() {
      const resumeFile = resumeInput.files[0];
  
      if (!resumeFile) {
        showError('Please select a resume file');
        return;
      }
  
      if (!resumeFile.name.endsWith('.tex')) {
        showError('Only .tex files are supported');
        return;
      }
  
      try {
        showStatus('Optimizing resume...', 'info');
        // Get the current tab's URL
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
          const jobUrl = tabs[0].url;
  
          const formData = new FormData();
          formData.append('resume', resumeFile);
          formData.append('job_url', jobUrl);
  
          fetch('http://localhost:5000/optimize', {
            method: 'POST',
            body: formData
          })
          .then(async response => {
            if (!response.ok) {
              const errorData = await response.json();
              throw new Error(errorData.error || 'Failed to optimize resume');
            }
            return response.blob();
          })
          .then(pdfBlob => {
            const downloadUrl = URL.createObjectURL(pdfBlob);
            const downloadLink = document.createElement('a');
            downloadLink.href = downloadUrl;
            downloadLink.download = 'optimized_resume.pdf';
            downloadLink.click();
            URL.revokeObjectURL(downloadUrl);
            showStatus('Resume optimized successfully!', 'success');
          })
          .catch(error => {
            showError(error.message);
          });
        });
      } catch (error) {
        showError(error.message);
      }
    });
  
    function showError(message) {
      statusDiv.textContent = message;
      statusDiv.className = 'error';
    }
  
    function showStatus(message, type) {
      statusDiv.textContent = message;
      statusDiv.className = type;
    }
  });