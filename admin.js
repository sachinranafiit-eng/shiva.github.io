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

const publishedProducts = Array.isArray(window.SHIVA_CATALOG_PRODUCTS)
  ? structuredClone(window.SHIVA_CATALOG_PRODUCTS)
  : [];

let products = loadProducts();
let selectedId = products[0] ? products[0].id : "";

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

if (window.sessionStorage.getItem(SESSION_KEY) === "yes") {
  loginSection.hidden = true;
  appSection.hidden = false;
  render();
}
