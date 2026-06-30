const header = document.querySelector("[data-header]");
const navToggle = document.querySelector("[data-nav-toggle]");
const nav = document.querySelector("[data-nav]");
const leadForm = document.querySelector("[data-lead-form]");
const formStatus = document.querySelector("[data-form-status]");
const productGrid = document.querySelector("[data-product-grid]");
const catalogFilters = document.querySelector("[data-catalog-filters]");
const cartList = document.querySelector("[data-cart-list]");
const cartCount = document.querySelector("[data-cart-count]");
const cartTotal = document.querySelector("[data-cart-total]");
const cartQuestion = document.querySelector("[data-cart-question]");
const cartStatus = document.querySelector("[data-cart-status]");
const sendCartButton = document.querySelector("[data-send-cart]");
const clearCartButton = document.querySelector("[data-clear-cart]");

const phoneForWhatsApp = "919259599151";
const adsConfig = window.SHIVA_ADS_CONFIG || {};
const publishedCatalogProducts = Array.isArray(window.SHIVA_CATALOG_PRODUCTS) ? window.SHIVA_CATALOG_PRODUCTS : [];
const savedCatalogProducts = (() => {
  try {
    const raw = window.localStorage && window.localStorage.getItem("shivaCatalogProducts");
    const parsed = raw ? JSON.parse(raw) : null;
    return Array.isArray(parsed) ? parsed : null;
  } catch (error) {
    return null;
  }
})();
const catalogProducts = savedCatalogProducts || publishedCatalogProducts;
const cart = new Map();

function getConversionSendTo(type) {
  return adsConfig.conversions && adsConfig.conversions[type];
}

function isConfiguredConversion(sendTo) {
  return typeof sendTo === "string" && sendTo.startsWith("AW-") && !sendTo.includes("REPLACE");
}

function trackGoogleAdsConversion(type, value = 1) {
  const sendTo = getConversionSendTo(type);
  if (!isConfiguredConversion(sendTo) || typeof window.gtag !== "function") return;

  window.gtag("event", "conversion", {
    send_to: sendTo,
    value,
    currency: "INR"
  });
}

function setHeaderState() {
  if (!header) return;
  header.classList.toggle("is-scrolled", window.scrollY > 12);
}

function formatPrice(value) {
  return `Rs. ${new Intl.NumberFormat("en-IN").format(value)}`;
}

function getProduct(productId) {
  return catalogProducts.find((product) => product.id === productId);
}

function renderProducts(filter = "All") {
  if (!productGrid) return;

  const products = filter === "All"
    ? catalogProducts
    : catalogProducts.filter((product) => product.category === filter);

  productGrid.innerHTML = products.map((product) => {
    const specs = Array.isArray(product.specs) ? product.specs : [];
    const productArt = product.art || "art-panel";
    const productBrand = product.brand || "Shiva Enterprises";
    const productTitle = product.title || "Inventory Item";
    const productModel = product.model || "Custom";
    const productUnit = product.unit || "piece";
    const stockText = product.stockStatus || (Number(product.stockQty) > 0 ? `${product.stockQty} in stock` : "");
    const visual = product.image
      ? `<div class="product-visual has-photo"><img src="${product.image}" alt="${productBrand} ${productTitle} product picture" loading="eager" decoding="async" onerror="this.parentElement.className='product-visual product-art ${productArt}'; this.remove();"></div>`
      : `<div class="product-visual product-art ${productArt}" role="img" aria-label="${productTitle} product picture"></div>`;

    return `
    <article class="product-card" data-product-id="${product.id}">
      ${visual}
      <div class="product-body">
        <div class="product-meta">
          <span class="product-category">${product.category || "Products"}</span>
          <span class="product-badge">${product.badge || "Available"}</span>
        </div>
        <p class="product-brand">${productBrand} <span>${productModel}</span></p>
        <h4>${productTitle}</h4>
        ${product.offer ? `<p class="product-offer">${product.offer}</p>` : ""}
        ${stockText ? `<p class="product-stock">${stockText}</p>` : ""}
        <ul class="product-specs">
          ${specs.map((spec) => `<li>${spec}</li>`).join("")}
        </ul>
        ${product.videoUrl ? `<a class="product-video-link" href="${product.videoUrl}" target="_blank" rel="noopener">Watch product video</a>` : ""}
        <div class="product-buy-row">
          <div class="product-price">
            <span>Starting Price</span>
            <strong>${product.priceLabel || `${formatPrice(Number(product.price) || 0)} / ${productUnit}`}</strong>
          </div>
          <button class="add-product" type="button" data-add-product="${product.id}">Add</button>
        </div>
      </div>
    </article>
  `;
  }).join("");
}

