(function(){
    const chatBtn = document.getElementById('chatToggleBtn');
    if (!chatBtn) return;
    
    const chatBox = document.getElementById('aiChatBox');
    const closeChat = document.getElementById('closeChatBtn');
    const clearChat = document.getElementById('clearChatBtn');
    const expandChat = document.getElementById('expandChatBtn');
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');
    const content = document.getElementById('chatContent');

    if (!chatBox || !closeChat || !clearChat || !expandChat || !input || !sendBtn || !content) return;

    let isExpanded = false;

    chatBtn.onclick = () => {
        chatBox.style.display = 'flex';
        setTimeout(() => {
            chatBox.style.opacity = '1';
            chatBox.style.transform = 'translateY(0) scale(1)';
        }, 10);
        chatBtn.style.transform = 'scale(0) rotate(180deg)';
        input.focus();
    };

    function closeChatBox() {
        chatBox.style.display = 'none';
        chatBtn.style.transform = 'scale(1) rotate(0deg)';
        if(isExpanded) toggleExpand();
    }
    closeChat.onclick = closeChatBox;

    function toggleExpand() {
        isExpanded = !isExpanded;
        chatBox.classList.toggle('expanded');
        const icon = expandChat.querySelector('i');
        icon.className = isExpanded ? 'fas fa-compress-alt' : 'fas fa-expand-alt';
    }
    expandChat.onclick = toggleExpand;

    clearChat.onclick = () => {
        if(confirm("Xóa cuộc hội thoại hiện tại?")) {
            content.innerHTML = '';
            if (typeof triggerProactiveGreeting === 'function') {
                triggerProactiveGreeting();
            }
        }
    };

    function renderMessage(msg) {
        let html = '';
        
        if (msg.role !== 'user') {
            html += `
            <div class="d-flex align-items-center mb-1 ps-2">
                <i class="fas fa-robot text-primary me-2 small"></i>
                <span class="fw-bold text-dark" style="font-size: 0.75rem;">AI Concierge</span>
            </div>`;
        }

        let bodyContent = msg.content || msg.reply_text || "";
        if (bodyContent && typeof marked !== 'undefined') {
            html += `<div>${marked.parse(bodyContent)}</div>`;
        } else if (bodyContent) {
            html += `<div>${bodyContent}</div>`;
        }

        const div = document.createElement('div');
        div.className = msg.role === 'user' ? 'msg-user' : 'msg-bot';
        div.innerHTML = html;
        div.style.animation = "fadeIn 0.3s ease-out"; 
        
        content.appendChild(div);
        content.scrollTop = content.scrollHeight;
    }

    window.renderMessage = renderMessage;

    if (sendBtn) {
        sendBtn.onclick = () => {
            if (typeof sendMessage === 'function') {
                sendMessage();
            }
        };
    }

    if (input) {
        input.onkeydown = (e) => { 
            if(e.key === 'Enter' && typeof sendMessage === 'function') {
                sendMessage();
            }
        };
    }
})();

function sortHotels() {
    const select = document.getElementById('sortSelect');
    if(!select) return;
    
    const sortBy = select.value;
    const grid = document.getElementById('hotelGrid');
    if(!grid) return;
    
    const items = Array.from(grid.getElementsByClassName('hotel-item'));
    
    items.sort((a, b) => {
        const getVal = (el, attr) => {
            const val = parseFloat(el.getAttribute(attr));
            return isNaN(val) ? 0 : val;
        };

        const priceA = getVal(a, 'data-price');
        const priceB = getVal(b, 'data-price');
        const ratingA = getVal(a, 'data-rating');
        const ratingB = getVal(b, 'data-rating');
        const reviewA = getVal(a, 'data-reviews');
        const reviewB = getVal(b, 'data-reviews');
        const matchA = getVal(a, 'data-match-score');
        const matchB = getVal(b, 'data-match-score');

        switch(sortBy) {
            case 'ai_match': 
                if (matchB !== matchA) return matchB - matchA;
                return ratingB - ratingA;
            case 'price_asc': return priceA - priceB;
            case 'price_desc': return priceB - priceA;
            case 'rating_desc': return ratingB - ratingA;
            case 'reviews_desc': return reviewB - reviewA;
            default: return 0;
        }
    });
    
    const fragment = document.createDocumentFragment();
    items.forEach(item => fragment.appendChild(item));
    grid.innerHTML = ""; 
    grid.appendChild(fragment);
}

window.sortHotels = sortHotels;
window.compareList = window.compareList || [];

