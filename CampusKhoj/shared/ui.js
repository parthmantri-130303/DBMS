/**
 * CampusKhoj Shared UI Helpers & Animations
 * WCAG 2.2 AA compliant, prefers-reduced-motion respected.
 */

export function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.setAttribute('aria-live', 'polite');
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${escapeHtml(message)}</span>
    <button class="toast-close" style="background:none;border:none;color:inherit;cursor:pointer;font-size:1.1rem;padding:0;min-width:auto;min-height:auto;" aria-label="Close">&times;</button>
  `;

  toast.querySelector('.toast-close').addEventListener('click', () => {
    toast.remove();
  });

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-8px)';
    toast.style.transition = 'opacity 200ms ease, transform 200ms ease';
    setTimeout(() => toast.remove(), 200);
  }, duration);
}

export function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

export function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
}

export function formatDateTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Renders the vertical animated timeline
 * Line grows downward, nodes pop in sequence.
 */
export function renderTimeline(container, events) {
  if (!container) return;
  if (!events || events.length === 0) {
    container.innerHTML = '<p class="text-muted" style="color:var(--muted-student);font-size:0.875rem;">No events recorded yet.</p>';
    return;
  }

  const isReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let html = '<ol class="timeline">';

  events.forEach((ev, idx) => {
    const isLatest = idx === events.length - 1;
    const nodeClass = isLatest ? 'timeline-node active' : 'timeline-node';
    const delay = isReduced ? 0 : idx * 80;

    html += `
      <li class="timeline-item" style="animation-delay: ${delay}ms;">
        <div class="${nodeClass}" style="animation-delay: ${delay}ms;">
          ${isLatest ? '&#10003;' : '&#8226;'}
        </div>
        <div class="timeline-content">
          <div style="display:flex;justify-content:space-between;align-items:baseline;gap:0.5rem;">
            <strong style="font-size:0.9375rem;color:var(--text-student);">${escapeHtml(ev.title)}</strong>
            <time style="font-size:0.75rem;color:var(--muted-student);white-space:nowrap;">${formatDateTime(ev.created_at)}</time>
          </div>
          ${ev.description ? `<p style="margin:0.25rem 0 0 0;font-size:0.8125rem;color:var(--muted-student);">${escapeHtml(ev.description)}</p>` : ''}
        </div>
      </li>
    `;
  });

  html += '</ol>';
  container.innerHTML = html;
}

/**
 * Animated count-up for KPI counters
 */
export function animateCountUp(element, endVal, duration = 600) {
  if (!element) return;
  const target = parseFloat(endVal) || 0;
  const isReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (isReduced) {
    element.textContent = target.toLocaleString('en-IN');
    return;
  }

  const startTime = performance.now();
  const startVal = 0;

  function update(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out quad
    const current = Math.round(startVal + (target - startVal) * (1 - (1 - progress) * (1 - progress)));
    element.textContent = current.toLocaleString('en-IN');

    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      element.textContent = target.toLocaleString('en-IN');
    }
  }

  requestAnimationFrame(update);
}

/**
 * Skeleton Loader renderer
 */
export function renderSkeletons(container, count = 3, cardType = 'card') {
  if (!container) return;
  let html = '';
  for (let i = 0; i < count; i++) {
    html += `
      <div class="card skeleton" style="height: 180px; margin-bottom: 1rem; border:none;"></div>
    `;
  }
  container.innerHTML = html;
}

/**
 * Password Rule live tick checker
 */
export function setupPasswordRuleTicks(inputElement, rulesContainer) {
  if (!inputElement || !rulesContainer) return;

  const ruleLength = rulesContainer.querySelector('[data-rule="length"]');
  const rulePrn = rulesContainer.querySelector('[data-rule="prn"]');
  const ruleCommon = rulesContainer.querySelector('[data-rule="common"]');

  inputElement.addEventListener('input', () => {
    const val = inputElement.value;
    const prn = inputElement.getAttribute('data-prn') || '';

    // Rule 1: Length >= 8
    const lenValid = val.length >= 8;
    updateRuleTick(ruleLength, lenValid);

    // Rule 2: Not PRN & Not contains PRN
    const prnValid = prn ? (val !== prn && !val.includes(prn)) : true;
    updateRuleTick(rulePrn, prnValid && val.length > 0);

    // Rule 3: Not common password
    const commonPasswords = ['password', '12345678', 'admin123', 'qwerty123'];
    const notCommon = !commonPasswords.includes(val.toLowerCase());
    updateRuleTick(ruleCommon, notCommon && val.length >= 8);
  });
}

function updateRuleTick(element, isValid) {
  if (!element) return;
  const icon = element.querySelector('.rule-icon');
  if (isValid) {
    element.style.color = 'var(--success)';
    if (icon) icon.innerHTML = '&#10003;'; // Checkmark
  } else {
    element.style.color = 'var(--muted-student)';
    if (icon) icon.innerHTML = '&#8226;'; // Dot
  }
}

/**
 * Dual Gallery & Live Camera Capture Controller
 */
export function setupMediaCapture({ container, input, onFileSelected, previewOnly = false }) {
  if (!container) return;

  container.innerHTML = `
    <div class="capture-selector-box" id="capture-drop-zone">
      <div style="font-size: 2.2rem; margin-bottom: 0.5rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">📸</div>
      <div style="font-weight: 600; font-size: 0.9375rem; color: var(--text-student);">Upload or Capture Photo</div>
      <div style="font-size: 0.8125rem; color: var(--muted-student); margin-top: 0.25rem;">
        Add clear photo to speed up verification (JPEG, PNG, WebP &le; 3MB)
      </div>
      <div class="capture-options">
        <button type="button" class="capture-btn capture-btn-gallery" id="btn-browse-gallery">
          📁 Choose from Gallery
        </button>
        <button type="button" class="capture-btn capture-btn-camera" id="btn-open-camera">
          📷 Click with Camera
        </button>
      </div>
      <div id="capture-preview-slot"></div>
    </div>
  `;

  const dropZone = container.querySelector('#capture-drop-zone');
  const btnGallery = container.querySelector('#btn-browse-gallery');
  const btnCamera = container.querySelector('#btn-open-camera');
  const previewSlot = container.querySelector('#capture-preview-slot');

  let activeStream = null;
  let currentFacingMode = 'environment';

  // Gallery button click
  btnGallery.addEventListener('click', () => {
    input.click();
  });

  // Drag and drop handlers
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
  });
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  });

  // File input change
  input.addEventListener('change', () => {
    if (input.files && input.files[0]) {
      handleFile(input.files[0]);
    }
  });

  function handleFile(file) {
    if (!file.type.startsWith('image/')) {
      showToast('Please select a valid image file (JPEG, PNG, WebP)', 'error');
      return;
    }
    if (file.size > 3 * 1024 * 1024) {
      showToast('Image size exceeds 3 MB limit', 'error');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      displayPreview(e.target.result, file.name, (file.size / 1024).toFixed(0) + ' KB');
      if (onFileSelected) onFileSelected(file);
    };
    reader.readAsDataURL(file);
  }

  function displayPreview(src, name, sizeStr) {
    previewSlot.innerHTML = `
      <div class="captured-preview-card">
        <img src="${src}" alt="Captured or uploaded item preview">
        <div class="captured-preview-actions">
          <span style="font-size:0.8125rem; font-weight:600; text-overflow:ellipsis; overflow:hidden; white-space:nowrap; max-width:200px;">
            ${escapeHtml(name)} (${sizeStr})
          </span>
          <button type="button" id="btn-remove-capture" style="background:#B3261E; border:none; color:#FFFFFF; border-radius:var(--radius-sm); padding:0.3rem 0.75rem; font-size:0.75rem; font-weight:600; cursor:pointer;">
            &times; Remove
          </button>
        </div>
      </div>
    `;

    previewSlot.querySelector('#btn-remove-capture').addEventListener('click', () => {
      previewSlot.innerHTML = '';
      input.value = '';
      if (onFileSelected) onFileSelected(null);
    });
  }

  // Camera modal handler
  btnCamera.addEventListener('click', async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showToast('Live camera is not supported on this browser. Opening file gallery instead.', 'info');
      input.click();
      return;
    }

    openCameraModal();
  });

  function openCameraModal() {
    const modal = document.createElement('div');
    modal.className = 'camera-modal-backdrop';
    modal.innerHTML = `
      <div class="camera-modal-content">
        <div class="camera-modal-header">
          <div class="camera-modal-title">
            <span>📷</span> Camera Viewfinder
          </div>
          <button type="button" id="btn-close-cam" style="background:none; border:none; color:#FFFFFF; font-size:1.5rem; cursor:pointer; padding:0; min-width:auto; min-height:auto;" aria-label="Close">&times;</button>
        </div>
        <div class="camera-viewfinder-wrap">
          <video id="camera-video" playsinline autoplay muted></video>
          <div class="camera-grid-overlay"></div>
          <div class="camera-corner-bracket camera-bracket-tl"></div>
          <div class="camera-corner-bracket camera-bracket-tr"></div>
          <div class="camera-corner-bracket camera-bracket-bl"></div>
          <div class="camera-corner-bracket camera-bracket-br"></div>
          <div id="shutter-flash-box"></div>
        </div>
        <div class="camera-modal-footer">
          <button type="button" class="camera-flip-btn" id="btn-flip-cam" title="Flip Camera" aria-label="Switch Camera">
            🔄
          </button>
          <button type="button" class="shutter-btn" id="btn-snap-shutter" title="Take Photo" aria-label="Take Photo"></button>
          <div style="width:44px;"></div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const video = modal.querySelector('#camera-video');
    const btnClose = modal.querySelector('#btn-close-cam');
    const btnFlip = modal.querySelector('#btn-flip-cam');
    const btnSnap = modal.querySelector('#btn-snap-shutter');
    const flashBox = modal.querySelector('#shutter-flash-box');

    function startStream() {
      if (activeStream) {
        activeStream.getTracks().forEach(t => t.stop());
      }
      navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: currentFacingMode }, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false
      }).then(stream => {
        activeStream = stream;
        video.srcObject = stream;
      }).catch(err => {
        showToast('Camera access denied or unavailable: ' + err.message, 'error');
        closeCamera();
        input.click();
      });
    }

    function closeCamera() {
      if (activeStream) {
        activeStream.getTracks().forEach(t => t.stop());
        activeStream = null;
      }
      modal.remove();
    }

    btnClose.addEventListener('click', closeCamera);

    btnFlip.addEventListener('click', () => {
      currentFacingMode = (currentFacingMode === 'environment') ? 'user' : 'environment';
      startStream();
    });

    btnSnap.addEventListener('click', () => {
      // Trigger flash
      flashBox.innerHTML = '<div class="shutter-flash-overlay"></div>';

      // Capture to canvas
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      canvas.toBlob((blob) => {
        const capturedFile = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
        
        // Populate input files via DataTransfer
        try {
          const dt = new DataTransfer();
          dt.items.add(capturedFile);
          input.files = dt.files;
        } catch {}

        displayPreview(canvas.toDataURL('image/jpeg', 0.85), capturedFile.name, (capturedFile.size / 1024).toFixed(0) + ' KB');
        if (onFileSelected) onFileSelected(capturedFile);
        
        setTimeout(closeCamera, 300);
      }, 'image/jpeg', 0.88);
    });

    startStream();
  }
}

