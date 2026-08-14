// ==UserScript==
// @name         MemOS - Memory Sync Plugin
// @namespace    https://github.com/memos/memos
// @version      1.0.0
// @description  Floating button to share selected text/memories directly from Ollama WebUI, Open-WebUI, or ChatGPT into MemOS.
// @author       MemOS Team
// @match        *://*/*
// @grant        none
// ==UserScript==

(function() {
    'use strict';

    // MemOS Plugin Configuration
    const MEMOS_API_URL = 'http://localhost:8000/api/v1/ollama/share-memory';

    // Create MemOS Floating Share Button
    function createMemOSButton() {
        if (document.getElementById('memos-share-btn')) return;

        const btn = document.createElement('button');
        btn.id = 'memos-share-btn';
        btn.innerHTML = '🧠 Share with MemOS';
        btn.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 99999;
            background: linear-gradient(135deg, #6366f1, #a855f7);
            color: #ffffff;
            border: none;
            border-radius: 30px;
            padding: 12px 20px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 10px 25px rgba(99, 102, 241, 0.4);
            transition: all 0.3s ease;
            font-family: system-ui, -apple-system, sans-serif;
        `;

        btn.onmouseover = () => btn.style.transform = 'scale(1.05)';
        btn.onmouseout = () => btn.style.transform = 'scale(1.0)';

        btn.onclick = async () => {
            const selectedText = window.getSelection().toString().trim();
            if (!selectedText) {
                alert('Please highlight/select the text or chat message you want to save to MemOS long-term memory!');
                return;
            }

            btn.innerHTML = '⏳ Saving...';
            try {
                const response = await fetch(MEMOS_API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        content: selectedText,
                        tags: ['browser_plugin', 'web_ui'],
                        source: 'memos_browser_plugin'
                    })
                });

                if (response.ok) {
                    btn.innerHTML = '✅ Saved to MemOS!';
                    setTimeout(() => btn.innerHTML = '🧠 Share with MemOS', 3000);
                } else {
                    btn.innerHTML = '❌ Error Saving';
                    setTimeout(() => btn.innerHTML = '🧠 Share with MemOS', 3000);
                }
            } catch (err) {
                alert('Could not connect to local MemOS server at ' + MEMOS_API_URL);
                btn.innerHTML = '🧠 Share with MemOS';
            }
        };

        document.body.appendChild(btn);
    }

    // Initialize button on load
    window.addEventListener('load', createMemOSButton);
    setTimeout(createMemOSButton, 2000);
})();
