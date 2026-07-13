// static/components/auth.js
import { RestClient } from '../api/rest.js';

export class AuthComponent {
    constructor(authContainerId, dashboardId, store, onAuthSuccess) {
        this.container = document.getElementById(authContainerId);
        this.dashboard = document.getElementById(dashboardId);
        this.store = store;
        this.onAuthSuccess = onAuthSuccess;
        
        this.isLoginMode = true; // true = login, false = register
        
        // Subscribe to auth state updates
        this.store.subscribe((state) => this.handleAuthState(state));
        
        this.init();
    }

    init() {
        this.renderForm();
        this.handleAuthState(this.store.state);
    }

    handleAuthState(state) {
        if (state.token) {
            // Logged in: show dashboard, hide auth form
            if (this.container) this.container.style.display = 'none';
            if (this.dashboard) this.dashboard.style.display = 'grid';
        } else {
            // Logged out: show auth form, hide dashboard
            if (this.container) this.container.style.display = 'flex';
            if (this.dashboard) this.dashboard.style.display = 'none';
            this.renderForm();
        }
    }

    toggleMode() {
        this.isLoginMode = !this.isLoginMode;
        this.renderForm();
    }

    renderForm() {
        if (!this.container) return;
        
        const title = this.isLoginMode ? 'Welcome Back, Agent' : 'Create Access Account';
        const subtitle = this.isLoginMode ? 'Authenticate to link Jarvis Core' : 'Register a new user identity';
        const buttonText = this.isLoginMode ? 'Access Core' : 'Register Core';
        const switchText = this.isLoginMode 
            ? "New agent? <span class='auth-link' id='auth-switch-btn'>Establish credentials</span>" 
            : "Have credentials? <span class='auth-link' id='auth-switch-btn'>Authenticate access</span>";

        this.container.innerHTML = `
            <div class="auth-card glass-panel">
                <div class="auth-header">
                    <h2>J.A.R.V.I.S</h2>
                    <h3>${title}</h3>
                    <p>${subtitle}</p>
                </div>
                
                <form id="auth-form" class="auth-form">
                    <div id="auth-error-alert" class="auth-alert error" style="display:none;"></div>
                    <div id="auth-success-alert" class="auth-alert success" style="display:none;"></div>

                    <div class="form-group">
                        <label for="auth-username">Identity Codename</label>
                        <input type="text" id="auth-username" required placeholder="Enter username...">
                    </div>
                    
                    <div class="form-group">
                        <label for="auth-password">Security Cipher</label>
                        <input type="password" id="auth-password" required placeholder="Enter password...">
                    </div>
                    
                    <button type="submit" class="auth-btn">${buttonText}</button>
                </form>
                
                <div class="auth-footer">
                    <p>${switchText}</p>
                </div>
            </div>
        `;

        // Bind events
        const form = document.getElementById('auth-form');
        if (form) {
            form.addEventListener('submit', (e) => this.handleSubmit(e));
        }

        const switchBtn = document.getElementById('auth-switch-btn');
        if (switchBtn) {
            switchBtn.addEventListener('click', () => this.toggleMode());
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const username = document.getElementById('auth-username').value.trim();
        const password = document.getElementById('auth-password').value.trim();
        
        const errorAlert = document.getElementById('auth-error-alert');
        const successAlert = document.getElementById('auth-success-alert');
        
        if (errorAlert) errorAlert.style.display = 'none';
        if (successAlert) successAlert.style.display = 'none';

        if (!username || !password) {
            this.showError('Codename and Cipher are required.');
            return;
        }

        const submitBtn = this.container.querySelector('.auth-btn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = this.isLoginMode ? 'Connecting...' : 'Registering...';
        }

        try {
            if (this.isLoginMode) {
                // Login
                const data = await RestClient.login(username, password);
                this.showSuccess('Access granted. Jarvis Core online.');
                setTimeout(() => {
                    this.store.setAuth(data.token, data.user);
                    if (this.onAuthSuccess) this.onAuthSuccess();
                }, 1000);
            } else {
                // Register
                await RestClient.register(username, password);
                this.showSuccess('Credentials registered. Authenticating...');
                setTimeout(async () => {
                    const loginData = await RestClient.login(username, password);
                    this.store.setAuth(loginData.token, loginData.user);
                    if (this.onAuthSuccess) this.onAuthSuccess();
                }, 1000);
            }
        } catch (err) {
            console.error(err);
            this.showError(err.message || 'Authentication sequence failed.');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = this.isLoginMode ? 'Access Core' : 'Register Core';
            }
        }
    }

    showError(msg) {
        const alert = document.getElementById('auth-error-alert');
        if (alert) {
            alert.textContent = msg;
            alert.style.display = 'block';
        }
    }

    showSuccess(msg) {
        const alert = document.getElementById('auth-success-alert');
        if (alert) {
            alert.textContent = msg;
            alert.style.display = 'block';
        }
    }
}
