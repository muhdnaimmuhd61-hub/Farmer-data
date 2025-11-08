
<!DOCTYPE html>
<html lang="ha">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ 'Admin Dashboard' if lang == 'en' else 'Dashbod ɗin Admin' }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f0f2f5; padding: 20px; font-family: Arial, sans-serif; }
        .card { padding: 25px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); background: white; }
        .table thead { background-color: #1E3A8A; color: white; }
        .table-hover tbody tr:hover { background-color: #e0f7fa; }
        .btn-download { background-color: #10B981; color: white; font-weight: bold; }
        #searchInput { margin-bottom: 15px; }
        th { cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap">
            <h2>{{ 'Admin Dashboard' if lang == 'en' else 'Dashbod ɗin Admin' }}</h2>
            <p class="mb-0">
                🌐 <a href="/admin?lang=en">English</a> | <a href="/admin?lang=ha">Hausa</a>
            </p>
        </div>

        <div class="d-flex justify-content-between mb-3 flex-wrap gap-2">
            <a href="/download" class="btn btn-download">{{ 'Download CSV' if lang == 'en' else 'Sauke CSV' }}</a>
            <input type="text" id="searchInput" class="form-control flex-grow-1" placeholder="{{ 'Search by Name, Location, or Crop' if lang == 'en' else 'Bincika da Suna, Wuri, ko Amfanin Gona' }}">
        </div>

        <div class="card table-responsive">
            <table class="table table-striped table-hover" id="farmersTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">ID</th>
                        <th onclick="sortTable(1)">{{ 'Name' if lang == 'en' else 'Suna' }}</th>
                        <th onclick="sortTable(2)">{{ 'Location' if lang == 'en' else 'Wuri' }}</th>
                        <th onclick="sortTable(3)">{{ 'Crop' if lang == 'en' else 'Amfanin Gona' }}</th>
                        <th onclick="sortTable(4)">{{ 'Phone' if lang == 'en' else 'Waya' }}</th>
                    </tr>
                </thead>
                <tbody>
                    {% for f in farmers %}
                    <tr>
                        <td>{{ f[0] }}</td>
                        <td>{{ f[1] }}</td>
                        <td>{{ f[2] }}</td>
                        <td>{{ f[3] }}</td>
                        <td>{{ f[4] }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Search/filter functionality
        const searchInput = document.getElementById('searchInput');
        const table = document.getElementById('farmersTable').getElementsByTagName('tbody')[0];

        searchInput.addEventListener('keyup', function() {
            const filter = searchInput.value.toLowerCase();
            const rows = table.getElementsByTagName('tr');
            for (let i = 0; i < rows.length; i++) {
                const cells = rows[i].getElementsByTagName('td');
                let match = false;
                for (let j = 1; j <= 3; j++) { // Name, Location, Crop
                    if (cells[j].innerText.toLowerCase().indexOf(filter) > -1) {
                        match = true;
                        break;
                    }
                }
                rows[i].style.display = match ? '' : 'none';
            }
        });

        // Sort table columns
        function sortTable(n) {
            const table = document.getElementById("farmersTable");
            let switching = true;
            let dir = "asc";
            while (switching) {
                switching = false;
                let rows = table.rows;
                for (let i = 1; i < (rows.length - 1); i++) {
                    let shouldSwitch = false;
                    let x = rows[i].getElementsByTagName("TD")[n];
                    let y = rows[i + 1].getElementsByTagName("TD")[n];
                    if (dir == "asc") {
                        if (x.innerText.toLowerCase() > y.innerText.toLowerCase()) {
                            shouldSwitch = true;
                            break;
                        }
                    } else if (dir == "desc") {
                        if (x.innerText.toLowerCase() < y.innerText.toLowerCase()) {
                            shouldSwitch = true;
                            break;
                        }
                    }
                }
                if (shouldSwitch) {
                    rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                    switching = true;
                } else {
                    if (dir == "asc") { dir = "desc"; switching = true; }
                }
            }
        }
    </script>
</body>
</html>
