<!DOCTYPE html>
<html>
<head>
    <title>Hwatch - Play</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/svg+xml" href="/static/img/hwatch.svg">
    <link rel="stylesheet" type="text/css" href="/static/css/app.css">
    <!-- <script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.4.3/echarts.min.js"></script> -->
    <!-- <script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.43.2/ace.js"></script> -->
    <!-- <script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.43.2/ext-language_tools.js"></script> -->
</head>
<body>
    <div class="app-container">
        <header class="app-header">
            <h1><span class="material-symbols-outlined">speed</span> Hwatch - Dashboard</h1>
            <nav class="app-nav">
                <button class="nav-btn active" data-view="dashboard">
                    <span class="material-symbols-outlined">home</span>
                    <span>Dashboard</span>
                </button>
                <button class="nav-btn" data-view="config">
                    <span class="material-symbols-outlined">settings</span>
                    <span>Config</span>
                </button>
                <button class="nav-btn" data-view="chart">
                    <span class="material-symbols-outlined">show_chart</span>
                    <span>Chart</span>
                </button>
                <button class="nav-btn" data-view="outfile">
                    <span class="material-symbols-outlined">description</span>
                    <span>Outfile</span>
                </button>
            </nav>
        </header>

        <div id="general-error-message" class="error-message" style="display: none;"></div>

        <main class="app-main">
            <!-- Dashboard View -->
            <section id="dashboard-view" class="view active">
                <div class="view-content">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th><div><span class="material-symbols-outlined">desktop_windows</span> Device</div></th>
                                <th><div><span class="material-symbols-outlined">label</span> Alias</div></th>
                                <th><div><span class="material-symbols-outlined">hub</span> IP</div></th>
                                <th><div><span class="material-symbols-outlined">list</span> Type</div></th>
                                <th><div><span class="material-symbols-outlined">sync</span> Frequency</div></th>
                                <th><div><span class="material-symbols-outlined">event</span> Mode</div></th>
                                <th><div><span class="material-symbols-outlined">storage</span> Storage</div></th>
                                <th><div><span class="material-symbols-outlined">toggle_on</span> Enabled</div></th>
                                <th><div><span class="material-symbols-outlined">tune</span> Action</div></th>
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
                            <button type="submit" class="btn btn-success">
                                <span class="material-symbols-outlined">save</span> Save
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
                        <div class="filter-group">
                            <label for="taskDropdown">Task</label>
                            <div class="dropdown" id="taskDropdown">
                                <button type="button" class="dropdown-toggle" id="taskDropdownToggle">
                                    Select a task
                                </button>
                                <div class="dropdown-menu" id="taskDropdownMenu">
                                    <!-- Task options will be loaded here -->
                                </div>
                            </div>
                            <input type="hidden" id="chart-task" name="task_alias" value="">
                        </div>
                        <div class="filter-group">
                            <label for="deviceDropdown">Devices</label>
                            <div class="dropdown" id="deviceDropdown">
                                <button type="button" class="dropdown-toggle" id="dropdownToggle">
                                    Select devices <span class="device-count" id="deviceCount"></span>
                                </button>
                                <div class="dropdown-menu" id="dropdownMenu">
                                    <!-- 设备选项将通过JavaScript动态添加 -->
                                </div>
                            </div>
                        </div>
                    </form>
                    
                    <div class="chart-container">
                        <div id="data-chart" style="width: 100%; height: 550px;"></div>
                        <!-- 图表工具箱将通过ECharts配置自动添加 -->
                    </div>
                </div>
            </section>

            <!-- Outfile View -->
            <section id="outfile-view" class="view">
                <div class="view-content">
                    <h3>Outfile Files</h3>
                    <div id="outfile-list">
                        <!-- File list will be loaded here -->
                    </div>
                </div>
            </section>
        </main>
    </div>

    <script src="/static/js/app.js"></script>
    <script src="/static/js/ace.js"></script>
    <script src="/static/js/ext-language_tools.js"></script>
    <script src="/static/js/echarts.min.js"></script>
</body>
</html>