export function getCategoryEmoji(catName = '', itemName = '') {
  const combined = `${catName} ${itemName}`.toLowerCase();
  if (combined.includes('calci') || combined.includes('calculator') || combined.includes('fx-') || combined.includes('scientific')) return '🧮';
  if (combined.includes('watch') || combined.includes('titan') || combined.includes('fastrack') || combined.includes('casio watch')) return '⌚';
  if (combined.includes('airpod') || combined.includes('headphone') || combined.includes('earphone') || combined.includes('buds') || combined.includes('boat')) return '🎧';
  if (combined.includes('phone') || combined.includes('mobile') || combined.includes('iphone') || combined.includes('samsung') || combined.includes('android')) return '📱';
  if (combined.includes('laptop') || combined.includes('macbook') || combined.includes('charger') || combined.includes('dell') || combined.includes('hp')) return '💻';
  if (combined.includes('key')) return '🔑';
  if (combined.includes('wallet') || combined.includes('purse') || combined.includes('money')) return '👛';
  if (combined.includes('bag') || combined.includes('pack') || combined.includes('rucksack')) return '🎒';
  if (combined.includes('bottle') || combined.includes('sipper') || combined.includes('flask')) return '🍶';
  if (combined.includes('ident') || combined.includes('card') || combined.includes('pass') || combined.includes('id ')) return '🪪';
  if (combined.includes('umbrella')) return '☂️';
  if (combined.includes('glasses') || combined.includes('specs') || combined.includes('sunglasses')) return '👓';
  if (combined.includes('ring') || combined.includes('chain') || combined.includes('gold') || combined.includes('silver')) return '💍';
  if (combined.includes('book') || combined.includes('stat') || combined.includes('pen') || combined.includes('notes')) return '📚';
  if (combined.includes('cloth') || combined.includes('shirt') || combined.includes('jacket') || combined.includes('hoodie')) return '🧥';
  if (combined.includes('elect')) return '💻';
  return '📦';
}

