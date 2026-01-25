// ============================================
// WHATSAPP INTEGRATION
// Generate WhatsApp links with pre-filled messages
// ============================================

class WhatsAppManager {
    constructor() {
        // WhatsApp number (tanpa +60 prefix, akan ditambah dalam link)
        this.phoneNumber = '01112576412';
        // Format untuk Malaysia: convert 011 → 6011
        this.formattedNumber = this.formatPhoneNumber(this.phoneNumber);
    }

    // Format phone number untuk WhatsApp link
    formatPhoneNumber(number) {
        // Remove any spaces, dashes, or special characters
        let cleaned = number.replace(/[\s\-\(\)]/g, '');

        // If starts with 0, replace with country code (Malaysia = 60)
        if (cleaned.startsWith('0')) {
            cleaned = '60' + cleaned.substring(1);
        }

        // If doesn't start with 60, add it
        if (!cleaned.startsWith('60')) {
            cleaned = '60' + cleaned;
        }

        return cleaned;
    }

    // Generate WhatsApp URL dengan message
    generateWhatsAppLink(productName, productPrice = null) {
        // Base URL untuk WhatsApp Web/App
        const baseUrl = 'https://wa.me/';

        // Generate message
        let message = `Hai, saya nak beli produk: ${productName}`;

        // Tambah price jika ada
        if (productPrice) {
            message += `\n\nHarga: RM ${parseFloat(productPrice).toFixed(2)}`;
        }

        // Encode message untuk URL
        const encodedMessage = encodeURIComponent(message);

        // Complete URL
        const url = `${baseUrl}${this.formattedNumber}?text=${encodedMessage}`;

        return url;
    }

    // Generate simple WhatsApp link (tanpa product info)
    generateSimpleLink(customMessage = null) {
        const baseUrl = 'https://wa.me/';
        const defaultMessage = 'Hai, saya berminat dengan produk AM Digitals';
        const message = customMessage || defaultMessage;
        const encodedMessage = encodeURIComponent(message);

        return `${baseUrl}${this.formattedNumber}?text=${encodedMessage}`;
    }

    // Open WhatsApp dengan produk info
    openWhatsApp(productName, productPrice = null) {
        const url = this.generateWhatsAppLink(productName, productPrice);
        window.open(url, '_blank');
    }

    // Check if mobile device
    isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    // Get appropriate WhatsApp URL based on device
    getWhatsAppUrl(productName, productPrice = null) {
        const link = this.generateWhatsAppLink(productName, productPrice);

        // On mobile, WhatsApp app will open automatically
        // On desktop, WhatsApp Web will open
        return link;
    }

    // Format display number (untuk display dalam UI)
    getDisplayNumber() {
        return this.phoneNumber;
    }

    // Validate phone number format
    isValidPhoneNumber(number) {
        // Malaysian phone number format validation
        const cleaned = number.replace(/[\s\-\(\)]/g, '');

        // Malaysian mobile: 01X-XXXX XXXX (10-11 digits)
        const mobilePattern = /^(01)[0-9]{8,9}$/;

        // With country code: 601X-XXXX XXXX
        const withCodePattern = /^(601)[0-9]{8,9}$/;

        return mobilePattern.test(cleaned) || withCodePattern.test(cleaned);
    }

    // Generate WhatsApp button HTML
    generateWhatsAppButton(productName, productPrice, buttonText = 'BUY SEKARANG') {
        const url = this.generateWhatsAppLink(productName, productPrice);

        return `
      <a href="${url}" 
         class="whatsapp-button" 
         target="_blank"
         rel="noopener noreferrer"
         aria-label="Beli ${productName} melalui WhatsApp">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
        </svg>
        ${buttonText}
      </a>
    `;
    }
}

// Export instance
window.whatsappManager = new WhatsAppManager();
