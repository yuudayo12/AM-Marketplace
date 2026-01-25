// ============================================
// MAIN APP LOGIC
// Homepage - Product Listing
// ============================================

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', async () => {
  await initializeApp();
});

// Initialize the app
async function initializeApp() {
  // Check if managers exist
  if (!window.productManager || !window.whatsappManager) {
    console.error("Critical managers not loaded!");
    showError('Fail sistem (products.js/whatsapp.js) tidak dapat dimuatkan. Sila refresh halaman.');
    return;
  }

  showLoading();

  try {
    // Load products
    await loadProducts();

    // Setup scroll effect for header
    setupHeaderScroll();

    hideLoading();
  } catch (error) {
    console.error('Error initializing app:', error);
    showError('Gagal memuatkan produk. Sila refresh halaman.');
    hideLoading();
  }
}

// Load and display products
async function loadProducts() {
  const productsGrid = document.getElementById('productsGrid');

  if (!productsGrid) return;

  // Get products from ProductManager
  let products = productManager.getProducts();

  // If no products in localStorage, load from JSON
  if (products.length === 0) {
    products = await productManager.loadDefaultProducts();
  }

  // Check if products exist
  if (!products || products.length === 0) {
    showEmptyState();
    return;
  }

  // Render products
  renderProducts(products);
}

// Render products grid
function renderProducts(products) {
  const productsGrid = document.getElementById('productsGrid');

  if (!productsGrid) return;

  productsGrid.innerHTML = '';

  products.forEach(product => {
    const productCard = createProductCard(product);
    productsGrid.appendChild(productCard);
  });
}

// Create product card element
function createProductCard(product) {
  const card = document.createElement('div');
  card.className = 'product-card';
  card.onclick = () => navigateToDetail(product.id);

  card.innerHTML = `
    <div class="product-image-container">
      <img 
        src="${product.image}" 
        alt="${product.name}"
        class="product-image"
        onerror="this.src='https://via.placeholder.com/800x600?text=AM+Digitals'"
      />
      <span class="product-category">${product.category}</span>
    </div>
    
    <div class="product-content">
      <h3 class="product-name">${product.name}</h3>
      <p class="product-description">${truncateText(product.description, 100)}</p>
      
      <div class="product-footer">
        <div class="product-price-container">
          <span class="product-price-currency">Harga</span>
          <span class="product-price">RM ${product.price.toFixed(2)}</span>
        </div>
        
        <div class="product-action">
          <span>Lihat Detail</span>
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </div>
  `;

  return card;
}

// Navigate to product detail page
function navigateToDetail(productId) {
  window.location.href = `product-detail.html?id=${productId}`;
}

// Truncate text with ellipsis
function truncateText(text, maxLength) {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

// Show loading state
function showLoading() {
  const productsGrid = document.getElementById('productsGrid');
  if (!productsGrid) return;

  productsGrid.innerHTML = `
    <div class="products-loading">
      <div class="spinner"></div>
      <p>Memuatkan produk...</p>
    </div>
  `;
}

// Hide loading state
function hideLoading() {
  // Loading will be replaced by products or empty state
}

// Show empty state
function showEmptyState() {
  const productsGrid = document.getElementById('productsGrid');
  if (!productsGrid) return;

  productsGrid.innerHTML = `
    <div class="products-empty">
      <h3>Tiada Produk</h3>
      <p>Belum ada produk tersedia buat masa ini.</p>
    </div>
  `;
}

// Show error message
function showError(message) {
  const productsGrid = document.getElementById('productsGrid');
  if (!productsGrid) return;

  productsGrid.innerHTML = `
    <div class="products-empty">
      <h3>Ralat</h3>
      <p>${message}</p>
    </div>
  `;
}

// Setup header scroll effect
function setupHeaderScroll() {
  const header = document.querySelector('.header');

  if (!header) return;

  let lastScroll = 0;

  window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;

    if (currentScroll > 50) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }

    lastScroll = currentScroll;
  });
}

// Search functionality
function handleSearch(query) {
  const productsGrid = document.getElementById('productsGrid');

  if (!query) {
    // If empty query, show all products
    const products = productManager.getProducts();
    renderProducts(products);
    return;
  }

  // Filter products
  const filtered = productManager.searchProducts(query);

  if (filtered.length === 0) {
    productsGrid.innerHTML = `
            <div class="products-empty">
                <h3>Tiada Produk Dijumpai</h3>
                <p>Tiada hasil untuk "${query}". Sila cuba kata kunci lain.</p>
                <button onclick="clearSearch()" class="btn btn-outline" style="margin-top: 1rem;">Reset Carian</button>
            </div>
        `;
  } else {
    renderProducts(filtered);
  }
}

function clearSearch() {
  const searchInput = document.getElementById('searchProduct');
  if (searchInput) {
    searchInput.value = '';
    handleSearch('');
  }
}

// Filter by category (optional - can be implemented later)
function filterProducts(category) {
  const results = productManager.filterByCategory(category);
  renderProducts(results);
}

// Format currency
function formatCurrency(amount) {
  return `RM ${parseFloat(amount).toFixed(2)}`;
}

// Smooth scroll to section
function scrollToSection(sectionId) {
  const section = document.getElementById(sectionId);
  if (section) {
    section.scrollIntoView({ behavior: 'smooth' });
  }
}
