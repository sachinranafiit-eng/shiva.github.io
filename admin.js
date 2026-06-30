const ADMIN_PIN = "9259599151";
const STORAGE_KEY = "shivaCatalogProducts";
const SESSION_KEY = "shivaAdminUnlocked";

const loginSection = document.querySelector("[data-admin-login]");
const appSection = document.querySelector("[data-admin-app]");
const pinInput = document.querySelector("[data-admin-pin]");
const unlockButton = document.querySelector("[data-admin-unlock]");
const lockButton = document.querySelector("[data-admin-lock]");
const loginStatus = document.querySelector("[data-login-status]");
const adminStatus = document.querySelector("[data-admin-status]");
const productForm = document.querySelector("[data-product-form]");
const productList = document.querySelector("[data-admin-list]");
const searchInput = document.querySelector("[data-admin-search]");
const categorySelect = document.querySelector("[data-admin-category]");
const editorTitle = document.querySelector("[data-editor-title]");
const previewPanel = document.querySelector("[data-admin-preview]");
const totalProducts = document.querySelector("[data-total-products]");
const totalCategories = document.querySelector("[data-total-categories]");
const totalValue = document.querySelector("[data-total-value]");
const saveMode = document.querySelector("[data-save-mode]");
const exportProductsButton = document.querySelector("[data-export-products]");
const exportJsonButton = document.querySelector("[data-export-json]");
const importJsonInput = document.querySelector("[data-import-json]");
const resetButton = document.querySelector("[data-reset-published]");
const newButton = document.querySelector("[data-new-product]");
const clearButton = document.querySelector("[data-clear-form]");
const deleteButton = document.querySelector("[data-delete-product]");
const duplicateButton = document.querySelector("[data-duplicate-product]");
const bulkFileInput = document.querySelector("[data-bulk-file]");
const bulkModeSelect = document.querySelector("[data-bulk-mode]");
const bulkCategorySelect = document.querySelector("[data-bulk-category]");
const bulkBrandInput = document.querySelector("[data-bulk-brand]");
const bulkApplyButton = document.querySelector("[data-apply-bulk]");
const bulkClearButton = document.querySelector("[data-clear-bulk]");
const bulkPreview = document.querySelector("[data-bulk-preview]");
const bulkTemplateButton = document.querySelector("[data-download-bulk-template]");

const publishedProducts = Array.isArray(window.SHIVA_CATALOG_PRODUCTS)
  ? structuredClone(window.SHIVA_CATALOG_PRODUCTS)
  : [];

let products = loadProducts();
let selectedId = products[0] ? products[0].id : "";
let pendingBulkProducts = [];

function loadProducts() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return Array.isArray(parsed) ? parsed : structuredClone(publishedProducts);
  } catch (error) {
    return structuredClone(publishedProducts);
  }
}

function persistProducts(message = "Inventory saved in this browser.") {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(products));
  setStatus(message);
  render();
}

function setStatus(message) {
  if (adminStatus) adminStatus.textContent = message;
}

