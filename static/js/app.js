// Bibliaolvasási Terv - Frontend JavaScript

// Aktuális fordítás (localStorage-ból vagy alapértelmezett)
let currentTranslation = localStorage.getItem('bibleTranslation') || 'SZIT';

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
    setupTranslationSelector();
    
    // Biblia versek betöltése
    loadBibleVerses();
});

// Fordítás választó beállítása
function setupTranslationSelector() {
    const selector = document.getElementById('translationSelect');
    if (!selector) return;
    
    // Beállítjuk az aktuális fordítást
    selector.value = currentTranslation;
    
    // Változás figyelése
    selector.addEventListener('change', function() {
        currentTranslation = this.value;
        localStorage.setItem('bibleTranslation', currentTranslation);
        
        // Versek újratöltése az új fordítással
        loadBibleVerses();
    });
}

// Biblia versek betöltése API-ból
function loadBibleVerses() {
    const bibleContents = document.querySelectorAll('.bible-content[data-reference]');
    
    bibleContents.forEach(content => {
        const reference = content.dataset.reference;
        if (!reference) return;
        
        // Betöltés jelzés
        content.innerHTML = `
            <div class="verse-loading text-center py-3">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Betöltés...</span>
                </div>
                <span class="ms-2 text-muted">Szöveg betöltése (${currentTranslation})...</span>
            </div>
        `;
        
        // API hívás a kiválasztott fordítással
        fetch(`/api/verses/${encodeURIComponent(reference)}?translation=${currentTranslation}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.html) {
                    content.innerHTML = data.html;
                    // Újra beállítjuk a szöveg kijelölést az új tartalomhoz
                    content.addEventListener('mouseup', handleTextSelection);
                    // Mobil touch esemény
                    content.addEventListener('touchend', function(e) {
                        setTimeout(() => handleTextSelection(e), 100);
                    });
                    // Kiemelések megjelölése a szövegben
                    applyHighlightsToText();
                } else {
                    content.innerHTML = `
                        <p class="text-muted fst-italic mb-0">
                            <i class="bi bi-exclamation-triangle"></i> 
                            ${data.error || 'Nem sikerült betölteni a szöveget'}
                        </p>
                        <p class="small text-muted mt-2">
                            <i class="bi bi-book"></i> ${reference}
                        </p>
                    `;
                }
            })
            .catch(error => {
                console.error('Hiba a versek betöltésekor:', error);
                content.innerHTML = `
                    <p class="text-muted fst-italic mb-0">
                        <i class="bi bi-wifi-off"></i> 
                        Hálózati hiba - nem sikerült betölteni
                    </p>
                    <p class="small text-muted mt-2">
                        <i class="bi bi-book"></i> ${reference}
                    </p>
                `;
            });
    });
}

// Kiemelések vizuális megjelölése a szövegben (csak saját kiemelések)
function applyHighlightsToText() {
    // Csak a saját kiemeléseket keressük (data-own="true")
    const highlightItems = document.querySelectorAll('.highlight-item[data-own="true"]');
    
    highlightItems.forEach(item => {
        const verseRef = item.dataset.ref;
        if (!verseRef) return;
        
        // Megkeressük a vers(ek)et a referencia alapján
        const verses = findVersesForReference(verseRef);
        verses.forEach(verse => {
            verse.classList.add('user-highlighted');
        });
    });
}

// Vers elemek keresése referencia alapján
function findVersesForReference(verseRef) {
    const results = [];
    if (!verseRef) return results;
    
    // Parse reference: "Lk 2,5" or "Lk 2,5-8"
    const match = verseRef.match(/^(.+?)\s*(\d+),(\d+)(?:-(\d+))?$/);
    if (!match) return results;
    
    const book = match[1].trim();
    const chapter = match[2];
    const startVerse = parseInt(match[3]);
    const endVerse = match[4] ? parseInt(match[4]) : startVerse;
    
    // Megkeressük az összes vers elemet
    document.querySelectorAll('.verse[data-ref]').forEach(verse => {
        const ref = verse.dataset.ref;
        const verseMatch = ref.match(/^(.+?)\s*(\d+),(\d+)$/);
        if (!verseMatch) return;
        
        const vBook = verseMatch[1].trim();
        const vChapter = verseMatch[2];
        const vNum = parseInt(verseMatch[3]);
        
        // Ellenőrizzük, hogy ez a vers a kiemeléshez tartozik-e
        if (vBook === book && vChapter === chapter && vNum >= startVerse && vNum <= endVerse) {
            results.push(verse);
        }
    });
    
    return results;
}

// Kiemelésre kattintáskor a szöveghez ugrás
function scrollToHighlightedVerse(verseRef) {
    const verses = findVersesForReference(verseRef);
    if (verses.length > 0) {
        const firstVerse = verses[0];
        // Görgetés a vershez
        firstVerse.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Villogtatás a kiemeléshez
        verses.forEach(v => {
            v.classList.add('highlight-flash');
            setTimeout(() => v.classList.remove('highlight-flash'), 2000);
        });
    }
}

// Szöveg kijelölés kezelése
let selectedVerseData = null;

function setupTextSelection() {
    // Kijelölés figyelése a bibliai szövegeken
    document.querySelectorAll('.bible-content').forEach(content => {
        content.addEventListener('mouseup', handleTextSelection);
        // Mobil eszközökön touchend és selectionchange esemény
        content.addEventListener('touchend', function(e) {
            // Kis késleltetés, hogy a kijelölés befejeződjön
            setTimeout(() => handleTextSelection(e), 100);
        });
    });
    
    // Mobil eszközökön a selectionchange eseményt is figyeljük
    document.addEventListener('selectionchange', function() {
        const selection = window.getSelection();
        if (selection && selection.toString().trim().length >= 3) {
            // Ellenőrizzük, hogy a kijelölés a bible-content-ben van-e
            if (selection.anchorNode) {
                const bibleContent = selection.anchorNode.parentElement?.closest('.bible-content');
                if (bibleContent) {
                    // Jelezzük, hogy van érvényes kijelölés
                    clearTimeout(window.selectionTimeout);
                    window.selectionTimeout = setTimeout(() => {
                        handleTextSelectionMobile(bibleContent);
                    }, 500);
                }
            }
        }
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

// Mobil kijelölés kezelése (selectionchange alapú)
function handleTextSelectionMobile(container) {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();
    
    if (selectedText.length < 3) {
        return;
    }
    
    // Keressük meg az első és utolsó verset a kijelölésben
    let firstRef = null;
    let lastRef = null;
    
    const verses = container.querySelectorAll('.verse[data-ref]');
    verses.forEach(verse => {
        if (selection.containsNode(verse, true)) {
            const ref = verse.dataset.ref;
            if (!firstRef) {
                firstRef = ref;
            }
            lastRef = ref;
        }
    });
    
    // Vers referencia összeállítása
    let verseRef = '';
    if (firstRef && lastRef) {
        const firstMatch = firstRef.match(/^(.+?)\s*(\d+),(\d+)$/);
        const lastMatch = lastRef.match(/^(.+?)\s*(\d+),(\d+)$/);
        
        if (firstMatch && lastMatch) {
            const book = firstMatch[1].trim();
            const firstChapter = firstMatch[2];
            const firstVerse = firstMatch[3];
            const lastChapter = lastMatch[2];
            const lastVerse = lastMatch[3];
            
            if (firstChapter === lastChapter) {
                if (firstVerse === lastVerse) {
                    verseRef = `${book} ${firstChapter},${firstVerse}`;
                } else {
                    verseRef = `${book} ${firstChapter},${firstVerse}-${lastVerse}`;
                }
            } else {
                verseRef = `${book} ${firstChapter},${firstVerse}-${lastChapter},${lastVerse}`;
            }
        } else {
            verseRef = firstRef;
        }
    }
    
    if (!verseRef) {
        return;
    }
    
    // Kijelölési adatok mentése
    selectedVerseData = {
        text: selectedText,
        verseRef: verseRef
    };
    
    // Megjelenítjük a kijelölés panelt
    showSelectionPanel(selectedText, verseRef);
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
    
    // Keressük meg az első és utolsó verset a kijelölésben
    let firstRef = null;
    let lastRef = null;
    
    // Végigmegyünk a kijelölt elemeken
    const verses = container.querySelectorAll('.verse[data-ref]');
    verses.forEach(verse => {
        if (selection.containsNode(verse, true)) {
            const ref = verse.dataset.ref;
            if (!firstRef) {
                firstRef = ref;
            }
            lastRef = ref;
        }
    });
    
    // Vers referencia összeállítása a data-ref-ből (pl "Lk 2,5")
    let verseRef = '';
    if (firstRef && lastRef) {
        // Kinyerjük a könyvet és fejezetet az első referenciából
        // Formátum: "Lk 2,5" -> könyv: "Lk", fejezet: "2", vers: "5"
        const firstMatch = firstRef.match(/^(.+?)\s*(\d+),(\d+)$/);
        const lastMatch = lastRef.match(/^(.+?)\s*(\d+),(\d+)$/);
        
        if (firstMatch && lastMatch) {
            const book = firstMatch[1].trim();
            const firstChapter = firstMatch[2];
            const firstVerse = firstMatch[3];
            const lastChapter = lastMatch[2];
            const lastVerse = lastMatch[3];
            
            if (firstChapter === lastChapter) {
                // Ugyanaz a fejezet
                if (firstVerse === lastVerse) {
                    verseRef = `${book} ${firstChapter},${firstVerse}`;
                } else {
                    verseRef = `${book} ${firstChapter},${firstVerse}-${lastVerse}`;
                }
            } else {
                // Különböző fejezetek
                verseRef = `${book} ${firstChapter},${firstVerse}-${lastChapter},${lastVerse}`;
            }
        } else {
            // Fallback ha nem sikerült parse-olni
            verseRef = firstRef;
        }
    }
    
    if (!verseRef) {
        return; // Nem sikerült referenciát gyűjteni
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
        // Maximum 100 karakter megjelenítése (rövidebb a lebegő panelen)
        const displayText = text.length > 100 ? text.substring(0, 100) + '...' : text;
        
        textElement.textContent = `„${displayText}”`;
        refElement.textContent = verseRef;
        panel.classList.remove('d-none');
        
        // NEM görgetünk - a panel fix pozícióban van a képernyő alján
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
        <div class="highlight-item p-2 mb-2 rounded fade-in new-highlight own-highlight" 
             style="background-color: #ffc10733;"
             data-id="${id}"
             data-ref="${verseRef || ''}"
             data-own="true">
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
    
    const newHighlightItem = list.querySelector(`[data-id="${id}"].highlight-item`);
    if (newHighlightItem) {
        newHighlightItem.addEventListener('click', () => {
            const ref = newHighlightItem.dataset.ref;
            if (ref) {
                scrollToHighlightedVerse(ref);
            }
        });
    }
    
    const newDeleteBtn = list.querySelector(`[data-id="${id}"].delete-highlight`);
    if (newDeleteBtn) {
        newDeleteBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            deleteHighlight(id);
        });
    }
    
    // Frissítjük a kiemeléseket a szövegben
    applyHighlightsToText();
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
    
    // Komment szerkesztés
    setupEditButtons();
}

function setupEditButtons() {
    // Szerkesztés gomb
    document.querySelectorAll('.edit-comment').forEach(btn => {
        btn.addEventListener('click', function() {
            const commentItem = this.closest('.comment-item');
            const contentEl = commentItem.querySelector('.comment-content');
            const editForm = commentItem.querySelector('.edit-form');
            
            // Megjelenítjük a szerkesztő űrlapot, elrejtjük a tartalmat
            contentEl.classList.add('d-none');
            editForm.classList.remove('d-none');
        });
    });
    
    // Mentés gomb
    document.querySelectorAll('.save-edit').forEach(btn => {
        btn.addEventListener('click', async function() {
            const id = this.dataset.id;
            const commentItem = this.closest('.comment-item');
            const textarea = commentItem.querySelector('.edit-textarea');
            const newContent = textarea.value.trim();
            
            if (!newContent) {
                alert('A megjegyzés nem lehet üres!');
                return;
            }
            
            await saveCommentEdit(id, newContent, commentItem);
        });
    });
    
    // Mégse gomb
    document.querySelectorAll('.cancel-edit').forEach(btn => {
        btn.addEventListener('click', function() {
            const commentItem = this.closest('.comment-item');
            const contentEl = commentItem.querySelector('.comment-content');
            const editForm = commentItem.querySelector('.edit-form');
            const textarea = commentItem.querySelector('.edit-textarea');
            
            // Visszaállítjuk az eredeti tartalmat
            textarea.value = contentEl.textContent;
            
            // Elrejtjük a szerkesztő űrlapot, megjelenítjük a tartalmat
            editForm.classList.add('d-none');
            contentEl.classList.remove('d-none');
        });
    });
}

async function saveCommentEdit(id, content, commentItem) {
    try {
        const response = await fetch(`/api/comment/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content: content })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const contentEl = commentItem.querySelector('.comment-content');
            const editForm = commentItem.querySelector('.edit-form');
            const textarea = commentItem.querySelector('.edit-textarea');
            
            // Frissítjük a tartalmat
            contentEl.textContent = content;
            textarea.value = content;
            
            // Elrejtjük a szerkesztő űrlapot
            editForm.classList.add('d-none');
            contentEl.classList.remove('d-none');
            
            // Vizuális visszajelzés
            commentItem.style.backgroundColor = '#d4edda';
            setTimeout(() => {
                commentItem.style.backgroundColor = '';
            }, 1000);
        } else {
            alert('Hiba történt a mentés során.');
        }
    } catch (error) {
        console.error('Hiba a komment szerkesztésekor:', error);
        alert('Hiba történt a mentés során.');
    }
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