/**
 * Animated Recent Items Slideshow Widget (Auto Carousel for Campus-Wide Discovery)
 */
export async function renderRecentItemsSlideshow(container, api, options = {}) {
  if (!container) return;

  try {
    let res;
    if (options.foundOnly !== false) {
      res = await api.getRecentFoundItems({ limit: options.limit || 8, campus_id: options.campus_id || 'ALL' });
    } else {
      res = await api.getRecentItems({ limit: options.limit || 8, ...options });
    }
    const items = res?.items || [];
    if (items.length === 0) {
      container.style.display = 'none';
      return;
    }
    container.style.display = 'block';

    let currentIndex = 0;
    let autoInterval = null;

    container.innerHTML = `
      <div class="slideshow-widget">
        <div class="slideshow-header">
          <div style="display:flex; align-items:center; gap:0.625rem;">
            <span class="pulse-indicator"></span>
            <h2 class="slideshow-title" style="margin:0;">
              Recently Found on Campus
            </h2>
          </div>
          <span style="font-size:0.75rem; color:var(--muted-student); font-weight:600; text-transform:uppercase; letter-spacing:0.04em;">
            Live Campus Feed
          </span>
        </div>
        <div class="slideshow-viewport">
          <div class="slideshow-track" id="slideshow-track">
            ${items.map(item => {
              const itemId = item.found_id || item.id;
              const itemType = (item.item_type || 'FOUND').toUpperCase();
              const isAvailable = (item.status === 'ACTIVE' || item.status === 'MATCHED' || item.availability_badge === 'Available');
              const statusClass = isAvailable ? 'slideshow-badge-available' : 'slideshow-badge-claimed';
              const locationParts = [item.building, item.location_name, item.room_no].filter(Boolean);
              const locationDisplay = locationParts.join(' • ');

              return `
              <a href="item-detail.html?id=${itemId}&type=${itemType.toLowerCase()}" class="slideshow-card">
                <div class="slideshow-media">
                  ${item.image_url 
                    ? `<img src="${item.image_url}" alt="${escapeHtml(item.item_name)}" loading="lazy">` 
                    : `<div style="font-size:3.5rem; opacity:0.8;">${getCategoryEmoji(item.category_name, item.item_name)}</div>`
                  }
                  <div style="position:absolute; top:0.625rem; left:0.625rem; display:flex; gap:0.35rem; flex-wrap:wrap; z-index:2;">
                    <span class="slideshow-badge ${itemType === 'LOST' ? 'slideshow-badge-lost' : 'slideshow-badge-found'}">
                      ${itemType}
                    </span>
                    <span class="slideshow-badge ${statusClass}">
                      ${isAvailable ? '🟢 Available' : '🔵 Claimed'}
                    </span>
                  </div>
                </div>
                <div class="slideshow-info">
                  <div class="slideshow-meta">
                    <span class="chip ${item.campus_code === 'KON' ? 'chip-kondhwa' : 'chip-bibwewadi'}" style="font-size:0.75rem;">
                      ${item.campus_code === 'KON' ? 'Kondhwa' : (item.campus_name || 'Campus')}
                    </span>
                    <span>&bull;</span>
                    <span style="font-weight:600; color:var(--primary-student);">
                      ${getCategoryEmoji(item.category_name, item.item_name)} ${escapeHtml(item.category_name || 'General')}
                    </span>
                    <span>&bull;</span>
                    <span>${formatDate(item.item_date || item.date_found || item.created_at)}</span>
                  </div>
                  <h3 class="slideshow-item-name">${escapeHtml(item.item_name)}</h3>
                  <div style="font-size:0.8125rem; color:var(--muted-student); margin-bottom:0.5rem; display:flex; align-items:center; gap:0.35rem;">
                    <span>📍</span> <span>${escapeHtml(locationDisplay || 'Campus Premises')}</span>
                    ${item.specific_spot ? `<span style="font-style:italic;">(${escapeHtml(item.specific_spot)})</span>` : ''}
                  </div>
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-top:auto; padding-top:0.5rem;">
                    <span style="font-size:0.8125rem; font-weight:700; color:${isAvailable ? '#2D6A4F' : '#2C5282'};">
                      ${isAvailable ? '✓ Ready to Claim' : '🔒 Already Claimed (Verify)'}
                    </span>
                    <span style="font-size:0.875rem; color:var(--primary-student); font-weight:600;">
                      View Details &rarr;
                    </span>
                  </div>
                </div>
              </a>
            `;
            }).join('')}
          </div>
        </div>
        <div class="slideshow-controls">
          <button type="button" class="slideshow-btn" id="btn-slide-prev" aria-label="Previous Slide">&larr;</button>
          <div class="slideshow-dots" id="slideshow-dots">
            ${items.map((_, i) => `<div class="slideshow-dot ${i === 0 ? 'active' : ''}" data-idx="${i}"></div>`).join('')}
          </div>
          <button type="button" class="slideshow-btn" id="btn-slide-next" aria-label="Next Slide">&rarr;</button>
        </div>
      </div>
    `;

    const track = container.querySelector('#slideshow-track');
    const dots = container.querySelectorAll('.slideshow-dot');
    const btnPrev = container.querySelector('#btn-slide-prev');
    const btnNext = container.querySelector('#btn-slide-next');

    function goToSlide(idx) {
      currentIndex = (idx + items.length) % items.length;
      track.style.transform = `translateX(-${currentIndex * 100}%)`;
      dots.forEach((d, i) => {
        d.classList.toggle('active', i === currentIndex);
      });
    }

    btnPrev.addEventListener('click', () => {
      goToSlide(currentIndex - 1);
      resetAuto();
    });

    btnNext.addEventListener('click', () => {
      goToSlide(currentIndex + 1);
      resetAuto();
    });

    dots.forEach(d => {
      d.addEventListener('click', () => {
        goToSlide(parseInt(d.getAttribute('data-idx')));
        resetAuto();
      });
    });

    function startAuto() {
      autoInterval = setInterval(() => {
        goToSlide(currentIndex + 1);
      }, 3800);
    }

    function resetAuto() {
      clearInterval(autoInterval);
      startAuto();
    }

    container.addEventListener('mouseenter', () => clearInterval(autoInterval));
    container.addEventListener('mouseleave', startAuto);

    startAuto();

  } catch (err) {
    console.warn('Failed to load recent slideshow:', err);
  }
}

