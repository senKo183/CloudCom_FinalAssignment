document.addEventListener('DOMContentLoaded', function() {
    if (!quizData.results || quizData.results.length === 0) return;

    // Biểu đồ điểm số
    const scoreCtx = document.getElementById('scoreChart').getContext('2d');
    new Chart(scoreCtx, {
        type: 'line',
        data: {
            labels: quizData.results.map(result => result.title),
            datasets: [{
                label: 'Điểm số',
                data: quizData.results.map(result => result.score),
                borderColor: '#2ecc71',
                backgroundColor: 'rgba(46, 204, 113, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Tiến độ học tập',
                    font: {
                        size: 16
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 10
                }
            }
        }
    });

    // Biểu đồ phân phối điểm
    const averageCtx = document.getElementById('averageChart').getContext('2d');
    const scores = quizData.results.map(result => result.score);
    
    const ranges = ['0-2', '2-4', '4-6', '6-8', '8-10'];
    const distribution = [0, 0, 0, 0, 0];
    scores.forEach(score => {
        if (score <= 2) distribution[0]++;
        else if (score <= 4) distribution[1]++;
        else if (score <= 6) distribution[2]++;
        else if (score <= 8) distribution[3]++;
        else distribution[4]++;
    });

    new Chart(averageCtx, {
        type: 'bar',
        data: {
            labels: ranges,
            datasets: [{
                label: 'Số lượng bài kiểm tra',
                data: distribution,
                backgroundColor: [
                    'rgba(231, 76, 60, 0.7)',
                    'rgba(230, 126, 34, 0.7)',
                    'rgba(241, 196, 15, 0.7)',
                    'rgba(46, 204, 113, 0.7)',
                    'rgba(52, 152, 219, 0.7)'
                ],
                borderColor: [
                    '#c0392b',
                    '#d35400',
                    '#f39c12',
                    '#27ae60',
                    '#2980b9'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Phân phối điểm',
                    font: {
                        size: 16
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}); 