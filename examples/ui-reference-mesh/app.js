'use strict';
const $ = (id) => document.getElementById(id);
const fields = ['title', 'url', 'collection', 'notes'];
const prefix = 'rdd-reference-library-draft-v1:';
function icon(kind) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class','icon'); svg.setAttribute('viewBox','0 0 24 24'); svg.setAttribute('aria-hidden','true'); svg.setAttribute('focusable','false');
  for (const [tag, attributes] of referenceIcons[kind] || referenceIcons.Research) {
    const child = document.createElementNS(svg.namespaceURI, tag);
    for (const [name, value] of Object.entries(attributes)) {
      if (name === 'key') continue;
      const attribute = name.replace(/[A-Z]/g, letter => '-' + letter.toLowerCase());
      child.setAttribute(attribute, name === 'strokeWidth' ? '1.35' : value);
    }
    svg.append(child);
  }
  return svg;
}

$('menu').replaceChildren(icon('menu'));
$('close-menu').replaceChildren(icon('close'));
$('back').replaceChildren(icon('back'), document.createTextNode(' Library'));
$('new').replaceChildren(icon('add'), document.createTextNode(' New reference'));
$('search-icon').replaceChildren(icon('search'));
const drafts = new Map();
const pending = new Set();
let items = [], selected = null, project = 'All references', query = '';
let loading = true;
const readRoute = () => {
  const route = new URL(location.href).searchParams;
  project = ['Interface','Interaction','Research'].includes(route.get('project')) ? route.get('project') : 'All references';
  query = route.get('q') || '';
  selected = route.get('item');
};
function route(push = false) {
  const url = new URL(location.href);
  url.search = '';
  if (project !== 'All references') url.searchParams.set('project', project);
  if (query) url.searchParams.set('q', query);
  if (selected) url.searchParams.set('item', selected);
  history[push ? 'pushState' : 'replaceState']({}, '', url);
}
function saved(id) { return items.find((item) => item.id === id); }
function draft(id) {
  if (drafts.has(id)) return drafts.get(id);
  try {
    const value = JSON.parse(localStorage.getItem(prefix + id));
    if (value && value.id === id && fields.every((f) => typeof value[f] === 'string') && Number.isInteger(value.revision)) {
      drafts.set(id, value); return value;
    }
  } catch { /* Malformed storage is not evidence of a recoverable draft. */ }
  return null;
}
function keep(value) {
  drafts.set(value.id, value);
  try { localStorage.setItem(prefix + value.id, JSON.stringify(value)); return true; }
  catch { if (selected === value.id) $('status').textContent = 'Browser storage is unavailable. Keep this page open until you save.'; return false; }
}
function forget(id) {
  drafts.delete(id);
  try { localStorage.removeItem(prefix + id); } catch { /* Storage warning remains scoped to this browser. */ }
}
function fieldsEqual(a, b) { return fields.every((field) => a[field] === b[field]); }
function fromForm() {
  const base = draft(selected) || saved(selected);
  return {id: selected, revision: base?.revision || 0, ...Object.fromEntries(fields.map((field) => [field, $(field).value]))};
}
function updateBadge() {
  $('draft-badge').dataset.state = pending.has(selected) ? 'pending' : draft(selected) ? 'draft' : 'saved';
  $('draft-badge').textContent = pending.has(selected) ? 'Saving…' : draft(selected) ? 'Draft kept locally' : 'Saved in library';
  $('save').disabled = pending.has(selected);
}
function renderNavigation() {
  $('collection-heading').textContent = project;
  for (const nav of document.querySelectorAll('.collections')) {
    nav.replaceChildren();
    for (const name of ['All references','Interface','Interaction','Research']) {
      const button = document.createElement('button');
      button.type = 'button'; button.setAttribute('aria-current', String(name === project));
      const label = document.createElement('span'); label.append(icon(name),document.createTextNode(name));
      const count = document.createElement('span'); count.textContent = items.filter((item) => name === 'All references' || item.collection === name).length;
      button.append(label,count);
      button.addEventListener('click', () => {
        project = name; route(); renderNavigation(); renderList();
        if ($('navigation').open) $('navigation').close();
      });
      nav.append(button);
    }
  }
}
function renderList() {
  const filtered = items.filter((item) => (project === 'All references' || item.collection === project) &&
    [item.title,item.url,item.notes].some((text) => text.toLowerCase().includes(query.toLowerCase()))).reverse();
  $('count').textContent = loading ? 'Loading references…' : `${filtered.length} reference${filtered.length === 1 ? '' : 's'}`;
  $('list').replaceChildren();
  for (const item of filtered) {
    const button = document.createElement('button'); button.className = 'reference'; button.type = 'button';
    button.dataset.id = item.id; button.setAttribute('aria-current', String(item.id === selected));
    button.dataset.collection = item.collection;
    const category = document.createElement('span'); category.className = 'category'; category.textContent = item.collection;
    const title = document.createElement('strong'); title.textContent = item.title;
    const host = document.createElement('span'); host.className = 'host'; host.textContent = new URL(item.url).hostname;
    const graphic = document.createElement('span'); graphic.className = 'reference-icon'; graphic.append(icon(item.collection));
    const meta = document.createElement('span'); meta.className = 'reference-meta'; meta.append(host,category);
    const excerpt = document.createElement('span'); excerpt.className = 'excerpt'; excerpt.textContent = item.notes;
    button.append(graphic,title,meta,excerpt); button.addEventListener('click', () => openItem(item.id)); $('list').append(button);
  }
  if (!loading && !filtered.length) {
    const empty = document.createElement('p'); empty.className = 'no-results';
    empty.textContent = query ? 'No matching references. Try another word; your open draft is still here.' : 'Nothing here yet. Save a reference for this collection.';
    $('list').append(empty);
  }
}
function openItem(id, push = true) {
  selected = id; route(push); renderList(); renderEditor();
  if (matchMedia('(max-width:800px)').matches) $('title').focus();
}
function renderEditor() {
  const value = selected && (draft(selected) || saved(selected));
  $('form').hidden = !value; $('empty').hidden = !!value;
  document.body.dataset.detail = String(!!value);
  if (!value) return;
  for (const field of fields) $(field).value = value[field];
  $('editor-title').textContent = saved(selected)?.title || 'A new reference';
  $('status').textContent = draft(selected) ? 'Recovered your local draft.' : '';
  updateBadge();
}
for (const field of fields) $(field).addEventListener('input', () => {
  const ok = keep(fromForm()); updateBadge();
  if (ok) $('status').textContent = pending.has(selected) ? 'Saving the earlier version. Your newer edits are kept.' : '';
});
$('search').addEventListener('input', () => { query = $('search').value; route(); renderList(); });
$('new').addEventListener('click', () => {
  const id = 'new-' + crypto.randomUUID();
  keep({id, revision:0,title:'',url:'',collection:project === 'All references' ? 'Interface' : project,notes:''});
  openItem(id); $('title').focus();
});
$('back').addEventListener('click', () => {
  const previous = selected; selected = null; route(true); renderEditor(); renderList();
  const button = [...document.querySelectorAll('.reference')].find((element) => element.dataset.id === previous);
  (button || $('new')).focus();
});
$('menu').addEventListener('click', () => $('navigation').showModal());
$('close-menu').addEventListener('click', () => $('navigation').close());
$('navigation').addEventListener('close', () => $('menu').focus());
$('navigation').addEventListener('keydown', (event) => {
  if (event.key !== 'Tab') return;
  const buttons = [...$('navigation').querySelectorAll('button:not(:disabled)')];
  const first = buttons[0], last = buttons[buttons.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault(); last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault(); first.focus();
  }
});
$('form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (pending.has(selected)) return;
  const snapshot = fromForm();
  let parsed;
  try { parsed = new URL(snapshot.url); } catch { parsed = null; }
  if (!snapshot.title.trim() || !parsed || !['http:','https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
    $('status').textContent = 'Add a title and a complete HTTP or HTTPS URL without credentials.'; return;
  }
  keep(snapshot); pending.add(snapshot.id); updateBadge(); $('status').textContent = 'Saving to your library…';
  try {
    const response = await fetch('/api/items', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(snapshot)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Save failed. Your draft has been kept.');
    const index = items.findIndex((item) => item.id === snapshot.id);
    if (index >= 0) items[index] = result.item; else items.push(result.item);
    const current = draft(snapshot.id);
    const newer = current && !fieldsEqual(current, snapshot);
    if (newer) keep({...current, revision:result.item.revision}); else forget(snapshot.id);
    renderNavigation(); renderList();
    if (selected === snapshot.id) {
      $('editor-title').textContent = result.item.title;
      $('status').textContent = newer ? 'Earlier version saved. Your newer edits are still a draft.' : 'Saved to your library.';
    }
  } catch (error) {
    if (selected === snapshot.id) $('status').textContent = error.message;
  } finally {
    pending.delete(snapshot.id); if (selected === snapshot.id) updateBadge();
  }
});
window.addEventListener('popstate', () => { readRoute(); $('search').value = query; renderNavigation(); renderList(); renderEditor(); });
document.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault(); selected = null; route(true); renderEditor(); $('search').focus();
  }
});
async function start() {
  readRoute(); $('search').value = query;
  try {
    const response = await fetch('/api/items'); if (!response.ok) throw new Error('Library unavailable');
    items = (await response.json()).items;
  } catch { $('load-error').textContent = 'Could not load your library. Reload to try again; local drafts are kept.'; }
  loading = false; renderNavigation(); renderList(); renderEditor();
}
start();