/**
 * Double Verification Dispute Modal
 */
export function openDoubleVerificationModal({ itemId, itemName, api, onSubmitted }) {
  const existing = document.getElementById('double-verify-modal');
  if (existing) existing.remove();

  const modal = document.createElement('div');
  modal.id = 'double-verify-modal';
  modal.className = 'modal-backdrop';
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-box" style="max-width: 520px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; border-bottom:1px solid var(--border-student); padding-bottom:0.75rem;">
        <div>
          <span class="chip" style="background:#EDF4FB; color:#23527C; font-size:0.75rem; font-weight:700;">Double Verification Dispute</span>
          <h3 style="margin:0.25rem 0 0 0; color:var(--primary-student); font-size:1.25rem;">
            Claim Dispute &mdash; ${escapeHtml(itemName || 'Item #' + itemId)}
          </h3>
        </div>
        <button type="button" id="btn-close-dispute" style="background:none; border:none; font-size:1.5rem; color:var(--muted-student); cursor:pointer; padding:0; min-width:auto; min-height:auto;" aria-label="Close">&times;</button>
      </div>

      <div style="background:#FFF9EB; border:1px solid #F2DC9B; border-radius:var(--radius-sm); padding:0.75rem; margin-bottom:1rem; font-size:0.8125rem; color:#785412; line-height:1.5;">
        <strong>Notice:</strong> This item is currently recorded as claimed. If you believe this is your lost property, submit your distinguishing details below. Campus Security will cross-examine evidence and contact you.
      </div>

      <form id="dispute-form">
        <div class="form-group" style="margin-bottom:1rem;">
          <label class="form-label" for="dispute-reason">Your Ownership Statement &amp; Distinguishing Marks *</label>
          <textarea id="dispute-reason" class="form-textarea" rows="4" placeholder="Mention serial numbers, unique scratches, purchase date, or contents inside..." required minlength="10" style="width:100%; box-sizing:border-box;"></textarea>
        </div>

        <div class="form-group" style="margin-bottom:1rem;">
          <label class="form-label" for="dispute-phone">Contact Phone Number *</label>
          <input type="tel" id="dispute-phone" class="form-input" placeholder="e.g. 9876543210" required style="width:100%; box-sizing:border-box;">
        </div>

        <div class="form-group" style="margin-bottom:1.25rem;">
          <label class="form-label" for="dispute-proof">Supporting Evidence / Receipt (Optional)</label>
          <input type="file" id="dispute-proof" class="form-input" accept="image/jpeg,image/png,image/webp,.pdf" style="width:100%; box-sizing:border-box;">
          <div style="font-size:0.75rem; color:var(--muted-student); margin-top:0.25rem;">Upload bill, packaging box photo, or previous photo of item in possession.</div>
        </div>

        <div style="display:flex; justify-content:flex-end; gap:0.75rem;">
          <button type="button" id="btn-cancel-dispute" class="btn-outline">Cancel</button>
          <button type="submit" id="btn-submit-dispute" class="btn-saffron">Submit for Double Verification</button>
        </div>
      </form>
    </div>
  `;

  document.body.appendChild(modal);

  const closeModal = () => modal.remove();
  modal.querySelector('#btn-close-dispute').addEventListener('click', closeModal);
  modal.querySelector('#btn-cancel-dispute').addEventListener('click', closeModal);

  modal.querySelector('#dispute-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const reason = modal.querySelector('#dispute-reason').value.trim();
    const phone = modal.querySelector('#dispute-phone').value.trim();
    const file = modal.querySelector('#dispute-proof').files[0];
    const submitBtn = modal.querySelector('#btn-submit-dispute');

    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting Request...';

    const formData = new FormData();
    formData.append('dispute_reason', reason);
    formData.append('contact_phone', phone);
    if (file) formData.append('proof', file);

    try {
      await api.requestDoubleVerification(itemId, formData);
      showToast('Double verification request filed! Campus Security Desk has been alerted.', 'success');
      closeModal();
      if (onSubmitted) onSubmitted();
    } catch (err) {
      showToast(err.message || 'Failed to submit dispute', 'error');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Submit for Double Verification';
    }
  });
}

/**
 * Web Audio API synthesized chime (100% offline, zero audio asset files)
 */
export function playNotificationChime() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();

    const now = ctx.currentTime;
    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    const gain = ctx.createGain();

    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(659.25, now); // E5
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(880.00, now + 0.12); // A5

    gain.gain.setValueAtTime(0.18, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.6);

    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(ctx.destination);

    osc1.start(now);
    osc1.stop(now + 0.15);
    osc2.start(now + 0.12);
    osc2.stop(now + 0.6);
  } catch {}
}

/**
 * Interactive Real-Time Claim Messenger Drawer
 */
export function openClaimMessengerDrawer({ claimId, userRole = 'STUDENT', api }) {
  let existing = document.getElementById('claim-messenger-drawer');
  if (existing) existing.remove();

  const isStaff = userRole === 'STAFF';

  const drawer = document.createElement('div');
  drawer.id = 'claim-messenger-drawer';
  drawer.style.cssText = `
    position: fixed; inset: 0; z-index: 10001; display: flex; justify-content: flex-end;
    background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); animation: fadeIn 150ms ease-out;
  `;

  drawer.innerHTML = `
    <div style="width: 100%; max-width: 440px; height: 100%; background: ${isStaff ? '#1C231E' : '#FFFFFF'}; display: flex; flex-direction: column; box-shadow: -8px 0 24px rgba(0,0,0,0.25); color: ${isStaff ? '#FFF' : '#2B2B2B'};">
      <div style="padding: 1.125rem 1.25rem; border-bottom: 1px solid ${isStaff ? '#2F3A34' : 'var(--border-student)'}; display: flex; align-items: center; justify-content: space-between; background: ${isStaff ? '#242D27' : 'var(--surface-alt-student)'};">
        <div style="display:flex; align-items:center; gap:0.625rem;">
          <span style="font-size:1.4rem;">💬</span>
          <div>
            <h3 style="margin:0; font-size:1.0625rem; color:${isStaff ? '#4DAE82' : 'var(--primary-student)'};">
              Claim Discussion #${claimId}
            </h3>
            <span style="font-size:0.75rem; color: ${isStaff ? '#A9AFA6' : 'var(--muted-student)'};">
              Private Channel &bull; ${isStaff ? 'Security Desk &harr; Claimant' : 'With Campus Security Desk'}
            </span>
          </div>
        </div>
        <button type="button" id="msg-close-btn" style="background:none; border:none; color:inherit; font-size:1.5rem; cursor:pointer; padding:0; min-width:auto; min-height:auto;">&times;</button>
      </div>

      <div id="msg-thread" style="flex: 1; overflow-y: auto; padding: 1.25rem; display: flex; flex-direction: column; gap: 0.875rem;">
        <div style="text-align:center; color:${isStaff ? '#A9AFA6' : 'var(--muted-student)'}; font-size:0.8125rem; padding: 2rem 0;">
          Loading conversation thread...
        </div>
      </div>

      <form id="msg-input-form" style="padding: 0.875rem 1.25rem; border-top: 1px solid ${isStaff ? '#2F3A34' : 'var(--border-student)'}; display: flex; gap: 0.5rem; background: ${isStaff ? '#1E2520' : '#FFF'};">
        <input type="text" id="msg-input-text" placeholder="Type a message or verification reply..." required
          style="flex:1; padding: 0.625rem 0.875rem; border-radius: var(--radius-md); border: 1.5px solid ${isStaff ? '#3B4741' : 'var(--border-student)'}; background: ${isStaff ? '#26302A' : '#FFF'}; color: inherit; font-family: inherit; font-size: 0.875rem;">
        <button type="submit" id="msg-send-btn" class="${isStaff ? 'btn-saffron' : 'btn-forest'}" style="padding: 0.625rem 1.125rem; min-height:auto; min-width:auto;">
          Send &rarr;
        </button>
      </form>
    </div>
  `;

  document.body.appendChild(drawer);

  const closeBtn = drawer.querySelector('#msg-close-btn');
  const thread = drawer.querySelector('#msg-thread');
  const form = drawer.querySelector('#msg-input-form');
  const input = drawer.querySelector('#msg-input-text');
  const sendBtn = drawer.querySelector('#msg-send-btn');

  let pollTimer = null;
  let lastCount = 0;

  closeBtn.addEventListener('click', () => {
    clearInterval(pollTimer);
    drawer.remove();
  });

  drawer.addEventListener('click', (e) => {
    if (e.target === drawer) {
      clearInterval(pollTimer);
      drawer.remove();
    }
  });

  async function fetchMessages(isFirst = false) {
    try {
      const res = await api.getClaimMessages(claimId);
      const messages = res.messages || [];

      if (messages.length !== lastCount || isFirst) {
        if (!isFirst && messages.length > lastCount) {
          playNotificationChime();
        }
        lastCount = messages.length;

        if (messages.length === 0) {
          thread.innerHTML = `
            <div style="text-align:center; padding: 3rem 1rem; color: ${isStaff ? '#A9AFA6' : 'var(--muted-student)'};">
              <span style="font-size:2.2rem; display:block; margin-bottom:0.5rem;">🔒</span>
              <strong style="color:inherit;">No messages yet</strong>
              <p style="margin:0.25rem 0 0 0; font-size:0.8125rem;">Use this direct channel to answer questions or arrange collection.</p>
            </div>
          `;
        } else {
          thread.innerHTML = messages.map(m => {
            const isMe = (isStaff && m.sender_role === 'STAFF') || (!isStaff && m.sender_role === 'STUDENT');
            const bubbleBg = isMe 
              ? (isStaff ? '#3E8E6A' : 'var(--primary-student)') 
              : (isStaff ? '#2C362F' : '#F4EFE6');
            const bubbleColor = isMe ? '#FFFFFF' : (isStaff ? '#F2EEE4' : '#2B2B2B');

            return `
              <div style="align-self: ${isMe ? 'flex-end' : 'flex-start'}; max-width: 82%;">
                <div style="font-size: 0.6875rem; color: ${isStaff ? '#A9AFA6' : 'var(--muted-student)'}; margin-bottom: 0.2rem; text-align: ${isMe ? 'right' : 'left'};">
                  ${escapeHtml(m.sender_name || (m.sender_role === 'STAFF' ? 'Security Desk Staff' : 'Student'))}
                </div>
                <div style="background: ${bubbleBg}; color: ${bubbleColor}; padding: 0.625rem 0.875rem; border-radius: var(--radius-md); font-size: 0.875rem; line-height: 1.45; word-break: break-word; box-shadow: var(--shadow-sm);">
                  ${escapeHtml(m.message_text)}
                </div>
                <div style="font-size: 0.65rem; color: ${isStaff ? '#889086' : 'var(--muted-student)'}; margin-top: 0.2rem; text-align: ${isMe ? 'right' : 'left'};">
                  ${formatDateTime(m.sent_at)} ${m.read_at && isMe ? '&bull; Read' : ''}
                </div>
              </div>
            `;
          }).join('');

          thread.scrollTop = thread.scrollHeight;
        }
      }
    } catch (err) {
      console.warn('Message fetch error:', err);
    }
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    sendBtn.disabled = true;
    try {
      await api.sendClaimMessage(claimId, text);
      input.value = '';
      await fetchMessages();
    } catch (err) {
      showToast(err.message || 'Failed to send message', 'error');
    } finally {
      sendBtn.disabled = false;
    }
  });

  fetchMessages(true);
  pollTimer = setInterval(fetchMessages, 3500);
}

/**
 * Digital QR Claim Passport Modal (Student View)
 */
export async function showClaimPassportModal({ claimId, api }) {
  try {
    const res = await api.getClaimPassport(claimId);
    const p = res;

    const modal = document.createElement('div');
    modal.className = 'camera-modal-backdrop';
    modal.innerHTML = `
      <div class="camera-modal-content" style="background:#FFFFFF; color:#2B2B2B; max-width: 480px; border-radius: var(--radius-lg); overflow:hidden;">
        <div style="background: linear-gradient(135deg, #1F4D3A 0%, #16382A 100%); color:#FFF; padding: 1.25rem 1.5rem; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-size:0.75rem; letter-spacing:0.06em; text-transform:uppercase; color:#DCE8DF; font-weight:700;">
              Official VIT Lost &amp; Found Cell
            </div>
            <h2 style="margin:0.2rem 0 0 0; font-family:var(--font-heading); font-size:1.375rem; color:#FFF;">
              Digital Claim Passport
            </h2>
          </div>
          <button type="button" id="btn-close-pass" style="background:none; border:none; color:#FFF; font-size:1.5rem; cursor:pointer; padding:0; min-height:auto; min-width:auto;">&times;</button>
        </div>

        <div style="padding: 1.5rem; text-align:center;">
          <div style="margin-bottom:1rem; display:inline-block; padding: 0.625rem; background:#FFF; border:2px dashed var(--primary-student); border-radius:var(--radius-lg); box-shadow:var(--shadow-md);">
            <img src="${p.qr_data_url}" alt="Verification QR Code" style="width: 190px; height: 190px; display:block;">
          </div>

          <div style="font-size:0.75rem; font-family:monospace; color:var(--muted-student); letter-spacing:0.05em; margin-bottom:1rem;">
            SECURITY TOKEN: ${p.security_hash}
          </div>

          <div style="background:#FAF6EE; border:1px solid var(--border-student); border-radius:var(--radius-md); padding:1rem; text-align:left; font-size:0.875rem;">
            <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
              <span style="color:var(--muted-student);">Passport Code:</span>
              <strong style="color:var(--primary-student);">${p.passport_code}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
              <span style="color:var(--muted-student);">Claimant:</span>
              <strong>${escapeHtml(p.claimant_name)} (${escapeHtml(p.claimant_prn)})</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
              <span style="color:var(--muted-student);">Claimed Item:</span>
              <strong>${escapeHtml(p.found_item_name)}</strong>
            </div>
            <div style="display:flex; justify-content:space-between;">
              <span style="color:var(--muted-student);">Campus Desk:</span>
              <strong>${escapeHtml(p.campus_name)}</strong>
            </div>
          </div>

          <p style="font-size:0.8125rem; color:var(--muted-student); margin:1rem 0 0 0;">
            Show this QR screen to the campus security guard for instant verification &amp; physical handover.
          </p>
        </div>

        <div style="padding: 1rem 1.5rem; background:#FAF6EE; border-top:1px solid var(--border-student); text-align:right;">
          <button type="button" id="btn-done-pass" class="btn-forest" style="width:100%;">Close Passport</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('#btn-close-pass').addEventListener('click', () => modal.remove());
    modal.querySelector('#btn-done-pass').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });

  } catch (err) {
    showToast(err.message || 'Failed to generate claim passport', 'error');
  }
}

