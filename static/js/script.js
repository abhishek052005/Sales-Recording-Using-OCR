// Base API configuration
const API_BASE_URL = '';

// DOM Elements
const uploadForm = document.getElementById('uploadForm');
const invoiceFile = document.getElementById('invoiceFile');
const fileName = document.getElementById('fileName');
const messageBox = document.getElementById('messageBox');
const submitBtn = document.getElementById('submitBtn');
const systemStatus = document.getElementById('systemStatus');
const reviewPanel = document.getElementById('reviewPanel');
const reviewForm = document.getElementById('reviewForm');
const reviewItemsList = document.getElementById('reviewItemsList');
const editReviewBtn = document.getElementById('editReviewBtn');
const confirmReviewBtn = document.getElementById('confirmReviewBtn');
const invoiceTableBody = document.getElementById('invoiceTableBody');
const sortToggleBtn = document.getElementById('sortToggleBtn');
const downloadFormat = document.getElementById('downloadFormat');

let activeInvoiceData = null;
let activeFileName = '';
let activeOcrText = '';
let pendingInvoices = [];
let processingBatch = false;
let savedInvoices = [];
let invoiceSortAsc = false;

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

const showNextInvoice = () => {
  const nextInvoice = pendingInvoices.shift();
  if (!nextInvoice) {
    activeInvoiceData = null;
    activeFileName = '';
    activeOcrText = '';
    reviewPanel.classList.add('hidden');
    return;
  }

  activeInvoiceData = nextInvoice.invoice_data || {};
  activeFileName = nextInvoice.filename || '';
  activeOcrText = nextInvoice.ocr_text || '';
  renderInvoice(activeInvoiceData);
  populateReviewForm(activeInvoiceData);
  reviewPanel.classList.remove('hidden');

  if (nextInvoice.duplicate_detected && nextInvoice.duplicate_invoice) {
    setMessage(
      'error',
      `Duplicate invoice detected for ${activeFileName}. Review before saving.`
    );
    setSystemStatus('Duplicate');
  } else {
    setMessage('success', `Ready to review ${activeFileName}.`);
    setSystemStatus('Review');
  }
  reviewPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

const handleInvoiceResult = (result) => {
  pendingInvoices.push(result);
  if (!activeInvoiceData) {
    showNextInvoice();
  } else {
    setMessage('success', `${pendingInvoices.length} more invoice(s) waiting for review.`);
  }
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

const getSortedInvoiceEntries = () => [...savedInvoices].sort((a, b) => {
  const aDate = a.created_at ? new Date(a.created_at).getTime() : 0;
  const bDate = b.created_at ? new Date(b.created_at).getTime() : 0;
  return invoiceSortAsc ? aDate - bDate : bDate - aDate;
});

const escapeHtml = (value) => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#039;');

const downloadXls = () => {
  const rows = getSortedInvoiceEntries();
  if (!rows.length) {
    setMessage('error', 'There are no saved invoices to download.');
    return;
  }

  const headers = ['ID', 'Invoice No.', 'Date', 'Vendor', 'GSTIN', 'Total', 'Saved'];
  const body = rows.map((entry) => [
    entry.id,
    entry.invoice_number,
    entry.invoice_date,
    entry.vendor_name,
    entry.vendor_gstin,
    entry.total,
    entry.created_at ? new Date(entry.created_at).toLocaleString() : '',
  ]);
  const table = [headers, ...body]
    .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>`)
    .join('');
  const blob = new Blob([
    `<html><head><meta charset="UTF-8"></head><body><table>${table}</table></body></html>`,
  ], { type: 'application/vnd.ms-excel' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'invoices.xls';
  link.click();
  URL.revokeObjectURL(url);
  setMessage('success', 'Invoice list downloaded as XLS.');
};

const downloadPdf = () => {
  const rows = getSortedInvoiceEntries();
  if (!rows.length) {
    setMessage('error', 'There are no saved invoices to download.');
    return;
  }

  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    setMessage('error', 'Allow pop-ups to download the PDF.');
    return;
  }
  const tableRows = rows.map((entry) => `
    <tr>
      <td>${escapeHtml(entry.id)}</td>
      <td>${escapeHtml(entry.invoice_number)}</td>
      <td>${escapeHtml(entry.invoice_date)}</td>
      <td>${escapeHtml(entry.vendor_name)}</td>
      <td>${escapeHtml(entry.vendor_gstin)}</td>
      <td>${escapeHtml(entry.total)}</td>
      <td>${escapeHtml(entry.created_at ? new Date(entry.created_at).toLocaleString() : '')}</td>
    </tr>`).join('');
  printWindow.document.write(`<!doctype html><html><head><title>Invoices</title>
    <style>body{font-family:Arial,sans-serif;padding:24px;color:#111}h1{font-size:20px}
    table{border-collapse:collapse;width:100%;font-size:11px}th,td{border:1px solid #aaa;padding:7px;text-align:left}
    th{background:#eee}</style></head><body><h1>Invoice Entries</h1>
    <table><thead><tr><th>ID</th><th>Invoice No.</th><th>Date</th><th>Vendor</th><th>GSTIN</th><th>Total</th><th>Saved</th></tr></thead>
    <tbody>${tableRows}</tbody></table></body></html>`);
  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
  setMessage('success', 'PDF print dialog opened. Choose "Save as PDF".');
};

/**
 * API Call: Fetch Invoice Entries
 */
const loadInvoiceEntries = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/invoices`, {
      method: 'GET',
    });

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
  const selectedFiles = invoiceFile.files ? [...invoiceFile.files] : [];
  fileName.textContent = selectedFiles.length
    ? `${selectedFiles.length} file(s) selected: ${selectedFiles.map((file) => file.name).join(', ')}`
    : 'No files selected';
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

  confirmReviewBtn.disabled = true;
  editReviewBtn.disabled = true;
  setMessage('success', 'Saving reviewed invoice...');
  setSystemStatus('Saving invoice');

  try {
    const response = await fetch(`${API_BASE_URL}/save-review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

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
    showNextInvoice();
  } catch (error) {
    setMessage('error', error.message || 'Unable to save the reviewed invoice.');
    setSystemStatus('Error');
  } finally {
    confirmReviewBtn.disabled = false;
    editReviewBtn.disabled = false;
  }
});

// API Call: Upload & Process Invoice
uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const selectedFiles = invoiceFile.files ? [...invoiceFile.files] : [];

  if (selectedFiles.length === 0) {
    setMessage('error', 'Please choose at least one invoice file before uploading.');
    return;
  }

  const formData = new FormData();
  selectedFiles.forEach((file) => formData.append('files', file));

  submitBtn.disabled = true;
  submitBtn.textContent = 'Processing invoices...';
  processingBatch = true;
  setSystemStatus(`Processing ${selectedFiles.length} invoice(s)`);
  setMessage('success', 'Uploading invoices. Each completed extraction will appear for review.');

  try {
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok || !response.body) {
      let result = {};
      try {
        result = await response.json();
      } catch (e) {
        throw new Error(`Server error (${response.status}: ${response.statusText})`);
      }
      throw new Error(result.error || result.detail || 'Upload failed.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      lines.filter((line) => line.trim()).forEach((line) => {
        const event = JSON.parse(line);
        if (event.type === 'invoice') {
          handleInvoiceResult(event.result);
        } else if (event.type === 'error') {
          setMessage('error', `${event.filename}: ${event.error}`);
          setSystemStatus('Error');
        }
      });
      if (done) break;
    }
    if (buffer.trim()) {
      const event = JSON.parse(buffer);
      if (event.type === 'invoice') handleInvoiceResult(event.result);
    }
  } catch (error) {
    setMessage('error', error.message || 'An unexpected error occurred.');
    setSystemStatus('Error');
  } finally {
    processingBatch = false;
    submitBtn.disabled = false;
    submitBtn.textContent = 'Process invoices';
    if (pendingInvoices.length > 0 && !activeInvoiceData) showNextInvoice();
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

if (downloadFormat) {
  downloadFormat.addEventListener('change', () => {
    if (downloadFormat.value === 'xls') downloadXls();
    if (downloadFormat.value === 'pdf') downloadPdf();
    downloadFormat.value = '';
  });
}

// Initial Loading
updateSortButtonText();
loadInvoiceEntries();