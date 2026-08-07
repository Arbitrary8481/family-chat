class FamilyChatCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    setConfig(config) {
        if (!config.entity) {
            throw new Error('You need to define an entity');
        }
        this.config = config;
    }

    set hass(hass) {
        if (!this.content) {
            this.innerHTML = `
                <ha-card>
                    <div class="card-header">
                        <ha-icon icon="mdi:message-text"></ha-icon>
                        <span>Family Chat</span>
                    </div>
                    <div class="card-content">
                        <iframe 
                            src="/api/hassio_ingress/${this.config.addon_slug || 'family_chat'}/"
                            style="width: 100%; height: 500px; border: none; border-radius: 8px;"
                            sandbox="allow-same-origin allow-scripts allow-forms"
                        ></iframe>
                    </div>
                </ha-card>
            `;
            
            // Add styles
            const style = document.createElement('style');
            style.textContent = `
                ha-card {
                    background: var(--card-background-color, var(--ha-card-background));
                    border-radius: var(--ha-card-border-radius, 12px);
                    box-shadow: var(--ha-card-box-shadow);
                    overflow: hidden;
                }
                .card-header {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 16px 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    font-weight: 600;
                    font-size: 18px;
                }
                .card-header ha-icon {
                    --mdc-icon-size: 24px;
                }
                .card-content {
                    padding: 0;
                }
                iframe {
                    display: block;
                }
            `;
            this.appendChild(style);
        }
    }

    getCardSize() {
        return 8;
    }

    static getConfigElement() {
        return document.createElement("family-chat-card-editor");
    }

    static getStubConfig() {
        return { entity: "sensor.family_chat", addon_slug: "family_chat" };
    }
}

customElements.define('family-chat-card', FamilyChatCard);

// Card editor for configuration UI
class FamilyChatCardEditor extends HTMLElement {
    setConfig(config) {
        this.config = config;
    }

    configChanged(newConfig) {
        const event = new Event("config-changed", {
            bubbles: true,
            composed: true
        });
        event.detail = { config: newConfig };
        this.dispatchEvent(event);
    }
}

customElements.define("family-chat-card-editor", FamilyChatCardEditor);

// Register card
window.customCards = window.customCards || [];
window.customCards.push({
    type: "family-chat-card",
    name: "Family Chat",
    description: "Discord-like chat for your family with file sharing and emojis",
    preview: true,
    documentationURL: "https://github.com/yourusername/family-chat"
});
