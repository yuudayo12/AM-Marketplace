# 🔐 Admin Panel - AM Digitals Marketplace

## Panduan Lengkap Pengurusan Produk

### 📋 Kandungan
1. [Login ke Admin Panel](#login-ke-admin-panel)
2. [Fungsi-fungsi Admin](#fungsi-fungsi-admin)
3. [Keselamatan](#keselamatan)
4. [Tips & Best Practices](#tips--best-practices)

---

## 🚀 Login ke Admin Panel

### Akses Admin Panel
1. Buka browser dan pergi ke: `login.html`
2. Masukkan credentials:
   - **Username**: `admin`
   - **Password**: `admin123`
3. Klik **Login**

### Keselamatan Login
- ✅ Session akan aktif selama **24 jam**
- ✅ Auto-extend session bila ada aktiviti
- ✅ Auto-redirect ke login jika session tamat
- ✅ Hanya admin yang authenticated boleh access admin panel

---

## ⚙️ Fungsi-fungsi Admin

### 1. **Tambah Produk Baru** ➕

**Cara:**
1. Klik butang **"Tambah Produk"** (hijau, di bahagian atas)
2. Isi maklumat produk:
   - **Nama Produk** (wajib)
   - **Harga** dalam RM (wajib)
   - **Kategori** (wajib)
   - **URL Gambar** (optional - akan guna placeholder jika kosong)
   - **Description** (wajib)
3. Klik **"Tambah Produk"**
4. Produk baru akan muncul dalam senarai

**Contoh:**
```
Nama: Website E-Commerce Premium
Harga: 2500.00
Kategori: Web Development
URL Gambar: https://example.com/ecommerce.jpg
Description: Website e-commerce lengkap dengan payment gateway, inventory management, dan admin panel.
```

---

### 2. **Edit Produk** ✏️

**Cara:**
1. Cari produk yang nak edit dalam jadual
2. Klik butang **Edit** (icon pensil, warna biru)
3. Modal akan terbuka dengan data sedia ada
4. Ubah maklumat yang nak diubah
5. Klik **"Simpan Perubahan"**

**Tips:**
- Semua field boleh diedit
- Harga akan auto-format ke 2 decimal places
- Gambar akan guna placeholder jika URL kosong

---

### 3. **Padam Produk** 🗑️

**Cara Padam 1 Produk:**
1. Cari produk yang nak padam
2. Klik butang **Delete** (icon tong sampah, warna merah)
3. Confirm deletion dalam popup
4. Produk akan dipadam terus

**Cara Padam SEMUA Produk:**
1. Scroll ke bahagian **Bulk Actions** (kotak kuning)
2. Klik butang **"DELETE ALL PRODUCTS"**
3. Confirm 2 kali (untuk keselamatan)
4. Semua produk akan dipadam

⚠️ **AMARAN**: Tindakan padam TIDAK boleh dibatalkan!

---

### 4. **Cari Produk** 🔍

**Cara:**
1. Guna search box di atas jadual
2. Taip keyword (nama, kategori, atau description)
3. Hasil akan auto-filter masa taip

**Contoh Search:**
- `website` - cari semua produk berkaitan website
- `RM 500` - cari produk dengan harga RM 500
- `Logo` - cari semua produk logo design

---

### 5. **Load Sample Products** 📦

**Cara:**
1. Klik butang **"Load Sample Products"**
2. Confirm action
3. 20 sample products akan di-load dari `products.json`

**Nota:**
- Ini akan **overwrite** data sedia ada
- Guna untuk testing atau reset ke data asal
- Semua custom products akan hilang

---

### 6. **Reset Data** 🔄

**Cara:**
1. Klik butang **"Reset Data"**
2. Confirm action
3. Data akan reset ke default products

**Guna bila:**
- Nak start fresh
- Nak buang semua custom products
- Testing purposes

---

### 7. **Statistik Dashboard** 📊

Dashboard menunjukkan:
- **Total Produk**: Jumlah semua produk
- **Kategori**: Bilangan kategori unik
- **Harga Purata**: Average harga semua produk
- **Nilai Total**: Jumlah harga semua produk

Auto-update bila:
- Tambah produk baru
- Edit produk
- Padam produk
- Search/filter

---

### 8. **Logout** 🚪

**Cara:**
1. Klik butang **"Logout"** (merah, di header)
2. Confirm logout
3. Session akan clear
4. Auto-redirect ke login page

---

## 🔒 Keselamatan

### Authentication System
```javascript
// Session Management
- Session duration: 24 jam
- Auto-extend: Setiap 5 minit aktiviti
- Auto-logout: Bila session expired
- Secure storage: LocalStorage dengan validation
```

### Tukar Password

**Cara tukar password admin:**

1. Buka file: `js/auth.js`
2. Cari baris ini:
```javascript
ADMIN_PASSWORD: 'admin123', // Change this to your secure password
```
3. Tukar `admin123` kepada password baru
4. Save file

**Contoh:**
```javascript
ADMIN_PASSWORD: 'MySecureP@ssw0rd2024!',
```

### Tukar Username

1. Buka file: `js/auth.js`
2. Cari baris ini:
```javascript
ADMIN_USERNAME: 'admin',
```
3. Tukar `admin` kepada username baru
4. Save file

---

## 💡 Tips & Best Practices

### 1. **Backup Data**
```javascript
// Export products to JSON
const products = productManager.getProducts();
const dataStr = JSON.stringify(products, null, 2);
const dataBlob = new Blob([dataStr], {type: 'application/json'});
const url = URL.createObjectURL(dataBlob);
const link = document.createElement('a');
link.href = url;
link.download = 'products-backup.json';
link.click();
```

### 2. **Gambar Produk**
- Guna URL yang stabil (jangan temporary links)
- Recommended size: 800x600px atau lebih
- Format: JPG, PNG, WebP
- Compress gambar untuk loading cepat

### 3. **Naming Convention**
```
✅ GOOD:
- "Website E-Commerce Premium"
- "Logo Design - Corporate Package"
- "Social Media Management (3 Months)"

❌ AVOID:
- "web"
- "logo123"
- "package 1"
```

### 4. **Pricing**
- Guna harga yang konsisten (contoh: 500.00, bukan 500)
- Update harga secara berkala
- Consider market rates

### 5. **Categories**
Gunakan kategori yang konsisten:
- Web Development
- Mobile Apps
- Graphic Design
- Digital Marketing
- SEO Services
- Content Creation

### 6. **Descriptions**
- Minimum 50 characters
- Explain features & benefits
- Include deliverables
- Mention timeline jika ada

---

## 🐛 Troubleshooting

### Masalah: Tak boleh login
**Penyelesaian:**
1. Check username & password betul
2. Clear browser cache
3. Try different browser
4. Check console untuk errors

### Masalah: Session expired cepat sangat
**Penyelesaian:**
1. Check system time betul
2. Extend session duration dalam `auth.js`:
```javascript
SESSION_DURATION: 48 * 60 * 60 * 1000, // 48 hours
```

### Masalah: Produk tak save
**Penyelesaian:**
1. Check LocalStorage enabled
2. Check browser storage quota
3. Clear old data
4. Try incognito mode

### Masalah: Gambar tak keluar
**Penyelesaian:**
1. Check URL valid
2. Check image accessible (no CORS issues)
3. Try different image URL
4. Guna placeholder sementara

---

## 📱 Mobile Access

Admin panel adalah **responsive** dan boleh diakses dari:
- 💻 Desktop/Laptop
- 📱 Tablet
- 📱 Mobile Phone

**Tips untuk mobile:**
- Guna landscape mode untuk table view
- Scroll horizontal untuk lihat semua columns
- Touch & hold untuk context menu

---

## 🔧 Advanced Features

### Custom Validation
Tambah validation dalam `admin-panel.html`:

```javascript
function validateProduct(data) {
    if (data.price < 0) {
        throw new Error('Harga mesti positive');
    }
    if (data.name.length < 3) {
        throw new Error('Nama produk terlalu pendek');
    }
    // Add more validations...
}
```

### Bulk Edit
Coming soon:
- Select multiple products
- Edit category for all selected
- Apply discount to selected items

---

## 📞 Support

Jika ada masalah atau soalan:
1. Check documentation ini
2. Check console untuk error messages
3. Review code comments
4. Contact developer

---

## ✅ Checklist Harian Admin

- [ ] Check new products added
- [ ] Update prices if needed
- [ ] Review product descriptions
- [ ] Check broken image links
- [ ] Backup data (weekly)
- [ ] Monitor statistics
- [ ] Test website functionality

---

## 🎯 Quick Reference

| Action | Shortcut/Method |
|--------|----------------|
| Add Product | Click "Tambah Produk" button |
| Edit Product | Click pencil icon on product row |
| Delete Product | Click trash icon on product row |
| Search | Type in search box (auto-filter) |
| Logout | Click "Logout" button in header |
| View Website | Click "Lihat Website" button |

---

**Version**: 1.0  
**Last Updated**: 2026-01-22  
**Maintained by**: AM Digitals Development Team

---

## 🔐 Security Reminder

⚠️ **PENTING:**
1. **JANGAN share** admin credentials
2. **TUKAR** default password selepas first login
3. **LOGOUT** selepas guna admin panel
4. **BACKUP** data secara berkala
5. **UPDATE** password every 3 months

---

*Dokumen ini adalah panduan lengkap untuk admin panel. Simpan untuk rujukan masa depan.*
