document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const fileName = document.getElementById('file-name');
    const uploadForm = document.getElementById('upload-form');
    const submitBtn = document.getElementById('submit-btn');

    // Drag and drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        dropArea.classList.add('border-primary');
    }

    function unhighlight() {
        dropArea.classList.remove('border-primary');
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    dropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length) {
            fileInput.files = files;
            updateFileName();
        }
    }

    // File input change handler
    fileInput.addEventListener('change', updateFileName);

    function updateFileName() {
        fileName.textContent = fileInput.files.length 
            ? fileInput.files[0].name 
            : 'Aucun fichier sélectionné';
    }

    // Form submission
    uploadForm.addEventListener('submit', handleSubmit);

    async function handleSubmit(e) {
        e.preventDefault();
        
        if (!fileInput.files.length) {
            showAlert('Veuillez sélectionner un fichier', 'danger');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        try {
            submitBtn.disabled = true;
            showProgressBar();
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erreur lors du traitement');
            }

            monitorProgress();
        } catch (error) {
            submitBtn.disabled = false;
            hideProgressBar();
            showAlert(error.message, 'danger');
        }
    }

    function showProgressBar() {
        document.getElementById('progress-container').style.display = 'block';
    }

    function hideProgressBar() {
        document.getElementById('progress-container').style.display = 'none';
    }

    function showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} mt-3`;
        alertDiv.textContent = message;
        alertDiv.setAttribute('role', 'alert');
        
        const container = document.querySelector('.card-body');
        container.insertBefore(alertDiv, container.firstChild);
        
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }

    function monitorProgress() {
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        const progressPercent = document.getElementById('progress-percent');

        const checkInterval = setInterval(async () => {
            try {
                const response = await fetch('/progress');
                const data = await response.json();

                if (data.error) {
                    clearInterval(checkInterval);
                    throw new Error(data.error);
                }

                if (data.total > 0) {
                    const percent = Math.round((data.current / data.total) * 100);
                    progressBar.style.width = `${percent}%`;
                    progressBar.setAttribute('aria-valuenow', percent);
                    progressPercent.textContent = `${percent}%`;
                }

                progressText.textContent = data.message;

                if (data.completed) {
                    clearInterval(checkInterval);
                    setTimeout(() => {
                        window.location.href = '/results';
                    }, 1500);
                }
            } catch (error) {
                clearInterval(checkInterval);
                submitBtn.disabled = false;
                showAlert(error.message, 'danger');
            }
        }, 1000);
    }
});