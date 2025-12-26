// Bibliaolvasási Terv - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Aktuális dátum az URL-ből
    const pathParts = window.location.pathname.split('/');
    const currentDate = pathParts[pathParts.length - 1] || getCurrentDateString();
    
    // Event listenerek beállítása
    setupCommentForm();
    setupHighlightForm();
    setupMarkReadButton();
    setupDeleteButtons();
    setupJumpToDateForm();
    setupTextToggle();
    setupTextSelection();
});

// Szöveg kijelölés kezelése
let selectedVerseData = null;

function setupTextSelection() {
    // Kijelölés figyelése a bibliai szövegeken
    document.querySelectorAll('.bible-content').forEach(content => {
        content.addEventListener('mouseup', handleTextSelection);
    });
    
    // Kiemelés megerősítése gomb
    const confirmBtn = document.getElementById('confirmHighlight');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', saveSelectionHighlight);
    }
    
    // Kiemelés megszakítása gomb
    const cancelBtn = document.getElementById('cancelHighlight');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', cancelSelectionHighlight);
    }
    
    // Kattintás máshova elrejti a kijelölés panelt
    document.addEventListener('click', function(e) {
        const selectionPanel = document.getElementById('selectionHighlight');
        if (selectionPanel && !selectionPanel.classList.contains('d-none')) {
            // Ha nem a panelre vagy a bibliai szövegre kattintottunk
            if (!selectionPanel.contains(e.target) && !e.target.closest('.bible-content')) {
                // Ne rejtsd el azonnal, csak ha nincs kijelölés
                const selection = window.getSelection();
                if (!selection || selection.toString().trim() === '') {
                    cancelSelectionHighlight();
                }
            }
        }
    });
}

function handleTextSelection(e) {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();
    
    if (selectedText.length < 3) {
        return; // Túl rövid kijelölés
    }
    
    // Keressük meg a kijelölt verseket
    const range = selection.getRangeAt(0);
    const container = e.currentTarget;
    const book = container.dataset.book || '';
    
    // Keressük meg az első és utolsó verset a kijelölésben
    let startVerse = null;
    let endVerse = null;
    
    // Végigmegyünk a kijelölt elemeken
    const verses = container.querySelectorAll('.verse');
    verses.forEach(verse => {
        if (selection.containsNode(verse, true)) {
            const verseNum = verse.dataset.verse;
            if (startVerse === null) {
                startVerse = verseNum;
            }
            endVerse = verseNum;
        }
    });
    
    // Vers referencia összeállítása
    let verseRef = book;
    if (startVerse && endVerse) {
        if (startVerse === endVerse) {
            verseRef += ` 1:${startVerse}`;
        } else {
            verseRef += ` 1:${startVerse}-${endVerse}`;
        }
    }
    
    // Kijelölési adatok mentése
    selectedVerseData = {
        text: selectedText,
        verseRef: verseRef
    };
    
    // Megjelenítjük a kijelölés panelt
    showSelectionPanel(selectedText, verseRef);
}

