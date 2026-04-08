/**
 * Infratech Engenharia — Webmail Theme JS
 * Funcionalidades extras sobre o tema Elastic do Roundcube
 */

(function () {
  'use strict';

  /* ============================================================
     PALETA DE CORES PARA AVATARES
     ============================================================ */
  var IT_COLORS = [
    '#4f46e5', '#059669', '#d97706', '#7c3aed',
    '#0891b2', '#be185d', '#1d4ed8', '#0f766e'
  ];

  function colorFrom(str) {
    var h = 0;
    for (var i = 0; i < str.length; i++) {
      h = str.charCodeAt(i) + ((h << 5) - h);
    }
    return IT_COLORS[Math.abs(h) % IT_COLORS.length];
  }

  function initials(name) {
    name = name.replace(/<[^>]+>/g, '').replace(/["']/g, '').trim();
    var parts = name.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }

  /* ============================================================
     AVATARES NA LISTA DE MENSAGENS
     Para cada <tr class="message">, extrai o nome do remetente
     e injeta um <span class="it-avatar"> no TD .sender
     ============================================================ */
  function initMessageAvatars() {
    var rows = document.querySelectorAll('#messagelist tr.message');
    rows.forEach(function (row) {
      if (row.querySelector('.it-avatar')) return;
      var senderTd = row.querySelector('td.sender');
      if (!senderTd) return;
      var nameEl = senderTd.querySelector('a') || senderTd;
      var name = nameEl.textContent.trim();
      if (!name) return;

      var av = document.createElement('span');
      av.className = 'it-avatar';
      av.textContent = initials(name);
      av.style.background = colorFrom(name);
      senderTd.insertBefore(av, senderTd.firstChild);
    });
  }

  /* ============================================================
     AVATAR DO USUÁRIO NO HEADER
     Extrai iniciais do e-mail do usuário logado e cria círculo
     ============================================================ */
  function initHeaderAvatar() {
    var right = document.querySelector('#infratech-header .it-header-right');
    if (!right || right.querySelector('.it-header-avatar')) return;
    var emailEl = right.querySelector('.it-user-email');
    if (!emailEl) return;

    var username = emailEl.textContent.trim();
    // Extrai nome da parte local do e-mail (antes do @)
    var localPart = username.split('@')[0].replace(/[._-]/g, ' ');
    var av = document.createElement('span');
    av.className = 'it-header-avatar';
    av.textContent = initials(localPart);
    right.appendChild(av);
  }

  /* ============================================================
     LABEL "PASTAS" NO SIDEBAR
     Injeta label de seção acima da lista de pastas e
     esconde o header original do elastic (duplica username)
     ============================================================ */
  function initSidebarLabel() {
    var sidebar = document.getElementById('layout-sidebar');
    if (!sidebar) return;

    // Esconde o .header original (tem username + logout que já aparecem no nosso header)
    var origHeader = sidebar.querySelector('.sidebar-header, .header');
    if (origHeader) origHeader.style.display = 'none';

    // Adiciona label de seção "PASTAS" antes do mailboxlist
    var content = sidebar.querySelector('.content') || sidebar;
    if (content.querySelector('.it-section-label')) return;
    var lbl = document.createElement('div');
    lbl.className = 'it-section-label';
    lbl.textContent = 'Pastas';
    content.insertBefore(lbl, content.firstChild);
  }

  /* ============================================================
     QUOTA BAR NO FOOTER DO SIDEBAR
     Usa os dados de quota do rcmail.env quando disponíveis
     ============================================================ */
  function initSidebarQuota() {
    var sidebar = document.getElementById('layout-sidebar');
    if (!sidebar) return;

    var footer = sidebar.querySelector('.footer');
    if (!footer) {
      footer = document.createElement('div');
      footer.className = 'footer';
      sidebar.appendChild(footer);
    }
    if (footer.querySelector('.it-quota-inner')) return;

    var pct = 0;
    if (window.rcmail && rcmail.env && rcmail.env.quota) {
      pct = Math.round(rcmail.env.quota.percent || 0);
    }

    // Limpa qualquer conteúdo do elastic que aparece sem estilo
    // (o elastic injeta span com "quota" inline)
    var existingNodes = Array.prototype.slice.call(footer.childNodes);
    existingNodes.forEach(function (node) {
      // remove nós de texto soltos e spans sem classe it-
      if (node.nodeType === 3 ||
          (node.nodeType === 1 && !node.className.match(/it-/))) {
        node.style && (node.style.display = 'none');
      }
    });

    var inner = document.createElement('div');
    inner.className = 'it-quota-inner';
    inner.innerHTML =
      '<div class="it-stat-row">' +
        '<span>Armazenamento</span>' +
        '<span class="it-stat-val">' + pct + '%</span>' +
      '</div>' +
      '<div class="it-quota-bar">' +
        '<div class="it-quota-fill" style="width:' + pct + '%"></div>' +
      '</div>';
    footer.insertBefore(inner, footer.firstChild);
  }

  /* ============================================================
     UTILIDADE: drag-resize genérico
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
     ============================================================ */
  function initComposeResize() {
    var compose = document.getElementById('compose-content')
                  || document.querySelector('.task-compose #layout-content');

    if (!compose) return;
    if (compose.querySelector('.it-compose-resize-handle')) return;

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
     ============================================================ */
  function initReplyResize() {
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
      if (parent.querySelector('.it-reply-resize-handle')) return;

      var handle = document.createElement('div');
      handle.className = 'it-reply-resize-handle';

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
     RESPONSIVIDADE MOBILE — classe it-view-open no #layout
     Controla stack de painéis em telas < 560px
     ============================================================ */

  function isMobile() {
    return window.innerWidth <= 560;
  }

  /* Injeta o botão "← Voltar" no header do #layout-content */
  function initBackButton() {
    var contentHeader = document.querySelector('#layout-content > .header');
    if (!contentHeader || contentHeader.querySelector('#it-back-btn')) return;

    var btn = document.createElement('button');
    btn.id = 'it-back-btn';
    btn.setAttribute('aria-label', 'Voltar para lista');
    btn.textContent = 'Voltar';

    btn.addEventListener('click', function () {
      var layout = document.getElementById('layout');
      if (layout) layout.classList.remove('it-view-open');
    });

    contentHeader.insertBefore(btn, contentHeader.firstChild);
  }

  /* Abre o painel de visualização em mobile */
  function openView() {
    if (!isMobile()) return;
    var layout = document.getElementById('layout');
    if (layout) layout.classList.add('it-view-open');
  }

  /* Fecha o painel de visualização em mobile (volta para lista) */
  function closeView() {
    var layout = document.getElementById('layout');
    if (layout) layout.classList.remove('it-view-open');
  }

  /* Hookeia cliques em linhas da lista de mensagens */
  function initMessageListClick() {
    var list = document.getElementById('messagelist');
    if (!list || list.dataset.itClick) return;
    list.dataset.itClick = '1';

    list.addEventListener('click', function (e) {
      var row = e.target.closest('tr.message');
      if (row) openView();
    });
  }

  /* Reseta estado ao redimensionar acima do breakpoint mobile */
  window.addEventListener('resize', function () {
    if (!isMobile()) closeView();
  });

  /* ============================================================
     INICIALIZAÇÃO
     ============================================================ */
  function init() {
    initHeaderAvatar();
    initSidebarLabel();
    initSidebarQuota();
    initMessageAvatars();
    initBackButton();
    initMessageListClick();
    initComposeResize();
    initReplyResize();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Observa mutações para pegar elementos carregados dinamicamente
  if (window.MutationObserver) {
    var observer = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        if (mutations[i].addedNodes.length > 0) {
          initMessageAvatars();
          initBackButton();
          initMessageListClick();
          initComposeResize();
          initReplyResize();
          break;
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (window.rcmail) {
    rcmail.addEventListener('init', function () {
      setTimeout(init, 300);
    });
    rcmail.addEventListener('insertrow', function () {
      setTimeout(function () {
        initMessageAvatars();
        initMessageListClick();
        initReplyResize();
      }, 100);
    });
    // Mensagem selecionada via teclado ou API do Roundcube
    rcmail.addEventListener('afterpreview', function () {
      openView();
    });
    // Atualiza a barra de quota quando o Roundcube recebe os dados
    rcmail.addEventListener('setquota', function (p) {
      var fill = document.querySelector('.it-quota-fill');
      var val  = document.querySelector('.it-stat-val');
      if (!fill || !p) return;
      var pct = Math.round(p.percent || 0);
      fill.style.width = pct + '%';
      if (val) val.textContent = pct + '%';
    });
  }

})();
