document.addEventListener('DOMContentLoaded', function () {
    const navButtons = document.querySelectorAll('.nav-btn');
    const views = document.querySelectorAll('.view');
    const tasksTableBody = document.getElementById('tasks-table-body');
    const configEditorElement = document.getElementById('config-editor');
    const configForm = document.getElementById('config-form');
    const chartForm = document.getElementById('chart-form');
    const chartContainer = document.getElementById('data-chart');
    let configEditor;
    let dataChart;

    // --- View-specific initialization ---

    function initDashboardView() {
        loadDashboardData();
    }

    function initConfigView() {
        if (!configEditor) {
            configEditor = ace.edit(configEditorElement);
            configEditor.setTheme('ace/theme/github');
            configEditor.session.setMode('ace/mode/yaml');
            configEditor.setOptions({
                showPrintMargin: false,
                highlightActiveLine: true,
                enableBasicAutocompletion: true,
                enableLiveAutocompletion: true,
                wrap: true,
                tabSize: 2,
            });
        }
        loadConfigData();
    }

    function initChartView() {
        if (!dataChart) {
            const ctx = chartContainer.getContext('2d');
            dataChart = new Chart(ctx, {
                type: 'line',
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                tooltipFormat: 'yyyy-MM-dd HH:mm:ss'
                            }
                        },
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        loadChartData();
    }

    // --- Data Loading ---

    async function loadDashboardData() {
        try {
            const response = await fetch('/api/tasks');
            const tasks = await response.json();
            renderTasksTable(tasks);
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        }
    }

    async function loadConfigData() {
        try {
            const response = await fetch('/api/config');
            const config = await response.text();
            if (configEditor) {
                configEditor.setValue(config, -1);
            }
        } catch (error) {
            console.error('Error loading config data:', error);
        }
    }

    async function loadChartData() {
        const formData = new FormData(chartForm);
        const params = new URLSearchParams(formData);
        try {
            const response = await fetch(`/api/chart?${params.toString()}`);
            const data = await response.json();
            updateChart(data);
            updateChartFilterOptions(data);
        } catch (error) {
            console.error('Error loading chart data:', error);
        }
    }
    
    // --- UI Rendering and Updates ---

    function renderTasksTable(tasks) {
        tasksTableBody.innerHTML = '';
        if (!tasks || tasks.length === 0) {
            tasksTableBody.innerHTML = '<tr><td colspan="5">No tasks found.</td></tr>';
            return;
        }
        tasks.forEach(task => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${task[0]}</td>
                <td>${task[1]}</td>
                <td>${task[2] || 'N/A'}</td>
                <td>${task[3]}</td>
                <td>${task[4] || 'N/A'}</td>
                <td>${task[5] || 'N/A'}</td>
                <td>
                    <span class="status-badge ${task[6] ? 'enabled' : 'disabled'}">
                        <i class="fas ${task[6] ? 'fa-check-circle' : 'fa-times-circle'}"></i>
                        ${task[6] ? 'Enabled' : 'Disabled'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm ${task[6] ? 'btn-danger' : 'btn-success'}" data-device="${task[0]}" data-alias="${task[1]}" data-action="${task[6] ? 'disable' : 'enable'}">
                        <i class="fas ${task[6] ? 'fa-stop' : 'fa-play'}"></i>
                        ${task[6] ? 'Disable' : 'Enable'}
                    </button>
                </td>
            `;
            tasksTableBody.appendChild(row);
        });
    }

    function updateChart(data) {
        if (dataChart) {
            dataChart.data.datasets = data.datasets;
            dataChart.update();
        }
    }

    function updateChartFilterOptions(data) {
        const taskSelect = document.getElementById('chart-task');
        const selectedTask = taskSelect.value;
        
        // Update task options
        taskSelect.innerHTML = '<option value="">Select a task</option>';
        data.tasks.forEach(task => {
            const option = document.createElement('option');
            option.value = task;
            option.textContent = task;
            if (task === selectedTask) {
                option.selected = true;
            }
            taskSelect.appendChild(option);
        });

        // Update device options
        const deviceList = document.getElementById('device-list');
        deviceList.innerHTML = '';
        let selectedCount = 0;
        console.log('Available devices:', data.available_devices);
        if (data.available_devices) {
            data.available_devices.forEach(device => {
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.name = 'devices';
                checkbox.value = device;
                checkbox.id = `device-${device}`;
                // Preserve selected state
                const previouslySelected = chartForm.querySelector(`input[type="checkbox"][value="${device}"]:checked`);
                if (previouslySelected) {
                    checkbox.checked = true;
                    selectedCount++;
                }
                
                const label = document.createElement('label');
                label.htmlFor = `device-${device}`;
                label.innerHTML = `<i class="fa-solid ${checkbox.checked ? 'fa-square-check' : 'fa-square'}"></i> ${device}`;

                const div = document.createElement('div');
                div.appendChild(checkbox);
                div.appendChild(label);
                deviceList.appendChild(div);
                console.log('Device added:', device);

                checkbox.addEventListener('change', () => {
                    label.querySelector('i').className = `fa-solid ${checkbox.checked ? 'fa-square-check' : 'fa-square'}`;
                    updateDeviceCount();
                });
            });
        }

        const deviceCountSpan = document.getElementById('deviceCount');
        function updateDeviceCount() {
            selectedCount = chartForm.querySelectorAll('input[type="checkbox"][name="devices"]:checked').length;
            deviceCountSpan.textContent = selectedCount;
        }
        updateDeviceCount(); // Initial count update

        // Close dropdown when clicking outside
        // Close dropdown when clicking outside and trigger data load
        document.addEventListener('click', (event) => {
            const dropdown = document.querySelector('.device-selector'); // Assuming .device-selector is the main container
            if (dropdown && !dropdown.contains(event.target)) {
                dropdownMenu.style.display = 'none';
                loadChartData(); // Trigger data load on close
            }
        });
    }


    // --- Event Handlers ---

    function handleNavClick(event) {
        const viewId = event.currentTarget.dataset.view + '-view';
        switchView(viewId);
    }

    async function handleTaskAction(event) {
        if (event.target.matches('[data-action]')) {
            const button = event.target;
            const device = button.dataset.device;
            const alias = button.dataset.alias;
            const action = button.dataset.action;
            
            try {
                await fetch(`/api/tasks/${action}/${device}/${alias}`, { method: 'POST' });
                loadDashboardData();
            } catch (error) {
                console.error(`Error ${action}ing task:`, error);
            }
        }
    }

    async function handleConfigSave(event) {
        event.preventDefault();
        const content = configEditor.getValue();
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/yaml' },
                body: content
            });
            if (response.ok) {
                alert('Config saved successfully!');
            } else {
                const error = await response.json();
                alert(`Error saving config: ${error.message}`);
            }
        } catch (error) {
            console.error('Error saving config:', error);
        }
    }

    function handleChartFormChange() {
        loadChartData();
    }
    
    // --- View Switching ---

    const viewInitializers = {
        'dashboard-view': initDashboardView,
        'config-view': initConfigView,
        'chart-view': initChartView,
    };

    function switchView(viewId) {
        views.forEach(view => view.classList.remove('active'));
        document.getElementById(viewId).classList.add('active');

        navButtons.forEach(button => button.classList.remove('active'));
        document.querySelector(`[data-view=${viewId.replace('-view', '')}]`).classList.add('active');

        if (viewInitializers[viewId]) {
            viewInitializers[viewId]();
        }
    }

    // --- Initial Setup ---

    navButtons.forEach(button => button.addEventListener('click', handleNavClick));
    tasksTableBody.addEventListener('click', handleTaskAction);
    configForm.addEventListener('submit', handleConfigSave);
    chartForm.addEventListener('change', handleChartFormChange);

    // Device dropdown in chart view
    const dropdownToggle = document.getElementById('dropdownToggle');
    const dropdownMenu = document.getElementById('dropdownMenu');
    const deviceCountSpan = document.getElementById('deviceCount');

    function updateDeviceCount() {
        const checkedCount = chartForm.querySelectorAll('input[type="checkbox"][name="devices"]:checked').length;
        deviceCountSpan.textContent = checkedCount;
    }

    if(dropdownToggle) {
        dropdownToggle.addEventListener('click', (event) => {
            event.stopPropagation(); // Prevent document click from closing immediately
            console.log('Dropdown toggle clicked!');
            console.log('Current display:', dropdownMenu.style.display);
            dropdownMenu.style.display = dropdownMenu.style.display === 'none' ? 'block' : 'none';
            console.log('New display:', dropdownMenu.style.display);
        });
    }

    // Close dropdown when clicking outside and trigger data load
    document.addEventListener('click', (event) => {
        const deviceSelector = document.querySelector('.device-selector');
        if (deviceSelector && !deviceSelector.contains(event.target)) {
            dropdownMenu.style.display = 'none';
            loadChartData(); // Trigger data load on close
        }
    });

    // Add change listener to checkboxes
    chartForm.addEventListener('change', (event) => {
        if (event.target.name === 'devices') {
            updateDeviceCount();
        }
    });

    // Initial view
    switchView('dashboard-view');
    updateDeviceCount(); // Initial count update
});