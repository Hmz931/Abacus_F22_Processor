document.addEventListener('DOMContentLoaded', function() {
    // Initialize financial ratios
    initFinancialRatios();
    
    // Initialize charts
    initCharts();
    
    // Add print button functionality
    document.getElementById('print-btn').addEventListener('click', function() {
        window.print();
    });

    function initFinancialRatios() {
        const bilanData = extractBilanData();
        
        // Calculate and display ratios
        displayRatio(
            'ratio-liquidite-generale', 
            'progress-liquidite',
            bilanData.actifsCirculants / bilanData.passifsCourants,
            1.5  // Recommended threshold
        );
        
        displayRatio(
            'ratio-liquidite-immediate', 
            'progress-liquidite-immediate',
            (bilanData.liquidites + bilanData.creances) / bilanData.passifsCourants,
            0.8  // Recommended threshold
        );
    }

    function extractBilanData() {
        const bilanData = {
            actifsCirculants: 0,
            liquidites: 0,
            creances: 0,
            passifsCourants: 0,
            immobilisations: 0,
            capitauxPropres: 0
        };

        // This would be replaced with actual data extraction from the page
        // For demo purposes, we're using fixed values
        bilanData.actifsCirculants = 1500000;
        bilanData.liquidites = 500000;
        bilanData.creances = 600000;
        bilanData.passifsCourants = 800000;
        bilanData.immobilisations = 1200000;
        bilanData.capitauxPropres = 1900000;

        return bilanData;
    }

    function displayRatio(ratioElementId, progressElementId, value, recommended) {
        const ratioElement = document.getElementById(ratioElementId);
        const progressElement = document.getElementById(progressElementId);
        
        if (isNaN(value) || !isFinite(value)) {
            ratioElement.textContent = 'N/A';
            progressElement.style.width = '0%';
            return;
        }

        const formattedValue = value.toFixed(2);
        ratioElement.textContent = formattedValue;
        
        // Set progress bar (capped at 100%)
        const progressPercent = Math.min((value / recommended) * 100, 100);
        progressElement.style.width = `${progressPercent}%`;
        
        // Set color based on value
        if (value >= recommended) {
            progressElement.classList.add('bg-success');
            progressElement.classList.remove('bg-warning', 'bg-danger');
        } else if (value >= recommended * 0.7) {
            progressElement.classList.add('bg-warning');
            progressElement.classList.remove('bg-success', 'bg-danger');
        } else {
            progressElement.classList.add('bg-danger');
            progressElement.classList.remove('bg-success', 'bg-warning');
        }
    }

    function initCharts() {
        const bilanData = extractBilanData();
        
        // Bilan Structure Chart
        const bilanCtx = document.getElementById('bilanChart').getContext('2d');
        new Chart(bilanCtx, {
            type: 'bar',
            data: {
                labels: ['Actifs Circulants', 'Liquidités', 'Créances', 'Immobilisations', 'Passifs Courants', 'Capitaux Propres'],
                datasets: [{
                    label: 'Montants (CHF)',
                    data: [
                        bilanData.actifsCirculants,
                        bilanData.liquidites,
                        bilanData.creances,
                        bilanData.immobilisations,
                        bilanData.passifsCourants,
                        bilanData.capitauxPropres
                    ],
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(153, 102, 255, 0.7)',
                        'rgba(255, 159, 64, 0.7)',
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(40, 167, 69, 0.7)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(40, 167, 69, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: getChartOptions('Structure du Bilan')
        });

        // Liquidité Chart
        const liquiditeCtx = document.getElementById('liquiditeChart').getContext('2d');
        new Chart(liquiditeCtx, {
            type: 'doughnut',
            data: {
                labels: ['Liquidités', 'Créances', 'Autres Actifs Courants'],
                datasets: [{
                    data: [
                        bilanData.liquidites,
                        bilanData.creances,
                        bilanData.actifsCirculants - bilanData.liquidites - bilanData.creances
                    ],
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(153, 102, 255, 0.7)',
                        'rgba(54, 162, 235, 0.7)'
                    ],
                    borderWidth: 1
                }]
            },
            options: getChartOptions('Composition des Actifs Courants')
        });
    }

    function getChartOptions(title) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: title,
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.raw.toLocaleString('fr-CH')} CHF`;
                        }
                    }
                },
                legend: {
                    position: 'bottom'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString('fr-CH');
                        }
                    }
                }
            }
        };
    }
});