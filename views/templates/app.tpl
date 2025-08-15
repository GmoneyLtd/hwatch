<!DOCTYPE html>
<html>
<head>
    <title>awatch - Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" type="text/css" href="/static/css/app.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.43.2/ace.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.43.2/ext-language_tools.js"></script>
</head>
<body>
    <div class="app-container">
        <header class="app-header">
            <h1><i class="fas fa-tachometer-alt"></i> awatch - Dashboard</h1>
            <nav class="app-nav">
                <button class="nav-btn active" data-view="dashboard">
                    <i class="fas fa-home"></i>
                    <span>Dashboard</span>
                </button>
                <button class="nav-btn" data-view="config">
                    <i class="fas fa-cog"></i>
                    <span>Config</span>
                </button>
                <button class="nav-btn" data-view="chart">
                    <i class="fas fa-chart-line"></i>
                    <span>Chart</span>
                </button>
            </nav>
        </header>

        <main class="app-main">
            <!-- Dashboard View -->
            <section id="dashboard-view" class="view active">
                <div class="view-content">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th><i class="fas fa-desktop"></i> Device</th>
                                <th><i class="fas fa-tag"></i> Alias</th>
                                <th><i class="fas fa-network-wired"></i> IP</th>
                                <th><i class="fas fa-list"></i> Type</th>
                                <th><i class="fas fa-sync-alt"></i> Frequency</th>
                                <th><i class="fas fa-calendar-alt"></i> Periodic</th>
                                <th><i class="fas fa-toggle-on"></i> Enabled</th>
                                <th><i class="fas fa-cogs"></i> Action</th>
                            </tr>
                        </thead>
                        <tbody id="tasks-table-body">
                            <!-- Tasks will be loaded here -->
                        </tbody>
                    </table>
                </div>
            </section>

            <!-- Config View -->
            <section id="config-view" class="view">
                <div class="view-content">
                    <div id="config-error" class="error-message" style="display: none;"></div>
                    <form id="config-form">
                        <div class="form-group">
                            <div id="config-editor" class="config-editor"></div>
                        </div>
                        <div class="form-actions">
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-save"></i> Save
                            </button>
                        </div>
                    </form>
                </div>
            </section>

            <!-- Chart View -->
            <section id="chart-view" class="view">
                <div class="view-content">
                    <form class="chart-filters" id="chart-form">
                        <div class="filter-group">
                            <label for="chart-start">Start</label>
                            <input type="datetime-local" id="chart-start" name="start">
                        </div>
                        <div class="filter-group">
                            <label for="chart-end">End</label>
                            <input type="datetime-local" id="chart-end" name="end">
                        </div>
                        <div class="filter-group"id="taskDropdown">
                            <label for="chart-task">Task</label>
                            <select id="chart-task" name="task_alias">
                                <option value="">Select a task</option>
                            </select>
                        </div>
                        <div class="dropdown" id="deviceDropdown" style="display: none;">
                            <button type="button" class="dropdown-toggle" id="dropdownToggle">
                                Select devices <span class="device-count" id="deviceCount"></span>
                            </button>
                            <div class="dropdown-menu" id="dropdownMenu">
                                <!-- 设备选项将通过JavaScript动态添加 -->
                            </div>
                        </div>                        
                    </form>
                    
                    <div class="chart-container">
                        <canvas id="data-chart"></canvas>
                    </div>
                </div>
            </section>
        </main>
    </div>

    <script src="/static/js/app.js"></script>
</body>
</html>