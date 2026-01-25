# ⚡ Quick Start Guide - AM Digitals Marketplace

## 🚀 5 Minit untuk Live!

### Step 1: Verify Files (✅ Completed)

Pastikan semua files ada:
```
✓ index.html
✓ product-detail.html
✓ login.html
✓ admin-panel.html
✓ css/ (4 files)
✓ js/ (4 files)
✓ data/products.json
```

### Step 2: Test Locally (Optional)

**Option A: Python HTTP Server**
```bash
cd am-digitals-marketplace
python -m http.server 8080
```
Buka: http://localhost:8080

**Option B: VS Code Live Server**
1. Install extension "Live Server"
2. Right-click `index.html` → "Open with Live Server"

**Option C: Node.js HTTP Server**
```bash
npx http-server -p 8080
```

### Step 3: Deploy ke Netlify (Recommended)

#### Method 1: Drag & Drop (PALING MUDAH)
1. Pergi ke: https://app.netlify.com/drop
2. Drag folder `am-digitals-marketplace` ke browser
3. ✅ Done! Website live dalam 1 minit

#### Method 2: GitHub + Netlify
```bash
# 1. Create Git repo
git init
git add .
git commit -m "Initial commit"

# 2. Push to GitHub
git remote add origin https://github.com/[username]/[repo-name].git
git push -u origin main

# 3. Connect Netlify to GitHub
# - Login Netlify
# - New site from Git
# - Select repository
# - Deploy!
```

---

## 🎯 Customize untuk Bisnes Anda

### 1. Update Nombor WhatsApp

**File**: `js/whatsapp.js` (Line 9)
```javascript
this.phoneNumber = '01112576412'; // ← Tukar dengan nombor anda
```

### 2. Update Product Data

**Two Options**:

**A) Via Admin Panel** (Recommended)
1. Buka: `https://yoursite.com/login.html`
2. Login (admin/admin123)
3. Add/Edit/Delete produk
4. Data auto-save di browser LocalStorage

**B) Edit JSON File**
1. Edit: `data/products.json`
2. Format:
```json
{
  "id": "1",
  "name": "Nama Produk",
  "price": 150,
  "category": "Category Name",
  "image": "https://image-url.com/image.jpg",
  "description": "Description lengkap produk..."
}
```

### 3. Update Brand Name & Colors

**File**: `index.html`, `product-detail.html`, `login.html`, `admin-panel.html`
- Search & replace "AM Digitals" dengan brand name anda

**File**: `css/styles.css` (Line 13-20)
```css
:root {
  --primary-color: #6366f1;    /* ← Tukar ke brand color */
  --secondary-color: #ec4899;  /* ← Secondary color */
  /* ... */
}
```

### 4. Change Admin Credentials (Security)

**File**: `js/auth.js` (Line 11-12)
```javascript
ADMIN_USERNAME: 'new_admin',    // ← Tukar username
ADMIN_PASSWORD: 'new_password', // ← Tukar password
```

⚠️ **PENTING**: Tukar default password selepas deploy!

---

## 📋 Testing Checklist

Sebelum launch, test semua features:

### Homepage (index.html)
- [ ] Products load correctly
- [ ] Images display (check multiple products)
- [ ] Click product → redirect to detail page
- [ ] Responsive di mobile (Chrome DevTools)

### Product Detail (product-detail.html)
- [ ] All product info displays
- [ ] WhatsApp button visible
- [ ] Click WhatsApp button → opens WhatsApp
- [ ] Message pre-filled dengan product name & price
- [ ] Back button works

### Admin Panel (login.html)
- [ ] Login page accessible
- [ ] Statistics show correct numbers
- [ ] Click "Tambah Produk" → modal opens
- [ ] Fill form → Save → product appears in table
- [ ] Edit product → changes saved
- [ ] Delete product → confirmation → deleted
- [ ] Upload image → preview shows
- [ ] Refresh page → changes persist

### Mobile Testing
- [ ] Test di actual device (atau Chrome DevTools mobile view)
- [ ] WhatsApp button works di mobile
- [ ] All buttons touch-friendly
- [ ] Text readable tanpa zoom
- [ ] Images load properly

### Cross-Browser
- [ ] Chrome ✓
- [ ] Firefox ✓
- [ ] Edge ✓
- [ ] Safari (Mac/iPhone) ✓

---

## 🔥 Troubleshooting

### Issue: Products tidak muncul di homepage

**Possible Causes**:
1. `products.json` not found
2. JavaScript error (check browser console)
3. LocalStorage disabled

**Solutions**:
```javascript
// Open browser console (F12)
// Check for errors

// Test if products load:
console.log(productManager.getProducts());

// Reset to default:
productManager.resetToDefault();
```

### Issue: WhatsApp button tidak berfungsi

**Check**:
1. Nombor phone correct format? (011XXXXXXXX)
2. WhatsApp installed? (mobile)
3. Browser console ada errors?

**Test**:
```javascript
// Console test:
console.log(whatsappManager.generateWhatsAppLink('Test Product', 100));
// Should output: https://wa.me/601112576412?text=...
```

### Issue: Admin changes tidak save

