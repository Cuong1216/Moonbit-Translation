// Frontend Application Logic for Gemini Novel Translator

document.addEventListener('DOMContentLoaded', () => {
    // Global State
    let activeGlossary = {};
    let extractedNovelText = "";
    let novelFilename = "ban_dich";
    let fullTranslationText = "";

    // DOM Elements
    const globalApiKeyInput = document.getElementById('global-api-key');
    const toggleApiKeyBtn = document.getElementById('toggle-api-key');

    // Tab 1 Elements (Glossary Builder)
    const glossarySourceFileInput = document.getElementById('glossary-source-file');
    const glossaryTranslatedFileInput = document.getElementById('glossary-translated-file');
    const btnBuildGlossary = document.getElementById('btn-build-glossary');
    const glossaryTableBody = document.getElementById('glossary-table-body');
    const btnAddTerm = document.getElementById('btn-add-term');
    const btnSaveGlossary = document.getElementById('btn-save-glossary');

    // Tab 2 Elements (Novel Translator)
    const novelFileInput = document.getElementById('novel-file');
    const aiProviderSelect = document.getElementById('ai-provider');
    const sourceLangSelect = document.getElementById('source-lang');
    const targetLangSelect = document.getElementById('target-lang');
    const translationModelSelect = document.getElementById('translation-model');
    const activeGlossaryCountText = document.getElementById('active-glossary-count');
    const btnStartTranslation = document.getElementById('btn-start-translation');
    const btnPauseTranslation = document.getElementById('btn-pause-translation');
    
    const translationStatusText = document.getElementById('translation-status-text');
    const translationPercentage = document.getElementById('translation-percentage');
    const translationProgressBar = document.getElementById('translation-progress-bar');
    const downloadActionsPanel = document.getElementById('download-actions');
    const translationPreviewArea = document.getElementById('translation-preview-area');

    const btnDownloadTxt = document.getElementById('btn-download-txt');
    const btnDownloadDocx = document.getElementById('btn-download-docx');

    const splitScreenTable = document.getElementById('split-screen-table');
    const splitScreenBody = document.getElementById('split-screen-body');

    // Các phần tử quản lý SQLite Glossary
    const glossaryCollectionSelect = document.getElementById('glossary-collection-select');
    const btnDeleteCollection = document.getElementById('btn-delete-collection');
    const newCollectionNameInput = document.getElementById('new-collection-name');
    const btnCreateCollection = document.getElementById('btn-create-collection');
    const translationGlossarySelect = document.getElementById('translation-glossary-select');

    let currentCollectionId = null;

    function escapeHtml(text) {
        if (!text) return "";
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    async function loadGlossaryCollections() {
        try {
            const response = await fetch('/api/glossaries');
            if (!response.ok) throw new Error('Không thể tải danh sách bộ thuật ngữ.');
            const collections = await response.json();
            
            // Nạp vào dropdown ở Tab Glossary
            glossaryCollectionSelect.innerHTML = '<option value="" disabled selected>-- Chọn bộ thuật ngữ --</option>';
            collections.forEach(col => {
                const opt = document.createElement('option');
                opt.value = col.id;
                opt.textContent = `${col.name} (${col.term_count} từ)`;
                glossaryCollectionSelect.appendChild(opt);
            });

            // Nạp vào dropdown ở Tab Dịch Truyện
            translationGlossarySelect.innerHTML = '<option value="" selected>-- Không sử dụng (Hoặc dùng Local) --</option>';
            collections.forEach(col => {
                const opt = document.createElement('option');
                opt.value = col.id;
                opt.textContent = col.name;
                translationGlossarySelect.appendChild(opt);
            });

            if (currentCollectionId) {
                glossaryCollectionSelect.value = currentCollectionId;
                translationGlossarySelect.value = currentCollectionId;
            }
        } catch (e) {
            console.error('Lỗi tải danh sách bộ thuật ngữ SQLite:', e);
        }
    }

    async function loadCollectionTerms(collectionId) {
        if (!collectionId) return;
        try {
            const response = await fetch(`/api/glossaries/${collectionId}/terms`);
            if (!response.ok) throw new Error('Không thể tải danh sách thuật ngữ.');
            const data = await response.json();
            
            activeGlossary = data.terms || {};
            renderGlossaryTable(activeGlossary);
            updateGlossaryCountDisplay();
        } catch (e) {
            console.error(e);
            alert(`Lỗi khi load từ khóa: ${e.message}`);
        }
    }

    // --- 1. API KEY CONFIGURATION & PROVIDER OPTIONS ---
    const modelsByProvider = {
        gemini: [
            { value: 'gemini-1.5-flash', text: 'Gemini 1.5 Flash (Nhanh & Tối ưu)' },
            { value: 'gemini-1.5-pro', text: 'Gemini 1.5 Pro (Thông minh vượt trội)' }
        ],
        claude: [
            { value: 'claude-3-5-sonnet-20241022', text: 'Claude 3.5 Sonnet (Thông minh & Đọc hiểu sâu)' },
            { value: 'claude-3-haiku-20240307', text: 'Claude 3 Haiku (Nhanh & Giá rẻ)' }
        ],
        openrouter: [
            { value: 'deepseek/deepseek-chat', text: 'DeepSeek V3 (Thông minh & Tối ưu chi phí)' },
            { value: 'meta-llama/llama-3.3-70b-instruct', text: 'Llama 3.3 70B Instruct (Mã nguồn mở mạnh mẽ)' },
            { value: 'google/gemini-2.5-pro', text: 'Gemini 2.5 Pro (Qua OpenRouter)' }
        ]
    };

    const apiKeyStorageKeys = {
        gemini: 'gemini_api_key',
        claude: 'claude_api_key',
        openrouter: 'openrouter_api_key'
    };

    const providerPlaceholders = {
        gemini: 'Nhập Gemini API Key tại đây...',
        claude: 'Nhập Anthropic Claude API Key tại đây...',
        openrouter: 'Nhập OpenRouter API Key tại đây...'
    };

    function handleProviderChange() {
        const provider = aiProviderSelect.value;
        
        // Cập nhật API Key input placeholder
        globalApiKeyInput.placeholder = providerPlaceholders[provider] || 'Nhập API Key tại đây...';
        
        // Nạp API Key đã lưu trong LocalStorage tương ứng
        const storageKey = apiKeyStorageKeys[provider];
        globalApiKeyInput.value = localStorage.getItem(storageKey) || '';
        
        // Cập nhật các Model tương ứng với Provider
        translationModelSelect.innerHTML = '';
        const models = modelsByProvider[provider] || [];
        models.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.value;
            opt.textContent = m.text;
            translationModelSelect.appendChild(opt);
        });
    }

    aiProviderSelect.addEventListener('change', handleProviderChange);
    // Khởi tạo trạng thái ban đầu
    handleProviderChange();

    // Toggle API Key visibility
    toggleApiKeyBtn.addEventListener('click', () => {
        const icon = toggleApiKeyBtn.querySelector('i');
        if (globalApiKeyInput.type === 'password') {
            globalApiKeyInput.type = 'text';
            icon.className = 'fa-regular fa-eye-slash';
        } else {
            globalApiKeyInput.type = 'password';
            icon.className = 'fa-regular fa-eye';
        }
    });

    // Save API key on input change
    globalApiKeyInput.addEventListener('input', () => {
        const provider = aiProviderSelect.value;
        const storageKey = apiKeyStorageKeys[provider];
        localStorage.setItem(storageKey, globalApiKeyInput.value.trim());
    });

    // --- 2. GLOSSARY CONFIGURATION ---
    // Tải danh sách bộ từ vựng SQLite ban đầu
    loadGlossaryCollections();

    // Load saved Glossary từ LocalStorage làm fallback
    const savedGlossaryRaw = localStorage.getItem('novel_glossary');
    if (savedGlossaryRaw) {
        try {
            activeGlossary = JSON.parse(savedGlossaryRaw);
            renderGlossaryTable(activeGlossary);
            updateGlossaryCountDisplay();
        } catch (e) {
            console.error("Lỗi parse glossary từ localStorage:", e);
        }
    } else {
        // Build initial state from current mockup rows in HTML
        syncGlossaryFromTable();
    }

    // Sự kiện tương tác SQLite Glossary Collections
    glossaryCollectionSelect.addEventListener('change', () => {
        currentCollectionId = parseInt(glossaryCollectionSelect.value);
        if (currentCollectionId) {
            loadCollectionTerms(currentCollectionId);
        }
    });

    translationGlossarySelect.addEventListener('change', async () => {
        const id = translationGlossarySelect.value;
        if (id) {
            try {
                const response = await fetch(`/api/glossaries/${id}/terms`);
                if (response.ok) {
                    const data = await response.json();
                    const count = Object.keys(data.terms || {}).length;
                    activeGlossaryCountText.textContent = `${count} thuật ngữ (SQLite)`;
                }
            } catch (e) {
                console.error(e);
            }
        } else {
            updateGlossaryCountDisplay();
        }
    });

    btnCreateCollection.addEventListener('click', async () => {
        const name = newCollectionNameInput.value.trim();
        if (!name) {
            alert('Vui lòng nhập tên bộ từ vựng mới!');
            return;
        }

        try {
            const response = await fetch('/api/glossaries', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name: name, description: '' })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Không thể tạo bộ từ vựng.');
            }

            alert('Đã tạo thành công bộ từ vựng mới!');
            newCollectionNameInput.value = '';
            
            currentCollectionId = data.collection.id;
            await loadGlossaryCollections();
            
            activeGlossary = {};
            renderGlossaryTable(activeGlossary);
            updateGlossaryCountDisplay();
        } catch (e) {
            console.error(e);
            alert(`Lỗi: ${e.message}`);
        }
    });

    btnDeleteCollection.addEventListener('click', async () => {
        const id = glossaryCollectionSelect.value;
        if (!id) {
            alert('Vui lòng chọn bộ thuật ngữ cần xóa!');
            return;
        }

        const confirmDelete = confirm('Bạn có chắc chắn muốn xóa bộ từ vựng này không? Tất cả các thuật ngữ thuộc bộ này cũng sẽ bị xóa vĩnh viễn.');
        if (!confirmDelete) return;

        try {
            const response = await fetch(`/api/glossaries/${id}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Không thể xóa bộ từ vựng.');
            }

            alert('Đã xóa bộ từ vựng thành công!');
            currentCollectionId = null;
            await loadGlossaryCollections();
            
            activeGlossary = {};
            renderGlossaryTable(activeGlossary);
            updateGlossaryCountDisplay();
        } catch (e) {
            console.error(e);
            alert(`Lỗi: ${e.message}`);
        }
    });

    function updateGlossaryCountDisplay() {
        const count = Object.keys(activeGlossary).length;
        activeGlossaryCountText.textContent = `${count} thuật ngữ`;
    }

    // Render glossary object into the table
    function renderGlossaryTable(glossaryObj) {
        glossaryTableBody.innerHTML = '';
        const keys = Object.keys(glossaryObj);
        
        if (keys.length === 0) {
            glossaryTableBody.innerHTML = `
                <tr id="empty-glossary-row">
                    <td colspan="3" class="text-center text-muted py-4">Chưa có thuật ngữ nào. Tải lên tệp hoặc tự thêm từ mới!</td>
                </tr>
            `;
            return;
        }

        keys.forEach(key => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td contenteditable="true" class="fw-semibold text-light glossary-cell source-cell">${key}</td>
                <td contenteditable="true" class="text-info glossary-cell target-cell">${glossaryObj[key]}</td>
                <td class="text-center">
                    <button class="btn btn-outline-danger btn-sm border-0 delete-row-btn" title="Xóa"><i class="fa-regular fa-trash-can"></i></button>
                </td>
            `;
            glossaryTableBody.appendChild(tr);
        });

        // Rebind delete buttons
        bindDeleteRowButtons();
    }

    // Bind event handler for delete buttons
    function bindDeleteRowButtons() {
        document.querySelectorAll('.delete-row-btn').forEach(btn => {
            btn.onclick = (e) => {
                const tr = e.target.closest('tr');
                if (tr) {
                    tr.remove();
                    if (glossaryTableBody.children.length === 0) {
                        renderGlossaryTable({});
                    }
                }
            };
        });
    }
    // Bind initially
    bindDeleteRowButtons();

    // Scan table cells and build dictionary state
    function syncGlossaryFromTable() {
        const glossary = {};
        document.querySelectorAll('#glossary-table-body tr').forEach(row => {
            const srcCell = row.querySelector('.source-cell');
            const tgtCell = row.querySelector('.target-cell');
            
            if (srcCell && tgtCell) {
                const src = srcCell.innerText.trim();
                const tgt = tgtCell.innerText.trim();
                if (src && tgt) {
                    glossary[src] = tgt;
                }
            }
        });
        activeGlossary = glossary;
        updateGlossaryCountDisplay();
    }

    // Add new row button
    btnAddTerm.addEventListener('click', () => {
        // Remove empty placeholder if it exists
        const emptyRow = document.getElementById('empty-glossary-row');
        if (emptyRow) emptyRow.remove();

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td contenteditable="true" class="fw-semibold text-light glossary-cell source-cell" placeholder="Từ gốc (ví dụ: Lin Dong)"></td>
            <td contenteditable="true" class="text-info glossary-cell target-cell" placeholder="Từ dịch (ví dụ: Lâm Động)"></td>
            <td class="text-center">
                <button class="btn btn-outline-danger btn-sm border-0 delete-row-btn" title="Xóa"><i class="fa-regular fa-trash-can"></i></button>
            </td>
        `;
        glossaryTableBody.appendChild(tr);
        bindDeleteRowButtons();

        // Focus on the newly created source cell
        tr.querySelector('.source-cell').focus();
    });

    // Save Glossary Button
    btnSaveGlossary.addEventListener('click', async () => {
        syncGlossaryFromTable();
        localStorage.setItem('novel_glossary', JSON.stringify(activeGlossary));

        if (currentCollectionId) {
            const termsList = [];
            for (const [src, tgt] of Object.entries(activeGlossary)) {
                termsList.push({ source_term: src, target_term: tgt });
            }

            try {
                const response = await fetch(`/api/glossaries/${currentCollectionId}/terms`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ terms: termsList })
                });

                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.detail || 'Lỗi lưu thuật ngữ vào database.');
                }

                alert('Đã lưu thành công bộ thuật ngữ vào SQLite Database và LocalStorage!');
                await loadGlossaryCollections();
            } catch (e) {
                console.error(e);
                alert(`Lỗi DB: ${e.message}`);
            }
        } else {
            alert('Đã lưu thành công bộ thuật ngữ vào LocalStorage của trình duyệt! (Mẹo: Hãy tạo hoặc chọn một bộ thuật ngữ SQLite ở cột bên trái để lưu trữ vĩnh viễn vào Database).');
        }
    });

    // Auto Scan/Build Glossary Tab 1
    btnBuildGlossary.addEventListener('click', async () => {
        const srcFile = glossarySourceFileInput.files[0];
        const tgtFile = glossaryTranslatedFileInput.files[0];
        const apiKey = globalApiKeyInput.value.trim();

        if (!srcFile || !tgtFile) {
            alert('Vui lòng chọn cả Tệp raw gốc và Tệp đã dịch cũ!');
            return;
        }

        if (!apiKey) {
            alert('Vui lòng điền Gemini API Key ở góc trên bên phải trước khi xây dựng thuật ngữ!');
            return;
        }

        const formData = new FormData();
        formData.append('source_file', srcFile);
        formData.append('translated_file', tgtFile);
        formData.append('api_key', apiKey);

        // Show loading state
        btnBuildGlossary.disabled = true;
        btnBuildGlossary.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Đang quét đối chiếu...';

        try {
            const response = await fetch('/api/build-glossary', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Lỗi quét thuật ngữ từ backend.');
            }

            // Successfully received glossary
            const newGlossary = data.glossary;
            activeGlossary = { ...activeGlossary, ...newGlossary }; // Merge with existing terms
            renderGlossaryTable(activeGlossary);
            localStorage.setItem('novel_glossary', JSON.stringify(activeGlossary));
            updateGlossaryCountDisplay();
            
            alert(`Xử lý thành công! Đã tự động quét được ${Object.keys(newGlossary).length} thuật ngữ đối chiếu từ tệp của bạn.`);
        } catch (e) {
            console.error(e);
            alert(`Lỗi: ${e.message}`);
        } finally {
            btnBuildGlossary.disabled = false;
            btnBuildGlossary.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles me-2"></i>Tự động quét thuật ngữ';
        }
    });


    // --- 3. NOVEL TRANSLATOR WORKFLOW ---
    // Handle Novel File Upload to extract text automatically
    novelFileInput.addEventListener('change', async () => {
        const file = novelFileInput.files[0];
        if (!file) return;

        // Save filename prefix
        const dotIndex = file.name.lastIndexOf('.');
        novelFilename = dotIndex !== -1 ? file.name.substring(0, dotIndex) : file.name;

        const formData = new FormData();
        formData.append('file', file);

        // UI Loading state
        btnStartTranslation.disabled = true;
        translationPreviewArea.innerHTML = `<div class="text-center py-5"><span class="spinner-border text-purple me-2" role="status"></span> Đang trích xuất nội dung văn bản tiểu thuyết từ file...</div>`;
        translationStatusText.textContent = "Đang đọc file tải lên...";

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Lỗi trích xuất file.');
            }

            extractedNovelText = data.content;
            
            // Show preview of extracted text (first 1000 characters)
            const previewText = extractedNovelText.length > 1500 
                ? extractedNovelText.substring(0, 1500) + "\n\n...[Còn tiếp]..."
                : extractedNovelText;

            translationPreviewArea.textContent = `[Đã trích xuất thành công văn bản]\n[Tổng ký tự: ${extractedNovelText.length.toLocaleString('vi-VN')} ký tự]\n\n--- Xem trước bản gốc ---\n${previewText}`;
            translationStatusText.textContent = "Đã nạp file thành công, sẵn sàng dịch.";
            btnStartTranslation.disabled = false;
        } catch (e) {
            console.error(e);
            translationPreviewArea.textContent = `Lỗi trích xuất tệp tin: ${e.message}`;
            translationStatusText.textContent = "Thất bại khi nạp file.";
        }
    });

    async function readTranslationStream(response) {
        // Stream Reader setup
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            // Decode current chunk and append to buffer
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            
            // Keep the last partial line in the buffer
            buffer = lines.pop();

            for (const line of lines) {
                const trimmedLine = line.trim();
                if (!trimmedLine) continue;

                if (trimmedLine.startsWith("data: ")) {
                    const rawData = trimmedLine.substring(6);
                    try {
                        const eventData = JSON.parse(rawData);

                        // Update Progress Bar
                        const progress = eventData.progress || 0;
                        translationProgressBar.style.width = `${progress}%`;
                        translationProgressBar.setAttribute('aria-valuenow', progress);
                        translationPercentage.textContent = `${progress}%`;
                        translationStatusText.textContent = eventData.status;

                        // Handle Events
                        if (eventData.event === 'translating') {
                            // Just status update
                        } else if (eventData.event === 'chunk_completed') {
                            const translatedPart = eventData.translated_chunk;
                            const sourcePart = eventData.source_chunk || "";
                            
                            // Tạo hàng tr và append vào bảng
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td style="vertical-align: top; padding: 10px;">
                                    <div class="text-secondary font-monospace" style="white-space: pre-wrap; font-size: 0.92rem; line-height: 1.5;">${escapeHtml(sourcePart)}</div>
                                </td>
                                <td style="vertical-align: top; padding: 10px;">
                                    <textarea class="form-control bg-dark text-info border-secondary translated-chunk-input" style="resize: vertical; min-height: 120px; font-size: 0.92rem; font-family: monospace; line-height: 1.5; color: #0dcaf0 !important;">${translatedPart}</textarea>
                                </td>
                            `;
                            splitScreenBody.appendChild(tr);

                            // Tự động cuộn xuống dưới cùng của container chứa bảng
                            const container = splitScreenTable.parentElement;
                            container.scrollTop = container.scrollHeight;
                            
                            // Để dự phòng, vẫn cộng dồn vào fullTranslationText
                            fullTranslationText += (fullTranslationText ? "\n\n" : "") + translatedPart;
                        } else if (eventData.event === 'paused') {
                            // UI Pause state
                            translationStatusText.textContent = "Đã tạm dừng dịch thuật.";
                            btnPauseTranslation.innerHTML = '<i class="fa-solid fa-play"></i> Tiếp tục';
                            btnPauseTranslation.className = "btn btn-success py-2 fw-semibold d-flex align-items-center justify-content-center gap-2";
                            btnPauseTranslation.disabled = false;
                            return; // Stop processing this stream
                        } else if (eventData.event === 'completed') {
                            if (eventData.full_translation && splitScreenBody.children.length === 0) {
                                fullTranslationText = eventData.full_translation;
                            }
                            
                            // Show download action button
                            downloadActionsPanel.classList.remove('d-none');
                            btnStartTranslation.disabled = false;
                            btnPauseTranslation.classList.add('d-none');
                            alert("Chúc mừng! Đã hoàn thành dịch thuật toàn bộ tệp truyện thành công.");
                        } else if (eventData.event === 'error') {
                            throw new Error(eventData.error || 'Lỗi xảy ra trong quá trình dịch.');
                        }
                    } catch (parseError) {
                        console.error("Lỗi parse dòng SSE JSON:", parseError, trimmedLine);
                    }
                }
            }
        }
    }

    // Start translation click
    btnStartTranslation.addEventListener('click', async () => {
        if (!extractedNovelText.strip) {
            // String extension
        }
        if (!extractedNovelText || extractedNovelText.trim().length === 0) {
            alert('Vui lòng tải lên tệp truyện cần dịch trước!');
            return;
        }

        const apiKey = globalApiKeyInput.value.trim();
        if (!apiKey) {
            alert('Vui lòng cấu hình API Key trước khi bắt đầu dịch!');
            return;
        }

        // Sync glossary just in case
        syncGlossaryFromTable();

        const provider = aiProviderSelect.value;
        const model = translationModelSelect.value;
        const sourceLang = sourceLangSelect.value;
        const targetLang = targetLangSelect.value;

        // Reset UI translation states
        btnStartTranslation.disabled = true;
        
        // Show pause button
        btnPauseTranslation.classList.remove('d-none');
        btnPauseTranslation.innerHTML = '<i class="fa-solid fa-pause"></i> Tạm dừng';
        btnPauseTranslation.className = "btn btn-warning py-2 fw-semibold d-flex align-items-center justify-content-center gap-2";
        btnPauseTranslation.disabled = false;

        downloadActionsPanel.classList.add('d-none');
        translationProgressBar.style.width = '0%';
        translationProgressBar.setAttribute('aria-valuenow', '0');
        translationPercentage.textContent = '0%';
        translationStatusText.textContent = "Đang chuẩn bị kết nối API...";
        
        // Cấu hình hiển thị bảng Split-screen
        translationPreviewArea.classList.add('d-none');
        splitScreenTable.classList.remove('d-none');
        splitScreenBody.innerHTML = "";
        
        fullTranslationText = "";

        try {
            const glossaryIdVal = translationGlossarySelect.value;
            const requestBody = {
                text: extractedNovelText,
                api_key: apiKey,
                model: model,
                source_lang: sourceLang,
                target_lang: targetLang,
                provider: provider
            };

            if (glossaryIdVal) {
                requestBody.glossary_id = parseInt(glossaryIdVal);
            } else {
                requestBody.glossary = activeGlossary;
            }

            // POST to /api/translate
            const response = await fetch('/api/translate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Lỗi thiết lập phiên dịch.');
            }

            await readTranslationStream(response);
        } catch (e) {
            console.error(e);
            translationStatusText.textContent = `Lỗi: ${e.message}`;
            translationPreviewArea.textContent += `\n\n[TIẾN TRÌNH THẤT BẠI]: ${e.message}`;
            btnStartTranslation.disabled = false;
            btnPauseTranslation.classList.add('d-none');
            alert(`Lỗi tiến trình: ${e.message}`);
        }
    });

    // Pause/Resume button handler
    btnPauseTranslation.addEventListener('click', async () => {
        btnPauseTranslation.disabled = true;
        const isPauseAction = btnPauseTranslation.innerText.trim().includes("Tạm dừng");

        if (isPauseAction) {
            btnPauseTranslation.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Đang tạm dừng...';
            try {
                const response = await fetch('/api/pause', {
                    method: 'POST'
                });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.detail || 'Không thể gửi lệnh tạm dừng.');
                }
            } catch (e) {
                console.error(e);
                alert(`Lỗi khi tạm dừng: ${e.message}`);
                btnPauseTranslation.disabled = false;
                btnPauseTranslation.innerHTML = '<i class="fa-solid fa-pause"></i> Tạm dừng';
            }
        } else {
            // Resume
            btnPauseTranslation.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Đang tiếp tục...';
            try {
                const response = await fetch('/api/resume', {
                    method: 'POST'
                });
                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.detail || 'Không thể tiếp tục dịch.');
                }
                
                // Khôi phục giao diện nút Tạm dừng
                btnPauseTranslation.innerHTML = '<i class="fa-solid fa-pause"></i> Tạm dừng';
                btnPauseTranslation.className = "btn btn-warning py-2 fw-semibold d-flex align-items-center justify-content-center gap-2";
                btnPauseTranslation.disabled = false;
                
                // Đọc tiếp stream
                await readTranslationStream(response);
            } catch (e) {
                console.error(e);
                alert(`Lỗi khi tiếp tục: ${e.message}`);
                btnPauseTranslation.disabled = false;
                btnPauseTranslation.innerHTML = '<i class="fa-solid fa-play"></i> Tiếp tục';
                btnPauseTranslation.className = "btn btn-success py-2 fw-semibold d-flex align-items-center justify-content-center gap-2";
            }
        }
    });


    // --- 4. EXPORT & DOWNLOAD SERVICES ---
    // Trigger file export helper
    async function triggerExport(format) {
        // Gom tất cả nội dung đã sửa đổi từ các textarea đối chiếu
        const textAreas = document.querySelectorAll('.translated-chunk-input');
        let editedTranslationText = "";

        if (textAreas.length > 0) {
            const texts = [];
            textAreas.forEach(ta => {
                texts.push(ta.value);
            });
            editedTranslationText = texts.join("\n\n");
        } else {
            editedTranslationText = fullTranslationText;
        }

        if (!editedTranslationText || editedTranslationText.trim().length === 0) {
            alert('Không có nội dung bản dịch nào để xuất file!');
            return;
        }

        try {
            const response = await fetch('/api/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: editedTranslationText,
                    format: format,
                    filename: `${novelFilename}_dich`
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Lỗi xuất file.');
            }

            // Handle file download
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = format === 'docx' ? `${novelFilename}_dich.docx` : `${novelFilename}_dich.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);
        } catch (e) {
            console.error(e);
            alert(`Không thể tải tệp kết quả: ${e.message}`);
        }
    }

    btnDownloadTxt.addEventListener('click', (e) => {
        e.preventDefault();
        triggerExport('txt');
    });

    btnDownloadDocx.addEventListener('click', (e) => {
        e.preventDefault();
        triggerExport('docx');
    });
});
