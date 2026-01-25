// ============================================
// ADMIN PANEL LOGIC - ROBUST VERSION
// ============================================

console.log("Admin module loading...");

// ============================================
// AUTHENTICATION CHECK
// ============================================

// Display session info
function updateSessionInfo() {
    const sessionInfo = authManager.getSessionInfo();
    if (sessionInfo) {
        const sessionEl = document.getElementById('sessionInfo');
        if (sessionEl) {
            sessionEl.textContent = `👤 Logged in as ${sessionInfo.username} • Session expires in ${sessionInfo.remainingTime}`;
        }
    }
}

// Logout function
window.handleLogout = function () {
    const confirmed = confirm('Adakah anda pasti mahu logout?');
    if (confirmed) {
        authManager.logout();
        window.location.href = 'login.html';
    }
};

// ============================================
// PRODUCT MANAGEMENT
// ============================================

let editingProductId = null;
let allProducts = [];

async function initAdmin() {
    console.log("Initializing admin panel...");

    // Protect this page
    if (!authManager.protectPage('login.html')) {
        console.warn("User not authenticated, redirecting...");
        return;
    }

    try {
        // Load products
        let products = productManager.getProducts();

        // Jika empty, cuba load dari JSON
        if (!products || products.length === 0) {
            console.log('No products in storage, loading from JSON...');
            products = await productManager.loadDefaultProducts();
        }

        allProducts = products || [];
        renderProducts(allProducts);
        updateStats(allProducts);
        updateSessionInfo();

        setInterval(updateSessionInfo, 60000);
        console.log("Admin panel ready!");

    } catch (error) {
        console.error('Error initializing admin:', error);
    }
}

// RENDER TABLE
window.renderProducts = function (products) {
    const tbody = document.getElementById('productsTableBody');
    if (!tbody) return;

    if (!products || products.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 3rem;">
                    <h3 style="color: var(--text-muted);">Tiada Produk</h3>
                    <p style="color: var(--text-muted);">Klik "Load Sample Products" untuk muat data sample.</p>
                </td>
            </tr>
        `;
        const countEl = document.getElementById('productCount');
        if (countEl) countEl.textContent = '0';
        return;
    }

    tbody.innerHTML = products.map(product => `
        <tr>
            <td><strong>#${product.id}</strong></td>
            <td>
                <img src="${product.image}" class="table-product-image" onerror="this.src='https://via.placeholder.com/60x60?text=No+Image'"/>
            </td>
            <td><div class="table-product-name">${product.name}</div></td>
            <td><span class="badge">${product.category}</span></td>
            <td class="table-product-price">RM ${parseFloat(product.price).toFixed(2)}</td>
            <td>
                <div class="table-actions">
                    <button class="btn-icon btn-edit" onclick="openEditModal('${product.id}')" title="Edit">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                    </button>
                    <button class="btn-icon btn-delete" onclick="confirmDelete('${product.id}')" title="Padam">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');

    const countEl = document.getElementById('productCount');
    if (countEl) countEl.textContent = products.length;
};

// ACTIONS
window.openAddModal = function () {
    editingProductId = null;
    document.getElementById('modalTitle').textContent = 'Tambah Produk Baru';
    document.getElementById('btnSubmit').textContent = 'Tambah Produk';
    document.getElementById('productForm').reset();
    document.getElementById('modalOverlay').classList.remove('hidden');
};

window.openEditModal = function (productId) {
    console.log("Editing product:", productId);
    editingProductId = productId;
    const product = productManager.getProductById(productId);

    if (!product) {
        alert('Produk tidak dijumpai');
        return;
    }

    document.getElementById('modalTitle').textContent = 'Edit Produk';
    document.getElementById('btnSubmit').textContent = 'Simpan Perubahan';

    document.getElementById('productName').value = product.name;
    document.getElementById('productPrice').value = product.price;
    document.getElementById('productCategory').value = product.category;
    document.getElementById('productImageUrl').value = product.image;
    document.getElementById('productDescription').value = product.description;

    document.getElementById('modalOverlay').classList.remove('hidden');
};

window.closeModal = function () {
    document.getElementById('modalOverlay').classList.add('hidden');
    editingProductId = null;
};

window.handleFormSubmit = function (e) {
    if (e) e.preventDefault();

    const formData = {
        name: document.getElementById('productName').value.trim(),
        price: document.getElementById('productPrice').value,
        category: document.getElementById('productCategory').value.trim(),
        image: document.getElementById('productImageUrl').value.trim() || 'https://via.placeholder.com/800x600?text=AM+Digitals',
        description: document.getElementById('productDescription').value.trim()
    };

    try {
        if (editingProductId) {
            productManager.updateProduct(editingProductId, formData);
        } else {
            productManager.addProduct(formData);
        }

        allProducts = productManager.getProducts();
        renderProducts(allProducts);
        updateStats(allProducts);
        closeModal();
        showToast('Berjaya simpan!', 'success');
    } catch (error) {
        alert('Ralat: ' + error.message);
    }
};

window.confirmDelete = function (productId) {
    const product = productManager.getProductById(productId);
    if (!product) return;

    if (confirm(`Padam "${product.name}"?`)) {
        productManager.deleteProduct(productId);
        allProducts = productManager.getProducts();
        renderProducts(allProducts);
        updateStats(allProducts);
        showToast('Produk dipadam', 'success');
    }
};

window.searchProducts = function () {
    const query = document.getElementById('searchInput').value.toLowerCase();
    const filtered = allProducts.filter(p =>
        p.name.toLowerCase().includes(query) || p.category.toLowerCase().includes(query)
    );
    renderProducts(filtered);
};

window.loadSampleProducts = async function () {
    if (confirm('Muat 20 sample?')) {
        allProducts = await productManager.resetToDefault();
        renderProducts(allProducts);
        updateStats(allProducts);
    }
};

window.resetToDefault = async function () {
    if (confirm('Reset data?')) {
        allProducts = await productManager.resetToDefault();
        renderProducts(allProducts);
        updateStats(allProducts);
    }
};

window.deleteAllProducts = function () {
    if (confirm('PADAM SEMUA?')) {
        productManager.saveProducts([]);
        allProducts = [];
        renderProducts([]);
        updateStats([]);
    }
};

window.updateStats = function (products) {
    document.getElementById('quickTotal').textContent = products.length;
    const catCount = [...new Set(products.map(p => p.category))].length;
    document.getElementById('quickCategories').textContent = catCount;
    const totalV = products.reduce((s, p) => s + parseFloat(p.price), 0);
    document.getElementById('quickValue').textContent = `RM ${totalV.toFixed(2)}`;
};

window.showToast = function (message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.background = type === 'success' ? '#10b981' : '#ef4444';
    toast.style.color = 'white';
    toast.style.padding = '1rem 2rem';
    toast.style.borderRadius = '8px';
    toast.style.zIndex = '9999';
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
};

// RUN INITIALIZATION
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdmin);
} else {
    initAdmin();
}
