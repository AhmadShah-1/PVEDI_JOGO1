// Thought Bubble Module
// Handles the Whiteboard / Canvas interaction using Fabric.js

const ThoughtBubbleModule = (() => {
  const dom = {
    canvasContainer: document.getElementById('canvas-container'),
    canvasEl: document.getElementById('thought-bubble-canvas'),
    downloadBtn: document.getElementById('tb-download'),
    downloadPDF: document.getElementById('de-download'),
    clearBtn: document.getElementById('tb-clear'),
    // Tools
    btnSelect: document.getElementById('tb-select'),
    btnDraw: document.getElementById('tb-draw'),
    btnText: document.getElementById('tb-text'),
    btnRect: document.getElementById('tb-rect'),
    btnCircle: document.getElementById('tb-circle'),
    btnNote: document.getElementById('tb-note'),
    // Color inputs
    inputDrawColor: document.getElementById('tb-draw-color'),
    inputTextColor: document.getElementById('tb-text-color'),
    inputRectColor: document.getElementById('tb-rect-color'),
    inputCircleColor: document.getElementById('tb-circle-color')
  };

  let canvas = null;
  // Map snippet IDs to Fabric objects to easily remove them
  let snippetMap = {}; 

  function init() {
    initCanvas();
    window.addEventListener('resize', resizeCanvas);
    
    // Buttons
    if (dom.downloadBtn) {
      dom.downloadBtn.addEventListener('click', downloadPNG);
    }
    
    if (dom.downloadPDF) {
        dom.downloadPDF.addEventListener('click', downloadPDF);
    }
    
    if (dom.clearBtn) {
        dom.clearBtn.addEventListener('click', clearCanvas);
    }

    // Tools
    if (dom.btnSelect) dom.btnSelect.addEventListener('click', () => setMode('select'));
    if (dom.btnDraw) dom.btnDraw.addEventListener('click', () => setMode('draw'));
    if (dom.btnText) dom.btnText.addEventListener('click', addText);
    if (dom.btnRect) dom.btnRect.addEventListener('click', addRect);
    if (dom.btnCircle) dom.btnCircle.addEventListener('click', addCircle);
    if (dom.btnNote) dom.btnNote.addEventListener('click', addNote);
    
    // Color inputs
    if (dom.inputDrawColor) {
        dom.inputDrawColor.addEventListener('input', (e) => {
            if (canvas) canvas.freeDrawingBrush.color = e.target.value;
        });
    }

    // Events from Bookmarks
    window.addEventListener('add-to-canvas', (e) => addSnippetToCanvas(e.detail));
    window.addEventListener('remove-from-canvas', (e) => removeSnippetFromCanvas(e.detail.id));
    
    // Set initial mode
    if (dom.btnSelect) setMode('select');
  }

  function initCanvas() {
    // Initial Size
    const width = dom.canvasContainer.clientWidth;
    const height = dom.canvasContainer.clientHeight;

    dom.canvasEl.width = width;
    dom.canvasEl.height = height;

    canvas = new fabric.Canvas('thought-bubble-canvas', {
      backgroundColor: 'transparent',
      selection: true
    });
    
    // Brush settings
    canvas.freeDrawingBrush.width = 5;
    canvas.freeDrawingBrush.color = dom.inputDrawColor ? dom.inputDrawColor.value : "#000000"; // Default black

    // Handle Delete key
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        const active = canvas.getActiveObjects();
        if (active.length) {
          canvas.discardActiveObject();
          active.forEach(obj => {
             // If it's a snippet, we should technically update Bookmark state too, 
             // but user flow says "click BM to revert". 
             // So if deleted here, maybe just remove visually? 
             // User requirement: "If a BM is clicked... snippet should be removed". 
             // Reverse: "Note that there should be a small delete button on the top right of each BM".
             // Let's just allow removing from canvas for now.
             canvas.remove(obj);
          });
          canvas.requestRenderAll();
        }
      }
    });
  }

  function resizeCanvas() {
    if (!canvas) return;
    const width = dom.canvasContainer.clientWidth;
    const height = dom.canvasContainer.clientHeight;
    canvas.setWidth(width);
    canvas.setHeight(height);
    canvas.renderAll();
  }

  function addSnippetToCanvas(snippet) {
    if (snippetMap[snippet.id]) return; // Already exists

    fabric.Image.fromURL(snippet.dataUrl, (img) => {
      img.set({
        left: 50,
        top: 50,
        scaleX: 0.5,
        scaleY: 0.5,
        cornerSize: 10,
        transparentCorners: false
      });
      
      // Store ID for removal
      img.snippetId = snippet.id;
      
      canvas.add(img);
      canvas.setActiveObject(img);
      snippetMap[snippet.id] = img;
    });
  }

  function removeSnippetFromCanvas(snippetId) {
    const obj = snippetMap[snippetId];
    if (obj) {
      canvas.remove(obj);
      delete snippetMap[snippetId];
      canvas.requestRenderAll();
    }
  }

  function clearCanvas() {
    if (confirm('Clear entire Thought Bubble?')) {
      canvas.clear();
      snippetMap = {};
      // Note: This doesn't update Bookmark state (Soft Green -> Soft Red). 
      // Ideally, we'd dispatch events back to Bookmarks, but keeping it simple.
    }
  }

  function downloadPNG() {
    if (!canvas) return;
    const dataURL = canvas.toDataURL({
      format: 'png',
      quality: 1,
      multiplier: 2 // High res
    });

    const link = document.createElement('a');
    link.download = 'thought_bubble.png';
    link.href = dataURL;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function downloadPDF() {
    if (!canvas) return;

    const imgData = canvas.toDataURL({
        format: 'png',
        multiplier: 2
    });

    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({
        orientation: 'landscape',
        unit: 'px',
        format: [canvas.width, canvas.height]
    });

    pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
    pdf.save('domain_expansion.pdf');
  }


  function setMode(mode) {
    if (!canvas) return;

    // UI Updates
    [dom.btnSelect, dom.btnDraw].forEach(btn => {
        if(btn) btn.classList.remove('active');
    });

    if (mode === 'select') {
        canvas.isDrawingMode = false;
        if(dom.btnSelect) dom.btnSelect.classList.add('active');
    } else if (mode === 'draw') {
        canvas.isDrawingMode = true;
        if(dom.btnDraw) dom.btnDraw.classList.add('active');
    }
  }

  function addText() {
    if (!canvas) return;
    const color = dom.inputTextColor ? dom.inputTextColor.value : '#000000';
    
    const text = new fabric.IText('Text', {
        left: 100,
        top: 100,
        fontFamily: 'Arial',
        fill: color,
        fontSize: 20
    });
    canvas.add(text);
    canvas.setActiveObject(text);
    setMode('select');
  }

  function addRect() {
    if (!canvas) return;
    const color = dom.inputRectColor ? dom.inputRectColor.value : '#ffff00';
    
    // Hex to RGB for opacity
    const r = parseInt(color.substr(1, 2), 16);
    const g = parseInt(color.substr(3, 2), 16);
    const b = parseInt(color.substr(5, 2), 16);
    const rgba = `rgba(${r},${g},${b},0.5)`;

    const rect = new fabric.Rect({
        left: 150,
        top: 150,
        fill: rgba,
        width: 150,
        height: 100,
        transparentCorners: false,
        lockUniScaling: false // Allow independent width/height scaling
    });
    
    // Set controls to allow non-uniform scaling
    rect.setControlsVisibility({
        mt: true, mb: true, ml: true, mr: true, 
        bl: true, br: true, tl: true, tr: true,
        mtr: true
    });

    canvas.add(rect);
    canvas.setActiveObject(rect);
    setMode('select');
  }

  function addCircle() {
    if (!canvas) return;
    const color = dom.inputCircleColor ? dom.inputCircleColor.value : '#000000';
    
    const circle = new fabric.Circle({
        left: 200,
        top: 200,
        fill: 'transparent',
        stroke: color,
        strokeWidth: 3,
        radius: 50
    });
    canvas.add(circle);
    canvas.setActiveObject(circle);
    setMode('select');
  }

  function addNote() {
    if (!canvas) return;
    
    // Group: Yellow Box + Centered Text
    const noteColor = '#fff740'; // Classic sticky note yellow
    const size = 200;

    const box = new fabric.Rect({
        fill: noteColor,
        width: size,
        height: size,
        shadow: 'rgba(0,0,0,0.3) 5px 5px 5px'
    });

    const text = new fabric.IText('Note', {
        fontFamily: 'Arial',
        fontSize: 24,
        fill: '#333',
        originX: 'center',
        originY: 'center',
        left: size / 2,
        top: size / 2,
        textAlign: 'center',
        splitByGrapheme: true,
        width: size - 20
    });

    const group = new fabric.Group([box, text], {
        left: 100,
        top: 100,
        subTargetCheck: true // Allow selecting inner objects (like text to edit)
    });

    // Make text editable on double click
    text.on('mousedblclick', () => {
        // To edit text inside group, we need to ungroup or handle specially.
        // Fabric doesn't support direct group text editing easily in all versions.
        // Easier approach: Add them as separate objects but select together?
        // Or just let user ungroup.
        
        // Better UX for simple "Sticky Note":
        // Just add IText with background color?
        // IText backgroundColor only covers text line.
        // Textbox with backgroundColor?
    });
    
    // Re-implementation using Textbox with background
    const note = new fabric.Textbox('Double-click to edit', {
        left: 100,
        top: 100,
        width: 200,
        fontSize: 20,
        backgroundColor: '#fff740',
        fill: '#333',
        padding: 20,
        textAlign: 'center',
        shadow: 'rgba(0,0,0,0.3) 5px 5px 5px',
        splitByGrapheme: true
    });

    canvas.add(note);
    canvas.setActiveObject(note);
    setMode('select');
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', ThoughtBubbleModule.init);

