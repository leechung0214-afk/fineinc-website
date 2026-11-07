'use strict';

// A deliberately small DOM, not an implementation of the portfolio behavior.
// HTML supplies the actual elements/attributes; fetch, history and aborts retain
// their observable state so a missing handler or swallowed error cannot pass.
const fs = require('node:fs');
const vm = require('node:vm');

const decode = text => String(text).replace(/&(?:amp|lt|gt|quot|apos|#39|#(\d+)|#x([\da-f]+));/gi, (all, dec, hex) =>
  dec ? String.fromCodePoint(Number(dec)) : hex ? String.fromCodePoint(parseInt(hex, 16)) :
    ({ '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&apos;': "'", '&#39;': "'" }[all.toLowerCase()] || all));

class Events {
  constructor() { this.listeners = new Map(); }
  addEventListener(type, handler, options = {}) {
    const rows = this.listeners.get(type) || [];
    rows.push({ handler, once: !!options.once });
    this.listeners.set(type, rows);
  }
  removeEventListener(type, handler) {
    this.listeners.set(type, (this.listeners.get(type) || []).filter(row => row.handler !== handler));
  }
  dispatchEvent(event) {
    if (!event.target) event.target = this;
    event.currentTarget = this;
    event.preventDefault ||= function () { this.defaultPrevented = true; };
    event.stopPropagation ||= function () { this.cancelBubble = true; };
    for (const row of [...(this.listeners.get(event.type) || [])]) {
      if (row.once) this.removeEventListener(event.type, row.handler);
      row.handler.call(this, event);
    }
    return !event.defaultPrevented;
  }
  emit(type, values = {}) { const event = { type, ...values }; this.dispatchEvent(event); return event; }
}

class TextNode {
  constructor(text) { this.nodeType = 3; this.data = text; this.parentNode = null; }
  get textContent() { return this.data; }
  set textContent(value) { this.data = String(value); }
}

class Element extends Events {
  constructor(tag, document, nodeType = 1) {
    super(); this.tagName = tag.toUpperCase(); this.nodeType = nodeType;
    this.ownerDocument = document; this.childNodes = []; this.parentNode = null;
    this.attributes = {}; this.dataset = {}; this.style = {}; this._value = null;
    this.open = false; this.disabled = false; this.hidden = false;
    this.classList = {
      contains: value => this.className.split(/\s+/).includes(value),
      add: (...values) => { this.className = [...new Set([...this.className.split(/\s+/).filter(Boolean), ...values])].join(' '); },
      remove: (...values) => { this.className = this.className.split(/\s+/).filter(value => !values.includes(value)).join(' '); },
      toggle: (value, force) => {
        const add = force === undefined ? !this.classList.contains(value) : force;
        this.classList[add ? 'add' : 'remove'](value); return add;
      },
    };
  }
  get id() { return this.attributes.id || ''; }
  set id(value) { this.setAttribute('id', value); }
  get className() { return this.attributes.class || ''; }
  set className(value) { this.attributes.class = String(value); }
  get children() { return this.childNodes.filter(node => node.nodeType === 1); }
  get parentElement() { return this.parentNode?.nodeType === 1 ? this.parentNode : null; }
  get firstChild() { return this.childNodes[0] || null; }
  get firstElementChild() { return this.children[0] || null; }
  get options() { return this.children.filter(node => node.tagName === 'OPTION'); }
  get textContent() { return this.childNodes.map(node => node.textContent).join(''); }
  set textContent(value) { this.replaceChildren(new TextNode(String(value ?? ''))); }
  get value() {
    if (this.tagName === 'SELECT') {
      const selected = this.options.find(node => node.value === this._value);
      return selected ? selected.value : this._value === null ? this.options[0]?.value || '' : '';
    }
    return this._value ?? this.attributes.value ?? (this.tagName === 'OPTION' ? this.textContent : '');
  }
  set value(value) { this._value = String(value); }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
    if (name === 'hidden') this.hidden = true;
    if (name === 'disabled') this.disabled = true;
    if (name === 'value') this._value = String(value);
    if (name.startsWith('data-')) this.dataset[name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = String(value);
  }
  getAttribute(name) { return this.attributes[name] ?? null; }
  hasAttribute(name) { return name in this.attributes; }
  removeAttribute(name) {
    delete this.attributes[name];
    if (name === 'hidden') this.hidden = false;
    if (name === 'disabled') this.disabled = false;
  }
  append(...nodes) {
    for (let node of nodes) {
      if (typeof node === 'string') node = new TextNode(node);
      if (node.nodeType === 11) { this.append(...[...node.childNodes]); continue; }
      node.remove?.(); node.parentNode = this; this.childNodes.push(node);
    }
  }
  prepend(...nodes) {
    const old = [...this.childNodes]; this.replaceChildren(...nodes, ...old);
  }
  appendChild(node) { this.append(node); return node; }
  removeChild(node) { this.childNodes.splice(this.childNodes.indexOf(node), 1); node.parentNode = null; return node; }
  replaceChildren(...nodes) { this.childNodes.forEach(node => { node.parentNode = null; }); this.childNodes = []; this.append(...nodes); }
  remove() { this.parentNode?.removeChild(this); }
  matches(selector) {
    if (selector.includes(',')) return selector.split(',').some(value => this.matches(value.trim()));
    const attribute = selector.match(/\[([^=\]]+)(?:=["']?([^"'\]]+)["']?)?\]/);
    if (attribute && (!this.hasAttribute(attribute[1]) || attribute[2] !== undefined && this.getAttribute(attribute[1]) !== attribute[2])) return false;
    const base = selector.replace(/\[[^\]]+\]/g, '');
    if (base.startsWith('#')) return this.id === base.slice(1);
    if (base.startsWith('.')) return base.slice(1).split('.').every(value => this.classList.contains(value));
    return !base || base === '*' || this.tagName === base.toUpperCase();
  }
  querySelectorAll(selector) {
    const result = [];
    for (const node of this.children) {
      if (node.matches(selector)) result.push(node);
      result.push(...node.querySelectorAll(selector));
    }
    return result;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  closest(selector) { return this.matches(selector) ? this : this.parentNode?.closest?.(selector) || null; }
  contains(node) { return node === this || this.children.some(child => child.contains(node)); }
  focus() { this.ownerDocument.activeElement = this; this.focused = true; }
  select() { this.selected = true; }
  setSelectionRange(start, end) { this.selectionStart = start; this.selectionEnd = end; }
  scrollIntoView(options) { this.lastScrollOptions = options; }
  getBoundingClientRect() { return { left: 0, top: 0, right: 100, bottom: 100 }; }
  showModal() { this.open = true; }
  close() { this.open = false; this.emit('close'); }
  click() { if (!this.disabled) this.emit('click'); }
  set innerHTML(value) {
    this.ownerDocument.innerHtmlWrites.push(String(value));
    this.replaceChildren(); parseHtml(String(value), this.ownerDocument, this);
  }
  get innerHTML() { throw new Error('DOM shim does not serialize HTML; use actual DOM state assertions.'); }
}

