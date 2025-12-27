function scrollDest(direction) {
    const wrapper = document.getElementById('destWrapper');
    const scrollAmount = 300; 
    
    if (direction === 1) {
        wrapper.scrollLeft += scrollAmount;
    } else {
        wrapper.scrollLeft -= scrollAmount;
    }
}

function reopenSurvey() {
    const modalEl = document.getElementById('surveyModal');
    if(modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    } else {
        alert("Vui lòng đăng nhập để sử dụng tính năng này!");
    }
}

async function submitSurvey() {
    const form = document.getElementById('surveyForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    const btn = document.querySelector('#surveyModal .btn-dark');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang lưu hồ sơ...';

    try {
        const resp = await fetch('/api/update_preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if(resp.ok) {
            const modalEl = document.getElementById('surveyModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if(modal) modal.hide();
            
            setTimeout(() => {
                location.reload();
            }, 300);
        } else {
            alert('Có lỗi xảy ra, vui lòng thử lại');
            btn.innerHTML = 'Lưu thay đổi & Cập nhật gợi ý 🚀';
        }
    } catch(e) { 
        console.error(e);
        alert('Có lỗi xảy ra, vui lòng thử lại');
        btn.innerHTML = 'Lưu thay đổi & Cập nhật gợi ý 🚀';
    }
}

const chatBtn = document.getElementById('chatToggleBtn');
const chatBox = document.getElementById('aiChatBox');
const closeChat = document.getElementById('closeChatBtn');
const clearChat = document.getElementById('clearChatBtn');
const expandChat = document.getElementById('expandChatBtn');
const input = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendChatBtn');
const content = document.getElementById('chatContent');

let isExpanded = false;

function renderMessage(msg) {
    let html = '';
    const content = document.getElementById('chatContent');

    if (msg.role !== 'user') {
        html += `
        <div class="d-flex align-items-center mb-1 ps-2">
            <i class="fas fa-robot text-primary me-2 small"></i>
            <span class="fw-bold text-dark" style="font-size: 0.75rem;">LigmaStay AI</span>
        </div>`;
    }

    let bodyHtml = '';

    if (msg.type === 'search_result' && msg.hotels) {
        let introText = msg.content || msg.reply_text || "";
        bodyHtml += `<div>${marked.parse(introText)}</div>`;
        
        msg.hotels.slice(0, 4).forEach(h => {
            let img = (h.images && h.images.length > 0) ? h.images[0].original_image : 'https://via.placeholder.com/90';
            let price = (h.rate_per_night && h.rate_per_night.lowest) ? h.rate_per_night.lowest : 'Liên hệ';
            let stars = h.overall_rating ? `<span class="text-warning ms-2" style="font-size:0.8rem"><i class="fas fa-star"></i> ${h.overall_rating}</span>` : '';
            
            bodyHtml += `
                <a href="/hotel/${h.property_token}" class="mini-hotel-card">
                    <img src="${img}" class="mini-img" alt="Hotel">
                    <div class="mini-info">
                        <div class="mini-name">${h.name}</div>
                        <div class="d-flex align-items-center">
                            <div class="mini-price">${price}</div>
                            ${stars}
                        </div>
                    </div>
                </a>`;
        });
        bodyHtml += `<div class="text-center mt-2"><small class="text-muted" style="font-size:0.7rem;">Nhấn vào thẻ để xem chi tiết</small></div>`;
    } 
    else {
        let rawText = msg.content || msg.reply_text || "";
        if(rawText) bodyHtml = marked.parse(rawText);
    }

    html += bodyHtml;

    const div = document.createElement('div');
    div.className = msg.role === 'user' ? 'msg-user' : 'msg-bot';
    
    div.style.animation = "fadeIn 0.3s ease-out"; 
    div.innerHTML = html;
    
    content.appendChild(div);
    content.scrollTop = content.scrollHeight;
}

document.addEventListener('DOMContentLoaded', async () => {
    const heroCheckboxes = document.querySelectorAll('#amenityHeroBtn + .dropdown-menu input[type="checkbox"]');
    const heroBtnText = document.getElementById('amenityHeroText');
    
    const box = document.getElementById('aiSuggestionBox');
    
    try {
        const resp = await fetch('/api/get_home_suggestion');
        const data = await resp.json();
        
        if (!data.is_logged_in) {
            box.style.display = 'flex';
            document.getElementById('aiLoading').style.display = 'none';
            document.getElementById('aiContent').style.display = 'none';
            document.getElementById('aiLoginPrompt').style.display = 'block';
            document.getElementById('aiActionForm').style.display = 'none';
            document.getElementById('aiLoginBtn').style.display = 'block';
        }
        else if (data.suggestion) {
            const s = data.suggestion;
            
            box.style.display = 'flex';
            document.getElementById('aiIcon').innerText = s.vibe_icon;
            document.getElementById('aiTitle').innerText = `Gợi ý riêng cho bạn: ${s.city}`;
            document.getElementById('aiGreeting').innerText = `"${s.greeting}"`;
            
            document.getElementById('aiInputCity').value = s.city;
            document.getElementById('aiInputPrice').value = s.price_range;
            
            document.getElementById('aiLoading').style.display = 'none';
            document.getElementById('aiContent').style.display = 'block';
            document.getElementById('aiLoginPrompt').style.display = 'none';
            document.getElementById('aiActionForm').style.display = 'block';
            document.getElementById('aiLoginBtn').style.display = 'none';
        }
        else {
            box.style.display = 'none';
        }
    } catch (e) {
        console.error("AI Suggestion Failed", e);
        box.style.display = 'none';
    }

    function updateHeroLabel() {
        const checked = Array.from(heroCheckboxes).filter(cb => cb.checked);
        if (checked.length === 0) {
            heroBtnText.textContent = "Tùy chọn";
        } else if (checked.length === 1) {
            const label = document.querySelector(`label[for="${checked[0].id}"]`).textContent;
            heroBtnText.textContent = label;
        } else {
            heroBtnText.textContent = `${checked.length} tiện nghi`;
        }
    }

    heroCheckboxes.forEach(cb => {
        cb.addEventListener('change', updateHeroLabel);
    });

    const heroDropdownMenu = document.querySelector('#amenityHeroBtn + .dropdown-menu');
    if (heroDropdownMenu) {
        heroDropdownMenu.addEventListener('click', function (e) {
            e.stopPropagation();
        });
    }
    try {
        const resp = await fetch('/api/get_chat_history');
        const history = await resp.json();
        if (history.length > 0) {
            content.innerHTML = ''; 
            history.forEach(msg => renderMessage(msg));
        }
    } catch (e) { console.error(e); }
});

chatBtn.onclick = () => { 
    chatBox.style.display = 'flex'; 
    setTimeout(() => {
        chatBox.style.opacity = '1';
        chatBox.style.transform = 'scale(1)';
    }, 10);
    chatBtn.style.transform = 'scale(0) rotate(180deg)'; 
    input.focus();
};

closeChat.onclick = () => { 
    chatBox.style.display = 'none'; 
    chatBtn.style.transform = 'scale(1) rotate(0deg)'; 
    if(isExpanded) toggleExpand();
};

function toggleExpand() {
    isExpanded = !isExpanded;
    chatBox.classList.toggle('expanded');
    
    const icon = expandChat.querySelector('i');
    if (isExpanded) {
        icon.classList.remove('fa-expand-alt');
        icon.classList.add('fa-compress-alt');
    } else {
        icon.classList.remove('fa-compress-alt');
        icon.classList.add('fa-expand-alt');
    }
}
expandChat.onclick = toggleExpand;

clearChat.onclick = async () => {
    if(confirm("Xóa lịch sử trò chuyện?")) {
        await fetch('/api/clear_chat', { method: 'POST' });
        content.innerHTML = `
            <div class="msg-bot">
                 <div class="d-flex align-items-center mb-2">
                    <strong class="me-2">AI Concierge</strong> <span class="badge bg-dark text-white rounded-pill" style="font-size: 0.6rem;">Bot</span>
                </div>
                Đã xóa bộ nhớ! Chúng ta bắt đầu lại nhé. <br>
                Bạn muốn đi đâu?
            </div>`;
    }
}

function showTyping() {
    const div = document.createElement('div');
    div.id = 'typingLoader';
    div.className = 'msg-bot';
    div.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    content.appendChild(div);
    content.scrollTop = content.scrollHeight;
}

function removeTyping() {
    const loader = document.getElementById('typingLoader');
    if(loader) loader.remove();
}

async function handleChat() {
    const text = input.value.trim();
    if(!text) return;

    renderMessage({ role: 'user', content: text });
    input.value = '';
    showTyping();

    try {
        const resp = await fetch('/api/chat_search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });
        const data = await resp.json();
        removeTyping();

        const msgData = {
            role: 'ai',
            type: data.type,
            content: data.reply_text,
            hotels: data.hotels
        };
        renderMessage(msgData);

    } catch (e) {
        console.error(e);
        removeTyping();
        renderMessage({ role: 'ai', content: "Mạng lỗi rồi, thử lại sau nha!" });
    }
}

sendBtn.onclick = handleChat;
input.onkeydown = (e) => { if(e.key === 'Enter') handleChat(); }

function openMoodModal() {
    new bootstrap.Modal(document.getElementById('moodModal')).show();
}

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('moodImage');
const preview = document.getElementById('imagePreview');
const placeholder = document.getElementById('uploadPlaceholder');

dropZone.onclick = () => fileInput.click();

fileInput.onchange = function() {
    const file = this.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
            placeholder.style.display = 'none';
        }
        reader.readAsDataURL(file);
    }
}

function resetMoodUI() {
    document.getElementById('moodResultSection').style.display = 'none';
    document.getElementById('moodInputSection').style.display = 'block';
    document.getElementById('moodFooter').style.display = 'block';

    document.getElementById('moodText').value = '';
    const fileInput = document.getElementById('moodImage');
    fileInput.value = ''; 
    const preview = document.getElementById('imagePreview');
    const placeholder = document.getElementById('uploadPlaceholder');

    preview.style.display = 'none'; 
    preview.src = '';               
    placeholder.style.display = 'block';
}

async function submitMoodSearch() {
    const text = document.getElementById('moodText').value;
    const file = fileInput.files[0];
    
    const inputSection = document.getElementById('moodInputSection');
    const resultSection = document.getElementById('moodResultSection');
    const footer = document.getElementById('moodFooter');
    const loading = document.getElementById('moodLoading');

    if (!text && !file) {
        alert("Hãy nhập tâm trạng hoặc chọn một bức ảnh nhé!"); 
        return;
    }

    loading.style.display = 'block';
    footer.style.display = 'none';
    
    const formData = new FormData();
    formData.append('mood_text', text);
    if (file) formData.append('mood_image', file);

    try {
        const resp = await fetch('/api/mood_search', {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();

        loading.style.display = 'none';

        if (data.error) {
            alert(data.error);
            footer.style.display = 'block';
            return;
        }

        inputSection.style.display = 'none';
        resultSection.style.display = 'block';

        const displayImg = preview.src && preview.style.display !== 'none' 
            ? preview.src 
            : 'https://cdn-icons-png.flaticon.com/512/2953/2953363.png';

        resultSection.innerHTML = `
            <div class="text-center py-3 animate__animated animate__fadeIn">
                <div class="mb-4 position-relative d-inline-block">
                    <img src="${displayImg}" 
                         style="width: 120px; height: 120px; object-fit: cover; border-radius: 50%; box-shadow: 0 10px 25px rgba(0,0,0,0.15); border: 4px solid white;">
                    <div class="position-absolute bottom-0 end-0 bg-success text-white rounded-circle d-flex align-items-center justify-content-center" 
                         style="width: 35px; height: 35px; border: 3px solid white;">
                        <i class="fas fa-check small"></i>
                    </div>
                </div>
                
                <h5 class="text-muted small text-uppercase fw-bold ls-1 mb-2">AI Gợi ý điểm đến</h5>
                <h2 class="fw-bold text-dark mb-3">${data.city}</h2>
                
                <div class="bg-light p-3 rounded-4 mb-4 mx-2">
                    <p class="mb-0 text-secondary fst-italic">
                        <i class="fas fa-quote-left text-muted opacity-25 me-2"></i>
                        ${data.explanation}
                        <i class="fas fa-quote-right text-muted opacity-25 ms-2"></i>
                    </p>
                </div>

                <div class="row g-2">
                    <div class="col-4">
                        <button onclick="resetMoodUI()" class="btn btn-outline-secondary w-100 rounded-pill py-3 fw-bold">
                            <i class="fas fa-undo"></i> Thử lại
                        </button>
                    </div>
                    <div class="col-8">
                        <button id="btnGoMoodResult" class="btn btn-dark w-100 rounded-pill py-3 fw-bold shadow-lg transform-scale">
                            Khám phá ngay 🚀
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('btnGoMoodResult').onclick = function() {
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang đi...';
            
            const hiddenForm = document.getElementById('hiddenSearchForm');
            document.getElementById('h_city').value = data.city;
            if(data.price_range) document.getElementById('h_price').value = data.price_range;

            const oldAms = hiddenForm.querySelectorAll('input[name="amenities"]');
            oldAms.forEach(el => el.remove());

            if (data.amenities && Array.isArray(data.amenities)) {
                data.amenities.forEach(am => {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'amenities';
                    input.value = am;
                    hiddenForm.appendChild(input);
                });
            }
            hiddenForm.submit();
        };

    } catch (e) {
        console.error(e);
        alert("Lỗi kết nối. Thử lại sau nhé.");
        loading.style.display = 'none';
        footer.style.display = 'block';
    }
}