function handleCompare(checkbox) {
    const hotelData = JSON.parse(checkbox.getAttribute('data-hotel'));
    if (checkbox.checked) {
        if (window.compareList.length >= 3) {
            if(window.showToast) window.showToast("Chỉ so sánh tối đa 3 khách sạn.", "error");
            else alert("Chỉ so sánh tối đa 3 khách sạn.");
            checkbox.checked = false;
            return;
        }
        window.compareList.push(hotelData);
    } else {
        window.compareList = window.compareList.filter(h => h.property_token !== hotelData.property_token);
    }
    updateCompareBar();
}

function updateCompareBar() {
    const bar = document.getElementById('compareBar');
    if (!bar) return;
    
    const countSpan = document.getElementById('compareCount');
    const previewArea = document.getElementById('comparePreviewArea');
    if (!countSpan || !previewArea) return;
    
    countSpan.innerText = `${window.compareList.length}/3 đã chọn`;
    
    let htmlContent = '';
    window.compareList.forEach((hotel, index) => {
        let imgSrc = (hotel.images && hotel.images.length > 0) ? hotel.images[0].original_image : 'https://via.placeholder.com/80x50';
        htmlContent += `
            <div class="text-center mx-3 fade-in">
                <img src="${imgSrc}" style="width:70px; height:45px; object-fit:cover; border-radius:6px; border:1px solid #ccc; margin-bottom: 4px;">
                <div style="font-size:0.75rem; max-width:90px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-weight:600;">${hotel.name}</div>
            </div>
        `;
    });
    previewArea.innerHTML = htmlContent;
    bar.style.display = window.compareList.length > 0 ? 'block' : 'none';
}

function clearCompare() {
    window.compareList = [];
    document.querySelectorAll('.compare-checkbox').forEach(cb => cb.checked = false);
    updateCompareBar();
}

window.handleCompare = handleCompare;
window.clearCompare = clearCompare;
window.updateCompareBar = updateCompareBar; 