**Possible Causes**:
1. LocalStorage disabled (private browsing)
2. Browser cache cleared
3. Using different browser

**Solutions**:
- Disable private/incognito mode
- Use same browser untuk admin
- Backup data regularly (export dari console)

### Issue: Images tidak load

**Solutions**:
1. Check image URL valid
2. Use placeholder: `https://via.placeholder.com/800x600?text=Product`
3. Upload images to image host (Imgur, Cloudinary)

---

## 💾 Backup & Restore Data

### Backup Products Data

**Method 1: Via Browser Console**
```javascript
// Copy semua products
console.log(JSON.stringify(productManager.getProducts(), null, 2));
```
Copy output → save ke file `products-backup.json`

**Method 2: Export dari LocalStorage**
```javascript
// Get raw data
console.log(localStorage.getItem('am_digitals_products'));
```

### Restore Data

**Method 1: Via Admin Panel**
Click "Reset ke Data Asal" → products reload dari `products.json`

**Method 2: Via Console**
```javascript
// Paste your backup data
const backupData = [ /* your products array */ ];
productManager.saveProducts(backupData);
location.reload();
```

---

## 🎨 Customization Ideas

### Change Hero Background
**File**: `css/styles.css` (Line 416)
```css
.hero {
  background: var(--gradient-dark);
  /* Or use image: */
  background-image: url('path/to/image.jpg');
  background-size: cover;
}
```

### Add Logo
**File**: `index.html` (Line 38)
```html
<div class="logo">
  <img src="logo.png" alt="Logo" style="height: 40px;">
  AM Digitals
</div>
```

### Change Font
**File**: `css/styles.css` (Line 91)
```css
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

:root {
  --font-family: 'Poppins', sans-serif;
}
```

### Add Footer Social Links
**File**: `index.html` (footer section)
```html
<div>
  <h4>Ikuti Kami</h4>
  <a href="https://facebook.com/..." target="_blank">
    Facebook
  </a>
  <a href="https://instagram.com/..." target="_blank">
    Instagram
  </a>
</div>
```

---

## 📊 Analytics Setup (Optional)

### Google Analytics

**Add to all HTML files before `</head>`**:
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### Facebook Pixel

```html
<!-- Facebook Pixel -->
<script>
  !function(f,b,e,v,n,t,s)
  {if(f.fbq)return;n=f.fbq=function(){n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)};
  if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
  n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];
  s.parentNode.insertBefore(t,s)}(window, document,'script',
  'https://connect.facebook.net/en_US/fbevents.js');
  fbq('init', 'YOUR_PIXEL_ID');
  fbq('track', 'PageView');
</script>
```

---

## 🔐 Security Best Practices

### Production Checklist

- [ ] **Change admin URL** dari `admin-xyz123.html` ke secret code
- [ ] **Jangan commit** `.env` files (if any)
- [ ] **Enable HTTPS** (automatic dengan Netlify/Vercel)
- [ ] **Add robots.txt** untuk hide admin page
```
User-agent: *
Disallow: /admin-*.html
```
- [ ] **Monitor access logs** (Netlify Analytics)
- [ ] **Backup data** regularly
- [ ] **Test XSS protection** (don't allow HTML dalam forms)

---

## 🎓 Next Steps

Setelah website live:

### Week 1
- [ ] Share link dengan audience
- [ ] Test WhatsApp flow dengan real customers
- [ ] Monitor analytics
- [ ] Gather feedback

### Week 2-4
- [ ] Add more products
- [ ] Optimize images
- [ ] Improve product descriptions
- [ ] A/B test different CTAs

### Month 2+
- [ ] Consider migration to database (Supabase)
- [ ] Add payment gateway integration
- [ ] Implement search & filter
- [ ] Add categories navigation
- [ ] Customer testimonials
- [ ] Email notifications

---

## 📞 Support

Jika ada masalah atau pertanyaan:

1. **Check Documentation**:
   - `README.md` - Overview
   - `ARCHITECTURE.md` - Technical details
   - `DEPLOYMENT.md` - Deployment options

2. **Debug**:
   - Browser console (F12)
   - Check file paths
   - Verify data format

3. **Community**:
   - Stack Overflow
   - Reddit r/webdev
   - Discord coding communities

---

## ✅ Launch Checklist

Final checklist sebelum announce ke public:

- [ ] All products data updated
- [ ] WhatsApp number correct
- [ ] All images loading
- [ ] SEO meta tags updated
- [ ] Favicon added (optional)
- [ ] Google Analytics installed
- [ ] Mobile responsive tested
- [ ] WhatsApp flow tested end-to-end
- [ ] Admin panel tested (add/edit/delete)
- [ ] Custom domain configured (if any)
- [ ] SSL certificate active (https://)
- [ ] Data backed up
- [ ] Social media ready (og:image, etc)

---

## 🎉 You're Ready to Launch!

Tahniah! Marketplace anda siap untuk go live. 

**Remember**:
- Start small, iterate fast
- Listen to customer feedback
- Monitor analytics
- Keep improving

**Good luck dengan bisnes digital anda!** 🚀

---

_Last updated: 2026-01-21_
