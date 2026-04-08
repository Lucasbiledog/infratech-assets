/**
 * Infratech Engenharia — Webmail Theme JS
 * Funcionalidades extras sobre o tema Elastic do Roundcube
 */

(function () {
  'use strict';

  /* ============================================================
     UTILIDADE: drag-resize genérico
     handle    — elemento DOM que serve de alça
     getSize   — função que retorna o tamanho atual (px)
     setSize   — função que aplica o novo tamanho (px)
     direction — 'up' (arrastar para cima aumenta) | 'down' (arrastar para baixo aumenta)
     min/max   — limites em px
     ============================================================ */
  function makeDragResize(opts) {
    var handle    = opts.handle;
    var getSize   = opts.getSize;
    var setSize   = opts.setSize;
    var direction = opts.direction || 'down';
    var min       = opts.min || 60;
    var max       = opts.max || 800;

    if (!handle) return;

    handle.addEventListener('mousedown', function (e) {
      e.preventDefault();
      e.stopPropagation();

      var startY    = e.clientY;
      var startSize = getSize();

      handle.classList.add('it-dragging');
      document.body.style.cursor     = 'ns-resize';
      document.body.style.userSelect = 'none';

      function onMove(e) {
        var delta   = direction === 'up' ? startY - e.clientY : e.clientY - startY;
        var newSize = Math.min(max, Math.max(min, startSize + delta));
        setSize(newSize);
      }

      function onUp() {
        handle.classList.remove('it-dragging');
        document.body.style.cursor     = '';
        document.body.style.userSelect = '';
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup',   onUp);
      }

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup',   onUp);
    });
  }

  /* ============================================================
     RESIZE — Janela de Compose flutuante
     O Elastic usa #compose-content dentro de um popup/dialog.
     Adicionamos uma alça no topo do container.
     ============================================================ */
  function initComposeResize() {
    // Roundcube coloca o compose em #compose-content ou .popupmenu
    var compose = document.getElementById('compose-content')
                  || document.querySelector('.task-compose #layout-content');

    if (!compose) return;
    if (compose.querySelector('.it-compose-resize-handle')) return; // já inicializado

    // Garante position:relative no pai
    compose.style.position = 'relative';

    var handle = document.createElement('div');
    handle.className = 'it-compose-resize-handle';
    compose.insertBefore(handle, compose.firstChild);

    makeDragResize({
      handle:    handle,
      getSize:   function () { return compose.offsetHeight; },
      setSize:   function (h) { compose.style.height = h + 'px'; },
      direction: 'up',
      min:       200,
      max:       window.innerHeight - 80,
    });
  }

  /* ============================================================
     RESIZE — Caixa de resposta inline (reply/forward)
     O Roundcube renderiza o editor como <iframe> ou <div contenteditable>
     dentro de #layout-content quando está em modo de composição.
     ============================================================ */
  function initReplyResize() {
    // Tenta localizar o editor de reply (TinyMCE iframe ou textarea/div)
    var editors = [
      document.getElementById('composebody'),
      document.querySelector('#compose-content iframe'),
      document.querySelector('.mce-edit-area iframe'),
      document.querySelector('#compose-content .composebody'),
    ];

    editors.forEach(function (editor) {
      if (!editor) return;
      var parent = editor.parentElement;
      if (!parent) return;
      if (parent.querySelector('.it-reply-resize-handle')) return; // já existe

      var handle = document.createElement('div');
      handle.className = 'it-reply-resize-handle';

      // Insere o handle imediatamente após o editor
      if (editor.nextSibling) {
        parent.insertBefore(handle, editor.nextSibling);
      } else {
        parent.appendChild(handle);
      }

      makeDragResize({
        handle:    handle,
        getSize:   function () { return editor.offsetHeight; },
        setSize:   function (h) {
          editor.style.height    = h + 'px';
          editor.style.minHeight = h + 'px';
        },
        direction: 'down',
        min:       80,
        max:       600,
      });
    });
  }

  /* ============================================================
     INICIALIZAÇÃO
     Roundcube carrega partes da UI de forma assíncrona,
     então observamos mutações no DOM para pegar novos editores.
     ============================================================ */
  function init() {
    initComposeResize();
    initReplyResize();
  }

  // Executa na carga inicial
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Observa mudanças no DOM (compose aberto dinamicamente)
  if (window.MutationObserver) {
    var observer = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        if (mutations[i].addedNodes.length > 0) {
          initComposeResize();
          initReplyResize();
          break;
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Hook no evento do Roundcube de abertura de compose
  if (window.rcmail) {
    rcmail.addEventListener('init', function () {
      setTimeout(init, 300);
    });
    rcmail.addEventListener('insertrow', function () {
      setTimeout(initReplyResize, 100);
    });
  }

})();
