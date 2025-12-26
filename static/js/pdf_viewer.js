// PDF Viewer Module
// Handles PDF rendering, page navigation, and Snippet Tool (visual cropping)

const PdfViewerModule = (() => {
  const dom = {
    container: document.getElementById('pdf-render-container'),
    wrapper: document.getElementById('pdf-wrapper'),
    prevBtn: document.getElementById('prev-page'),
    nextBtn: document.getElementById('next-page'),
    pageIndicator: document.getElementById('page-indicator'),
    totalPages: document.getElementById('total-pages'),
    label: document.getElementById('pdf-doc-label'),
    snippetBtn: document.getElementById('snippet-tool-btn'),
    overlay: document.getElementById('selection-overlay'),
  };

  let pdfDoc = null;
  let pageNum = 1;
  let pageRendering = false;
  let pageNumPending = null;
  let scale = 1.2; 
  let canvas = null;
  let ctx = null;

  // Snippet State
  let isSnippetMode = false;
  let isDrawing = false;
  let startX = 0;
  let startY = 0;

  function handlePageInput() {
    if (!pdfDoc) return;
    
    // Extract number from text (should be just a number)
    const text = dom.pageIndicator.textContent.trim();
    const newPage = parseInt(text);
    
    if (isNaN(newPage) || newPage < 1 || newPage > pdfDoc.numPages) {
      // Invalid input, restore current page
      dom.pageIndicator.textContent = pageNum;
      return;
    }
    
    pageNum = newPage;
    queueRenderPage(pageNum);
  }

  function init() {
    dom.prevBtn.addEventListener('click', onPrevPage);
    dom.nextBtn.addEventListener('click', onNextPage);
    dom.snippetBtn.addEventListener('click', toggleSnippetMode);
    
    // Handle page number input (blur and Enter key)
    dom.pageIndicator.addEventListener('blur', handlePageInput);
    dom.pageIndicator.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        dom.pageIndicator.blur(); // This will trigger handlePageInput
      }
    });
    
    // Listen for metadata event from Chat to load PDF
    window.addEventListener('rag-meta', (e) => {
      const meta = e.detail;
      if (meta.pdf_url) {
        loadPdf(meta.pdf_url, meta.first_page, meta.doc_label);
      }
    });

    // Listen for "jump-to-page" event (from Bookmarks)
    window.addEventListener('jump-to-page', (e) => {
      if (pdfDoc && e.detail.page) {
        queueRenderPage(e.detail.page);
      }
    });

    // Overlay Mouse Events for Snipping
    dom.wrapper.addEventListener('mousedown', startSelection);
    dom.wrapper.addEventListener('mousemove', updateSelection);
    dom.wrapper.addEventListener('mouseup', endSelection);
  }


  async function loadPdf(url, initialPage, label) {
    dom.label.textContent = label || "Document";
    try {
      const loadingTask = pdfjsLib.getDocument(url);
      pdfDoc = await loadingTask.promise;
      dom.totalPages.textContent = pdfDoc.numPages;
      
      pageNum = initialPage || 1;
      renderPage(pageNum);
    } catch (err) {
      console.error('Error loading PDF:', err);
      dom.container.innerHTML = `<div style="padding:20px; color:red">Error loading PDF</div>`;
    }
  }

  async function renderPage(num) {
    pageRendering = true;
    
    // Fetch page
    const page = await pdfDoc.getPage(num);
    
    // Prepare canvas
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.className = 'pdf-page-canvas';
      dom.container.innerHTML = '';
      dom.container.appendChild(canvas);
      ctx = canvas.getContext('2d');
    }

    const viewport = page.getViewport({ scale: scale });
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    // Render
    const renderContext = {
      canvasContext: ctx,
      viewport: viewport
    };
    
    await page.render(renderContext).promise;
    
    pageRendering = false;
    pageNum = num; // Update the current page number
    dom.pageIndicator.textContent = num;

    if (pageNumPending !== null) {
      renderPage(pageNumPending);
      pageNumPending = null;
    }
  }

  function queueRenderPage(num) {
    if (pageRendering) {
      pageNumPending = num;
    } else {
      renderPage(num);
    }
  }

  function onPrevPage() {
    if (pageNum <= 1) return;
    pageNum--;
    queueRenderPage(pageNum);
  }

  function onNextPage() {
    if (pageNum >= pdfDoc.numPages) return;
    pageNum++;
    queueRenderPage(pageNum);
  }

  // --- Snippet Tool Logic ---

  function toggleSnippetMode() {
    isSnippetMode = !isSnippetMode;
    if (isSnippetMode) {
      dom.snippetBtn.classList.add('active');
      dom.wrapper.style.cursor = 'crosshair';
      dom.overlay.style.display = 'block';
    } else {
      dom.snippetBtn.classList.remove('active');
      dom.wrapper.style.cursor = 'default';
      dom.overlay.style.display = 'none';
      dom.overlay.style.width = '0';
      dom.overlay.style.height = '0';
    }
  }

  function startSelection(e) {
    if (!isSnippetMode) return;
    isDrawing = true;
    
    const rect = dom.wrapper.getBoundingClientRect();
    startX = e.clientX - rect.left + dom.wrapper.scrollLeft;
    startY = e.clientY - rect.top + dom.wrapper.scrollTop;

    dom.overlay.style.left = `${startX}px`;
    dom.overlay.style.top = `${startY}px`;
    dom.overlay.style.width = '0px';
    dom.overlay.style.height = '0px';
    dom.overlay.style.display = 'block';
  }

  function updateSelection(e) {
    if (!isSnippetMode || !isDrawing) return;
    
    const rect = dom.wrapper.getBoundingClientRect();
    const currentX = e.clientX - rect.left + dom.wrapper.scrollLeft;
    const currentY = e.clientY - rect.top + dom.wrapper.scrollTop;

    const width = currentX - startX;
    const height = currentY - startY;

    dom.overlay.style.width = `${Math.abs(width)}px`;
    dom.overlay.style.height = `${Math.abs(height)}px`;
    dom.overlay.style.left = `${width < 0 ? currentX : startX}px`;
    dom.overlay.style.top = `${height < 0 ? currentY : startY}px`;
  }

  function endSelection(e) {
    if (!isSnippetMode || !isDrawing) return;
    isDrawing = false;
    
    // 1. Calculate relative coordinates on the canvas
    // Note: The overlay is relative to pdf-wrapper, but we need coordinates relative to the canvas itself.
    // Assuming the canvas is the first child of container and centered/positioned naturally.
    if (!canvas) return;

    const overlayRect = dom.overlay.getBoundingClientRect();
    const canvasRect = canvas.getBoundingClientRect();

    // Intersection of selection and canvas
    const x = overlayRect.left - canvasRect.left;
    const y = overlayRect.top - canvasRect.top;
    const w = overlayRect.width;
    const h = overlayRect.height;

    if (w < 10 || h < 10) return; // Ignore accidental clicks

    // 2. Crop from Canvas
    try {
      // Scale coordinates back to canvas actual size if CSS size differs (it shouldn't if we set width/height attribs)
      const scaleX = canvas.width / canvasRect.width;
      const scaleY = canvas.height / canvasRect.height;

      const sourceX = x * scaleX;
      const sourceY = y * scaleY;
      const sourceW = w * scaleX;
      const sourceH = h * scaleY;

      // Create temp canvas for the snippet
      const tmpCanvas = document.createElement('canvas');
      tmpCanvas.width = sourceW;
      tmpCanvas.height = sourceH;
      const tmpCtx = tmpCanvas.getContext('2d');

      tmpCtx.drawImage(
        canvas, 
        sourceX, sourceY, sourceW, sourceH, 
        0, 0, sourceW, sourceH
      );

      const dataUrl = tmpCanvas.toDataURL('image/png');

      // 3. Dispatch event with snippet data
      const event = new CustomEvent('snippet-created', {
        detail: {
          id: Date.now().toString(),
          dataUrl: dataUrl,
          name: `Snippet ${dom.pageIndicator.textContent}`,
          page: pageNum
        }
      });
      window.dispatchEvent(event);

      // Reset
      toggleSnippetMode(); // Turn off after one snip? Or keep on? User said "visual selection", usually one-off.
                           // Let's turn off to indicate success.
    } catch (err) {
      console.error('Error creating snippet:', err);
    }
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', PdfViewerModule.init);

