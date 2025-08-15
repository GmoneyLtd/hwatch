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
            taskDropdownMenu.addEventListener('click', (event) => {
                if (event.target.name === 'task') {
                    const selectedTask = event.target.value;
                    document.getElementById('chart-task').value = selectedTask;
                    taskDropdownToggle.textContent = selectedTask;
                    taskDropdownMenu.style.display = 'none';
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
        const deviceDropdown = document.getElementById('deviceDropdown');
        if (deviceDropdown) {
            // 移除已有的事件监听器（防止重复绑定）
            deviceDropdown.removeEventListener('change', deviceChangeHandler);
            deviceDropdown.addEventListener('change', deviceChangeHandler);
        }
    }
    
    // 定义事件处理函数，避免重复绑定
    function taskSelectHandler() {
        // 切换任务时清除设备选择状态
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
                const div = document.createElement('div');
                div.className = 'dropdown-item';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.name = 'devices';
                checkbox.value = device;
                checkbox.id = `device-${device}`;
                
                // 保持选中状态 - 检查之前选中的设备或新数据中的选中设备
                if (data.selected_devices && data.selected_devices.includes(device)) {
                    checkbox.checked = true;
                } else if (currentlyCheckedDevices.has(device)) {
                    checkbox.checked = true;
                }
                
                const label = document.createElement('label');
                label.htmlFor = `device-${device}`;
                label.textContent = device;
                
                div.appendChild(checkbox);
                div.appendChild(label);
                dropdownMenu.appendChild(div);

                // 添加事件监听器（使用命名函数避免重复绑定）
                checkbox.removeEventListener('change', deviceCheckboxChangeHandler);
                checkbox.addEventListener('change', deviceCheckboxChangeHandler);
                
                // 防止下拉菜单在点击复选框或标签时关闭
                checkbox.removeEventListener('click', preventDropdownCloseHandler);
                checkbox.addEventListener('click', preventDropdownCloseHandler);
                
                label.removeEventListener('click', preventDropdownCloseHandler);
                label.addEventListener('click', preventDropdownCloseHandler);
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
    
    // 定义事件处理函数，避免重复绑定
    function deviceCheckboxChangeHandler(event) {
        updateDeviceCount();
        loadChartData(); // 设备选择改变时加载图表数据
    }
    
    function preventDropdownCloseHandler(event) {
        event.stopPropagation();
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