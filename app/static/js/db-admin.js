/**
 * Database Admin functionality
 * Handles loading and displaying database tables
 */

document.addEventListener('DOMContentLoaded', async () => {
    // DOM elements
    const tableSelect = document.getElementById('table-select');
    const tableHeaders = document.getElementById('table-headers');
    const tableData = document.getElementById('table-data');
    const pagination = document.getElementById('pagination');
    const searchFilter = document.getElementById('search-filter');
    const columnFilter = document.getElementById('column-filter');
    const applyFilterBtn = document.getElementById('apply-filter');
    const clearFilterBtn = document.getElementById('clear-filter');
    const addRecordBtn = document.getElementById('add-record-button');
    
    // Modal elements
    const recordModal = document.getElementById('record-modal');
    const modalTitle = document.getElementById('modal-title');
    const formFields = document.getElementById('form-fields');
    const recordForm = document.getElementById('record-form');
    const saveRecordBtn = document.getElementById('save-record-btn');
    const cancelRecordBtn = document.getElementById('cancel-record-btn');
    const closeBtns = document.querySelectorAll('.close');
    
    // Confirmation dialog elements
    const confirmDialog = document.getElementById('confirm-dialog');
    const confirmMessage = document.getElementById('confirm-message');
    const confirmYesBtn = document.getElementById('confirm-yes');
    const confirmNoBtn = document.getElementById('confirm-no');
    
    // State variables
    let currentTable = '';
    let currentPage = 1;
    const pageSize = 20;
    let totalPages = 1;
    let currentData = [];
    let filteredData = [];
    let columns = [];
    let filterColumn = '';
    let filterValue = '';
    let primaryKeyColumn = 'id'; // Default primary key
    let currentEditId = null;
    let onConfirmAction = null; // Callback for confirmation dialog
    
    // Initialize
    init();
    
    async function init() {
        try {
            // Load available tables
            await loadTables();
            
            // Set up event listeners
            setupEventListeners();
        } catch (error) {
            console.error('Error initializing admin panel:', error);
            showMessage('Error loading admin panel: ' + error.message, 'error');
        }
    }
    
    function setupEventListeners() {
        // Table selection
        tableSelect.addEventListener('change', async () => {
            currentTable = tableSelect.value;
            if (currentTable) {
                currentPage = 1;
                filterColumn = '';
                filterValue = '';
                searchFilter.value = '';
                resetFilter();
                await loadTableData();
                addRecordBtn.style.display = 'block';
            } else {
                clearTable();
                addRecordBtn.style.display = 'none';
            }
        });
        
        // Filter controls
        applyFilterBtn.addEventListener('click', () => {
            filterColumn = columnFilter.value;
            filterValue = searchFilter.value.trim().toLowerCase();
            applyFilter();
        });
        
        clearFilterBtn.addEventListener('click', resetFilter);
        
        // Add event for table cell expansion (for long content)
        tableData.addEventListener('click', (e) => {
            if (e.target.classList.contains('data-cell-content')) {
                e.target.classList.toggle('expanded');
            }
        });
        
        // Add record button
        addRecordBtn.addEventListener('click', () => {
            openAddRecordModal();
        });
        
        // Save record form submission
        recordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveRecord();
        });
        
        // Cancel add/edit record
        cancelRecordBtn.addEventListener('click', () => {
            closeModal(recordModal);
        });
        
        // Close modals with X buttons
        closeBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                closeModal(modal);
            });
        });
        
        // Confirmation dialog buttons
        confirmYesBtn.addEventListener('click', () => {
            if (typeof onConfirmAction === 'function') {
                onConfirmAction();
            }
            closeModal(confirmDialog);
        });
        
        confirmNoBtn.addEventListener('click', () => {
            closeModal(confirmDialog);
        });
        
        // Close modals when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target === recordModal) {
                closeModal(recordModal);
            }
            if (e.target === confirmDialog) {
                closeModal(confirmDialog);
            }
        });
    }
    
    async function loadTables() {
        try {
            const response = await fetch('/api/db/tables');
            if (!response.ok) {
                throw new Error(`Failed to load tables: ${response.statusText}`);
            }
            
            const data = await response.json();
            const tables = data.tables || [];
            
            // Populate table select dropdown
            tableSelect.innerHTML = '<option value="">-- Select a table --</option>';
            tables.forEach(table => {
                const option = document.createElement('option');
                option.value = table;
                option.textContent = table;
                tableSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading tables:', error);
            showMessage('Error loading tables: ' + error.message, 'error');
        }
    }
    
    async function loadTableData() {
        try {
            // Show loading state
            tableData.innerHTML = '<tr><td colspan="100%" style="text-align: center;">Loading...</td></tr>';
            
            // Make API request
            const response = await fetch(`/api/db/table/${currentTable}`);
            if (!response.ok) {
                throw new Error(`Failed to load table data: ${response.statusText}`);
            }
            
            const data = await response.json();
            currentData = data.rows || [];
            columns = data.columns || [];
            
            // Determine primary key - usually 'id' but could be different
            primaryKeyColumn = determinePrimaryKey();
            
            // Set up filter controls
            setupFilterControls();
            
            // Reset filter state but keep any existing filter
            filteredData = currentData;
            if (filterColumn && filterValue) {
                applyFilter();
            } else {
                renderTable();
            }
        } catch (error) {
            console.error(`Error loading data for table ${currentTable}:`, error);
            tableData.innerHTML = `<tr><td colspan="100%" style="text-align: center;">Error: ${error.message}</td></tr>`;
        }
    }
    
    function determinePrimaryKey() {
        // Try to determine primary key for the table
        // Usually 'id', but could be different
        if (columns.includes('id')) {
            return 'id';
        } else if (columns.length > 0) {
            // Default to first column if no 'id' is found
            return columns[0];
        }
        return '';
    }
    
    function setupFilterControls() {
        // Reset column filter options
        columnFilter.innerHTML = '<option value="">-- Select column --</option>';
        
        // Add options for each column
        columns.forEach(column => {
            const option = document.createElement('option');
            option.value = column;
            option.textContent = column;
            columnFilter.appendChild(option);
        });
        
        // Show filter controls
        searchFilter.style.display = 'block';
        columnFilter.style.display = 'block';
        applyFilterBtn.style.display = 'block';
        clearFilterBtn.style.display = 'block';
    }
    
    function applyFilter() {
        if (!filterValue) {
            filteredData = currentData;
            renderTable();
            return;
        }
        
        filteredData = currentData.filter(row => {
            if (filterColumn) {
                // Filter by specific column
                const value = String(row[filterColumn] || '').toLowerCase();
                return value.includes(filterValue);
            } else {
                // Filter across all columns
                return Object.values(row).some(value => 
                    String(value || '').toLowerCase().includes(filterValue)
                );
            }
        });
        
        currentPage = 1;
        renderTable();
    }
    
    function resetFilter() {
        filterColumn = '';
        filterValue = '';
        searchFilter.value = '';
        columnFilter.value = '';
        filteredData = currentData;
        currentPage = 1;
        renderTable();
    }
    
    function renderTable() {
        // Clear table
        tableHeaders.innerHTML = '';
        tableData.innerHTML = '';
        
        // Calculate pagination
        totalPages = Math.ceil(filteredData.length / pageSize);
        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = Math.min(startIndex + pageSize, filteredData.length);
        const pageData = filteredData.slice(startIndex, endIndex);
        
        // Render table headers
        if (columns.length > 0) {
            // Add extra column for actions
            const actionsHeader = document.createElement('th');
            actionsHeader.textContent = 'Actions';
            tableHeaders.appendChild(actionsHeader);
            
            // Add data columns
            columns.forEach(column => {
                const th = document.createElement('th');
                th.textContent = column;
                tableHeaders.appendChild(th);
            });
        }
        
        // Render table data
        if (pageData.length === 0) {
            const colspan = columns.length + 1; // +1 for actions column
            tableData.innerHTML = `<tr><td colspan="${colspan}" style="text-align: center;">No data found</td></tr>`;
        } else {
            pageData.forEach(row => {
                const tr = document.createElement('tr');
                
                // Add actions cell
                const actionsTd = document.createElement('td');
                actionsTd.className = 'action-cell';
                
                // Edit button
                const editButton = document.createElement('button');
                editButton.className = 'row-action-button edit-button';
                editButton.textContent = 'Edit';
                editButton.addEventListener('click', () => openEditRecordModal(row));
                actionsTd.appendChild(editButton);
                
                // Delete button
                const deleteButton = document.createElement('button');
                deleteButton.className = 'row-action-button delete-button';
                deleteButton.textContent = 'Delete';
                deleteButton.addEventListener('click', () => confirmDeleteRecord(row));
                actionsTd.appendChild(deleteButton);
                
                tr.appendChild(actionsTd);
                
                // Add data cells
                columns.forEach(column => {
                    const td = document.createElement('td');
                    const value = row[column];
                    
                    // Create content wrapper for potential expansion
                    const contentDiv = document.createElement('div');
                    contentDiv.className = 'data-cell-content';
                    
                    // Format value based on type
                    if (value === null || value === undefined) {
                        contentDiv.textContent = '';
                    } else if (typeof value === 'object') {
                        try {
                            contentDiv.textContent = JSON.stringify(value, null, 2);
                        } catch (e) {
                            contentDiv.textContent = String(value);
                        }
                    } else {
                        contentDiv.textContent = String(value);
                    }
                    
                    td.appendChild(contentDiv);
                    tr.appendChild(td);
                });
                
                tableData.appendChild(tr);
            });
        }
        
        // Render pagination
        renderPagination();
    }
    
    function renderPagination() {
        pagination.innerHTML = '';
        
        if (totalPages <= 1) return;
        
        // Previous button
        const prevButton = document.createElement('button');
        prevButton.textContent = '←';
        prevButton.disabled = currentPage === 1;
        prevButton.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                renderTable();
            }
        });
        pagination.appendChild(prevButton);
        
        // Page numbers
        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        
        // Adjust start if we're near the end
        if (endPage - startPage < 4) {
            startPage = Math.max(1, endPage - 4);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const pageButton = document.createElement('button');
            pageButton.textContent = i;
            pageButton.classList.toggle('active', i === currentPage);
            pageButton.addEventListener('click', () => {
                currentPage = i;
                renderTable();
            });
            pagination.appendChild(pageButton);
        }
        
        // Next button
        const nextButton = document.createElement('button');
        nextButton.textContent = '→';
        nextButton.disabled = currentPage === totalPages;
        nextButton.addEventListener('click', () => {
            if (currentPage < totalPages) {
                currentPage++;
                renderTable();
            }
        });
        pagination.appendChild(nextButton);
    }
    
    function clearTable() {
        tableHeaders.innerHTML = '';
        tableData.innerHTML = '';
        pagination.innerHTML = '';
        searchFilter.style.display = 'none';
        columnFilter.style.display = 'none';
        applyFilterBtn.style.display = 'none';
        clearFilterBtn.style.display = 'none';
        addRecordBtn.style.display = 'none';
    }
    
    function showMessage(message, type = 'info') {
        // Create message element if it doesn't exist
        let messageContainer = document.querySelector('.message-container');
        if (!messageContainer) {
            messageContainer = document.createElement('div');
            messageContainer.className = 'message-container';
            document.body.appendChild(messageContainer);
        }
        
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}`;
        messageElement.textContent = message;
        messageContainer.appendChild(messageElement);
        
        // Remove after 5 seconds
        setTimeout(() => {
            messageElement.classList.add('fade-out');
            setTimeout(() => {
                messageContainer.removeChild(messageElement);
            }, 500);
        }, 5000);
    }
    
    function openAddRecordModal() {
        modalTitle.textContent = `Add New Record to ${currentTable}`;
        currentEditId = null;
        generateFormFields();
        openModal(recordModal);
    }
    
    function openEditRecordModal(row) {
        modalTitle.textContent = `Edit Record in ${currentTable}`;
        currentEditId = row[primaryKeyColumn];
        generateFormFields(row);
        openModal(recordModal);
    }
    
    function generateFormFields(data = null) {
        formFields.innerHTML = '';
        
        columns.forEach(column => {
            // Skip auto-generated fields for new records if no data provided
            if (!data && (column === 'id' || column.endsWith('_at'))) {
                return;
            }
            
            const fieldDiv = document.createElement('div');
            fieldDiv.className = 'form-field';
            
            const label = document.createElement('label');
            label.setAttribute('for', `field-${column}`);
            label.textContent = column;
            fieldDiv.appendChild(label);
            
            let input;
            const value = data ? data[column] : '';
            
            // Create appropriate input type based on data
            if (column.includes('content') || column.includes('description') || 
                column.includes('message') || column.includes('metadata')) {
                // Textarea for longer text
                input = document.createElement('textarea');
                input.id = `field-${column}`;
                input.name = column;
                input.value = value !== null && value !== undefined ? value : '';
            } else {
                // Regular input for everything else
                input = document.createElement('input');
                input.id = `field-${column}`;
                input.name = column;
                input.type = 'text';
                input.value = value !== null && value !== undefined ? value : '';
                
                // Handle boolean values
                if (typeof value === 'boolean') {
                    input.value = value ? '1' : '0';
                }
                
                // Disable primary key for edits
                if (data && column === primaryKeyColumn) {
                    input.disabled = true;
                }
            }
            
            fieldDiv.appendChild(input);
            formFields.appendChild(fieldDiv);
        });
    }
    
    async function saveRecord() {
        try {
            // Collect form data
            const formData = {};
            const inputs = formFields.querySelectorAll('input, textarea');
            
            inputs.forEach(input => {
                if (!input.disabled) { // Skip disabled fields
                    formData[input.name] = input.value;
                }
            });
            
            let response;
            
            if (currentEditId === null) {
                // Create new record
                response = await fetch(`/api/db/table/${currentTable}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
            } else {
                // Update existing record
                response = await fetch(`/api/db/table/${currentTable}/${currentEditId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
            }
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server error: ${errorText}`);
            }
            
            const result = await response.json();
            
            closeModal(recordModal);
            await loadTableData(); // Refresh the table
            
            const action = currentEditId === null ? 'created' : 'updated';
            showMessage(`Record ${action} successfully`, 'success');
            
        } catch (error) {
            console.error('Error saving record:', error);
            showMessage(`Error saving record: ${error.message}`, 'error');
        }
    }
    
    function confirmDeleteRecord(row) {
        const recordId = row[primaryKeyColumn];
        confirmMessage.textContent = `Are you sure you want to delete this record (${primaryKeyColumn}: ${recordId})?`;
        
        onConfirmAction = async () => {
            try {
                const response = await fetch(`/api/db/table/${currentTable}/${recordId}`, {
                    method: 'DELETE'
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`Server error: ${errorText}`);
                }
                
                await loadTableData(); // Refresh the table
                showMessage('Record deleted successfully', 'success');
                
            } catch (error) {
                console.error('Error deleting record:', error);
                showMessage(`Error deleting record: ${error.message}`, 'error');
            }
        };
        
        openModal(confirmDialog);
    }
    
    function openModal(modal) {
        modal.style.display = 'block';
    }
    
    function closeModal(modal) {
        modal.style.display = 'none';
    }
}); 