function renderCart() {
  if (!cartList || !cartCount || !cartTotal) return;

  const items = [...cart.entries()].map(([productId, quantity]) => ({
    product: getProduct(productId),
    quantity
  })).filter((item) => item.product);

  const totalQuantity = items.reduce((sum, item) => sum + item.quantity, 0);
  const total = items.reduce((sum, item) => sum + (item.product.price * item.quantity), 0);

  cartCount.textContent = totalQuantity === 1 ? "1 item" : `${totalQuantity} items`;
  cartTotal.textContent = formatPrice(total);

  if (!items.length) {
    cartList.innerHTML = '<p class="empty-cart">Add products from the list to build a quotation inquiry.</p>';
    return;
  }

  cartList.innerHTML = items.map(({ product, quantity }) => `
    <article class="cart-item">
      <div class="cart-item-title">
        <span>${product.brand} ${product.title}</span>
        <button type="button" data-remove-product="${product.id}">Remove</button>
      </div>
      <div class="cart-item-controls">
        <div class="qty-stepper" aria-label="Quantity for ${product.title}">
          <button type="button" data-decrease-product="${product.id}">-</button>
          <span>${quantity}</span>
          <button type="button" data-increase-product="${product.id}">+</button>
        </div>
        <strong class="cart-line-total">${formatPrice(product.price * quantity)}</strong>
      </div>
    </article>
  `).join("");
}

function addToCart(productId) {
  cart.set(productId, (cart.get(productId) || 0) + 1);
  renderCart();

  if (cartStatus) {
    const product = getProduct(productId);
    cartStatus.textContent = product ? `${product.title} added to inquiry list.` : "Item added to inquiry list.";
  }
}

function updateCartQuantity(productId, change) {
  const currentQuantity = cart.get(productId) || 0;
  const nextQuantity = currentQuantity + change;

  if (nextQuantity <= 0) {
    cart.delete(productId);
  } else {
    cart.set(productId, nextQuantity);
  }

  renderCart();
}

function sendCartInquiry() {
  if (!cart.size) {
    if (cartStatus) {
      cartStatus.textContent = "Please add at least one product before making an inquiry.";
    }
    return;
  }

  const items = [...cart.entries()].map(([productId, quantity]) => ({
    product: getProduct(productId),
    quantity
  })).filter((item) => item.product);

  const total = items.reduce((sum, item) => sum + (item.product.price * item.quantity), 0);
  const question = cartQuestion ? cartQuestion.value.trim() : "";
  const lines = items.map(({ product, quantity }) => {
    const lineTotal = product.price * quantity;
    return `- ${product.brand || "Shiva Enterprises"} ${product.title || "Inventory Item"} (${product.model || "Custom"}) x ${quantity} @ ${formatPrice(product.price)} = ${formatPrice(lineTotal)}`;
  });

  const inquiry = [
    "Hello Shiva Enterprises, I want to make a product quotation inquiry.",
    "",
    "Selected Items:",
    ...lines,
    "",
    `Estimated Starting Total: ${formatPrice(total)}`,
    question ? `Question / Requirement: ${question}` : "",
    "",
    "Please confirm final price after site visit, brand selection and installation scope."
  ].filter(Boolean).join("\n");

  if (cartStatus) {
    cartStatus.textContent = "Opening WhatsApp with selected products.";
  }

  trackGoogleAdsConversion("productInquiry", total || 1);
  trackGoogleAdsConversion("whatsappClick");
  window.open(`https://wa.me/${phoneForWhatsApp}?text=${encodeURIComponent(inquiry)}`, "_blank", "noopener");
}

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;

  const trackedLink = target.closest("[data-track]");
  if (!(trackedLink instanceof HTMLElement)) return;

  const trackingType = trackedLink.dataset.track;
  if (trackingType) {
    trackGoogleAdsConversion(trackingType);
  }
});