/**
 * High-Resolution Printable "LOST / FOUND" Notice Poster Generator Modal
 */
export async function showPosterGeneratorModal({ itemType = 'lost', itemId, api }) {
  try {
    const res = await api.getItemPosterData(itemType, itemId);
    const { item, qr_data_url } = res;
    const isLost = itemType.toLowerCase() === 'lost';

    const modal = document.createElement('div');
    modal.className = 'camera-modal-backdrop';
    modal.innerHTML = `
      <div class="camera-modal-content" style="background:#FFFFFF; color:#2B2B2B; max-width: 580px; border-radius: var(--radius-lg); overflow:hidden;">
        <div style="padding: 1rem 1.25rem; border-bottom:1px solid var(--border-student); display:flex; justify-content:space-between; align-items:center;">
          <h3 style="margin:0; font-family:var(--font-heading); color:var(--primary-student);">
            🖨️ ${isLost ? 'Lost Item Flyer Poster' : 'Found Item Announcement'}
          </h3>
          <button type="button" id="btn-close-poster" style="background:none; border:none; font-size:1.5rem; cursor:pointer; padding:0; min-height:auto; min-width:auto;">&times;</button>
        </div>

        <div style="padding: 1.25rem; max-height: 70vh; overflow-y:auto; text-align:center;">
          <canvas id="poster-canvas" width="600" height="850" style="width:100%; max-width:400px; border:1px solid var(--border-student); border-radius:var(--radius-md); box-shadow:var(--shadow-md);"></canvas>
        </div>

        <div style="padding: 1rem 1.25rem; background:#FAF6EE; border-top:1px solid var(--border-student); display:flex; gap:0.75rem; justify-content:flex-end;">
          <button type="button" id="btn-print-poster" class="btn-outline">🖨️ Print</button>
          <button type="button" id="btn-download-poster" class="${isLost ? 'btn-terracotta' : 'btn-forest'}">📥 Download PNG</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const canvas = modal.querySelector('#poster-canvas');
    const ctx = canvas.getContext('2d');

    // Draw high-resolution poster
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, 600, 850);

    // Header bar
    ctx.fillStyle = isLost ? '#B8532F' : '#1F4D3A';
    ctx.fillRect(0, 0, 600, 95);

    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 20px Georgia, serif';
    ctx.textAlign = 'center';
    ctx.fillText('VISHWAKARMA INSTITUTE OF TECHNOLOGY, PUNE', 300, 42);

    ctx.font = '13px sans-serif';
    ctx.fillText('CAMPUS LOST & FOUND CELL • OFFICIAL NOTICE', 300, 72);

    // Title Tag
    ctx.fillStyle = isLost ? '#B8532F' : '#1F4D3A';
    ctx.font = 'bold 36px Georgia, serif';
    ctx.fillText(isLost ? 'ATTENTION: LOST ITEM' : 'NOTICE: FOUND ITEM', 300, 155);

    // Item Name
    ctx.fillStyle = '#2B2B2B';
    ctx.font = 'bold 26px sans-serif';
    ctx.fillText(item.item_name || 'Item Name', 300, 200);

    // Image or Icon
    const qrImg = new Image();
    qrImg.src = qr_data_url;

    if (item.image_url) {
      const itemImg = new Image();
      itemImg.crossOrigin = 'anonymous';
      itemImg.onload = () => {
        ctx.save();
        ctx.beginPath();
        ctx.roundRect(160, 230, 280, 220, 12);
        ctx.clip();
        ctx.drawImage(itemImg, 160, 230, 280, 220);
        ctx.restore();
        drawDetailsAndQR();
      };
      itemImg.onerror = () => {
        drawFallbackPlaceholder();
        drawDetailsAndQR();
      };
      itemImg.src = item.image_url;
    } else {
      drawFallbackPlaceholder();
      drawDetailsAndQR();
    }

    function drawFallbackPlaceholder() {
      ctx.fillStyle = '#F4EFE6';
      ctx.beginPath();
      ctx.roundRect(160, 230, 280, 220, 12);
      ctx.fill();
      ctx.fillStyle = '#1F4D3A';
      ctx.font = '72px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('📦', 300, 360);
    }

    function drawDetailsAndQR() {
      // Info box
      ctx.fillStyle = '#FAF6EE';
      ctx.beginPath();
      ctx.roundRect(50, 480, 500, 170, 10);
      ctx.fill();
      ctx.strokeStyle = '#E6DFD3';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.textAlign = 'left';
      ctx.fillStyle = '#2B2B2B';
      ctx.font = '15px sans-serif';
      
      const locText = `${item.building || ''} — ${item.location_name || ''} ${item.room_no ? `(${item.room_no})` : ''}`;
      ctx.fillText(`📍 Location: ${locText}`, 75, 520);
      ctx.fillText(`🏢 Campus: ${item.campus_name || ''}`, 75, 555);
      ctx.fillText(`📅 Date Reported: ${formatDate(item.date_lost || item.date_found)}`, 75, 590);
      ctx.fillText(`🏷️ Category: ${item.category_name || ''}`, 75, 625);

      // Description
      ctx.fillStyle = '#6B6B63';
      ctx.font = 'italic 14px sans-serif';
      ctx.textAlign = 'center';
      const desc = item.description ? (item.description.length > 70 ? item.description.substring(0, 67) + '...' : item.description) : '';
      ctx.fillText(`"${desc}"`, 300, 685);

      // QR Code
      qrImg.onload = () => {
        ctx.drawImage(qrImg, 80, 715, 100, 100);
        ctx.textAlign = 'left';
        ctx.fillStyle = isLost ? '#B8532F' : '#1F4D3A';
        ctx.font = 'bold 16px sans-serif';
        ctx.fillText('Scan QR to View or Claim on CampusKhoj', 200, 755);
        ctx.fillStyle = '#6B6B63';
        ctx.font = '13px sans-serif';
        ctx.fillText('Direct student portal link & security verification', 200, 780);
      };
      if (qrImg.complete) qrImg.onload();
    }

    modal.querySelector('#btn-close-poster').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });

    modal.querySelector('#btn-download-poster').addEventListener('click', () => {
      const link = document.createElement('a');
      link.download = `CampusKhoj_${itemType}_${itemId}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    });

    modal.querySelector('#btn-print-poster').addEventListener('click', () => {
      const dataUrl = canvas.toDataURL('image/png');
      const w = window.open('');
      w.document.write(`<img src="${dataUrl}" style="width:100%;max-width:700px;display:block;margin:auto;" onload="window.print();window.close();">`);
    });

  } catch (err) {
    showToast(err.message || 'Failed to load poster data', 'error');
  }
}