function showCompareModal() {
    if (window.compareList.length < 2) { 
        if(window.showToast) window.showToast("Vui lòng chọn ít nhất 2 khách sạn để so sánh.", "error");
        else alert("Vui lòng chọn ít nhất 2 khách sạn.");
        return; 
    }
    
    const table = document.getElementById('compareTable');
    const area = document.getElementById('aiAnalysisArea');
    if (!table || !area) return;
    
    area.innerHTML = '';

    const h1 = window.compareList[0]; 
    const h2 = window.compareList[1];
    const h3 = window.compareList[2] || null;
    
    const renderCheck = (cond) => cond ? '<i class="fas fa-check text-success"></i>' : '<i class="fas fa-times text-muted opacity-25"></i>';
    
    const hasAmenity = (hotel, key) => {
        if (!hotel || !hotel.amenities) return false;
        return hotel.amenities.some(a => {
            const name = (typeof a === 'string') ? a : (a.name || '');
            return name.toLowerCase().includes(key.toLowerCase());
        });
    };

    const getImg = (h) => (h.images && h.images.length > 0) ? h.images[0].original_image : 'https://via.placeholder.com/400x300';
    const getPrice = (h) => (h.rate_per_night && h.rate_per_night.lowest) ? h.rate_per_night.lowest : 'Liên hệ';

    let html = `
        <thead>
            <tr>
                <th class="bg-light-header" style="width: 15%">Tiêu chí</th>
                <th style="width: ${h3 ? '28%' : '42%'}">${h1.name}</th>
                <th style="width: ${h3 ? '28%' : '42%'}">${h2.name}</th>
                ${h3 ? `<th style="width: 28%">${h3.name}</th>` : ''}
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Hình ảnh</td>
                <td><img src="${getImg(h1)}" class="cmp-img"></td>
                <td><img src="${getImg(h2)}" class="cmp-img"></td>
                ${h3 ? `<td><img src="${getImg(h3)}" class="cmp-img"></td>` : ''}
            </tr>
            <tr>
                <td class="fw-bold">Giá/đêm</td>
                <td class="cmp-price">${getPrice(h1)}</td>
                <td class="cmp-price">${getPrice(h2)}</td>
                ${h3 ? `<td class="cmp-price">${getPrice(h3)}</td>` : ''}
            </tr>
            <tr>
                <td>Đánh giá</td>
                <td>
                    <span class="badge bg-dark">${h1.overall_rating || 'N/A'}/5</span>
                    <div class="small text-muted mt-1">${h1.reviews || 0} reviews</div>
                </td>
                <td>
                    <span class="badge bg-dark">${h2.overall_rating || 'N/A'}/5</span>
                    <div class="small text-muted mt-1">${h2.reviews || 0} reviews</div>
                </td>
                ${h3 ? `
                <td>
                    <span class="badge bg-dark">${h3.overall_rating || 'N/A'}/5</span>
                    <div class="small text-muted mt-1">${h3.reviews || 0} reviews</div>
                </td>` : ''}
            </tr>
            <tr>
                <td>Hạng sao</td>
                <td class="text-warning">${'<i class="fas fa-star"></i>'.repeat(h1.extracted_hotel_class || 0)}</td>
                <td class="text-warning">${'<i class="fas fa-star"></i>'.repeat(h2.extracted_hotel_class || 0)}</td>
                ${h3 ? `<td class="text-warning">${'<i class="fas fa-star"></i>'.repeat(h3.extracted_hotel_class || 0)}</td>` : ''}
            </tr>
            <tr class="bg-light">
                <td colspan="${h3 ? 4 : 3}" class="fw-bold text-start ps-3 text-uppercase small text-muted">Tiện nghi nổi bật</td>
            </tr>
    `;

    const amenitiesList = [
        { key: 'Pool', label: 'Bể bơi' },
        { key: 'Breakfast', label: 'Bữa sáng' },
        { key: 'Wi-Fi', label: 'Wi-Fi' },
        { key: 'Gym', label: 'Gym/Fitness' },
        { key: 'Spa', label: 'Spa & Massage' },
        { key: 'Bar', label: 'Bar/Lounge' }
    ];

    amenitiesList.forEach(am => {
        html += `
            <tr>
                <td>${am.label}</td>
                <td>${renderCheck(hasAmenity(h1, am.key) || hasAmenity(h1, am.key.replace(' ', '-')))}</td>
                <td>${renderCheck(hasAmenity(h2, am.key) || hasAmenity(h2, am.key.replace(' ', '-')))}</td>
                ${h3 ? `<td>${renderCheck(hasAmenity(h3, am.key) || hasAmenity(h3, am.key.replace(' ', '-')))}</td>` : ''}
            </tr>
        `;
    });

    html += `
            <tr>
                <td></td>
                <td><a href="/hotel/${h1.property_token}" class="btn btn-dark w-100 btn-sm">Xem chi tiết</a></td>
                <td><a href="/hotel/${h2.property_token}" class="btn btn-dark w-100 btn-sm">Xem chi tiết</a></td>
                ${h3 ? `<td><a href="/hotel/${h3.property_token}" class="btn btn-dark w-100 btn-sm">Xem chi tiết</a></td>` : ''}
            </tr>
        </tbody>
    `;

    table.innerHTML = html;
    new bootstrap.Modal(document.getElementById('compareModal')).show();
}

window.showCompareModal = showCompareModal;

async function runAiCompare() {
    const area = document.getElementById('aiAnalysisArea');
    if (!area) return;
    
    area.innerHTML = `
        <div class="d-flex align-items-center justify-content-center py-3 text-muted">
            <div class="spinner-border spinner-border-sm me-2 text-dark" role="status"></div>
            <span>Đang phân tích dữ liệu...</span>
        </div>
    `;
    
    try {
        const resp = await fetch('/api/compare_ai', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hotels: window.compareList })
        });
        const data = await resp.json();
        
        if (data.reply && typeof marked !== 'undefined') {
            area.innerHTML = `
                <div class="alert alert-secondary mt-3 border-0 bg-light shadow-sm" style="border-radius: 12px;">
                    <h6 class="fw-bold text-dark mb-2"><i class="fas fa-robot me-1"></i> Gợi ý từ AI:</h6>
                    <div class="small text-dark" style="line-height: 1.6;">${marked.parse(data.reply)}</div>
                </div>`;
        } else if (data.reply) {
            area.innerHTML = `
                <div class="alert alert-secondary mt-3 border-0 bg-light shadow-sm" style="border-radius: 12px;">
                    <h6 class="fw-bold text-dark mb-2"><i class="fas fa-robot me-1"></i> Gợi ý từ AI:</h6>
                    <div class="small text-dark" style="line-height: 1.6;">${data.reply}</div>
                </div>`;
        } else {
            area.innerHTML = '<div class="text-danger small mt-2">Không thể nhận phản hồi từ AI.</div>';
        }
    } catch(e) { 
        area.innerHTML = '<div class="text-danger small mt-2">Lỗi kết nối mạng.</div>'; 
    }
}

window.runAiCompare = runAiCompare;

