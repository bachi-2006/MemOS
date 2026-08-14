// Content script for MemOS Chrome Extension
const MEMOS_API = 'http://localhost:8000/api/v1/ollama/share-memory';

function injectMemOSButton() {
    if (!document.body) return;
    if (document.getElementById('memos-ext-btn')) return;

    const btn = document.createElement('div');
    btn.id = 'memos-ext-btn';
    btn.innerText = '🧠 Save to MemOS';
    btn.style.cssText = `
        position: fixed !important;
        bottom: 24px !important;
        right: 24px !important;
        z-index: 2147483647 !important;
        background: linear-gradient(135deg, #6366f1, #a855f7) !important;
        color: #ffffff !important;
        padding: 10px 18px !important;
        border-radius: 30px !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.5) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        user-select: none !important;
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
    `;

    btn.onmouseover = () => {
        btn.style.transform = 'scale(1.05)';
        btn.style.boxShadow = '0 12px 30px rgba(99, 102, 241, 0.7)';
    };
    btn.onmouseout = () => {
        btn.style.transform = 'scale(1.0)';
        btn.style.boxShadow = '0 8px 25px rgba(99, 102, 241, 0.5)';
    };

    btn.onclick = async (e) => {
        e.preventDefault();
        e.stopPropagation();

        const text = window.getSelection().toString().trim();
        if (!text) {
            alert('💡 Please highlight/select any text or response on screen first, then click "🧠 Save to MemOS"!');
            return;
        }

        btn.innerText = '⏳ Saving...';
        try {
            const res = await fetch(MEMOS_API, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: text, source: 'chrome_extension', tags: ['ollama_ui', 'web_sync'] })
            });

            if (res.ok) {
                btn.innerText = '✅ Saved to MemOS!';
            } else {
                btn.innerText = '❌ Error Saving';
            }
            setTimeout(() => { btn.innerText = '🧠 Save to MemOS'; }, 2500);
        } catch (e) {
            alert('⚠️ Cannot reach MemOS Backend at http://localhost:8000. Make sure the MemOS server is running!');
            btn.innerText = '🧠 Save to MemOS';
        }
    };

    document.body.appendChild(btn);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectMemOSButton);
} else {
    injectMemOSButton();
}

setInterval(injectMemOSButton, 2000);

