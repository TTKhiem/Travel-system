const loginForm = document.getElementById('login-form-wrapper');
const registerForm = document.getElementById('register-form-wrapper');
const btnLogin = document.getElementById('btn-tab-login');
const btnRegister = document.getElementById('btn-tab-register');
const authModal = new bootstrap.Modal(document.getElementById('authModal'));

function openAuthModal(tab) {
    switchAuthTab(tab);
    authModal.show();
}

function switchAuthTab(tab) {
    if(tab === 'login') {
        loginForm.style.display = 'block'; registerForm.style.display = 'none';
        btnLogin.classList.add('active'); btnRegister.classList.remove('active');
    } else {
        loginForm.style.display = 'none'; registerForm.style.display = 'block';
        btnLogin.classList.remove('active'); btnRegister.classList.add('active');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    restoreSearchState();

    const aiToggles = document.querySelectorAll('input[name="ai_autofill"]');
    aiToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            let state = {};
            try { state = JSON.parse(localStorage.getItem('ligma_search_state')) || {}; } catch (e) {}
            
            state.ai_autofill = this.checked ? 'on' : 'off';
            localStorage.setItem('ligma_search_state', JSON.stringify(state));
            
            aiToggles.forEach(t => t.checked = this.checked);
        });
    });

    const searchForms = document.querySelectorAll('form[action="/search_handler"]');
    searchForms.forEach(form => {
        form.addEventListener('submit', function() {
            const formData = new FormData(form);
            const state = {
                city: formData.get('city'),
                price: formData.get('price_range'),
                rating: formData.get('rating'),
                amenities: formData.getAll('amenities'),
                ai_autofill: formData.get('ai_autofill') ? 'on' : 'off'
            };
            localStorage.setItem('ligma_search_state', JSON.stringify(state));
        });
    });

    const amenityCheckboxes = document.querySelectorAll('input[name="amenities"]');
    const amenityBtnText = document.getElementById('amenityBtnText');
    const amenityHeroText = document.getElementById('amenityHeroText');

    function updateAmenityLabel() {
        const checked = Array.from(amenityCheckboxes).filter(cb => cb.checked);
        let label = "Tùy chọn";
        
        if (checked.length === 1) {
            const id = checked[0].id;
            const labelEl = document.querySelector(`label[for="${id}"]`);
            if(labelEl) label = labelEl.textContent;
        } else if (checked.length > 1) {
            label = `${checked.length} tiện nghi`;
        }

        if (amenityBtnText) amenityBtnText.textContent = label;
        if (amenityHeroText) amenityHeroText.textContent = label;
    }

    amenityCheckboxes.forEach(cb => {
        cb.addEventListener('change', updateAmenityLabel);
    });

    function restoreSearchState() {
        const savedRaw = localStorage.getItem('ligma_search_state');
        if (!savedRaw) return;

        try {
            const state = JSON.parse(savedRaw);

            if (state.ai_autofill) {
                document.querySelectorAll('input[name="ai_autofill"]').forEach(toggle => {
                    toggle.checked = (state.ai_autofill === 'on');
                });
            }

            ['city', 'price_range', 'rating'].forEach(key => {
                let inputName = key;
                if(key === 'price') inputName = 'price_range'; 
                
                if (state[key] || state[inputName]) {
                    const val = state[key] || state[inputName];
                    document.querySelectorAll(`select[name="${inputName}"]`).forEach(sel => sel.value = val);
                }
            });

            if (state.amenities && Array.isArray(state.amenities)) {
                document.querySelectorAll('input[name="amenities"]').forEach(cb => {
                    cb.checked = state.amenities.includes(cb.value);
                });
                updateAmenityLabel();
            }

        } catch (e) { console.error("Restore State Error:", e); }
    }

    const toastContainer = document.querySelector('.toast-container');
    if (toastContainer) {
        window.showToast = function(message, type = 'info') {
            const id = 'toast-' + Date.now();
            const icon = type === 'error' ? 'fa-exclamation-circle text-danger' : 'fa-check-circle text-success';
            const title = type === 'error' ? 'Lỗi' : 'Thông báo';
            const html = `
                <div id="${id}" class="toast custom-toast animate__animated animate__fadeInRight" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="toast-header">
                        <i class="fas ${icon} me-2"></i><strong class="me-auto text-dark">${title}</strong>
                        <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                    </div>
                    <div class="toast-body text-dark">${message}</div>
                </div>`;
            toastContainer.insertAdjacentHTML('beforeend', html);
            const toastEl = document.getElementById(id);
            const bsToast = new bootstrap.Toast(toastEl, { delay: 5000 });
            bsToast.show();
            toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
        };
    }
    
});

