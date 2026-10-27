(function () {
  // Confirm before destructive forms
  document.querySelectorAll('form[data-confirm]').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      if (!confirm(f.getAttribute('data-confirm'))) e.preventDefault();
    });
  });

  var form = document.getElementById('person-form');
  if (!form || !window.WC) return;
  var WC = window.WC;

  // ---- photo preview (camera or upload both land in the "photo" field) ----
  var main = form.querySelector('[data-photo]');
  var alt = form.querySelector('[data-photo-alt]');
  var box = document.getElementById('photo-box');
  function preview(file) {
    if (!file) return;
    var url = URL.createObjectURL(file);
    box.innerHTML = '';
    var img = document.createElement('img');
    img.src = url; img.alt = 'New photo';
    box.appendChild(img);
  }
  main.addEventListener('change', function () { preview(main.files[0]); });
  alt.addEventListener('change', function () {
    if (!alt.files[0]) return;
    try { var dt = new DataTransfer(); dt.items.add(alt.files[0]); main.files = dt.files; } catch (e) { alt.name = 'photo'; main.name = ''; }
    preview(alt.files[0]);
  });

  // ---- occasions ----
  var list = document.getElementById('occ-list');
  var tpl = document.getElementById('occ-template');
  var empty = document.getElementById('occ-empty');

  function lang() {
    var r = form.querySelector('input[name="language"]:checked');
    return r ? r.value : 'en';
  }
  function firstName() {
    var n = (form.querySelector('#name').value || '').trim().split(/\s+/)[0];
    return n || '[name]';
  }
  function fill(t, detail) {
    return (t || '').split('{name}').join(firstName()).split('{my_name}').join(WC.myName).split('{detail}').join(detail);
  }
  function refresh(block) {
    var type = block.querySelector('[data-type]').value;
    var info = WC.occasions[type];
    var detail = block.querySelector('[data-detail]').value.trim();
    var custom = block.querySelector('[data-custom]').value.trim();
    var l = lang();
    var text = custom ? fill(custom, detail) : fill(WC.templates[l][type], detail || (info.extra ? '[' + info.extra.toLowerCase() + ']' : info.label.toLowerCase()));
    block.querySelector('[data-preview]').textContent = text;
    block.querySelector('[data-langname]').textContent = WC.langs[l];
    var rec = block.querySelector('[data-recurring]').value === '1';
    block.querySelector('[data-yearhint]').textContent = rec ? '— year optional' : '— year needed';
  }
  function onType(block) {
    var info = WC.occasions[block.querySelector('[data-type]').value];
    var extra = block.querySelector('[data-extra]');
    extra.hidden = !info.extra;
    block.querySelector('[data-extralabel]').textContent = info.extra;
    block.querySelector('[data-detail]').placeholder = info.hint || '';
    block.querySelector('[data-recurring]').value = info.yearly ? '1' : '0';
    block.querySelector('[data-ai]').value = info.ai ? '1' : '0';
    refresh(block);
  }
  function wire(block) {
    block.querySelector('[data-type]').addEventListener('change', function () { onType(block); });
    ['[data-detail]', '[data-custom]'].forEach(function (s) {
      block.querySelector(s).addEventListener('input', function () { refresh(block); });
    });
    block.querySelector('[data-recurring]').addEventListener('change', function () { refresh(block); });
    block.querySelector('[data-remove]').addEventListener('click', function () {
      var hasId = block.querySelector('input[name="occ_id"]').value;
      if (hasId && !confirm('Remove this occasion? It is deleted when you save.')) return;
      block.remove();
      empty.hidden = list.querySelector('[data-occ]') !== null;
    });
    refresh(block);
  }
  list.querySelectorAll('[data-occ]').forEach(wire);
  document.getElementById('add-occ').addEventListener('click', function () {
    var node = tpl.content.firstElementChild.cloneNode(true);
    list.appendChild(node);
    empty.hidden = true;
    wire(node);
    node.scrollIntoView({behavior: 'smooth', block: 'center'});
    node.querySelector('[data-type]').focus();
  });
  form.querySelectorAll('input[name="language"]').forEach(function (r) {
    r.addEventListener('change', function () { list.querySelectorAll('[data-occ]').forEach(refresh); });
  });
  form.querySelector('#name').addEventListener('input', function () { list.querySelectorAll('[data-occ]').forEach(refresh); });
})();