function parseHtml(html, document, parent) {
  const stack = [parent];
  const voids = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
  for (const token of html.matchAll(/<!--[\s\S]*?-->|<![^>]*>|<\/?[a-z][^>]*>|[^<]+/gi)) {
    const text = token[0];
    if (text.startsWith('<!')) continue;
    if (text.startsWith('</')) {
      const tag = text.slice(2, -1).trim().toUpperCase();
      const index = stack.findLastIndex(node => node.tagName === tag);
      if (index > 0) stack.length = index;
    } else if (text.startsWith('<')) {
      const tag = text.match(/^<([^\s/>]+)/)[1]; const node = document.createElement(tag);
      for (const match of text.slice(tag.length + 1, -1).matchAll(/([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g))
        node.setAttribute(match[1], decode(match[2] ?? match[3] ?? match[4] ?? ''));
      stack.at(-1).append(node);
      if (!voids.has(tag.toLowerCase()) && !text.endsWith('/>')) stack.push(node);
    } else stack.at(-1).append(new TextNode(decode(text)));
  }
}

function makeClock() {
  let serial = 0; let now = 0; const timers = new Map();
  return {
    setTimeout(fn, delay = 0) { const id = ++serial; timers.set(id, { fn, at: now + Number(delay) }); return id; },
    clearTimeout(id) { timers.delete(id); },
    advance(ms) {
      const end = now + ms; let guard = 0;
      while (true) {
        const next = [...timers].filter(([, row]) => row.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
        if (!next) break;
        if (++guard > 1000) throw new Error('Unexpected unbounded timer loop');
        now = next[1].at; timers.delete(next[0]); next[1].fn();
      }
      now = end;
    },
    pending: () => [...timers.values()].map(row => row.at - now),
  };
}

async function flush() { for (let i = 0; i < 4; i++) await new Promise(resolve => setImmediate(resolve)); }
function effectivelyVisible(node) {
  for (let current = node; current; current = current.parentNode)
    if (current.hidden || current.style?.display === 'none' || current.style?.visibility === 'hidden') return false;
  return !!node;
}

async function mount({ htmlPath, sourcePath, responses = [], url = 'https://example.test/fineinc-website/?v=keep', clipboard = 'success' }) {
  const document = new Element('#document', null, 9); document.ownerDocument = document;
  document.innerHtmlWrites = []; document.createElement = tag => new Element(tag, document);
  document.createDocumentFragment = () => new Element('#fragment', document, 11);
  document.createTextNode = value => new TextNode(value);
  document.getElementById = id => document.querySelector('#' + id);
  parseHtml(fs.readFileSync(htmlPath, 'utf8'), document, document);
  document.body = document.querySelector('body'); document.documentElement = document.querySelector('html');
  const window = new Events(); const location = new URL(url); const clock = makeClock();
  const entries = [{ url: location.href, state: null }]; let position = 0; const historyCalls = [];
  const updateLocation = value => { location.href = new URL(value, location.href).href; };
  const history = {
    get length() { return entries.length; }, get state() { return entries[position].state; },
    replaceState(state, unused, target) { updateLocation(target); entries[position] = { url: location.href, state }; historyCalls.push({ method: 'replace', url: location.href }); },
    pushState(state, unused, target) { updateLocation(target); entries.splice(position + 1); entries.push({ url: location.href, state }); position++; historyCalls.push({ method: 'push', url: location.href }); },
    back() { if (position > 0) { position--; updateLocation(entries[position].url); window.emit('popstate', { state: entries[position].state }); } },
    forward() { if (position + 1 < entries.length) { position++; updateLocation(entries[position].url); window.emit('popstate', { state: entries[position].state }); } },
  };
  const calls = []; const pending = []; const writes = [];
  function fetch(url, options = {}) {
    const spec = responses[calls.length] || { pending: true }; const call = { url, options, spec };
    calls.push(call);
    return new Promise((resolve, reject) => {
      let settled = false;
      const finish = (method, value) => { if (!settled) { settled = true; method(value); } };
      const success = () => finish(resolve, { ok: spec.status === undefined || spec.status >= 200 && spec.status < 300, status: spec.status ?? 200, json: async () => {
        call.jsonRequested = true;
        if (spec.jsonError) throw new SyntaxError('invalid JSON');
        if (spec.jsonPending) return new Promise((resolveBody, rejectBody) => {
          call.resolveBody = () => resolveBody(structuredClone(spec.data)); call.rejectBody = rejectBody;
        });
        return structuredClone(spec.data);
      } });
      call.resolve = success; call.reject = error => finish(reject, error);
      options.signal?.addEventListener('abort', () => {
        call.aborted = true;
        const error = new DOMException('Aborted', 'AbortError');
        finish(reject, error); call.rejectBody?.(error);
      }, { once: true });
      if (options.signal?.aborted) { call.aborted = true; finish(reject, new DOMException('Aborted', 'AbortError')); }
      else if (spec.pending) pending.push(call);
      else if (spec.error) finish(reject, new Error(spec.error));
      else success();
    });
  }
  const navigator = clipboard === 'missing' ? {} : { clipboard: { writeText: async value => { writes.push(value); if (clipboard === 'reject') throw new Error('Clipboard denied'); } } };
  Object.assign(window, { document, location, history, navigator, setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout });
  const context = { document, window, location, history, navigator, fetch, URL, URLSearchParams, AbortController, DOMException, setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout, console, structuredClone };
  vm.runInNewContext(fs.readFileSync(sourcePath, 'utf8'), context, { filename: sourcePath, timeout: 3000 });
  await flush();
  return { document, window, location, history, historyCalls, calls, pending, writes, clock, ids: new Proxy({}, { get: (_, id) => document.getElementById(id) }), flush,
    async input(id, value) { const node = document.getElementById(id); node.value = value; node.emit('input'); clock.advance(1000); await flush(); },
    async change(id, value) { const node = document.getElementById(id); node.value = value; node.emit('change'); await flush(); },
    async click(id) {
      const node = document.getElementById(id);
      if (!effectivelyVisible(node)) throw new Error(`Cannot user-click a hidden control: #${id}`);
      if (node.disabled) throw new Error(`Cannot user-click a disabled control: #${id}`);
      node.click(); await flush();
    },
  };
}

module.exports = { mount, flush, effectivelyVisible };
