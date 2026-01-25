/**
 * AM Digitals - Authentication System
 * Secure admin authentication with session management
 */

const authManager = {
    // Admin credentials (In production, use backend authentication)
    ADMIN_USERNAME: 'admin',
    ADMIN_PASSWORD: 'admin123', // Change this to your secure password
    SESSION_KEY: 'am_digitals_admin_session',
    SESSION_DURATION: 24 * 60 * 60 * 1000, // 24 hours

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        const session = this.getSession();

        if (!session) {
            return false;
        }

        // Check if session has expired
        const now = new Date().getTime();
        if (now > session.expiresAt) {
            this.logout();
            return false;
        }

        return true;
    },

    /**
     * Get current session
     */
    getSession() {
        try {
            const sessionData = localStorage.getItem(this.SESSION_KEY);
            return sessionData ? JSON.parse(sessionData) : null;
        } catch (error) {
            console.error('Error reading session:', error);
            return null;
        }
    },

    /**
     * Login with username and password
     */
    login(username, password) {
        // Validate credentials
        if (username !== this.ADMIN_USERNAME || password !== this.ADMIN_PASSWORD) {
            return {
                success: false,
                message: 'Username atau password salah!'
            };
        }

        // Create session
        const now = new Date().getTime();
        const session = {
            username: username,
            loginTime: now,
            expiresAt: now + this.SESSION_DURATION
        };

        try {
            localStorage.setItem(this.SESSION_KEY, JSON.stringify(session));
            return {
                success: true,
                message: 'Login berjaya!'
            };
        } catch (error) {
            console.error('Error saving session:', error);
            return {
                success: false,
                message: 'Error menyimpan session'
            };
        }
    },

    /**
     * Logout and clear session
     */
    logout() {
        localStorage.removeItem(this.SESSION_KEY);
    },

    /**
     * Protect page - redirect to login if not authenticated
     */
    protectPage(loginPageUrl = 'login.html') {
        if (!this.isAuthenticated()) {
            window.location.href = loginPageUrl;
            return false;
        }
        return true;
    },

    /**
     * Get session info
     */
    getSessionInfo() {
        const session = this.getSession();
        if (!session) return null;

        const now = new Date().getTime();
        const remainingTime = session.expiresAt - now;
        const remainingHours = Math.floor(remainingTime / (60 * 60 * 1000));
        const remainingMinutes = Math.floor((remainingTime % (60 * 60 * 1000)) / (60 * 1000));

        return {
            username: session.username,
            loginTime: new Date(session.loginTime),
            expiresAt: new Date(session.expiresAt),
            remainingTime: `${remainingHours}h ${remainingMinutes}m`
        };
    },

    /**
     * Extend session
     */
    extendSession() {
        const session = this.getSession();
        if (!session) return false;

        const now = new Date().getTime();
        session.expiresAt = now + this.SESSION_DURATION;

        try {
            localStorage.setItem(this.SESSION_KEY, JSON.stringify(session));
            return true;
        } catch (error) {
            console.error('Error extending session:', error);
            return false;
        }
    }
};
// Export for use in other files
window.authManager = authManager;

// Auto-extend session on user activity
let activityTimeout;
function resetActivityTimer() {
    clearTimeout(activityTimeout);
    activityTimeout = setTimeout(() => {
        if (authManager.isAuthenticated()) {
            authManager.extendSession();
        }
    }, 5 * 60 * 1000); // Extend every 5 minutes of activity
}

// Track user activity
if (typeof window !== 'undefined') {
    ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(event => {
        document.addEventListener(event, resetActivityTimer, true);
    });
}
