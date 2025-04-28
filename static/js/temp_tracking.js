// Temperature Tracking JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Global variables
    let currentDate = new Date();
    let currentMonth = currentDate.getMonth();
    let currentYear = currentDate.getFullYear();
    
    // DOM Elements
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');
    const currentMonthYearElem = document.getElementById('current-month-year');
    const calendarDaysElem = document.getElementById('calendar-days');
    const monthlyViewBtn = document.getElementById('monthly-view-btn');
    const yearlyViewBtn = document.getElementById('yearly-view-btn');
    const exportCsvBtn = document.getElementById('export-csv-btn');
    const monthlyView = document.getElementById('monthly-view');
    const yearlyView = document.getElementById('yearly-view');
    const tempEntryModal = document.getElementById('temp-entry-modal');
    const closeModalBtn = document.querySelector('.close-modal');
    const cancelModalBtn = document.querySelector('.cancel-btn');
    const modalDateTitle = document.getElementById('modal-date-title');
    const entryDateInput = document.getElementById('entry-date');
    const temperatureForm = document.getElementById('temperature-form');
    const refrigeratorTempInput = document.getElementById('refrigerator-temp');
    const freezerTempInput = document.getElementById('freezer-temp');
    const ln2LevelInput = document.getElementById('ln2-level');
    const roomTempInput = document.getElementById('room-temp');
    const humidityInput = document.getElementById('humidity');
    const correctiveActionContainer = document.getElementById('corrective-action-container');
    const correctiveActionInput = document.getElementById('corrective-action');
    const monthlyComplianceStats = document.getElementById('monthly-compliance-stats');
    const yearlyComplianceChart = document.getElementById('yearly-compliance-chart');
    const monthlyBreakdownTable = document.getElementById('monthly-breakdown-table');
    
    // Reference ranges
    const referenceRanges = {
        refrigerator: { min: 2, max: 8 },
        freezer: { min: -30, max: -15 },
        ln2: { min: 60, max: 100 },
        room: { min: 20, max: 25 },
        humidity: { min: 30, max: 60 }
    };
    
    // Initialize
    renderCalendar();
    updateMonthlyCompliance();
    
    // Event listeners
    prevMonthBtn.addEventListener('click', () => {
        currentMonth--;
        if (currentMonth < 0) {
            currentMonth = 11;
            currentYear--;
        }
        renderCalendar();
        updateMonthlyCompliance();
    });
    
    nextMonthBtn.addEventListener('click', () => {
        currentMonth++;
        if (currentMonth > 11) {
            currentMonth = 0;
            currentYear++;
        }
        renderCalendar();
        updateMonthlyCompliance();
    });
    
    monthlyViewBtn.addEventListener('click', () => {
        monthlyViewBtn.classList.add('active');
        yearlyViewBtn.classList.remove('active');
        monthlyView.classList.add('active');
        yearlyView.classList.remove('active');
    });
    
    yearlyViewBtn.addEventListener('click', () => {
        yearlyViewBtn.classList.add('active');
        monthlyViewBtn.classList.remove('active');
        yearlyView.classList.add('active');
        monthlyView.classList.remove('active');
        renderYearlyView();
    });
    
    exportCsvBtn.addEventListener('click', exportTemperatureData);
    
    closeModalBtn.addEventListener('click', closeModal);
    cancelModalBtn.addEventListener('click', closeModal);
    
    // Close modal if clicked outside
    window.addEventListener('click', (e) => {
        if (e.target === tempEntryModal) {
            closeModal();
        }
    });
    
    // Form validation and submission
    temperatureForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        // Check if values are within range and show corrective action if needed
        const refrigeratorTemp = parseFloat(refrigeratorTempInput.value);
        const freezerTemp = parseFloat(freezerTempInput.value);
        const ln2Level = parseFloat(ln2LevelInput.value);
        const roomTemp = parseFloat(roomTempInput.value);
        const humidity = parseFloat(humidityInput.value);
        
        const isRefrigeratorCompliant = isValueInRange(refrigeratorTemp, referenceRanges.refrigerator.min, referenceRanges.refrigerator.max);
        const isFreezerCompliant = isValueInRange(freezerTemp, referenceRanges.freezer.min, referenceRanges.freezer.max);
        const isLn2Compliant = isValueInRange(ln2Level, referenceRanges.ln2.min, referenceRanges.ln2.max);
        const isRoomCompliant = isValueInRange(roomTemp, referenceRanges.room.min, referenceRanges.room.max);
        const isHumidityCompliant = isValueInRange(humidity, referenceRanges.humidity.min, referenceRanges.humidity.max);
        
        const allCompliant = isRefrigeratorCompliant && isFreezerCompliant && isLn2Compliant && isRoomCompliant && isHumidityCompliant;
        
        if (!allCompliant) {
            correctiveActionContainer.classList.remove('hidden');
            
            if (correctiveActionInput.value.trim() === '') {
                // Use translation for alert message
                alert(window.i18n ? window.i18n.getTranslation('corrective_action_required') : 'Corrective action is required for out-of-range values');
                return;
            }
        } else {
            correctiveActionContainer.classList.add('hidden');
        }
        
        // Prepare data for submission
        const formData = {
            date: entryDateInput.value,
            refrigerator_temp: refrigeratorTemp,
            freezer_temp: freezerTemp,
            ln2_level: ln2Level,
            room_temp: roomTemp,
            humidity: humidity,
            corrective_action: correctiveActionInput.value,
            is_compliant: allCompliant,
            compliance: {
                refrigerator: isRefrigeratorCompliant,
                freezer: isFreezerCompliant,
                ln2: isLn2Compliant,
                room: isRoomCompliant,
                humidity: isHumidityCompliant
            }
        };
        
        // Submit the data
        saveTemperatureData(formData)
            .then(response => {
                if (response.success) {
                    closeModal();
                    renderCalendar();
                    updateMonthlyCompliance();
                } else {
                    // Use translation for error message
                    alert(window.i18n ? window.i18n.getTranslation('error_saving') + ': ' + response.message : 'Error saving data: ' + response.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert(window.i18n ? window.i18n.getTranslation('error_saving') : 'An error occurred while saving the data.');
            });
    });
    
    // Check input values as they are entered
    document.querySelectorAll('#temperature-form input[type="number"]').forEach(input => {
        input.addEventListener('input', checkInputValues);
    });
    
    // Functions
    function renderCalendar() {
        // Update month and year display
        const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 
                         'August', 'September', 'October', 'November', 'December'];
        currentMonthYearElem.textContent = `${months[currentMonth]} ${currentYear}`;
        
        // Clear previous calendar
        calendarDaysElem.innerHTML = '';
        
        // Get first day of month and number of days
        const firstDayOfMonth = new Date(currentYear, currentMonth, 1).getDay();
        const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
        
        // Previous month's days
        const prevMonthDays = new Date(currentYear, currentMonth, 0).getDate();
        for (let i = firstDayOfMonth - 1; i >= 0; i--) {
            const dayElement = createDayElement(prevMonthDays - i, true);
            calendarDaysElem.appendChild(dayElement);
        }
        
        // Current month's days
        for (let i = 1; i <= daysInMonth; i++) {
            const date = new Date(currentYear, currentMonth, i);
            const dateString = formatDate(date);
            
            // Get temperature data for this day if it exists
            fetchTemperatureData(dateString)
                .then(data => {
                    const dayElement = createDayElement(i, false, date, data);
                    calendarDaysElem.appendChild(dayElement);
                    
                    // Add click event to open modal
                    if (!dayElement.classList.contains('inactive')) {
                        dayElement.addEventListener('click', () => openTemperatureModal(date, data));
                    }
                });
        }
        
        // Next month's days
        const totalCalendarCells = 42; // 6 rows x 7 days
        const nextMonthDays = totalCalendarCells - (firstDayOfMonth + daysInMonth);
        for (let i = 1; i <= nextMonthDays; i++) {
            const dayElement = createDayElement(i, true);
            calendarDaysElem.appendChild(dayElement);
        }
    }
    
    function createDayElement(dayNumber, isInactive, date = null, data = null) {
        const dayElement = document.createElement('div');
        dayElement.classList.add('calendar-day');
        
        if (isInactive) {
            dayElement.classList.add('inactive');
        }
        
        // Check if this is today
        if (date && isSameDay(date, new Date())) {
            dayElement.classList.add('today');
        }
        
        // Add the day number
        const dayNumberElement = document.createElement('div');
        dayNumberElement.classList.add('day-number');
        dayNumberElement.textContent = dayNumber;
        dayElement.appendChild(dayNumberElement);
        
        // Add status indicators if data exists
        if (data) {
            const statusDotsElement = document.createElement('div');
            statusDotsElement.classList.add('status-dots');
            
            // Add compliance status
            if (data.is_compliant) {
                dayElement.classList.add('compliant');
                
                // Add green status dots for each parameter
                for (const key in data.compliance) {
                    if (data.compliance[key]) {
                        const dot = document.createElement('div');
                        dot.classList.add('status-dot', 'compliant', key);
                        statusDotsElement.appendChild(dot);
                    }
                }
            } else {
                dayElement.classList.add('non-compliant');
                
                // Add red status dots for non-compliant parameters
                for (const key in data.compliance) {
                    if (!data.compliance[key]) {
                        const dot = document.createElement('div');
                        dot.classList.add('status-dot', 'non-compliant', key);
                        statusDotsElement.appendChild(dot);
                    }
                }
            }
            
            dayElement.appendChild(statusDotsElement);
        }
        
        return dayElement;
    }
    
    function openTemperatureModal(date, data = null) {
        // Format date for display
        const formattedDate = date.toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
        
        // Set modal title and date input
        modalDateTitle.textContent = `Temperature Recording - ${formattedDate}`;
        entryDateInput.value = formatDate(date);
        
        // Clear form
        temperatureForm.reset();
        correctiveActionContainer.classList.add('hidden');
        
        // Pre-fill with existing data if available
        if (data) {
            refrigeratorTempInput.value = data.refrigerator_temp;
            freezerTempInput.value = data.freezer_temp;
            ln2LevelInput.value = data.ln2_level;
            roomTempInput.value = data.room_temp;
            humidityInput.value = data.humidity;
            
            if (data.corrective_action) {
                correctiveActionInput.value = data.corrective_action;
                if (!data.is_compliant) {
                    correctiveActionContainer.classList.remove('hidden');
                }
            }
        }
        
        // Show modal
        tempEntryModal.style.display = 'block';
    }
    
    function closeModal() {
        tempEntryModal.style.display = 'none';
    }
    
    function checkInputValues() {
        const refrigeratorTemp = parseFloat(refrigeratorTempInput.value);
        const freezerTemp = parseFloat(freezerTempInput.value);
        const ln2Level = parseFloat(ln2LevelInput.value);
        const roomTemp = parseFloat(roomTempInput.value);
        const humidity = parseFloat(humidityInput.value);
        
        const isRefrigeratorCompliant = isNaN(refrigeratorTemp) || isValueInRange(refrigeratorTemp, referenceRanges.refrigerator.min, referenceRanges.refrigerator.max);
        const isFreezerCompliant = isNaN(freezerTemp) || isValueInRange(freezerTemp, referenceRanges.freezer.min, referenceRanges.freezer.max);
        const isLn2Compliant = isNaN(ln2Level) || isValueInRange(ln2Level, referenceRanges.ln2.min, referenceRanges.ln2.max);
        const isRoomCompliant = isNaN(roomTemp) || isValueInRange(roomTemp, referenceRanges.room.min, referenceRanges.room.max);
        const isHumidityCompliant = isNaN(humidity) || isValueInRange(humidity, referenceRanges.humidity.min, referenceRanges.humidity.max);
        
        const allCompliant = isRefrigeratorCompliant && isFreezerCompliant && isLn2Compliant && isRoomCompliant && isHumidityCompliant;
        
        // Toggle corrective action field visibility
        if (!allCompliant) {
            correctiveActionContainer.classList.remove('hidden');
        } else {
            correctiveActionContainer.classList.add('hidden');
        }
        
        // Highlight out-of-range inputs
        toggleErrorClass(refrigeratorTempInput, !isRefrigeratorCompliant);
        toggleErrorClass(freezerTempInput, !isFreezerCompliant);
        toggleErrorClass(ln2LevelInput, !isLn2Compliant);
        toggleErrorClass(roomTempInput, !isRoomCompliant);
        toggleErrorClass(humidityInput, !isHumidityCompliant);
    }
    
    function toggleErrorClass(element, isError) {
        if (isError) {
            element.classList.add('error');
        } else {
            element.classList.remove('error');
        }
    }
    
    function updateMonthlyCompliance() {
        // Fetch monthly compliance data
        const startDate = formatDate(new Date(currentYear, currentMonth, 1));
        const endDate = formatDate(new Date(currentYear, currentMonth + 1, 0));
        
        fetchMonthlyComplianceData(startDate, endDate)
            .then(data => {
                // Clear previous stats
                monthlyComplianceStats.innerHTML = '';
                
                if (!data || !data.total_days) {
                    // No data for the month
                    monthlyComplianceStats.innerHTML = '<div class="no-data">' + 
                        (window.i18n ? window.i18n.getTranslation('no_data_available') : 'No data available for this month') + 
                        '</div>';
                    return;
                }
                
                // Create overall compliance card
                const overallCard = document.createElement('div');
                overallCard.classList.add('stat-card');
                
                const overallTitle = document.createElement('div');
                overallTitle.classList.add('stat-title');
                overallTitle.innerHTML = '<i class="fas fa-check-circle"></i> ' + 
                    (window.i18n ? window.i18n.getTranslation('overall_compliance') : 'Overall Compliance');
                
                const overallValue = document.createElement('div');
                overallValue.classList.add('stat-value');
                const compliancePercent = Math.round((data.compliant_days / data.total_days) * 100);
                overallValue.textContent = `${compliancePercent}%`;
                
                // Add color class based on compliance percentage
                if (compliancePercent >= 90) {
                    overallValue.classList.add('stat-good');
                } else if (compliancePercent >= 75) {
                    overallValue.classList.add('stat-warning');
                } else {
                    overallValue.classList.add('stat-bad');
                }
                
                const overallDetails = document.createElement('div');
                overallDetails.classList.add('stat-details');
                overallDetails.textContent = `${data.compliant_days} of ${data.total_days} days`;
                
                overallCard.appendChild(overallTitle);
                overallCard.appendChild(overallValue);
                overallCard.appendChild(overallDetails);
                monthlyComplianceStats.appendChild(overallCard);
                
                // Create parameter-specific compliance cards
                for (const param in data.parameters) {
                    const paramData = data.parameters[param];
                    const paramCard = document.createElement('div');
                    paramCard.classList.add('stat-card');
                    
                    const paramTitle = document.createElement('div');
                    paramTitle.classList.add('stat-title');
                    let iconClass, paramName;
                    
                    switch(param) {
                        case 'refrigerator':
                            iconClass = 'fa-temperature-low';
                            paramName = 'Refrigerator';
                            break;
                        case 'freezer':
                            iconClass = 'fa-temperature-low';
                            paramName = 'Freezer';
                            break;
                        case 'ln2':
                            iconClass = 'fa-tint';
                            paramName = 'LN2 Level';
                            break;
                        case 'room':
                            iconClass = 'fa-thermometer-half';
                            paramName = 'Room Temp';
                            break;
                        case 'humidity':
                            iconClass = 'fa-water';
                            paramName = 'Humidity';
                            break;
                    }
                    
                    paramTitle.innerHTML = `<i class="fas ${iconClass}"></i> ${paramName}`;
                    
                    const paramValue = document.createElement('div');
                    paramValue.classList.add('stat-value');
                    const paramPercent = Math.round((paramData.compliant / paramData.total) * 100);
                    paramValue.textContent = `${paramPercent}%`;
                    
                    if (paramPercent >= 90) {
                        paramValue.classList.add('stat-good');
                    } else if (paramPercent >= 75) {
                        paramValue.classList.add('stat-warning');
                    } else {
                        paramValue.classList.add('stat-bad');
                    }
                    
                    paramCard.appendChild(paramTitle);
                    paramCard.appendChild(paramValue);
                    monthlyComplianceStats.appendChild(paramCard);
                }
            });
    }
    
    function renderYearlyView() {
        // Fetch yearly compliance data
        const startDate = formatDate(new Date(currentYear, 0, 1));
        const endDate = formatDate(new Date(currentYear, 11, 31));
        
        fetchYearlyComplianceData(startDate, endDate)
            .then(data => {
                // Render yearly chart
                renderYearlyChart(data);
                
                // Render monthly breakdown table
                renderMonthlyBreakdownTable(data);
            });
    }
    
    function renderYearlyChart(data) {
        // For now, we'll just display a simple placeholder
        // In production, this would use a charting library like Chart.js
        yearlyComplianceChart.innerHTML = '<div class="chart-placeholder">Monthly compliance chart would be displayed here</div>';
    }
    
    function renderMonthlyBreakdownTable(data) {
        const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 
                        'August', 'September', 'October', 'November', 'December'];
        
        let tableHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Month</th>
                        <th>Compliance %</th>
                        <th>Refrigerator</th>
                        <th>Freezer</th>
                        <th>LN2 Level</th>
                        <th>Room Temp</th>
                        <th>Humidity</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        // Mock data for demonstration
        const mockData = months.map((month, index) => ({
            month,
            compliance: Math.floor(Math.random() * 25) + 75, // 75-100%
            refrigerator: Math.floor(Math.random() * 20) + 80, // 80-100%
            freezer: Math.floor(Math.random() * 20) + 80, // 80-100%
            ln2: Math.floor(Math.random() * 20) + 80, // 80-100%
            room: Math.floor(Math.random() * 20) + 80, // 80-100%
            humidity: Math.floor(Math.random() * 20) + 80 // 80-100%
        }));
        
        mockData.forEach(row => {
            tableHTML += `
                <tr>
                    <td>${row.month}</td>
                    <td class="${getComplianceClass(row.compliance)}">${row.compliance}%</td>
                    <td class="${getComplianceClass(row.refrigerator)}">${row.refrigerator}%</td>
                    <td class="${getComplianceClass(row.freezer)}">${row.freezer}%</td>
                    <td class="${getComplianceClass(row.ln2)}">${row.ln2}%</td>
                    <td class="${getComplianceClass(row.room)}">${row.room}%</td>
                    <td class="${getComplianceClass(row.humidity)}">${row.humidity}%</td>
                </tr>
            `;
        });
        
        tableHTML += `
                </tbody>
            </table>
        `;
        
        monthlyBreakdownTable.innerHTML = tableHTML;
    }
    
    function getComplianceClass(percentage) {
        if (percentage >= 90) return 'stat-good';
        if (percentage >= 75) return 'stat-warning';
        return 'stat-bad';
    }
    
    // Helper functions
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    function isValueInRange(value, min, max) {
        return value >= min && value <= max;
    }
    
    function isSameDay(date1, date2) {
        return date1.getFullYear() === date2.getFullYear() &&
               date1.getMonth() === date2.getMonth() &&
               date1.getDate() === date2.getDate();
    }
    
    // API calls
    async function fetchTemperatureData(date) {
        try {
            const response = await fetch(`/temperature-data?date=${date}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data.data;
        } catch (error) {
            console.error('Error fetching temperature data:', error);
            return null;
        }
    }
    
    async function saveTemperatureData(data) {
        try {
            const response = await fetch('/temperature-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error saving temperature data:', error);
            throw error;
        }
    }
    
    async function fetchMonthlyComplianceData(startDate, endDate) {
        try {
            const response = await fetch(`/temperature-compliance?start_date=${startDate}&end_date=${endDate}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data.data;
        } catch (error) {
            console.error('Error fetching monthly compliance data:', error);
            return null;
        }
    }
    
    async function fetchYearlyComplianceData(startDate, endDate) {
        try {
            const response = await fetch(`/temperature-compliance-yearly?start_date=${startDate}&end_date=${endDate}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data.data;
        } catch (error) {
            console.error('Error fetching yearly compliance data:', error);
            return null;
        }
    }
    
    // Function to export temperature data as CSV
    async function exportTemperatureData() {
        try {
            // Show export message
            if (window.i18n) {
                alert(window.i18n.getTranslation('exporting_data'));
            }
            
            // Determine date range based on current view
            let startDate, endDate;
            
            if (monthlyView.classList.contains('active')) {
                // Monthly view - export current month
                startDate = formatDate(new Date(currentYear, currentMonth, 1));
                endDate = formatDate(new Date(currentYear, currentMonth + 1, 0));
            } else {
                // Yearly view - export entire year
                startDate = formatDate(new Date(currentYear, 0, 1));
                endDate = formatDate(new Date(currentYear, 11, 31));
            }
            
            // Call the export endpoint with date range
            const response = await fetch(`/export-temperature-data?start_date=${startDate}&end_date=${endDate}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Get the CSV data
            const blob = await response.blob();
            
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            
            // Generate filename based on date range
            let filename;
            if (monthlyView.classList.contains('active')) {
                const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 
                             'August', 'September', 'October', 'November', 'December'];
                filename = `Temperature_Data_${months[currentMonth]}_${currentYear}.csv`;
            } else {
                filename = `Temperature_Data_${currentYear}.csv`;
            }
            
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            
            // Clean up
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
        } catch (error) {
            console.error('Error exporting temperature data:', error);
            alert(window.i18n ? window.i18n.getTranslation('export_error') : 'An error occurred while exporting the data. Please try again.');
        }
    }
}); 