if (navToggle && header) {
  navToggle.addEventListener("click", () => {
    const isOpen = header.classList.toggle("nav-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
    navToggle.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
  });
}

if (nav && header && navToggle) {
  nav.addEventListener("click", (event) => {
    if (event.target instanceof HTMLAnchorElement) {
      header.classList.remove("nav-open");
      navToggle.setAttribute("aria-expanded", "false");
      navToggle.setAttribute("aria-label", "Open navigation");
    }
  });
}

if (catalogFilters) {
  catalogFilters.addEventListener("click", (event) => {
    const button = event.target;
    if (!(button instanceof HTMLButtonElement)) return;

    const filter = button.dataset.filter || "All";
    catalogFilters.querySelectorAll("button").forEach((filterButton) => {
      filterButton.classList.toggle("active", filterButton === button);
    });
    renderProducts(filter);
  });
}

if (productGrid) {
  productGrid.addEventListener("click", (event) => {
    const button = event.target;
    if (!(button instanceof HTMLButtonElement)) return;

    const productId = button.dataset.addProduct;
    if (productId) {
      addToCart(productId);
    }
  });
}

if (cartList) {
  cartList.addEventListener("click", (event) => {
    const button = event.target;
    if (!(button instanceof HTMLButtonElement)) return;

    if (button.dataset.increaseProduct) {
      updateCartQuantity(button.dataset.increaseProduct, 1);
    }

    if (button.dataset.decreaseProduct) {
      updateCartQuantity(button.dataset.decreaseProduct, -1);
    }

    if (button.dataset.removeProduct) {
      cart.delete(button.dataset.removeProduct);
      renderCart();
    }
  });
}

if (sendCartButton) {
  sendCartButton.addEventListener("click", sendCartInquiry);
}

if (clearCartButton) {
  clearCartButton.addEventListener("click", () => {
    cart.clear();
    renderCart();
    if (cartStatus) {
      cartStatus.textContent = "Selected items cleared.";
    }
  });
}

if (leadForm) {
  leadForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(leadForm);
    const details = {
      name: String(formData.get("name") || "").trim(),
      phone: String(formData.get("phone") || "").trim(),
      email: String(formData.get("email") || "").trim(),
      service: String(formData.get("service") || "").trim(),
      location: String(formData.get("location") || "").trim(),
      message: String(formData.get("message") || "").trim()
    };

    const inquiry = [
      "Hello Shiva Enterprises, I would like to request a free site visit/technical consultation.",
      "",
      `Name: ${details.name}`,
      `Phone: ${details.phone}`,
      details.email ? `Email: ${details.email}` : "",
      `Service Required: ${details.service}`,
      details.location ? `Project Location: ${details.location}` : "",
      details.message ? `Message: ${details.message}` : ""
    ].filter(Boolean).join("\n");

    const whatsappUrl = `https://wa.me/${phoneForWhatsApp}?text=${encodeURIComponent(inquiry)}`;

    if (formStatus) {
      formStatus.textContent = "Opening WhatsApp with your consultation request.";
    }

    trackGoogleAdsConversion("consultationLead");
    trackGoogleAdsConversion("whatsappClick");
    window.open(whatsappUrl, "_blank", "noopener");
  });
}

renderProducts();
renderCart();
window.addEventListener("scroll", setHeaderState, { passive: true });
setHeaderState();
