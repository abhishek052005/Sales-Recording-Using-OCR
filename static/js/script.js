// Base API configuration
const API_BASE_URL = '';

// Authentication Guard: Check for JWT token
const token = localStorage.getItem('access_token');
if (!token) {
  window.location.href = 'auth.html';
}

// DOM Elements
const uploadForm = document.getElementById('uploadForm');
const invoiceFile = document.getElementById('invoiceFile');
const fileName = document.getElementById('fileName');
const messageBox = document.getElementById('messageBox');
const submitBtn = document.getElementById('submitBtn');
const systemStatus = document.getElementById('systemStatus');
const logoutBtn = document.getElementById('logoutBtn');
const reviewPanel = document.getElementById('reviewPanel');
const reviewForm = document.getElementById('reviewForm');
const reviewItemsList = document.getElementById('reviewItemsList');
const editReviewBtn = document.getElementById('editReviewBtn');
const invoiceTableBody = document.getElementById('invoiceTableBody');
const sortToggleBtn = document.getElementById('sortToggleBtn');

if (logoutBtn) {
  logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('access_token');
    window.location.href = 'auth.html';
  });
}

let activeInvoiceData = null;
let activeFileName = '';
let activeOcrText = '';
let savedInvoices = [];
let invoiceSortAsc = false;

/**
 * Helper to construct Authorization headers
 */
const getAuthHeaders = (additionalHeaders = {}) => ({
  'Authorization': `Bearer ${token}`,
  ...additionalHeaders,
});

/**
 * UI Helper Functions
 */
const setSystemStatus = (text) => {
  if (systemStatus) {
    systemStatus.textContent = text;
  }
};

const setMessage = (type, text) => {
  messageBox.classList.remove('hidden', 'success', 'error');
  messageBox.classList.add(type);
  messageBox.textContent = text;
};

const formatMoney = (value) => {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(Number(value));
};

const safeText = (value) => {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  return String(value);
};

const asNumber = (value) => {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
};

/**
 * Render Invoice Table
 */