/**
 * Camera QR Scanner Modal for Admin Security Desk
 */
export function openAdminQrScannerModal({ onVerified, api }) {
  const modal = document.createElement('div');
  modal.className = 'camera-modal-backdrop';
  modal.innerHTML = `
    <div class="camera-modal-content" style="max-width: 500px;">
      <div class="camera-modal-header">
        <div class="camera-modal-title">
          <span>📷</span> Security Desk QR Passport Scanner
        </div>
        <button type="button" id="btn-close-scanner" style="background:none; border:none; color:#FFF; font-size:1.5rem; cursor:pointer; padding:0; min-height:auto; min-width:auto;">&times;</button>
      </div>
      <div class="camera-viewfinder-wrap" style="height: 320px;">
        <video id="qr-video" playsinline autoplay muted></video>
        <div class="camera-grid-overlay"></div>
        <div class="camera-corner-bracket camera-bracket-tl"></div>
        <div class="camera-corner-bracket camera-bracket-tr"></div>
        <div class="camera-corner-bracket camera-bracket-bl"></div>
        <div class="camera-corner-bracket camera-bracket-br"></div>
      </div>
      <div style="padding: 1.25rem; background: #141915;">
        <label style="font-size: 0.8125rem; color: #A9AFA6; display:block; margin-bottom: 0.375rem;">
          Or enter Passport Code / Claim ID manually:
        </label>
        <div style="display:flex; gap:0.5rem;">
          <input type="text" id="manual-passport-code" placeholder="e.g. CK-PASSPORT-0021 or 21" 
            style="flex:1; padding: 0.5rem 0.75rem; background:#242B26; border:1px solid #3B4741; color:#FFF; border-radius:var(--radius-md);">
          <button type="button" id="btn-submit-code" class="btn-saffron" style="min-height:auto; padding:0.5rem 1rem;">
            Verify
          </button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  const video = modal.querySelector('#qr-video');
  const closeBtn = modal.querySelector('#btn-close-scanner');
  const codeInput = modal.querySelector('#manual-passport-code');
  const submitBtn = modal.querySelector('#btn-submit-code');

  let activeStream = null;

  navigator.mediaDevices?.getUserMedia({ video: { facingMode: 'environment' } })
    .then(stream => {
      activeStream = stream;
      video.srcObject = stream;
    }).catch(() => {
      // Video not available, user can enter manually
    });

  function closeModal() {
    if (activeStream) {
      activeStream.getTracks().forEach(t => t.stop());
    }
    modal.remove();
  }

  closeBtn.addEventListener('click', closeModal);

  async function handleVerify(code) {
    if (!code) return;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Verifying...';
    try {
      const res = await api.verifyPassportCode(code);
      showToast(res.message, 'success');
      closeModal();
      if (onVerified) onVerified(res.claim);
    } catch (err) {
      showToast(err.message || 'Passport verification failed', 'error');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Verify';
    }
  }

  submitBtn.addEventListener('click', () => handleVerify(codeInput.value.trim()));
  codeInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleVerify(codeInput.value.trim());
  });
}

/**
 * CampusKhoj Native Messages Drawer (Simulated SMS & WhatsApp Outbox)
 * Strictly database-backed from message_outbox table.
 * Zero brand copying, zero sounds, zero confetti.
 * Prominent honesty badge: "Simulated: no real SMS or WhatsApp is sent".
 */
export async function openMessagesDrawer({ api, onClosed }) {
  const existing = document.getElementById('ck-messages-drawer-backdrop');
  if (existing) existing.remove();

  const backdrop = document.createElement('div');
  backdrop.id = 'ck-messages-drawer-backdrop';
  backdrop.className = 'ck-messages-backdrop';

  backdrop.innerHTML = `
    <div class="ck-messages-drawer" role="dialog" aria-modal="true" aria-label="Simulated Messages Outbox">
      <!-- Header -->
      <div class="ck-messages-header">
        <h3><span>💬</span> Messages &amp; SMS Alerts</h3>
        <button type="button" class="ck-messages-close" id="ck-drawer-close" aria-label="Close Drawer">&times;</button>
      </div>

      <!-- Honesty Rule Banner -->
      <div class="ck-simulated-banner">
        <span>⚠️</span>
        <span>Simulated: no real SMS or WhatsApp is sent.</span>
      </div>

      <!-- Controls -->
      <div class="ck-messages-controls">
        <div class="ck-filter-chips">
          <button type="button" class="ck-filter-btn active" data-channel="ALL">All</button>
          <button type="button" class="ck-filter-btn" data-channel="SMS">SMS</button>
          <button type="button" class="ck-filter-btn" data-channel="WHATSAPP">WhatsApp</button>
        </div>
        <button type="button" id="ck-btn-read-all" class="btn-outline" style="font-size:0.75rem; padding:0.25rem 0.6rem; border-radius:var(--radius-pill);">
          Mark All Read
        </button>
      </div>

      <!-- Messages Body -->
      <div class="ck-messages-body" id="ck-drawer-messages-list">
        <div style="text-align:center; padding:2rem 1rem; color:var(--muted-student);">
          Loading messages...
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(backdrop);
  requestAnimationFrame(() => backdrop.classList.add('active'));

  const closeBtn = backdrop.querySelector('#ck-drawer-close');
  const readAllBtn = backdrop.querySelector('#ck-btn-read-all');
  const filterBtns = backdrop.querySelectorAll('.ck-filter-btn');
  const msgList = backdrop.querySelector('#ck-drawer-messages-list');

  let activeChannel = 'ALL';
  let cachedMessages = [];

  function closeDrawer() {
    backdrop.classList.remove('active');
    setTimeout(() => {
      backdrop.remove();
      if (onClosed) onClosed();
    }, 260);
  }

  closeBtn.addEventListener('click', closeDrawer);
  backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop) closeDrawer();
  });

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeChannel = btn.getAttribute('data-channel');
      renderList();
    });
  });

  readAllBtn.addEventListener('click', async () => {
    try {
      await api.markAllMessagesRead();
      cachedMessages.forEach(m => m.status = 'READ');
      renderList();
      updateBadgeCounts(0);
      showToast('All simulated messages marked as read', 'success');
    } catch (err) {
      showToast(err.message || 'Failed to mark messages as read', 'error');
    }
  });

  function renderList() {
    const filtered = activeChannel === 'ALL'
      ? cachedMessages
      : cachedMessages.filter(m => (m.channel || '').toUpperCase() === activeChannel);

    if (filtered.length === 0) {
      msgList.innerHTML = `
        <div style="text-align:center; padding:3rem 1.5rem; color:var(--muted-student);">
          <div style="font-size:2rem; margin-bottom:0.5rem;">📭</div>
          <strong style="color:var(--primary-student); font-size:0.95rem; display:block; margin-bottom:0.25rem;">
            No simulated messages yet
          </strong>
          <p style="font-size:0.8125rem; margin:0; line-height:1.4;">
            When a match is found, claim is filed, or verification update happens, your simulated SMS/WhatsApp alert will appear here.
          </p>
        </div>
      `;
      return;
    }

    msgList.innerHTML = '';
    filtered.forEach(m => {
      const bubble = document.createElement('div');
      bubble.className = `ck-msg-bubble ${m.status === 'SIMULATED' ? 'unread' : ''}`;

      const channelClass = (m.channel || 'SMS').toLowerCase() === 'whatsapp' ? 'ck-channel-whatsapp' : 'ck-channel-sms';

      let actionHtml = '';
      if (m.ref_type === 'LOST') {
        actionHtml = `<a href="item-detail.html?type=lost&id=${m.ref_id}" class="ck-msg-action-btn">Open Lost Report &rarr;</a>`;
      } else if (m.ref_type === 'FOUND') {
        actionHtml = `<a href="item-detail.html?type=found&id=${m.ref_id}" class="ck-msg-action-btn">Open Found Item &rarr;</a>`;
      } else if (m.ref_type === 'CLAIM') {
        actionHtml = `<a href="my-claims.html?id=${m.ref_id}" class="ck-msg-action-btn">View Claim Details &rarr;</a>`;
      }

      const formattedTime = new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' });

      bubble.innerHTML = `
        <div class="ck-msg-meta-row">
          <div style="display:flex; align-items:center; gap:0.35rem;">
            <span class="ck-channel-chip ${channelClass}">${escapeHtml(m.channel || 'SMS')}</span>
            <span class="ck-badge-simulated">Simulated</span>
          </div>
          <span class="ck-msg-phone">${escapeHtml(m.to_phone_masked || 'No phone saved')}</span>
        </div>
        <p class="ck-msg-text">${escapeHtml(m.body)}</p>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.25rem;">
          ${actionHtml}
          <span class="ck-msg-time">${escapeHtml(formattedTime)}</span>
        </div>
      `;
      msgList.appendChild(bubble);
    });
  }

  // Load from API
  try {
    const res = await api.getMyMessages({ page: 1, page_size: 50 });
    cachedMessages = res.messages || [];
    renderList();
    updateBadgeCounts(res.unread_count || 0);
  } catch (err) {
    msgList.innerHTML = `
      <div style="padding:1.5rem; text-align:center; color:#B4341B;">
        Failed to load messages: ${escapeHtml(err.message)}
      </div>
    `;
  }
}

/**
 * Updates UI badge counts on messages triggers
 */
function updateBadgeCounts(count) {
  const badges = document.querySelectorAll('.ck-messages-unread-badge');
  badges.forEach(b => {
    if (count > 0) {
      b.textContent = count;
      b.style.display = 'inline-flex';
    } else {
      b.style.display = 'none';
    }
  });
}

/**
 * Attaches Messages Drawer Trigger to buttons & fetches unread count
 */
export async function attachMessagesTrigger({ api }) {
  // Update badge count
  try {
    const res = await api.getMyMessagesUnreadCount();
    updateBadgeCounts(res.unread_count || 0);
  } catch {}

  // Wire buttons with class or id
  document.querySelectorAll('.btn-open-messages, #btn-open-messages').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      openMessagesDrawer({ api, onClosed: () => attachMessagesTrigger({ api }) });
    });
  });
}



