# 🛒 AM Digitals - Marketplace Produk Digital

Marketplace ringkas dan modern untuk menjual produk digital dalam Bahasa Melayu.

## 🎯 Ciri-Ciri Utama

### Pelanggan (Frontend)
- ✅ Paparan senarai produk (20 produk)
- ✅ Detail produk lengkap dengan gambar
- ✅ Butang "BUY SEKARANG" dengan WhatsApp integration
- ✅ Mobile-first responsive design
- ✅ Fast-loading & ringan

### Admin Panel
- ✅ Login Page: `login.html` (Secure Auth)
- ✅ Admin Dashboard: `admin-panel.html`
- ✅ Tambah, edit, padam produk
- ✅ Upload/edit gambar produk

## 🛠️ Teknologi

- **Frontend**: HTML5, CSS3 (Modern Minimalist), JavaScript (Vanilla)
- **Data Storage**: LocalStorage (boleh migrate ke Supabase/Firebase kemudian)
- **Image Storage**: Base64 / External URLs
- **WhatsApp API**: Deep-link integration

## 📁 Struktur Folder

```
am-digitals-marketplace/
├── index.html              # Homepage - senarai produk
├── product-detail.html     # Halaman detail produk
├── login.html              # Admin Login Page
├── admin-panel.html        # Admin Dashboard (Protected)
├── css/
│   ├── styles.css          # Global styles
│   ├── products.css        # Product listing styles
│   ├── product-detail.css  # Product detail styles
│   └── admin.css           # Admin panel styles
├── js/
│   ├── app.js              # Main app logic
│   ├── products.js         # Product management
│   ├── whatsapp.js         # WhatsApp integration
│   └── admin.js            # Admin panel logic
├── data/
│   └── products.json       # Sample product data (initial)
├── images/
│   └── placeholder/        # Placeholder images
├── package.json
└── README.md
```

## 🚀 Cara Guna

### Development
```bash
# Method 1: Guna Python HTTP Server
python -m http.server 8080

# Method 2: Guna Node HTTP Server
npx http-server -p 8080

# Method 3: Live Server (VS Code Extension)
```

Kemudian buka: `http://localhost:8080`

### Production (Deploy Percuma)

#### Option 1: Netlify (Recommended)
1. Daftar account percuma di [Netlify](https://netlify.com)
2. Drag & drop folder projek
3. Done! 🎉

#### Option 2: Vercel
1. Install Vercel CLI: `npm i -g vercel`
2. Run: `vercel`
3. Follow prompts

#### Option 3: GitHub Pages
1. Push ke GitHub repository
2. Enable GitHub Pages di Settings
3. Choose main branch

## 📝 Cara Guna Admin Panel

1. Buka: `http://localhost:8080/login.html`
2. Login (Username: `admin`, Password: `admin123`)
3. Tambah produk baru dengan klik "Tambah Produk"
4. Edit/Padam produk yang sedia ada
5. Data disimpan dalam LocalStorage browser

**⚠️ Nota**: Sila tukar password default dalam `js/auth.js` sebelum production!

## 🔗 WhatsApp Integration

Butang "BUY SEKARANG" akan auto-generate mesej:
```
Hai, saya nak beli produk: {NAMA PRODUK}
```

Nombor WhatsApp: `01112576412`

Format link: `https://wa.me/60{nombor}?text={mesej}`

## 📱 Mobile-First Design

- Responsive untuk semua screen sizes
- Touch-friendly buttons (minimum 44px)
- Fast loading (<2s)
- Optimized images

## 🎨 Design System

- **Colors**: Modern gradient dengan vibrant accents
- **Typography**: Clean sans-serif fonts
- **Spacing**: Consistent 8px grid
- **Animations**: Smooth micro-interactions

## 🔮 Future Enhancements

Kemudahan untuk dikembangkan:
- [ ] Integrate dengan Supabase database
- [ ] Payment gateway (Stripe, PayPal, local banks)
- [ ] Email notifications
- [ ] Search & filter produk
- [ ] Categories/tags
- [ ] Customer reviews
- [ ] Analytics dashboard

## 📞 Sokongan

WhatsApp: 01112576412