const renderInvoiceEntries = (entries = savedInvoices) => {
  if (!Array.isArray(entries) || entries.length === 0) {
    invoiceTableBody.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">No saved invoices yet.</td>
      </tr>
    `;
    return;
  }

  const sortedEntries = [...entries].sort((a, b) => {
    const aDate = a.created_at ? new Date(a.created_at).getTime() : 0;
    const bDate = b.created_at ? new Date(b.created_at).getTime() : 0;
    return invoiceSortAsc ? aDate - bDate : bDate - aDate;
  });

  invoiceTableBody.innerHTML = sortedEntries
    .map(
      (entry) => `
        <tr>
          <td>${safeText(entry.id)}</td>
          <td>${safeText(entry.invoice_number)}</td>
          <td>${safeText(entry.invoice_date)}</td>
          <td>${safeText(entry.vendor_name)}</td>
          <td>${safeText(entry.vendor_gstin)}</td>
          <td>${formatMoney(entry.total)}</td>
          <td>${safeText(entry.created_at ? new Date(entry.created_at).toLocaleString() : '—')}</td>
        </tr>
      `
    )
    .join('');
};

/**
 * API Call: Fetch Invoice Entries
 */
const loadInvoiceEntries = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/invoices`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });

    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = 'auth.html';
      return;
    }

    let result = {};
    try {
      result = await response.json();
    } catch (e) {
      throw new Error(`Server error (${response.status}: ${response.statusText})`);
    }

    if (!response.ok) {
      throw new Error(result.error || result.detail || 'Could not load invoices.');
    }

    savedInvoices = Array.isArray(result.items) ? result.items : [];
    renderInvoiceEntries();
  } catch (error) {
    invoiceTableBody.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">Unable to load saved invoices.</td>
      </tr>
    `;
  }
};

/**
 * Display Extracted Summary
 */
const renderInvoice = (data) => {
  if (!data) return;

  const vendor = data.vendor || {};
  const customer = data.customer || {};

  document.getElementById('invoiceNumber').textContent = safeText(data.invoice_number);
  document.getElementById('invoiceDate').textContent = safeText(data.invoice_date);
  document.getElementById('subtotalValue').textContent = formatMoney(data.subtotal);
  document.getElementById('totalValue').textContent = formatMoney(data.total);

  document.getElementById('vendorName').textContent = safeText(vendor.name);
  document.getElementById('vendorGstin').textContent = safeText(vendor.gstin);
  document.getElementById('vendorPhone').textContent = safeText(vendor.phone);
  document.getElementById('vendorEmail').textContent = safeText(vendor.email);

  document.getElementById('customerName').textContent = safeText(customer.name);
  document.getElementById('customerGstin').textContent = safeText(customer.gstin);
  document.getElementById('customerPhone').textContent = safeText(customer.phone);
  document.getElementById('customerEmail').textContent = safeText(customer.email);
};

/**
 * Build Review Form Line Items
 */
const buildReviewItems = (items = []) => {
  if (!Array.isArray(items) || items.length === 0) {
    reviewItemsList.innerHTML = '<div class="empty-state">No line items available.</div>';
    return;
  }

  reviewItemsList.innerHTML = items
    .map(
      (item, index) => `
        <div class="review-item-row" data-index="${index}">
          <label>
            <span>Description</span>
            <input type="text" name="item_description_${index}" value="${safeText(item.description).replace('—', '')}" />
          </label>
          <label>
            <span>Qty</span>
            <input type="number" step="0.01" name="item_quantity_${index}" value="${safeText(item.quantity).replace('—', '')}" />
          </label>
          <label>
            <span>Unit</span>
            <input type="number" step="0.01" name="item_unit_price_${index}" value="${safeText(item.unit_price).replace('—', '')}" />
          </label>
          <label>
            <span>Tax</span>
            <input type="number" step="0.01" name="item_tax_rate_${index}" value="${safeText(item.tax_rate).replace('—', '')}" />
          </label>
          <label>
            <span>Amount</span>
            <input type="number" step="0.01" name="item_amount_${index}" value="${safeText(item.amount).replace('—', '')}" />
          </label>
        </div>
      `
    )
    .join('');
};

/**
 * Populate Review Form
 */
const populateReviewForm = (data) => {
  const vendor = data.vendor || {};
  const customer = data.customer || {};

  if (reviewForm.elements.invoice_number) {
    reviewForm.elements.invoice_number.value = safeText(data.invoice_number).replace('—', '');
  }
  if (reviewForm.elements.invoice_date) {
    reviewForm.elements.invoice_date.value = data.invoice_date || '';
  }
  if (reviewForm.elements.vendor_name) {
    reviewForm.elements.vendor_name.value = safeText(vendor.name).replace('—', '');
  }
  if (reviewForm.elements.vendor_gstin) {
    reviewForm.elements.vendor_gstin.value = safeText(vendor.gstin).replace('—', '');
  }
  if (reviewForm.elements.subtotal) {
    reviewForm.elements.subtotal.value = data.subtotal ?? '';
  }
  if (reviewForm.elements.tax) {
    reviewForm.elements.tax.value = data.tax ?? '';
  }
  if (reviewForm.elements.total) {
    reviewForm.elements.total.value = data.total ?? '';
  }
  if (reviewForm.elements.customer_name) {
    reviewForm.elements.customer_name.value = safeText(customer.name).replace('—', '');
  }
  if (reviewForm.elements.customer_gstin) {
    reviewForm.elements.customer_gstin.value = safeText(customer.gstin).replace('—', '');
  }

  buildReviewItems(data.items || []);
};

/**
 * Collect Form Data from Review Panel
 */
const collectReviewData = () => {
  const rows = [...reviewItemsList.querySelectorAll('.review-item-row')];

  return {
    invoice_number: reviewForm.elements.invoice_number ? reviewForm.elements.invoice_number.value.trim() || null : null,
    invoice_date: reviewForm.elements.invoice_date ? reviewForm.elements.invoice_date.value || null : null,
    currency: 'INR',
    vendor: {
      name: reviewForm.elements.vendor_name ? reviewForm.elements.vendor_name.value.trim() || null : null,
      gstin: reviewForm.elements.vendor_gstin ? reviewForm.elements.vendor_gstin.value.trim() || null : null,
      address: null,
      phone: null,
      email: null,
    },
    customer: {
      name: reviewForm.elements.customer_name ? reviewForm.elements.customer_name.value.trim() || null : null,
      gstin: reviewForm.elements.customer_gstin ? reviewForm.elements.customer_gstin.value.trim() || null : null,
      address: null,
      phone: null,
      email: null,
    },
    items: rows.map((row) => ({
      description: row.querySelector('input[name^="item_description_"]').value.trim() || '',
      quantity: asNumber(row.querySelector('input[name^="item_quantity_"]').value),
      unit_price: asNumber(row.querySelector('input[name^="item_unit_price_"]').value),
      tax_rate: asNumber(row.querySelector('input[name^="item_tax_rate_"]').value),
      amount: asNumber(row.querySelector('input[name^="item_amount_"]').value),
    })),
    subtotal: asNumber(reviewForm.elements.subtotal.value),
    tax: asNumber(reviewForm.elements.tax.value),
    total: asNumber(reviewForm.elements.total.value),
  };
};

/**
 * Event Listeners
 */
invoiceFile.addEventListener('change', () => {
  const selected = invoiceFile.files && invoiceFile.files[0];
  fileName.textContent = selected ? selected.name : 'No file selected';
});

editReviewBtn.addEventListener('click', () => {
  reviewPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (reviewForm.elements.invoice_number) {
    reviewForm.elements.invoice_number.focus();
  }
  setMessage('success', 'Review the extracted values and correct any field before confirming.');
});

// API Call: Save Review
reviewForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const payload = {
    filename: activeFileName,
    ocr_text: activeOcrText,
    invoice_data: collectReviewData(),
  };

  submitBtn.disabled = true;
  editReviewBtn.disabled = true;
  setMessage('success', 'Saving reviewed invoice...');
  setSystemStatus('Saving invoice');

  try {
    const response = await fetch(`${API_BASE_URL}/save-review`, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    });

    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = 'auth.html';
      return;
    }

    let result = {};
    try {
      result = await response.json();
    } catch (e) {
      throw new Error(`Server error (${response.status}: ${response.statusText})`);
    }

    if (!response.ok) {
      throw new Error(result.error || result.detail || 'Failed to save invoice.');
    }

    setMessage('success', `Invoice saved successfully: ${result.filename}`);
    setSystemStatus('Saved');
    await loadInvoiceEntries();
  } catch (error) {
    setMessage('error', error.message || 'Unable to save the reviewed invoice.');
    setSystemStatus('Error');
  } finally {
    submitBtn.disabled = false;
    editReviewBtn.disabled = false;
  }
});

// API Call: Upload & Process Invoice
uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const selectedFile = invoiceFile.files && invoiceFile.files[0];

  if (!selectedFile) {
    setMessage('error', 'Please choose an invoice file before uploading.');
    return;
  }

  const formData = new FormData();
  formData.append('file', selectedFile);

  submitBtn.disabled = true;
  submitBtn.textContent = 'Processing...';
  setSystemStatus('Processing invoice');
  setMessage('success', 'Uploading invoice and extracting data...');

  try {
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    });

    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = 'auth.html';
      return;
    }

    let result = {};
    try {
      result = await response.json();
    } catch (e) {
      throw new Error(`Server error (${response.status}: ${response.statusText})`);
    }

    if (!response.ok) {
      throw new Error(result.error || result.detail || 'Upload failed.');
    }

    activeInvoiceData = result.invoice_data || {};
    activeFileName = result.filename || selectedFile.name;
    activeOcrText = result.ocr_text || '';

    renderInvoice(activeInvoiceData);
    populateReviewForm(activeInvoiceData);
    reviewPanel.classList.remove('hidden');

    if (result.duplicate_detected && result.duplicate_invoice) {
      setMessage(
        'error',
        `Duplicate invoice detected. Existing invoice ID ${result.duplicate_invoice.id} already exists. Review before saving.`
      );
      setSystemStatus('Duplicate');
    } else {
      setMessage('success', 'Invoice extracted successfully. Review and confirm the details before saving.');
      setSystemStatus('Review');
    }
  } catch (error) {
    setMessage('error', error.message || 'An unexpected error occurred.');
    setSystemStatus('Error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Process invoice';
  }
});

/**
 * Sorting Control
 */
const updateSortButtonText = () => {
  if (!sortToggleBtn) return;
  sortToggleBtn.textContent = invoiceSortAsc ? 'Sort: Oldest first' : 'Sort: Newest first';
};

if (sortToggleBtn) {
  sortToggleBtn.addEventListener('click', () => {
    invoiceSortAsc = !invoiceSortAsc;
    updateSortButtonText();
    renderInvoiceEntries();
  });
}

// Initial Loading
updateSortButtonText();
loadInvoiceEntries();