function formatPrice(value) {
  return `Rs. ${new Intl.NumberFormat("en-IN").format(Number(value) || 0)}`;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function slugify(value) {
  return String(value || "item")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "item";
}

function uniqueId(base, currentId = "") {
  const clean = slugify(base);
  if (!products.some((product) => product.id === clean && product.id !== currentId)) return clean;

  let counter = 2;
  while (products.some((product) => product.id === `${clean}-${counter}` && product.id !== currentId)) {
    counter += 1;
  }
  return `${clean}-${counter}`;
}

function getFilteredProducts() {
  const query = (searchInput && searchInput.value.trim().toLowerCase()) || "";
  const category = (categorySelect && categorySelect.value) || "All";

  return products.filter((product) => {
    const matchesCategory = category === "All" || product.category === category;
    const haystack = [
      product.id,
      product.brand,
      product.model,
      product.title,
      product.category,
      product.badge
    ].join(" ").toLowerCase();
    return matchesCategory && (!query || haystack.includes(query));
  });
}

function updateCategoryOptions() {
  if (!categorySelect) return;
  const categories = [...new Set(products.map((product) => product.category).filter(Boolean))].sort();
  const currentValue = categorySelect.value || "All";
  categorySelect.innerHTML = [
    '<option value="All">All categories</option>',
    ...categories.map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`)
  ].join("");
  categorySelect.value = categories.includes(currentValue) ? currentValue : "All";
}

function renderSummary() {
  const categories = new Set(products.map((product) => product.category).filter(Boolean));
  const value = products.reduce((sum, product) => {
    const qty = Number(product.stockQty) || 0;
    return sum + ((Number(product.price) || 0) * qty);
  }, 0);

  totalProducts.textContent = String(products.length);
  totalCategories.textContent = String(categories.size);
  totalValue.textContent = formatPrice(value);
  saveMode.textContent = window.localStorage.getItem(STORAGE_KEY) ? "Local Draft" : "Published";
}

function renderList() {
  if (!productList) return;
  const filtered = getFilteredProducts();

  if (!filtered.length) {
    productList.innerHTML = '<p class="empty-cart">No inventory items found.</p>';
    return;
  }

  productList.innerHTML = filtered.map((product) => `
    <button class="admin-product-row ${product.id === selectedId ? "is-active" : ""}" type="button" data-select-product="${escapeHtml(product.id)}">
      <span>
        <strong>${escapeHtml(product.brand || "Shiva Enterprises")} ${escapeHtml(product.title || "Inventory Item")}</strong>
        <span>${escapeHtml(product.model || "Custom")} | ${escapeHtml(product.category || "Products")}</span>
        <small>${escapeHtml(product.stockStatus || (Number(product.stockQty) > 0 ? `${product.stockQty} in stock` : "Stock not set"))}</small>
      </span>
      <strong>${formatPrice(product.price)}</strong>
    </button>
  `).join("");
}

function productToForm(product) {
  const data = product || {};
  productForm.elements.id.value = data.id || "";
  productForm.elements.category.value = data.category || "Electrical";
  productForm.elements.brand.value = data.brand || "";
  productForm.elements.model.value = data.model || "";
  productForm.elements.title.value = data.title || "";
  productForm.elements.badge.value = data.badge || "";
  productForm.elements.price.value = data.price ?? "";
  productForm.elements.unit.value = data.unit || "piece";
  productForm.elements.stockQty.value = data.stockQty ?? "";
  productForm.elements.stockStatus.value = data.stockStatus || "";
  productForm.elements.priceLabel.value = data.priceLabel || "";
  productForm.elements.image.value = data.image || "";
  productForm.elements.art.value = data.art || "art-panel";
  productForm.elements.videoUrl.value = data.videoUrl || "";
  productForm.elements.offer.value = data.offer || "";
  productForm.elements.specs.value = Array.isArray(data.specs) ? data.specs.join("\n") : "";
  editorTitle.textContent = data.id ? `Editing ${data.title || data.id}` : "New Inventory Item";
  renderPreview(formToProduct(false));
}

function formToProduct(assignId = true) {
  const formData = new FormData(productForm);
  const title = String(formData.get("title") || "").trim();
  const brand = String(formData.get("brand") || "").trim();
  const model = String(formData.get("model") || "").trim();
  const rawId = String(formData.get("id") || "").trim();
  const existingId = selectedId || rawId;
  const id = assignId ? uniqueId(rawId || `${brand}-${model}-${title}`, existingId) : rawId;
  const stockQtyRaw = String(formData.get("stockQty") || "").trim();
  const specs = String(formData.get("specs") || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const product = {
    id,
    brand,
    model,
    title,
    category: String(formData.get("category") || "Electrical").trim(),
    badge: String(formData.get("badge") || "").trim(),
    price: Number(formData.get("price")) || 0,
    unit: String(formData.get("unit") || "piece").trim(),
    priceLabel: String(formData.get("priceLabel") || "").trim(),
    image: String(formData.get("image") || "").trim(),
    art: String(formData.get("art") || "art-panel").trim(),
    offer: String(formData.get("offer") || "").trim(),
    videoUrl: String(formData.get("videoUrl") || "").trim(),
    specs
  };

  if (stockQtyRaw !== "") product.stockQty = Number(stockQtyRaw) || 0;
  const stockStatus = String(formData.get("stockStatus") || "").trim();
  if (stockStatus) product.stockStatus = stockStatus;

  Object.keys(product).forEach((key) => {
    if (product[key] === "" || (Array.isArray(product[key]) && !product[key].length)) {
      delete product[key];
    }
  });

  return product;
}

function renderEditor() {
  const selectedProduct = products.find((product) => product.id === selectedId) || null;
  productToForm(selectedProduct);
}

function renderPreview(product) {
  if (!previewPanel) return;
  const specs = Array.isArray(product.specs) ? product.specs : [];
  const image = product.image
    ? `<img src="${escapeHtml(product.image)}" alt="${escapeHtml(product.title || "Product")} preview" onerror="this.remove();">`
    : `<span>${escapeHtml(product.category || "Product")}</span>`;

  previewPanel.innerHTML = `
    <article class="admin-preview-card">
      <div class="admin-preview-image">${image}</div>
      <div class="admin-preview-content">
        <span class="product-category">${escapeHtml(product.category || "Products")}</span>
        <h3>${escapeHtml(product.brand || "Shiva Enterprises")} ${escapeHtml(product.title || "Inventory Item")}</h3>
        <p>${escapeHtml(product.model || "Custom model")} | ${escapeHtml(product.badge || "Available")}</p>
        <strong>${escapeHtml(product.priceLabel || `${formatPrice(product.price)} / ${product.unit || "piece"}`)}</strong>
        ${product.offer ? `<p>${escapeHtml(product.offer)}</p>` : ""}
        <ul>${specs.map((spec) => `<li>${escapeHtml(spec)}</li>`).join("")}</ul>
      </div>
    </article>
  `;
}

function clearForm() {
  selectedId = "";
  productToForm({
    id: "",
    category: "Electrical",
    art: "art-panel",
    unit: "piece",
    specs: []
  });
  setStatus("Ready for new item.");
}

function saveCurrentProduct() {
  const product = formToProduct(true);
  if (!product.id || !product.title || !product.brand) {
    setStatus("Brand, item title and product ID are required.");
    return;
  }

  const index = products.findIndex((item) => item.id === selectedId || item.id === product.id);
  if (index >= 0) {
    products[index] = product;
  } else {
    products.unshift(product);
  }
  selectedId = product.id;
  persistProducts(`${product.title} saved.`);
}

function deleteCurrentProduct() {
  if (!selectedId) {
    setStatus("Select an item before deleting.");
    return;
  }
  const product = products.find((item) => item.id === selectedId);
  products = products.filter((item) => item.id !== selectedId);
  selectedId = products[0] ? products[0].id : "";
  persistProducts(product ? `${product.title} deleted.` : "Item deleted.");
}

function duplicateCurrentProduct() {
  const product = products.find((item) => item.id === selectedId);
  if (!product) {
    setStatus("Select an item before duplicating.");
    return;
  }
  const copy = structuredClone(product);
  copy.id = uniqueId(`${product.id}-copy`);
  copy.title = `${product.title || "Inventory Item"} Copy`;
  products.unshift(copy);
  selectedId = copy.id;
  persistProducts("Duplicate item created.");
}

function downloadFile(filename, mimeType, content) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function exportProductsJs() {
  const content = `window.SHIVA_CATALOG_PRODUCTS = ${JSON.stringify(products, null, 2)};\n`;
  downloadFile("products.js", "text/javascript", content);
  setStatus("Downloaded products.js. Upload it to GitHub root to update public inventory.");
}

function exportJson() {
  downloadFile("shiva-inventory-backup.json", "application/json", JSON.stringify(products, null, 2));
  setStatus("Downloaded inventory JSON backup.");
}

function importJson(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = JSON.parse(String(reader.result || ""));
      const imported = Array.isArray(parsed) ? parsed : parsed.products;
      if (!Array.isArray(imported)) throw new Error("JSON must be an array of products.");
      products = imported;
      selectedId = products[0] ? products[0].id : "";
      persistProducts("Imported inventory JSON.");
    } catch (error) {
      setStatus(error.message || "Could not import JSON.");
    }
  };
  reader.readAsText(file);
}

function normalizeHeader(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

function getRowValue(row, keys) {
  const normalizedRow = Object.entries(row).reduce((lookup, [key, value]) => {
    lookup[normalizeHeader(key)] = value;
    return lookup;
  }, {});

  for (const key of keys) {
    const value = normalizedRow[normalizeHeader(key)];
    if (value !== undefined && String(value).trim() !== "") return String(value).trim();
  }
  return "";
}

function parseMoney(value) {
  const cleaned = String(value || "")
    .replace(/,/g, "")
    .replace(/[^\d.-]/g, "");
  return Number(cleaned) || 0;
}

function parseQuantity(value) {
  const cleaned = String(value || "")
    .replace(/,/g, "")
    .replace(/[^\d.-]/g, "");
  return Number(cleaned) || 0;
}

function splitTechnicalData(value) {
  return String(value || "")
    .split(/\r?\n|;|\|/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"' && quoted && next === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(cell);
      if (row.some((value) => String(value).trim() !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }

  row.push(cell);
  if (row.some((value) => String(value).trim() !== "")) rows.push(row);
  if (!rows.length) return [];

  const headers = rows[0].map((header) => String(header || "").trim());
  return rows.slice(1).map((values) => headers.reduce((item, header, index) => {
    item[header || `Column ${index + 1}`] = values[index] || "";
    return item;
  }, {}));
}

function rowsToProducts(rows) {
  const defaultCategory = bulkCategorySelect ? bulkCategorySelect.value : "Electrical";
  const defaultBrand = (bulkBrandInput && bulkBrandInput.value.trim()) || "Shiva Enterprises";
  const usedIds = new Set(products.map((product) => product.id).filter(Boolean));
  const imported = [];
  let skipped = 0;

  rows.forEach((row) => {
    const title = getRowValue(row, ["item", "item name", "product", "product name", "name", "title", "description"]);
    if (!title) {
      skipped += 1;
      return;
    }

    const unit = getRowValue(row, ["unit", "uom", "unit of measure"]) || "piece";
    const stockQty = parseQuantity(getRowValue(row, ["qty", "qty.", "quantity", "stock", "stock qty", "stock quantity", "qnty"]));
    const price = parseMoney(getRowValue(row, ["rate", "price", "mrp", "amount", "unit rate", "selling price"]));
    const brand = getRowValue(row, ["brand", "make", "company"]) || defaultBrand;
    const model = getRowValue(row, ["model", "model no", "model number", "sku", "code"]);
    const category = getRowValue(row, ["category", "type", "group"]) || defaultCategory;
    const image = getRowValue(row, ["image", "image url", "photo", "picture"]);
    const badge = getRowValue(row, ["badge", "label", "tag"]);
    const offer = getRowValue(row, ["offer", "discount", "remark", "remarks", "note"]);
    const technicalData = getRowValue(row, ["technical data", "technical", "specs", "specification", "specifications"]);
    const baseId = slugify(`${brand}-${model || title}-${title}`);
    let id = baseId;
    let counter = 2;

    while (usedIds.has(id)) {
      id = `${baseId}-${counter}`;
      counter += 1;
    }
    usedIds.add(id);

    const specs = splitTechnicalData(technicalData);
    if (!specs.length) {
      specs.push(`Unit: ${unit}`);
      if (stockQty) specs.push(`Quantity: ${stockQty}`);
    }

    const product = {
      id,
      category,
      brand,
      model,
      title,
      price,
      unit,
      priceLabel: price ? `${formatPrice(price)} / ${unit}` : "",
      stockQty,
      stockStatus: stockQty > 0 ? `${stockQty} in stock` : "Stock not set",
      image,
      art: "art-panel",
      badge,
      offer,
      specs
    };

    Object.keys(product).forEach((key) => {
      if (product[key] === "" || (Array.isArray(product[key]) && !product[key].length)) {
        delete product[key];
      }
    });

    imported.push(product);
  });

  return { imported, skipped };
}

function loadXlsxLibrary() {
  if (window.XLSX) return Promise.resolve(window.XLSX);

  return new Promise((resolve, reject) => {
    const existingScript = document.querySelector("[data-xlsx-loader]");
    if (existingScript) {
      existingScript.addEventListener("load", () => resolve(window.XLSX));
      existingScript.addEventListener("error", () => reject(new Error("Excel reader could not load. Save the sheet as CSV and upload again.")));
      return;
    }

    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js";
    script.async = true;
    script.dataset.xlsxLoader = "true";
    script.onload = () => {
      if (window.XLSX) {
        resolve(window.XLSX);
      } else {
        reject(new Error("Excel reader could not start. Save the sheet as CSV and upload again."));
      }
    };
    script.onerror = () => reject(new Error("Excel reader could not load. Save the sheet as CSV and upload again."));
    document.head.appendChild(script);
  });
}

function renderBulkPreview(message = "") {
  if (!bulkPreview) return;

  if (!pendingBulkProducts.length) {
    bulkPreview.innerHTML = `<p>${escapeHtml(message || "No Excel file selected.")}</p>`;
    if (bulkApplyButton) bulkApplyButton.disabled = true;
    if (bulkClearButton) bulkClearButton.disabled = true;
    return;
  }

  const visibleProducts = pendingBulkProducts.slice(0, 12);
  bulkPreview.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Item</th>
          <th>Brand</th>
          <th>Category</th>
          <th>Unit</th>
          <th>Qty.</th>
          <th>Rate</th>
        </tr>
      </thead>
      <tbody>
        ${visibleProducts.map((product) => `
          <tr>
            <td>${escapeHtml(product.title)}</td>
            <td>${escapeHtml(product.brand || "Shiva Enterprises")}</td>
            <td>${escapeHtml(product.category || "Electrical")}</td>
            <td>${escapeHtml(product.unit || "piece")}</td>
            <td>${escapeHtml(product.stockQty ?? "")}</td>
            <td>${formatPrice(product.price)}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
    <p>${escapeHtml(message || `${pendingBulkProducts.length} item(s) ready to import.`)}</p>
  `;
  if (bulkApplyButton) bulkApplyButton.disabled = false;
  if (bulkClearButton) bulkClearButton.disabled = false;
}

function handleBulkRows(rows, fileName) {
  const { imported, skipped } = rowsToProducts(rows);
  pendingBulkProducts = imported;
  const skippedText = skipped ? ` ${skipped} blank row(s) skipped.` : "";
  renderBulkPreview(`${imported.length} item(s) loaded from ${fileName}.${skippedText}`);
  setStatus(imported.length ? "Review imported items, then click Add Imported Items." : "No valid item rows found.");
}

function importBulkFile(file) {
  const extension = file.name.split(".").pop().toLowerCase();
  const reader = new FileReader();

  reader.onload = async () => {
    try {
      if (extension === "csv") {
        handleBulkRows(parseCsv(String(reader.result || "")), file.name);
        return;
      }

      setStatus("Reading Excel file...");
      renderBulkPreview("Reading Excel file. Please wait.");

      const XLSX = await loadXlsxLibrary();
      const workbook = XLSX.read(new Uint8Array(reader.result), { type: "array" });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      const rows = XLSX.utils.sheet_to_json(sheet, { defval: "", raw: false });
      handleBulkRows(rows, file.name);
    } catch (error) {
      pendingBulkProducts = [];
      renderBulkPreview(error.message || "Could not read uploaded file.");
      setStatus(error.message || "Could not read uploaded file.");
    }
  };

  if (extension === "csv") {
    reader.readAsText(file);
  } else {
    reader.readAsArrayBuffer(file);
  }
}

function applyBulkImport() {
  if (!pendingBulkProducts.length) {
    setStatus("Upload an Excel or CSV file first.");
    return;
  }

  if (bulkModeSelect && bulkModeSelect.value === "replace") {
    products = structuredClone(pendingBulkProducts);
  } else {
    products = [...structuredClone(pendingBulkProducts), ...products];
  }

  selectedId = products[0] ? products[0].id : "";
  const count = pendingBulkProducts.length;
  pendingBulkProducts = [];
  renderBulkPreview(`${count} imported item(s) added. Click Export products.js for GitHub publishing.`);
  if (bulkFileInput) bulkFileInput.value = "";
  persistProducts(`${count} bulk item(s) imported.`);
}

function clearBulkImport() {
  pendingBulkProducts = [];
  if (bulkFileInput) bulkFileInput.value = "";
  renderBulkPreview("Bulk import cleared.");
  setStatus("Bulk import cleared.");
}

function downloadBulkTemplate() {
  const template = [
    ["item", "unit", "Qty.", "rate", "brand", "category", "model", "image", "offer", "technical data"],
    ["LED Bulb 12W Cool White", "piece", "10", "180", "Philips", "Electrical", "12W-CW", "assets/products/led-bulb.jpg", "Up to 40% discount", "Wattage: 12W; Color: Cool White"],
    ["6A Modular Switch", "piece", "20", "95", "Schneider Electric", "Electrical", "6A-1W", "assets/products/switch.jpg", "Project rate available", "Rating: 6A; Type: 1 way"]
  ].map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n");
  downloadFile("shiva-bulk-upload-template.csv", "text/csv", template);
  setStatus("Downloaded bulk upload CSV template.");
}

function resetToPublished() {
  products = structuredClone(publishedProducts);
  selectedId = products[0] ? products[0].id : "";
  window.localStorage.removeItem(STORAGE_KEY);
  setStatus("Reset to published products.");
  render();
}

function render() {
  updateCategoryOptions();
  renderSummary();
  renderList();
  renderEditor();
}

function unlock() {
  const value = pinInput ? pinInput.value.trim() : "";
  if (value !== ADMIN_PIN) {
    if (loginStatus) loginStatus.textContent = "Wrong PIN.";
    return;
  }
  window.sessionStorage.setItem(SESSION_KEY, "yes");
  loginSection.hidden = true;
  appSection.hidden = false;
  render();
}

function lock() {
  window.sessionStorage.removeItem(SESSION_KEY);
  appSection.hidden = true;
  loginSection.hidden = false;
  if (pinInput) pinInput.value = "";
}

unlockButton.addEventListener("click", unlock);
pinInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") unlock();
});
lockButton.addEventListener("click", lock);

productList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-select-product]");
  if (!button) return;
  selectedId = button.dataset.selectProduct;
  render();
});

productForm.addEventListener("submit", (event) => {
  event.preventDefault();
  saveCurrentProduct();
});

productForm.addEventListener("input", () => {
  renderPreview(formToProduct(false));
});

searchInput.addEventListener("input", renderList);
categorySelect.addEventListener("change", renderList);
newButton.addEventListener("click", clearForm);
clearButton.addEventListener("click", clearForm);
deleteButton.addEventListener("click", deleteCurrentProduct);
duplicateButton.addEventListener("click", duplicateCurrentProduct);
exportProductsButton.addEventListener("click", exportProductsJs);
exportJsonButton.addEventListener("click", exportJson);
resetButton.addEventListener("click", resetToPublished);
importJsonInput.addEventListener("change", (event) => {
  const file = event.target.files && event.target.files[0];
  if (file) importJson(file);
  event.target.value = "";
});

bulkFileInput.addEventListener("change", (event) => {
  const file = event.target.files && event.target.files[0];
  if (file) importBulkFile(file);
});

bulkApplyButton.addEventListener("click", applyBulkImport);
bulkClearButton.addEventListener("click", clearBulkImport);
bulkTemplateButton.addEventListener("click", downloadBulkTemplate);

if (window.sessionStorage.getItem(SESSION_KEY) === "yes") {
  loginSection.hidden = true;
  appSection.hidden = false;
  render();
}
