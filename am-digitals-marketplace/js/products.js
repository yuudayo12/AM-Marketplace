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
    const stored = localStorage.getItem(this.storageKey);
    return stored ? JSON.parse(stored) : [];
  }

  // Get product by ID
  getProductById(id) {
    const products = this.getProducts();
    return products.find(product => product.id === id);
  }

  // Save products to localStorage
  saveProducts(products) {
    localStorage.setItem(this.storageKey, JSON.stringify(products));
  }

  // Add new product
  addProduct(productData) {
    const products = this.getProducts();
    
    // Generate new ID
    const newId = this.generateId(products);
    
    const newProduct = {
      id: newId,
      name: productData.name,
      price: parseFloat(productData.price),
      category: productData.category,
      image: productData.image,
      description: productData.description
    };

    products.push(newProduct);
    this.saveProducts(products);
    
    return newProduct;
  }

  // Update existing product
  updateProduct(id, productData) {
    const products = this.getProducts();
    const index = products.findIndex(p => p.id === id);
    
    if (index !== -1) {
      products[index] = {
        ...products[index],
        ...productData,
        price: parseFloat(productData.price)
      };
      this.saveProducts(products);
      return products[index];
    }
    
    return null;
  }

  // Delete product
  deleteProduct(id) {
    const products = this.getProducts();
    const filtered = products.filter(p => p.id !== id);
    this.saveProducts(filtered);
    return filtered.length < products.length;
  }

  // Generate unique ID
  generateId(products) {
    if (products.length === 0) return '1';
    const maxId = Math.max(...products.map(p => parseInt(p.id) || 0));
    return String(maxId + 1);
  }

  // Search products
  searchProducts(query) {
    const products = this.getProducts();
    const lowercaseQuery = query.toLowerCase();
    
    return products.filter(product => 
      product.name.toLowerCase().includes(lowercaseQuery) ||
      product.description.toLowerCase().includes(lowercaseQuery) ||
      product.category.toLowerCase().includes(lowercaseQuery)
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
    const categories = products.map(p => p.category);
    return [...new Set(categories)].sort();
  }

  // Get statistics
  getStats() {
    const products = this.getProducts();
    
    return {
      totalProducts: products.length,
      totalValue: products.reduce((sum, p) => sum + p.price, 0),
      avgPrice: products.length > 0 
        ? (products.reduce((sum, p) => sum + p.price, 0) / products.length) 
        : 0,
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
const productManager = new ProductManager();
