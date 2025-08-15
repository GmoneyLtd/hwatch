document.addEventListener('DOMContentLoaded', function () {
    const navButtons = document.querySelectorAll('.nav-btn');
    const views = document.querySelectorAll('.view');
    const tasksTableBody = document.getElementById('tasks-table-body');
    const configEditorElement = document.getElementById('config-editor');
    const configForm = document.getElementById('config-form');
    const chartForm = document.getElementById('chart-form');
    const chartContainer = document.getElementById('data-chart');
    const taskDropdownToggle = document.getElementById('taskDropdownToggle');
    const taskDropdownMenu = document.getElementById('taskDropdownMenu');
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
        // 设置默认时间范围为最近2小时
        setDefaultTimeRange();
        
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
        
        // 初始化时加载数据
        loadChartData();
        
        // 添加事件监听器
        setupChartEventListeners();
    }
    
    // 设置默认时间范围为最近2小时
    function setDefaultTimeRange() {
        const now = new Date();
        const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000);
        
        const startInput = document.getElementById('chart-start');
        const endInput = document.getElementById('chart-end');
        
        // 格式化为datetime-local需要的格式: YYYY-MM-DDTHH:mm
        if (startInput && endInput) {
            startInput.value = twoHoursAgo.toISOString().slice(0, 16);
            endInput.value = now.toISOString().slice(0, 16);
        }
    }
    
    function setupChartEventListeners() {
        // 任务选择改变时触发数据加载
        if (taskDropdownToggle) {
            taskDropdownToggle.addEventListener('click', (event) => {
                event.stopPropagation();
                taskDropdownMenu.style.display = taskDropdownMenu.style.display === 'none' ? 'block' : 'none';
            });
        }

        if (taskDropdownMenu) {
            taskDropdownMenu.addEventListener('change', (event) => {
                if (event.target.name === 'task') {
                    const selectedTask = event.target.value;
                    document.getElementById('chart-task').value = selectedTask;
                    taskDropdownToggle.textContent = selectedTask;
                    taskDropdownMenu.style.display = 'none';

                    // Clear device selection
                    const dropdownMenu = document.getElementById('dropdownMenu');
                    if (dropdownMenu) {
                        const checkboxes = dropdownMenu.querySelectorAll('input[type="checkbox"]');
                        checkboxes.forEach(cb => {
                            cb.checked = false;
                        });
                        updateDeviceCount();
                    }

                    loadChartData();
                }
            });
        }
    
        // 时间选择改变时触发数据加载
        const timeInputs = document.querySelectorAll('#chart-start, #chart-end');
        timeInputs.forEach(input => {
            // 移除已有的事件监听器（防止重复绑定）
            input.removeEventListener('change', timeInputChangeHandler);
            input.addEventListener('change', timeInputChangeHandler);
        });
        
        // 设备选择改变时触发数据加载
        const dropdownMenu = document.getElementById('dropdownMenu');
        if (dropdownMenu) {
            dropdownMenu.addEventListener('change', (event) => {
                if (event.target.name === 'devices') {
                    updateDeviceCount();
                    loadChartData();
                }
            });
            dropdownMenu.addEventListener('click', (event) => {
                event.stopPropagation(); // Prevent dropdown from closing when clicking on checkbox/label
            });
        }
    }
    
    
    
    function timeInputChangeHandler() {
        loadChartData();
    }
    
    function deviceChangeHandler(event) {
        if (event.target.name === 'devices') {
            updateDeviceCount();
            loadChartData();
        }
    }

    // --- Data Loading ---

    async function loadDashboardData() {
        hideErrorMessage();
        try {
            const response = await fetch('/api/tasks');
            const tasks = await response.json();
            renderTasksTable(tasks);
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            displayErrorMessage('Failed to load dashboard data. Please try again.');
        }
    }

    async function loadConfigData() {
        hideErrorMessage();
        try {
            const response = await fetch('/api/config');
            const config = await response.text();
            if (configEditor) {
                configEditor.setValue(config, -1);
            }
        } catch (error) {
            console.error('Error loading config data:', error);
            displayErrorMessage('Failed to load config data. Please try again.');
        }
    }

    async function loadChartData() {
        hideErrorMessage();
        const formData = new FormData(chartForm);
        const params = new URLSearchParams(formData);
        
        // 特殊处理devices参数，使用列表方式传递
        const devices = [];
        const deviceCheckboxes = document.querySelectorAll('input[name="devices"]:checked');
        deviceCheckboxes.forEach(checkbox => {
            devices.push(checkbox.value);
        });
        
        // 构建查询参数
        const urlParams = new URLSearchParams();
        for (const [key, value] of params.entries()) {
            // 跳过devices参数，我们单独处理
            if (key !== 'devices') {
                urlParams.append(key, value);
            }
        }
        
        // 添加devices参数（使用列表方式）
        if (devices.length > 0) {
            urlParams.append('devices', devices.join(','));
        }
        
        try {
            const response = await fetch(`/api/chart?${urlParams.toString()}`);
            const data = await response.json();
            updateChart(data);
            updateChartFilterOptions(data);
        } catch (error) {
            console.error('Error loading chart data:', error);
            displayErrorMessage('Failed to load chart data. Please try again.');
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
        const selectedTask = document.getElementById('chart-task').value;

        // 更新任务选项
        taskDropdownMenu.innerHTML = '';
        if (data.tasks && data.tasks.length > 0) {
            data.tasks.forEach(task => {
                const div = document.createElement('div');
                div.className = 'dropdown-item';
                
                const radio = document.createElement('input');
                radio.type = 'radio';
                radio.name = 'task';
                radio.value = task;
                radio.id = `task-${task}`;
                
                if (task === selectedTask) {
                    radio.checked = true;
                    taskDropdownToggle.textContent = task;
                }
                
                const label = document.createElement('label');
                label.htmlFor = `task-${task}`;
                label.textContent = task;
                
                div.appendChild(radio);
                div.appendChild(label);
                taskDropdownMenu.appendChild(div);
            });
        }

        // 更新任务选项
        taskDropdownMenu.innerHTML = '';
        if (data.tasks && data.tasks.length > 0) {
            data.tasks.forEach(task => {
                const isChecked = (task === selectedTask);
                const item = createDropdownItem('radio', 'task', task, `task-${task}`, task, isChecked);
                if (isChecked) {
                    taskDropdownToggle.textContent = task;
                }
                taskDropdownMenu.appendChild(item);
            });
        }

        // 更新设备选项
        const dropdownMenu = document.getElementById('dropdownMenu');
        const deviceDropdown = document.getElementById('deviceDropdown');
        const deviceCountSpan = document.getElementById('deviceCount');
        
        // 始终显示设备下拉菜单（根据是否有可用设备决定内容）
        deviceDropdown.style.display = 'block';
        if (data.available_devices && data.available_devices.length > 0) {
            // 保存当前选中的设备
            const currentlyCheckedDevices = new Set();
            if (dropdownMenu) {
                const currentCheckboxes = dropdownMenu.querySelectorAll('input[type="checkbox"]');
                currentCheckboxes.forEach(cb => {
                    if (cb.checked) {
                        currentlyCheckedDevices.add(cb.value);
                    }
                });
            }
            
            dropdownMenu.innerHTML = '';
            
            data.available_devices.forEach(device => {
                const isChecked = (data.selected_devices && data.selected_devices.includes(device)) || currentlyCheckedDevices.has(device);
                const item = createDropdownItem('checkbox', 'devices', device, `device-${device}`, device, isChecked);
                dropdownMenu.appendChild(item);
            });
            
            // 更新设备计数
            updateDeviceCount();
        } else {
            // 没有可用设备时显示提示信息
            dropdownMenu.innerHTML = '<div class="dropdown-item">No devices available</div>';
            if (deviceCountSpan) {
                deviceCountSpan.textContent = '(0/0)';
            }
        }
    }
    
    

    function updateDeviceCount() {
        const dropdownMenu = document.getElementById('dropdownMenu');
        if (!dropdownMenu) return;
        
        const checkedCount = dropdownMenu.querySelectorAll('input[type="checkbox"]:checked').length;
        const totalCount = dropdownMenu.querySelectorAll('input[type="checkbox"]').length;
        const deviceCountSpan = document.getElementById('deviceCount');
        if (deviceCountSpan) {
            deviceCountSpan.textContent = `(${checkedCount}/${totalCount})`;
        }
    }


    // --- Event Handlers ---

    function handleNavClick(event) {
        const viewId = event.currentTarget.dataset.view + '-view';
        switchView(viewId);
    }

    async function handleTaskAction(event) {
        if (event.target.matches('[data-action]')) {
            hideErrorMessage();
            const button = event.target;
            const device = button.dataset.device;
            const alias = button.dataset.alias;
            const action = button.dataset.action;
            
            try {
                await fetch(`/api/tasks/${action}/${device}/${alias}`, { method: 'POST' });
                loadDashboardData();
            } catch (error) {
                console.error(`Error ${action}ing task:`, error);
                displayErrorMessage(`Failed to ${action} task. Please try again.`);
            }
        }
    }

    async function handleConfigSave(event) {
        event.preventDefault();
        hideErrorMessage('config-error');
        const content = configEditor.getValue();
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/yaml' },
                body: content
            });
            if (response.ok) {
                displayErrorMessage('Config saved successfully!', 'config-error');
            } else {
                const error = await response.json();
                displayErrorMessage(`Error saving config: ${error.message}`, 'config-error');
            }
        } catch (error) {
            console.error('Error saving config:', error);
            displayErrorMessage('Failed to save config. Please try again.', 'config-error');
        }
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

    // 设备下拉菜单功能
    const dropdownToggle = document.getElementById('dropdownToggle');
    const dropdownMenu = document.getElementById('dropdownMenu');

    if (dropdownToggle) {
        dropdownToggle.addEventListener('click', (event) => {
            event.stopPropagation();
            dropdownMenu.style.display = dropdownMenu.style.display === 'none' ? 'block' : 'none';
        });
    }

    // 点击外部关闭下拉菜单
    document.addEventListener('click', (event) => {
        const deviceDropdown = document.getElementById('deviceDropdown');
        if (deviceDropdown && !deviceDropdown.contains(event.target)) {
            document.getElementById('dropdownMenu').style.display = 'none';
        }

        const taskDropdown = document.getElementById('taskDropdown');
        if (taskDropdown && !taskDropdown.contains(event.target)) {
            taskDropdownMenu.style.display = 'none';
        }
    });

    // 初始视图
    switchView('dashboard-view');
});

function displayErrorMessage(message, elementId = 'general-error-message') {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        // Hide after 5 seconds
        setTimeout(() => {
            errorElement.style.display = 'none';
            errorElement.textContent = '';
        }, 5000);
    }
}

function hideErrorMessage(elementId = 'general-error-message') {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.style.display = 'none';
        errorElement.textContent = '';
    }
}

function createDropdownItem(type, name, value, id, textContent, isChecked) {
    const div = document.createElement('div');
    div.className = 'dropdown-item';
    
    const input = document.createElement('input');
    input.type = type;
    input.name = name;
    input.value = value;
    input.id = id;
    input.checked = isChecked;
    
    const label = document.createElement('label');
    label.htmlFor = id;
    label.textContent = textContent;
    
    div.appendChild(input);
    div.appendChild(label);
    return div;
}