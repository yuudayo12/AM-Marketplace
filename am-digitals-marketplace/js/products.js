// ============================================
// PRODUCTS MANAGEMENT
// Handling product data with LocalStorage
// ============================================

class ProductManager {
  constructor() {
    this.storageKey = 'am_digitals_products';
    this.initialize();
  }

  // Initialize products - load from localStorage or use default data
  initialize() {
    const stored = localStorage.getItem(this.storageKey);
    if (!stored) {
      // Load default products from products.json
      this.loadDefaultProducts();
    }
  }

  // Load default products from JSON file
  async loadDefaultProducts() {
    try {
      const response = await fetch('./data/products.json');
      const products = await response.json();
      this.saveProducts(products);
      return products;
    } catch (error) {
      console.error('Error loading default products:', error);
      return [];
    }
  }

  // Get all products
  getProducts() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (!stored) return [];
      const parsed = JSON.parse(stored);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.error('Error parsing products from storage:', error);
      return [];
    }
  }

  // Get product by ID
  getProductById(id) {
    try {
      const products = this.getProducts();
      return products.find(product => String(product.id) === String(id));
    } catch (error) {
      return null;
    }
  }

  // Save products to localStorage
  saveProducts(products) {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(products));
      return true;
    } catch (error) {
      console.error('Error saving products:', error);
      return false;
    }
  }

  // Add new product
  addProduct(productData) {
    const products = this.getProducts();

    // Generate new ID
    const newId = this.generateId(products);

    const newProduct = {
      id: newId,
      name: productData.name || 'Produk Tanpa Nama',
      price: parseFloat(productData.price) || 0,
      category: productData.category || 'Lain-lain',
      image: productData.image || 'https://via.placeholder.com/800x600?text=AM+Digitals',
      description: productData.description || ''
    };

    products.push(newProduct);
    this.saveProducts(products);

    return newProduct;
  }

  // Update existing product
  updateProduct(id, productData) {
    const products = this.getProducts();
    const index = products.findIndex(p => String(p.id) === String(id));

    if (index !== -1) {
      products[index] = {
        ...products[index],
        ...productData,
        price: parseFloat(productData.price) || 0
      };
      this.saveProducts(products);
      return products[index];
    }

    return null;
  }

  // Delete product
  deleteProduct(id) {
    const products = this.getProducts();
    const filtered = products.filter(p => String(p.id) !== String(id));
    this.saveProducts(filtered);
    return filtered.length < products.length;
  }

  // Generate unique ID
  generateId(products) {
    if (!products || products.length === 0) return '1';
    const ids = products.map(p => parseInt(p.id)).filter(id => !isNaN(id));
    if (ids.length === 0) return '1';
    const maxId = Math.max(...ids);
    return String(maxId + 1);
  }

  // Search products
  searchProducts(query) {
    const products = this.getProducts();
    if (!query) return products;
    const lowercaseQuery = query.toLowerCase();

    return products.filter(product =>
      (product.name && product.name.toLowerCase().includes(lowercaseQuery)) ||
      (product.description && product.description.toLowerCase().includes(lowercaseQuery)) ||
      (product.category && product.category.toLowerCase().includes(lowercaseQuery))
    );
  }

  // Filter by category
  filterByCategory(category) {
    const products = this.getProducts();
    if (!category || category === 'all') return products;
    return products.filter(product => product.category === category);
  }

  // Get all unique categories
  getCategories() {
    const products = this.getProducts();
    const categories = products.map(p => p.category).filter(Boolean);
    return [...new Set(categories)].sort();
  }

  // Get statistics
  getStats() {
    const products = this.getProducts();
    const totalValue = products.reduce((sum, p) => sum + (parseFloat(p.price) || 0), 0);

    return {
      totalProducts: products.length,
      totalValue: totalValue,
      avgPrice: products.length > 0 ? (totalValue / products.length) : 0,
      categories: this.getCategories().length
    };
  }

  // Format price to MYR
  formatPrice(price) {
    return `RM ${parseFloat(price).toFixed(2)}`;
  }

  // Reset to default products
  async resetToDefault() {
    localStorage.removeItem(this.storageKey);
    return await this.loadDefaultProducts();
  }
}

// Export for use in other files
window.productManager = new ProductManager();
