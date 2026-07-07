// static/components/connection-indicator.js

export class ConnectionIndicator {
    constructor(elementId, store) {
        this.element = document.getElementById(elementId);
        this.store = store;
        this.store.subscribe((state) => this.render(state));
    }

    render(state) {
        const status = state.connectionStatus;
        if (!this.element) return;
        
        this.element.className = `connection-badge ${status}`;
        
        let label = 'Offline';
        if (status === 'connected') label = 'Online';
        if (status === 'connecting') label = 'Reconnecting...';

        this.element.innerHTML = `
            <span class="badge-dot"></span>
            <span>${label}</span>
        `;
    }
}