function showSelectionPanel(text, verseRef) {
    const panel = document.getElementById('selectionHighlight');
    const textElement = document.getElementById('selectedText');
    const refElement = document.getElementById('selectedVerseRef');
    
    if (panel && textElement && refElement) {
        // Maximum 200 karakter megjelenítése
        const displayText = text.length > 200 ? text.substring(0, 200) + '...' : text;
        
        textElement.textContent = `"${displayText}"`;
        refElement.textContent = verseRef;
        panel.classList.remove('d-none');
        
        // Görgetés a panelhez
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function cancelSelectionHighlight() {
    const panel = document.getElementById('selectionHighlight');
    if (panel) {
        panel.classList.add('d-none');
    }
    selectedVerseData = null;
    window.getSelection().removeAllRanges();
}

async function saveSelectionHighlight() {
    if (!selectedVerseData) return;
    
    const date = getDateFromUrl();
    
    try {
        const response = await fetch('/api/highlight', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date: date,
                text: selectedVerseData.text,
                verse_ref: selectedVerseData.verseRef,
                color: 'yellow'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addHighlightToDOM(data.id, data.username, selectedVerseData.verseRef, selectedVerseData.text);
            cancelSelectionHighlight();
        }
    } catch (error) {
        console.error('Hiba a kiemelés mentésekor:', error);
        alert('Hiba történt a kiemelés mentésekor.');
    }
}

function getCurrentDateString() {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${month}-${day}`;
}

function getDateFromUrl() {
    const pathParts = window.location.pathname.split('/');
    const lastPart = pathParts[pathParts.length - 1];
    // Ellenőrizzük, hogy dátum formátum-e (MM-DD)
    if (/^\d{2}-\d{2}$/.test(lastPart)) {
        return lastPart;
    }
    return getCurrentDateString();
}

// Komment form kezelése
function setupCommentForm() {
    const form = document.getElementById('commentForm');
    if (!form) return;
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const content = document.getElementById('commentContent').value.trim();
        const verseRef = document.getElementById('commentVerse').value.trim();
        
        if (!content) return;
        
        const date = getDateFromUrl();
        
        try {
            const response = await fetch('/api/comment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    date: date,
                    content: content,
                    verse_ref: verseRef,
                    type: 'comment'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Új komment hozzáadása a DOM-hoz
                addCommentToDOM(data.id, data.username, verseRef, content);
                
                // Form ürítése
                document.getElementById('commentContent').value = '';
                document.getElementById('commentVerse').value = '';
            }
        } catch (error) {
            console.error('Hiba a komment küldésekor:', error);
            alert('Hiba történt a komment küldésekor.');
        }
    });
}

function addCommentToDOM(id, username, verseRef, content) {
    const list = document.getElementById('commentsList');
    const noComments = document.getElementById('noComments');
    
    if (noComments) {
        noComments.remove();
    }
    
    const now = new Date().toLocaleString('hu-HU');
    
    const commentHtml = `
        <div class="comment-item p-3 mb-3 border rounded fade-in new-comment" data-id="${id}">
            <div class="d-flex justify-content-between align-items-start mb-2">
                <div>
                    <strong class="text-primary">
                        <i class="bi bi-person-circle"></i> ${username}
                    </strong>
                    ${verseRef ? `<span class="badge bg-secondary ms-2">${verseRef}</span>` : ''}
                </div>
                <div>
                    <small class="text-muted">${now}</small>
                    <button class="btn btn-sm btn-outline-danger ms-2 delete-comment" data-id="${id}">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
            <p class="mb-0">${escapeHtml(content)}</p>
        </div>
    `;
    
    list.insertAdjacentHTML('afterbegin', commentHtml);
    
    // Új törlés gomb eseménykezelő
    const newDeleteBtn = list.querySelector(`[data-id="${id}"].delete-comment`);
    if (newDeleteBtn) {
        newDeleteBtn.addEventListener('click', () => deleteComment(id));
    }
}

// Kiemelés form kezelése
function setupHighlightForm() {
    const form = document.getElementById('highlightForm');
    if (!form) return;
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const text = document.getElementById('highlightText').value.trim();
        const verseRef = document.getElementById('highlightVerse').value.trim();
        
        if (!text) return;
        
        const date = getDateFromUrl();
        
        try {
            const response = await fetch('/api/highlight', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    date: date,
                    text: text,
                    verse_ref: verseRef,
                    color: 'yellow'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                addHighlightToDOM(data.id, data.username, verseRef, text);
                
                document.getElementById('highlightText').value = '';
                document.getElementById('highlightVerse').value = '';
            }
        } catch (error) {
            console.error('Hiba a kiemelés mentésekor:', error);
            alert('Hiba történt a kiemelés mentésekor.');
        }
    });
}

function addHighlightToDOM(id, username, verseRef, text) {
    const list = document.getElementById('highlightsList');
    const noHighlights = document.getElementById('noHighlights');
    
    if (noHighlights) {
        noHighlights.remove();
    }
    
    const highlightHtml = `
        <div class="highlight-item p-2 mb-2 rounded fade-in new-highlight" 
             style="background-color: #ffc10733;"
             data-id="${id}">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    ${verseRef ? `<strong class="text-primary">${verseRef}:</strong>` : ''}
                    <span>"${escapeHtml(text)}"</span>
                    <br>
                    <small class="text-muted">
                        <i class="bi bi-person"></i> ${username}
                    </small>
                </div>
                <button class="btn btn-sm btn-outline-danger delete-highlight" data-id="${id}">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>
    `;
    
    list.insertAdjacentHTML('afterbegin', highlightHtml);
    
    const newDeleteBtn = list.querySelector(`[data-id="${id}"].delete-highlight`);
    if (newDeleteBtn) {
        newDeleteBtn.addEventListener('click', () => deleteHighlight(id));
    }
}

// Olvasottként megjelölés
function setupMarkReadButton() {
    const btn = document.getElementById('markReadBtn');
    if (!btn) return;
    
    btn.addEventListener('click', async function() {
        const date = this.dataset.date;
        const isRead = this.dataset.read === 'true';
        const newState = !isRead;
        
        try {
            const response = await fetch('/api/mark-read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    date: date,
                    is_read: newState
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Gomb frissítése
                this.dataset.read = newState.toString();
                
                if (newState) {
                    this.classList.remove('btn-outline-success');
                    this.classList.add('btn-success');
                    this.innerHTML = '<i class="bi bi-check-circle-fill"></i> Elolvasva ✓';
                } else {
                    this.classList.remove('btn-success');
                    this.classList.add('btn-outline-success');
                    this.innerHTML = '<i class="bi bi-circle"></i> Megjelölés olvasottként';
                }
            }
        } catch (error) {
            console.error('Hiba az olvasás megjelölésekor:', error);
        }
    });
}

// Törlés gombok
function setupDeleteButtons() {
    // Komment törlés
    document.querySelectorAll('.delete-comment').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.dataset.id;
            deleteComment(id);
        });
    });
    
    // Kiemelés törlés
    document.querySelectorAll('.delete-highlight').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.dataset.id;
            deleteHighlight(id);
        });
    });
}

async function deleteComment(id) {
    if (!confirm('Biztosan törlöd ezt a kommentet?')) return;
    
    try {
        const response = await fetch(`/api/comment/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            const element = document.querySelector(`.comment-item[data-id="${id}"]`);
            if (element) {
                element.style.opacity = '0';
                setTimeout(() => element.remove(), 300);
            }
        }
    } catch (error) {
        console.error('Hiba a komment törlésekor:', error);
    }
}

