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
            configEditor.setTheme('ace/theme/cloud_editor');
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
            dataChart = echarts.init(chartContainer);
        }

        // 初始化时加载数据
        loadChartData();

        // 添加事件监听器
        setupChartEventListeners();
    }

    function initOutfileView() {
        loadOutfileList();
    }

    // 设置默认时间范围为当前时间前2小时到后1小时（基于当前时区）
    function setDefaultTimeRange() {
        const now = new Date();
        const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000);
        const oneHourLater = new Date(now.getTime() + 1 * 60 * 60 * 1000);

        const startInput = document.getElementById('chart-start');
        const endInput = document.getElementById('chart-end');

        // 格式化为datetime-local需要的格式: YYYY-MM-DDTHH:mm（本地时区）
        if (startInput && endInput) {
            // 使用本地时区时间，而不是UTC时间
            const formatLocalDateTime = (date) => {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                return `${year}-${month}-${day}T${hours}:${minutes}`;
            };

            startInput.value = formatLocalDateTime(twoHoursAgo);
            endInput.value = formatLocalDateTime(oneHourLater);
        }
    }

    function setupChartEventListeners() {
        // 任务选择改变时触发数据加载
        if (taskDropdownMenu) {
            taskDropdownMenu.addEventListener('change', (event) => {
                if (event.target.name === 'task') {
                    const selectedTask = event.target.value;
                    document.getElementById('chart-task').value = selectedTask;
                    taskDropdownToggle.textContent = selectedTask;
                    taskDropdownMenu.classList.remove('show');

                    // Clear label and device selection
                    document.getElementById('chart-label').value = '';
                    document.getElementById('labelDropdownToggle').textContent = 'Select a label';
                    clearDeviceSelection();

                    loadChartData(); // Load labels
                }
            });
        }

        // Label选择改变时触发数据加载
        const labelDropdownMenu = document.getElementById('labelDropdownMenu');
        if (labelDropdownMenu) {
            labelDropdownMenu.addEventListener('change', (event) => {
                if (event.target.name === 'label') {
                    const selectedLabel = event.target.value;
                    document.getElementById('chart-label').value = selectedLabel;
                    document.getElementById('labelDropdownToggle').textContent = selectedLabel;
                    labelDropdownMenu.classList.remove('show');

                    // Clear device selection
                    clearDeviceSelection();
                    loadChartData(); // Load device list
                }
            });
        }

        // 时间选择改变时触发数据加载
        const timeInputs = document.querySelectorAll('#chart-start, #chart-end');
        timeInputs.forEach(input => {
            // 添加事件监听器
            input.addEventListener('change', timeInputChangeHandler);
        });

        // 设备选择改变时触发数据加载
        const dropdownMenu = document.getElementById('dropdownMenu');
        if (dropdownMenu) {
            dropdownMenu.addEventListener('change', (event) => {
                if (event.target.name === 'devices') {
                    updateDeviceCount();
                    loadChartData(); // Load chart data
                }
            });
            dropdownMenu.addEventListener('click', (event) => {
                event.stopPropagation(); // Prevent dropdown from closing when clicking on checkbox/label
            });
        }
    }

    function clearDeviceSelection() {
        const dropdownMenu = document.getElementById('dropdownMenu');
        if (dropdownMenu) {
            const checkboxes = dropdownMenu.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(cb => {
                cb.checked = false;
            });
            updateDeviceCount();
        }
    }



    function timeInputChangeHandler() {
        // 时间变化时，清空任务和设备选择
        clearTaskAndDeviceSelection();
        loadChartData();
    }

    function clearTaskAndDeviceSelection() {
        // 清空任务选择
        document.getElementById('chart-task').value = '';
        taskDropdownToggle.textContent = 'Select a task';

        // 清空label选择
        document.getElementById('chart-label').value = '';
        document.getElementById('labelDropdownToggle').textContent = 'Select a label';

        // 清空设备选择
        clearDeviceSelection();
    }

    // --- Data Loading ---

    async function loadDashboardData() {
        hideErrorMessage();
        console.log('Requesting dashboard data from /api/tasks');
        try {
            const response = await fetch('/api/tasks');
            console.log('Response from /api/tasks:', response);
            const tasks = await response.json();
            console.log('Parsed dashboard data:', tasks);
            renderTasksTable(tasks);
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            displayErrorMessage('Failed to load dashboard data. Please try again.');
        }
    }

    async function loadConfigData() {
        hideErrorMessage();
        console.log('Requesting config data from /api/config');
        try {
            const response = await fetch('/api/config');
            console.log('Response from /api/config:', response);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const config = await response.text();
            // console.log('Parsed config data:', config);
            if (configEditor) {
                configEditor.setValue(config, -1);
            }
        } catch (error) {
            console.error('Error loading config data:', error);
            displayErrorMessage('Failed to load config data. Please try again.');
        }
    }

    let chartDataAbortController = null;
    async function loadChartData() {
        if (chartDataAbortController) {
            chartDataAbortController.abort();
        }
        chartDataAbortController = new AbortController();
        const signal = chartDataAbortController.signal;

        if (dataChart) {
            dataChart.clear();
        }
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

        // 添加label参数
        const selectedLabel = document.getElementById('chart-label').value;
        if (selectedLabel) {
            urlParams.append('label', selectedLabel);
        }

        // 添加devices参数（使用列表方式）
        if (devices.length > 0) {
            urlParams.append('devices', devices.join(','));
        }

        const requestUrl = `/api/chart?${urlParams.toString()}`;
        console.log('Requesting chart data from:', requestUrl);
        try {
            const response = await fetch(requestUrl, { signal });
            console.log('Response from chart API:', response);
            const data = await response.json();
            console.log('Parsed chart data:', data);
            updateChart(data);
            updateChartFilterOptions(data);
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Fetch aborted');
            } else {
                console.error('Error loading chart data:', error);
                displayErrorMessage('Failed to load chart data. Please try again.');
            }
        }
    }

    async function loadOutfileList() {
        hideErrorMessage();
        console.log('Requesting outfile list from /api/outfiles');
        try {
            const response = await fetch('/api/outfiles');
            console.log('Response from /api/outfiles:', response);
            const files = await response.json();
            console.log('Parsed outfile list:', files);
            renderOutfileList(files);
        } catch (error) {
            console.error('Error loading outfile list:', error);
            displayErrorMessage('Failed to load outfile list. Please try again.');
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
            // 获取目标设备的IP地址信息
            let deviceInfo = 'N/A';
            let ipInfo = 'N/A';
            if (task.targets && task.targets.length > 0) {
                deviceInfo = task.targets.join(', ');
            }
            if (task.target_ips && task.target_ips.length > 0) {
                ipInfo = task.target_ips.join(', ');
            }

            row.innerHTML = `
                <td>${deviceInfo}</td>
                <td>${task.alias}</td>
                <td>${ipInfo}</td>
                <td>${task.protocol || 'N/A'}</td>
                <td>${task.schedule_seconds || 'N/A'}</td>
                <td>${task.schedule_mode || 'N/A'}</td>
                <td>${task.storage || 'null'}</td>
                <td>
                    <span class="status-badge ${task.enabled ? 'enabled' : 'disabled'}">
                        <i class="fas ${task.enabled ? 'fa-check-circle' : 'fa-times-circle'}"></i>
                        ${task.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm ${task.enabled ? 'btn-danger' : 'btn-success'}" data-device="${task.targets[0] || ''}" data-alias="${task.alias}" data-action="${task.enabled ? 'disable' : 'enable'}">
                        <i class="fas ${task.enabled ? 'fa-stop' : 'fa-play'}"></i>
                        ${task.enabled ? 'Disable' : 'Enable'}
                    </button>
                </td>
            `;
            tasksTableBody.appendChild(row);
        });
    }

    function renderOutfileList(files) {
        const outfileListDiv = document.getElementById('outfile-list');
        outfileListDiv.innerHTML = ''; // Clear previous list

        if (!files || files.length === 0) {
            outfileListDiv.innerHTML = '<p>No files found in outfile directory.</p>';
            return;
        }

        const ul = document.createElement('ul');
        ul.className = 'file-list'; // Add a class for styling

        files.forEach(file => {
            // 格式化文件大小
            let sizeText = '';
            if (file.size < 1024) {
                sizeText = file.size + ' B';
            } else if (file.size < 1024 * 1024) {
                sizeText = (file.size / 1024).toFixed(1) + ' KB';
            } else {
                sizeText = (file.size / (1024 * 1024)).toFixed(1) + ' MB';
            }

            // 格式化创建时间
            const date = new Date(file.created_at * 1000);
            const dateText = date.getFullYear() + '-' +
                String(date.getMonth() + 1).padStart(2, '0') + '-' +
                String(date.getDate()).padStart(2, '0') + ' ' +
                String(date.getHours()).padStart(2, '0') + ':' +
                String(date.getMinutes()).padStart(2, '0') + ':' +
                String(date.getSeconds()).padStart(2, '0');

            const li = document.createElement('li');
            li.innerHTML = `
                <div class="file-info">
                    <i class="fas fa-file"></i>
                    <span class="file-name" title="${file.name}">${file.name}</span>
                    <span class="file-created-at">${dateText}</span>
                    <span class="file-size">${sizeText}</span>
                </div>
                <div class="file-actions">
                    <a href="/outfile/${file.name}" download="${file.name}" class="btn btn-success">Download</a>
                </div>
            `;
            ul.appendChild(li);
        });
        outfileListDiv.appendChild(ul);
    }

    function updateChart(data) {
        if (dataChart) {
            // 准备CSV下载功能
            const downloadCSV = function () {
                let csvContent = "data:text/csv;charset=utf-8,";

                // 添加CSV头部
                const headers = ["Time"];
                data.datasets.forEach(dataset => {
                    headers.push(dataset.label);
                });
                csvContent += headers.join(",") + "\r\n";

                // 创建时间点的集合
                const timePoints = new Set();
                data.datasets.forEach(dataset => {
                    dataset.data.forEach(point => {
                        timePoints.add(point.x);
                    });
                });

                // 按时间排序
                const sortedTimePoints = Array.from(timePoints).sort();

                // 为每个时间点创建一行数据
                sortedTimePoints.forEach(timestamp => {
                    const date = new Date(timestamp);
                    // 使用更易读的时间格式：YYYY-MM-DD HH:mm:ss
                    const formattedTime = date.getFullYear() + '-' +
                        String(date.getMonth() + 1).padStart(2, '0') + '-' +
                        String(date.getDate()).padStart(2, '0') + ' ' +
                        String(date.getHours()).padStart(2, '0') + ':' +
                        String(date.getMinutes()).padStart(2, '0') + ':' +
                        String(date.getSeconds()).padStart(2, '0');
                    let row = [formattedTime];

                    data.datasets.forEach(dataset => {
                        const point = dataset.data.find(p => p.x === timestamp);
                        row.push(point ? point.y : "");
                    });

                    csvContent += row.join(",") + "\r\n";
                });

                // 创建下载链接
                const encodedUri = encodeURI(csvContent);
                const link = document.createElement("a");
                link.setAttribute("href", encodedUri);
                link.setAttribute("download", "chart_data.csv");
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            };

            const option = {
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'cross'
                    },
                    formatter: function (params) {
                        const date = new Date(params[0].value[0]);
                        // 使用更易读的时间格式：YYYY-MM-DD HH:mm:ss
                        const formattedDateTime = date.getFullYear() + '-' +
                            String(date.getMonth() + 1).padStart(2, '0') + '-' +
                            String(date.getDate()).padStart(2, '0') + ' ' +
                            String(date.getHours()).padStart(2, '0') + ':' +
                            String(date.getMinutes()).padStart(2, '0') + ':' +
                            String(date.getSeconds()).padStart(2, '0');

                        let result = `<div style="font-weight:bold;margin-bottom:5px;">${formattedDateTime}</div>`;

                        params.forEach(param => {
                            result += `<div style="margin: 3px 0">
                                <span style="display:inline-block;margin-right:5px;border-radius:50%;width:10px;height:10px;background-color:${param.color}"></span>
                                ${param.seriesName}: ${param.value[1]}
                            </div>`;
                        });

                        return result;
                    }
                },
                toolbox: {
                    feature: {
                        myRefresh: {
                            show: true,
                            title: 'Refresh Data',
                            icon: 'path://M12,6V9L16,5L12,1V4A8,8 0 0,0 4,12C4,13.57 4.46,15.03 5.24,16.26L6.7,14.8C6.25,13.97 6,13 6,12A6,6 0 0,1 12,6M18.76,7.74L17.3,9.2C17.74,10.04 18,11 18,12A6,6 0 0,1 12,18V15L8,19L12,23V20A8,8 0 0,0 20,12C20,10.43 19.54,8.97 18.76,7.74Z',
                            onclick: function () {
                                loadChartData();
                            }
                        },
                        saveAsImage: {
                            title: 'Save as Image',
                            name: 'chart_data',
                            icon: 'path://M21,19V5C21,3.89 20.1,3 19,3H5A2,2 0 0,0 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19M8.5,13.5L11,16.5L14.5,12L19,18H5L8.5,13.5Z'
                        },
                        dataView: {
                            title: 'Data View',
                            readOnly: true,
                            lang: ['Data View', 'Close', 'Refresh'],
                            optionToContent: function (opt) {
                                // 自定义数据视图内容，复用CSS中的.data-table样式
                                let table = '<table class="data-table"><thead>';

                                // 表头
                                table += '<tr>';
                                table += '<th>Time</th>';
                                opt.series.forEach(series => {
                                    table += `<th>${series.name}</th>`;
                                });
                                table += '</tr>';
                                table += '</thead><tbody>';

                                // 收集所有时间点
                                const timePoints = new Set();
                                opt.series.forEach(series => {
                                    series.data.forEach(point => {
                                        timePoints.add(point[0]);
                                    });
                                });

                                // 按时间排序
                                const sortedTimePoints = Array.from(timePoints).sort();

                                // 生成表格行
                                sortedTimePoints.forEach(timestamp => {
                                    const date = new Date(timestamp);
                                    const formattedTime = date.getFullYear() + '-' +
                                        String(date.getMonth() + 1).padStart(2, '0') + '-' +
                                        String(date.getDate()).padStart(2, '0') + ' ' +
                                        String(date.getHours()).padStart(2, '0') + ':' +
                                        String(date.getMinutes()).padStart(2, '0') + ':' +
                                        String(date.getSeconds()).padStart(2, '0');

                                    table += '<tr>';
                                    table += `<td>${formattedTime}</td>`;

                                    opt.series.forEach(series => {
                                        const point = series.data.find(p => p[0] === timestamp);
                                        const value = point ? point[1] : '';
                                        table += `<td>${value}</td>`;
                                    });

                                    table += '</tr>';
                                });

                                table += '</tbody></table>';
                                return table;
                            }
                        },
                        myTool1: {
                            show: true,
                            title: 'Download CSV',
                            icon: 'path://M4.7,22.9L29.3,45.5L54.7,23.4M4.6,43.6L4.6,58L53.8,58L53.8,43.6M29.2,45.1L29.2,0',
                            onclick: downloadCSV
                        }
                    },
                    right: '5%',
                    top: '5%'
                },
                grid: {
                    left: '3%',
                    right: '3%',
                    bottom: '3%', // 增加底部空间以便更好地显示x轴标签
                    containLabel: true
                },
                legend: {
                    data: data.datasets.map(dataset => dataset.label)
                },
                xAxis: {
                    type: 'time',
                    axisLine: {
                        show: true,
                        onZero: false, // X轴与Y轴的最小值相交，而不是与0相交
                        lineStyle: {
                            color: '#333'
                        }
                    },
                    axisLabel: {
                        formatter: function (value) {
                            const date = new Date(value);
                            return date.toLocaleDateString() + '\n' + date.toLocaleTimeString();
                        },
                        interval: 'auto',
                        rotate: 0,
                        margin: 12,
                        textStyle: {
                            fontSize: 11
                        }
                    },
                    splitLine: {
                        show: true,
                        lineStyle: {
                            type: 'dashed',
                            opacity: 0.3
                        }
                    }
                },
                yAxis: {
                    type: 'value',
                    scale: true,
                    min: function (value) {
                        // 优化：减少重复计算，当值相同时直接返回
                        return value.min === value.max ?
                            Math.ceil(value.max * 0.9) :
                            Math.floor(value.min - (value.max - value.min) * 0.1);
                    },
                    max: function (value) {
                        // 优化：减少重复计算，当值相同时直接返回
                        return value.min === value.max ?
                            Math.floor(value.min * 1.1) :
                            Math.ceil(value.max + (value.max - value.min) * 0.1);
                    },
                    axisLabel: {
                        formatter: function (value) {
                            // 不显示负值刻度
                            if (value < 0) {
                                return '';
                            }
                            return value;
                        }
                    },
                    axisLine: {
                        show: true,
                        lineStyle: {
                            color: '#333'
                        }
                    },
                    splitLine: {
                        show: true,
                        lineStyle: {
                            type: 'dashed',
                            opacity: 0.3
                        }
                    }
                },
                series: data.datasets.map(dataset => ({
                    name: dataset.label,
                    type: 'line',
                    data: dataset.data.map(item => [item.x, item.y]),
                    showSymbol: false,
                    symbolSize: 5,
                    emphasis: {
                        focus: 'series',
                        itemStyle: {
                            borderWidth: 2
                        }
                    }
                }))
            };
            dataChart.setOption(option);
        }
    }

    function updateChartFilterOptions(data) {
        const selectedTask = document.getElementById('chart-task').value;
        const selectedLabel = document.getElementById('chart-label').value;

        // 更新任务选项 - 始终显示完整的任务列表
        taskDropdownMenu.innerHTML = '';
        if (!selectedTask) {
            taskDropdownToggle.textContent = 'Select a task';
        }
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

        // 更新Label选项 - 只有当选择了task时才显示labels
        const labelDropdownMenu = document.getElementById('labelDropdownMenu');
        const labelDropdownToggle = document.getElementById('labelDropdownToggle');

        labelDropdownMenu.innerHTML = '';
        if (!selectedLabel) {
            labelDropdownToggle.textContent = 'Select a label';
        }

        if (selectedTask && data.labels && data.labels.length > 0) {
            data.labels.forEach(label => {
                const isChecked = (label === selectedLabel);
                const item = createDropdownItem('radio', 'label', label, `label-${label}`, label, isChecked);
                if (isChecked) {
                    labelDropdownToggle.textContent = label;
                }
                labelDropdownMenu.appendChild(item);
            });
        }

        // 更新设备选项 - 只有当选择了task时才显示设备
        const dropdownMenu = document.getElementById('dropdownMenu');
        const deviceDropdown = document.getElementById('deviceDropdown');
        const deviceCountSpan = document.getElementById('deviceCount');

        // 始终显示设备下拉菜单（根据是否有可用设备决定内容）
        deviceDropdown.style.display = 'block';
        if (selectedTask && data.available_devices && data.available_devices.length > 0) {
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

            // 立即更新UI状态
            updateTaskUI(button, action);

            const requestUrl = `/api/tasks/${action}/${device}/${alias}`;
            console.log(`Sending ${action} request to: ${requestUrl}`);
            try {
                const response = await fetch(requestUrl, { method: 'POST' });
                console.log(`Response for ${action} task:`, response);
                if (!response.ok) {
                    // 如果请求失败，恢复UI状态
                    const reverseAction = action === 'enable' ? 'disable' : 'enable';
                    updateTaskUI(button, reverseAction);
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                // 由于配置更新是异步的，我们不重新加载数据，而是依赖UI状态更新
            } catch (error) {
                console.error(`Error ${action}ing task:`, error);
                displayErrorMessage(`Failed to ${action} task. Please try again.`);
            }
        }
    }

    function updateTaskUI(button, action) {
        // 更新按钮状态
        if (action === 'enable') {
            button.dataset.action = 'disable';
            button.classList.remove('btn-success');
            button.classList.add('btn-danger');
            button.innerHTML = '<i class="fas fa-stop"></i> Disable';
        } else {
            button.dataset.action = 'enable';
            button.classList.remove('btn-danger');
            button.classList.add('btn-success');
            button.innerHTML = '<i class="fas fa-play"></i> Enable';
        }

        // 更新状态标签
        const statusBadge = button.closest('tr').querySelector('.status-badge');
        if (statusBadge) {
            if (action === 'enable') {
                statusBadge.classList.remove('disabled');
                statusBadge.classList.add('enabled');
                statusBadge.innerHTML = '<i class="fas fa-check-circle"></i> Enabled';
            } else {
                statusBadge.classList.remove('enabled');
                statusBadge.classList.add('disabled');
                statusBadge.innerHTML = '<i class="fas fa-times-circle"></i> Disabled';
            }
        }
    }

    async function handleConfigSave(event) {
        event.preventDefault();
        hideErrorMessage('config-error');
        const content = configEditor.getValue();

        console.log('Saving config to /api/config with content:', content);
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/yaml' },
                body: content
            });
            console.log('Response from config save:', response);
            if (response.ok) {
                displayErrorMessage('Config saved successfully!', 'config-error');
                // 成功消息也应在5秒后自动隐藏
                setTimeout(() => {
                    hideErrorMessage('config-error');
                }, 2000);
            } else {
                const errorText = await response.text();
                console.error('Error response from config save:', errorText);
                displayErrorMessage(`Error saving config: ${errorText}`, 'config-error');
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
        'outfile-view': initOutfileView,
    };

    function switchView(viewId) {
        const currentView = document.querySelector('.view.active');
        if (currentView && currentView.id === 'chart-view' && viewId !== 'chart-view') {
            clearTaskAndDeviceSelection();
        }

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

    function setupDropdown(dropdownId, toggleId, menuId) {
        const dropdown = document.getElementById(dropdownId);
        const toggle = document.getElementById(toggleId);
        const menu = document.getElementById(menuId);

        if (toggle && menu) {
            toggle.addEventListener('click', (event) => {
                event.stopPropagation();
                menu.classList.toggle('show');
            });
        }
    }

    // Add event listener for window resize to adjust chart size
    window.addEventListener('resize', function () {
        if (dataChart) {
            dataChart.resize();
        }
    });

    setupDropdown('taskDropdown', 'taskDropdownToggle', 'taskDropdownMenu');
    setupDropdown('labelDropdown', 'labelDropdownToggle', 'labelDropdownMenu');
    setupDropdown('deviceDropdown', 'dropdownToggle', 'dropdownMenu');

    document.addEventListener('click', (event) => {
        const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
        openDropdowns.forEach(dropdown => {
            if (!dropdown.parentElement.contains(event.target)) {
                dropdown.classList.remove('show');
            }
        });
    });

    // 初始视图
    switchView('dashboard-view');

    // --- Help Button ---
    const helpButton = document.getElementById('help-btn');
    if (helpButton) {
        helpButton.addEventListener('click', function () {
            // Open help documentation in a new tab
            window.open('/help', '_blank');
        });
    }
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