# 🚀 Panduan Deployment - AM Digitals Marketplace

Marketplace ini boleh di-deploy secara **PERCUMA** menggunakan beberapa platform. Berikut adalah panduan lengkap.

---

## 📋 Pre-Deployment Checklist

Sebelum deploy, pastikan:
- ✅ Semua file ada dalam folder projek
- ✅ Data produk (`data/products.json`) sudah dikemas kini
- ✅ Nombor WhatsApp betul dalam `js/whatsapp.js` (semasa: 01112576412)
- ✅ Test locally dulu dengan HTTP server

---

## 🌐 Option 1: Netlify (PALING MUDAH - Recommended)

### Cara Deploy:

#### Method 1: Drag & Drop (Paling Mudah)
1. **Daftar account percuma**: [https://app.netlify.com/signup](https://app.netlify.com/signup)
2. Login ke Netlify Dashboard
3. **Drag & drop** folder `am-digitals-marketplace` terus ke Netlify
4. Tunggu deploy siap (~1 minit)
5. **Done!** ✅ Website anda live di `https://[random-name].netlify.app`

#### Method 2: Netlify CLI
```bash
# Install Netlify CLI
npm install -g netlify-cli

# Navigate to project directory
cd am-digitals-marketplace

# Login
netlify login

# Deploy
netlify deploy --prod
```

### Features Netlify:
- ✅ Free SSL (HTTPS automatic)
- ✅ CDN global (fast loading)
- ✅ Free custom domain support
- ✅ Auto deployment dari Git (optional)
- ✅ Tiada credit card diperlukan

### Custom Domain (Optional):
1. Pergi ke **Site settings → Domain management**
2. Add custom domain (contoh: `amdigitals.com`)
3. Update DNS settings mengikut arahan Netlify

---

## 🔷 Option 2: Vercel

### Cara Deploy:

```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to project
cd am-digitals-marketplace

# Deploy
vercel

# Follow prompts
```

Atau guna **Vercel Dashboard**:
1. Daftar: [https://vercel.com/signup](https://vercel.com/signup)
2. Import project dari GitHub
3. Deploy!

### Features Vercel:
- ✅ Free SSL
- ✅ Fast CDN
- ✅ Serverless functions support
- ✅ Analytics (premium tier)

---

## 📄 Option 3: GitHub Pages

### Cara Deploy:

1. **Create GitHub repository**
```bash
cd am-digitals-marketplace
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/am-digitals.git
git push -u origin main
```

2. **Enable GitHub Pages**
   - Pergi ke repository Settings
   - Scroll ke **Pages** section
   - Source: Deploy from `main` branch
   - Folder: `/` (root)
   - Save

3. **Access website**
   - URL: `https://yourusername.github.io/am-digitals/`

### Note:
- Free untuk public repositories
- Tiada server-side processing
- Perfect untuk static sites

---

## ☁️ Option 4: Firebase Hosting

### Cara Deploy:

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Initialize Firebase
cd am-digitals-marketplace
firebase init hosting

# Select:
# - Public directory: . (current directory)
# - Single-page app: No
# - Overwrite index.html: No

# Deploy
firebase deploy
```

### Features Firebase:
- ✅ Free tier: 10GB storage, 360MB/day bandwidth
- ✅ Fast CDN
- ✅ Custom domain support
- ✅ SSL automatic

---

## 🎯 Option 5: Render

1. **Daftar**: [https://render.com/](https://render.com/)
2. **New Static Site**
3. Connect Git repository atau upload files
4. Build command: (leave empty)
5. Publish directory: `.`
6. Deploy!

### Features:
- ✅ Free tier available
- ✅ SSL included
- ✅ Auto deploy from Git

---

## 🔧 Configuration After Deployment

### 1. Update WhatsApp Number (Jika Perlu)
Edit file `js/whatsapp.js`:
```javascript
this.phoneNumber = '01112576412'; // Tukar dengan nombor anda
```

### 2. Update Products Data
Edit file `data/products.json` dengan produk anda sendiri.

### 3. SEO Optimization
Update meta tags dalam:
- `index.html` (homepage)
- `product-detail.html` (detail page)

Tukar:
- Title
- Description
- Keywords
- Open Graph data

### 4. Google Analytics (Optional)
Tambah tracking code sebelum `</head>`:
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

---

## 📱 Custom Domain Setup

### Untuk Netlify:
1. Dashboard → Domain settings
2. Add custom domain
3. Update nameservers atau DNS records

### Untuk Vercel:
1. Project settings → Domains
2. Add domain
3. Update DNS (A record atau CNAME)

### DNS Configuration:
```
Type: A
Name: @
Value: [Platform IP]

Type: CNAME  
Name: www
Value: [your-site].netlify.app
```

---

## 🔐 Security Best Practices

### 1. Admin Panel URL
- URL sekarang: `/admin-xyz123.html`
- **JANGAN share** URL ini secara public
- Tukar `xyz123` kepada kod rahsia anda sendiri

### 2. LocalStorage Data
- Data produk disimpan di browser LocalStorage
- **Backup data** secara berkala
- Jangan clear browser cache jika admin

### 3. Image Hosting
Untuk produksi, gunakan platform image hosting:
- **Cloudinary** (free tier: 25GB)
- **ImgBB** (free)
- **Imgur** (free)
- **Supabase Storage** (free: 1GB)

---

## 📊 Performance Optimization

### 1. Image Optimization
- Compress images sebelum upload
- Gunakan: [TinyPNG](https://tinypng.com)
- Recommended size: <500KB per image

### 2. Lazy Loading (Already implemented via browser)
```html
<img loading="lazy" src="..." alt="...">
```

### 3. Caching
Platforms seperti Netlify & Vercel automatik enable caching.

---

## 🐛 Troubleshooting

### Issue: Products tidak muncul
**Solution**: 
- Check browser console untuk errors
- Pastikan `data/products.json` accessible
- Clear browser cache dan reload

### Issue: WhatsApp link tidak berfungsi
**Solution**:
- Check format nombor dalam `whatsapp.js`
- Pastikan WhatsApp app installed di mobile
- Test di browser berbeza

### Issue: Admin panel tidak save data
**Solution**:
- LocalStorage mungkin disabled
- Check browser privacy settings
- Guna browser lain (Chrome, Firefox)

---

## 📧 Support & Maintenance

### Backup Data
Export products dari admin panel:
```javascript
// Run di browser console
console.log(JSON.stringify(productManager.getProducts(), null, 2));
```

Copy output dan save sebagai backup.

### Update Products
1. Login ke admin panel: `https://yoursite.com/admin-xyz123.html`
2. Tambah/Edit/Padam produk
3. Data auto-save di browser

---

## 🎓 Next Steps (Enhancement Ideas)

Selepas deploy, anda boleh tambah:

1. **Database Backend** (Migrate dari LocalStorage)
   - Supabase (recommended)
   - Firebase Firestore
   - MongoDB Atlas

2. **Authentication** untuk admin
   - Firebase Auth
   - Auth0
   - Supabase Auth

3. **Payment Gateway**
   - Stripe
   - PayPal
   - Senangpay (Malaysia)
   - Billplz (Malaysia)

4. **Email Notifications**
   - EmailJS (free)
   - SendGrid
   - Mailgun

5. **Search & Filter** (already prepared in code)
6. **Product Categories** navigation
7. **Customer Reviews**
8. **WhatsApp Chatbot** integration

---

## ✅ Launch Checklist

Sebelum launch production:

- [ ] Test semua produk links
- [ ] Test WhatsApp buttons (mobile & desktop)
- [ ] Test admin panel CRUD operations
- [ ] Update SEO meta tags
- [ ] Add Google Analytics
- [ ] Setup custom domain
- [ ] Backup product data
- [ ] Test di multiple devices
- [ ] Test di multiple browsers
- [ ] Check page speed (Google PageSpeed Insights)
- [ ] Submit to Google Search Console

---

## 🎉 Congratulations!

Website marketplace digital anda sudah siap untuk deployment! 

Untuk sokongan atau pertanyaan:
- WhatsApp: 011-1257 6412
- GitHub Issues (if applicable)

**Good luck dengan bisnes digital anda!** 🚀
