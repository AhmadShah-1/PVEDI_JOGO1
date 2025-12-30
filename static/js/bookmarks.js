// Bookmarks Module
// Handles Page Links, Snippet List, and Folders

const BookmarksModule = (() => {
  const dom = {
    pageLinksList: document.getElementById('page-links-list'),
    bookmarksContainer: document.getElementById('bookmarks-container'),
    newFolderInput: document.getElementById('new-folder-name'),
    createFolderBtn: document.getElementById('create-folder-btn')
  };

  // State
  let bookmarks = []; // { id, name, type: 'snippet'|'folder', children: [], dataUrl, isActive }
  // Flattened structure or nested? Let's use nested for folders.
  // Actually, to support drag-and-drop simply, a flat list with a parentId might be easier, 
  // but User asked for "folders" specifically. Let's do a top-level array that can contain items or folders.
  
  // NOTE: For simplicity in this demo, we'll keep it 1-level deep: Root -> Folders -> Snippets.
  // Items at root are temp snippets.
  
  function init() {
    loadFromStorage();
    renderBookmarks();

    // Listeners
    dom.createFolderBtn.addEventListener('click', createFolder);
    
    // Allow Enter key to create folder
    dom.newFolderInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        createFolder();
      }
    });
    
    // External Events
    window.addEventListener('rag-meta', (e) => {
      updatePageLinks(e.detail.pages);
    });

    window.addEventListener('snippet-created', (e) => {
      addSnippet(e.detail);
    });
  }

  // --- Page Links Section ---

  function updatePageLinks(pages) {
    dom.pageLinksList.innerHTML = '';
    if (!pages || pages.length === 0) {
      dom.pageLinksList.innerHTML = 'No pages referenced.';
      return;
    }

    pages.forEach(page => {
      const link = document.createElement('div');
      link.className = 'page-link';
      link.textContent = `Page ${page}`;
      link.onclick = () => {
        window.dispatchEvent(new CustomEvent('jump-to-page', { detail: { page } }));
      };
      dom.pageLinksList.appendChild(link);
    });
  }

  // --- Bookmarks / Snippets Logic ---

  function createFolder() {
    const name = dom.newFolderInput.value.trim();
    if (!name) return;

    const folder = {
      id: 'folder-' + Date.now(),
      type: 'folder',
      name: name,
      children: []
    };
    
    bookmarks.push(folder);
    saveToStorage();
    renderBookmarks();
    dom.newFolderInput.value = '';
  }

  function addSnippet(snippetData) {
    const snippet = {
      id: snippetData.id,
      type: 'snippet',
      name: snippetData.name,
      dataUrl: snippetData.dataUrl,
      isActive: false // "Soft Red" initially
    };
    bookmarks.push(snippet); // Add to root (temp storage)
    saveToStorage();
    renderBookmarks();
  }

  function toggleSnippetActive(id, parentId = null) {
    // Find snippet
    let snippet = null;
    let list = bookmarks;
    
    if (parentId) {
      const folder = bookmarks.find(f => f.id === parentId);
      if (folder) list = folder.children;
    }
    
    snippet = list.find(s => s.id === id);
    if (!snippet) return;

    snippet.isActive = !snippet.isActive;
    
    // Dispatch event to Thought Bubble
    const eventName = snippet.isActive ? 'add-to-canvas' : 'remove-from-canvas';
    window.dispatchEvent(new CustomEvent(eventName, { detail: snippet }));

    renderBookmarks();
    saveToStorage();
  }

  function deleteItem(id, parentId = null) {
    if (confirm('Delete this item?')) {
      if (parentId) {
        const folder = bookmarks.find(f => f.id === parentId);
        if (folder) {
          folder.children = folder.children.filter(c => c.id !== id);
        }
      } else {
        bookmarks = bookmarks.filter(b => b.id !== id);
      }
      saveToStorage();
      renderBookmarks();
    }
  }

  function renameItem(id, parentId = null) {
    let item = null;
    if (parentId) {
      const folder = bookmarks.find(f => f.id === parentId);
      if (folder) item = folder.children.find(c => c.id === id);
    } else {
      item = bookmarks.find(b => b.id === id);
    }

    if (item) {
      const newName = prompt("Rename to:", item.name);
      if (newName) {
        item.name = newName;
        saveToStorage();
        renderBookmarks();
      }
    }
  }

  // --- Drag and Drop Logic ---
  
  function handleDragStart(e, id, parentId) {
    e.dataTransfer.setData('text/plain', JSON.stringify({ id, parentId }));
  }

  function handleDropOnFolder(e, folderId) {
    e.preventDefault();
    const data = JSON.parse(e.dataTransfer.getData('text/plain'));
    
    if (data.parentId === folderId) return; // Dropped on self's parent

    // Find item
    let item = null;
    if (data.parentId) {
      const parent = bookmarks.find(f => f.id === data.parentId);
      item = parent.children.find(c => c.id === data.id);
      // Remove from old parent
      parent.children = parent.children.filter(c => c.id !== data.id);
    } else {
      item = bookmarks.find(b => b.id === data.id);
      // Remove from root
      bookmarks = bookmarks.filter(b => b.id !== data.id);
    }

    // Add to new folder
    const targetFolder = bookmarks.find(f => f.id === folderId);
    if (targetFolder && item) {
      targetFolder.children.push(item);
    }

    saveToStorage();
    renderBookmarks();
  }

  // --- Rendering ---

  function renderBookmarks() {
    dom.bookmarksContainer.innerHTML = '';
    
    bookmarks.forEach(item => {
      if (item.type === 'folder') {
        renderFolder(item);
      } else {
        renderSnippet(item, null);
      }
    });
  }

  function renderFolder(folder) {
    const el = document.createElement('div');
    el.className = 'folder-item';
    el.innerHTML = `
      <div class="folder-header">
        <span class="folder-title">📁 ${folder.name}</span>
        <span class="folder-count">(${folder.children.length})</span>
        <div class="folder-actions">
          <button class="rename-folder-btn" title="Rename Folder">✎</button>
          <button class="delete-folder-btn" title="Delete Folder">×</button>
        </div>
      </div>
      <div class="folder-content"></div>
    `;

    // Drop Zone
    const header = el.querySelector('.folder-header');
    const titleSpan = el.querySelector('.folder-title');
    const content = el.querySelector('.folder-content');
    
    // Toggle folder open/close when clicking on title
    titleSpan.addEventListener('click', (e) => {
      e.stopPropagation();
      content.classList.toggle('open');
      console.log(`Folder "${folder.name}" toggled. Open:`, content.classList.contains('open'));
    });
    
    // Drag and drop handlers with visual feedback
    header.addEventListener('dragover', (e) => {
      e.preventDefault();
      header.classList.add('drag-over');
    });
    
    header.addEventListener('dragleave', () => {
      header.classList.remove('drag-over');
    });
    
    header.addEventListener('drop', (e) => {
      header.classList.remove('drag-over');
      handleDropOnFolder(e, folder.id);
    });

    // Folder actions
    el.querySelector('.rename-folder-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      renameItem(folder.id, null);
    });
    
    el.querySelector('.delete-folder-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      deleteItem(folder.id, null);
    });

    // Render Children
    folder.children.forEach(child => {
      const childEl = renderSnippet(child, folder.id, false);
      content.appendChild(childEl);
    });

    dom.bookmarksContainer.appendChild(el);
  }

  function renderSnippet(snippet, parentId, appendToContainer = true) {
    const el = document.createElement('div');
    el.className = `snippet-item ${snippet.isActive ? 'active' : ''}`;
    el.draggable = true;
    el.innerHTML = `
      <div class="snippet-name" title="${snippet.name}">${snippet.name}</div>
      <div class="snippet-actions">
        <button class="rename-btn">✎</button>
        <button class="delete-btn">×</button>
      </div>
    `;

    // Events
    el.addEventListener('click', (e) => {
      // Ignore clicks on actions
      if (e.target.tagName === 'BUTTON') return;
      toggleSnippetActive(snippet.id, parentId);
    });

    el.addEventListener('dragstart', (e) => handleDragStart(e, snippet.id, parentId));

    el.querySelector('.rename-btn').onclick = () => renameItem(snippet.id, parentId);
    el.querySelector('.delete-btn').onclick = () => deleteItem(snippet.id, parentId);

    if (appendToContainer) {
      dom.bookmarksContainer.appendChild(el);
    }
    return el;
  }

  // --- Persistence ---
  // Currently using localStorage: bookmarks persist across browser sessions
  // To use sessionStorage instead (clears when browser closes), change localStorage to sessionStorage

  function saveToStorage() {
    localStorage.setItem('rag_bookmarks', JSON.stringify(bookmarks));
  }

  function loadFromStorage() {
    const raw = localStorage.getItem('rag_bookmarks');
    if (raw) {
      try {
        bookmarks = JSON.parse(raw);
      } catch (e) {
        console.error('Failed to load bookmarks', e);
      }
    }
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', BookmarksModule.init);

