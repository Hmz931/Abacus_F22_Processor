document.getElementById('uploadBtn').addEventListener('click', async () => {
    const fileInput = document.getElementById('fileInput');
    if (!fileInput.files.length) return alert('Veuillez sélectionner un fichier');

    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    
    loading.classList.remove('hidden');
    results.classList.add('hidden');

    try {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Erreur inconnue');

        loading.classList.add('hidden');
        results.classList.remove('hidden');
    } catch (error) {
        loading.classList.add('hidden');
        alert('Erreur: ' + error.message);
    }
});