async function deleteHighlight(id) {
    if (!confirm('Biztosan törlöd ezt a kiemelést?')) return;
    
    try {
        const response = await fetch(`/api/highlight/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            const element = document.querySelector(`.highlight-item[data-id="${id}"]`);
            if (element) {
                element.style.opacity = '0';
                setTimeout(() => element.remove(), 300);
            }
        }
    } catch (error) {
        console.error('Hiba a kiemelés törlésekor:', error);
    }
}

// Ugrás dátumra
function setupJumpToDateForm() {
    const form = document.getElementById('jumpToDateForm');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const month = document.getElementById('jumpMonth').value;
        const day = document.getElementById('jumpDay').value;
        
        window.location.href = `/daily/${month}-${day}`;
    });
}

// Szöveg megjelenítés/elrejtés gombok
function setupTextToggle() {
    document.querySelectorAll('.toggle-text').forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.dataset.target;
            const target = document.getElementById(targetId);
            
            if (target) {
                const bsCollapse = new bootstrap.Collapse(target, {
                    toggle: true
                });
                
                // Gomb ikon váltása
                this.classList.toggle('collapsed');
                
                // Gomb szöveg váltása
                if (this.classList.contains('collapsed')) {
                    this.innerHTML = '<i class="bi bi-eye-slash"></i> Szöveg';
                } else {
                    this.innerHTML = '<i class="bi bi-eye"></i> Szöveg';
                }
            }
        });
    });
}

// Segédfüggvények
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
