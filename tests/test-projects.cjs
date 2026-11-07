'use strict';

// Run: node tests/test-projects.cjs
// This executes the real browser script against DOM parsed from the real HTML.
// It never launches a browser, contacts the network, or changes public data.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { mount, effectivelyVisible } = require('./fixtures/project-dom.cjs');
const root = path.resolve(__dirname, '..');
const htmlPath = path.join(root, 'index.html');
const sourcePath = path.join(root, 'assets/projects.js');
const artifact = path.join(__dirname, '_artifacts/20261107_portfolio/frontend-tests');
const checks = [];
const tests = [];
const test = (name, fn) => tests.push({ name, fn });
const photo = name => ({ src: `assets/projects/${name}.jpg`, alt: `검증 사진 ${name}` });
const project = (id, rest = {}) => ({ id, title: `검증 행사 ${id}`, startDate: '2026-01-02', category: '포럼·회의', location: '광주', role: '음향', cover: photo(id), gallery: [], ...rest });
const payload = projects => ({ schemaVersion: 1, replaceExisting: true, projects });
const valid = () => payload([
  project('alpha', { title: 'ＡＣＣ 무대 ＆ 영상', location: '광주 문화관', role: '음향·조명', category: '포럼·회의 & 공개+행사', gallery: [photo('alpha'), photo('alpha-second')] }),
  { id: 'beta', title: '청소년 예술 축제', year: 2025, category: '공연', location: '여수', role: '조명', cover: photo('beta'), gallery: [] },
  { id: 'gamma', title: 'ACC 야외 공연', year: 2024, month: 7, category: '공연', location: '광주', role: '음향', cover: photo('gamma'), gallery: [] },
]);
const start = (responses, extras = {}) => mount({ htmlPath, sourcePath, responses, ...extras });
const loaded = extras => start([{ data: valid() }], extras);
const cards = app => app.ids.projectGrid.querySelectorAll('.project-photo-card');
const visible = app => cards(app).filter(card => !card.hidden);
const visibleTitles = app => visible(app).map(card => card.querySelector('.project-title-button').textContent);
const state = app => app.ids.projectLoadState.dataset.state;
function categoryDefault(app, stage) {
  const options = app.ids.projectCategory.options.filter(option => option.value === 'all');
  assert.equal(options.length, 1, `${stage}: exactly one default category option`);
  assert.equal(options[0].textContent, '전체 분야', `${stage}: visible default category label`);
}
function noResultLeak(app) {
  assert.equal(app.ids.projectGrid.children.length, 0, 'failed fetch must not preserve or partially render projects');
  assert.equal(app.ids.projectTools.hidden, true, 'filters must remain hidden until valid nonempty data');
  assert.equal(app.ids.projectCount.textContent.trim(), '', 'failure must not claim real/zero project counts');
  assert.equal(app.ids.projectEmpty.hidden, true, 'load failure is distinct from zero search results');
  assert.equal(app.ids.projectRetry.hidden, false, 'retry must be reachable');
  assert.equal(effectivelyVisible(app.ids.projectRetry), true, 'retry must be visible through its ancestors');
  assert.equal(app.ids.projectRetry.disabled, false, 'retry must remain usable');
}

test('actual HTML exposes accessible controls and an empty initial grid', async () => {
  const app = await start([{ pending: true }]);
  for (const id of ['projectLoadState', 'projectLoadMessage', 'projectRetry', 'projectTools', 'projectCount', 'projectSearch', 'projectYear', 'projectCategory', 'projectFilterReset', 'projectFilterShare', 'projectShareStatus', 'projectShareUrl', 'projectEmpty', 'projectGrid', 'projectDialog'])
    assert.ok(app.ids[id], `actual HTML missing #${id}`);
  assert.equal(app.ids.projectLoadState.getAttribute('role'), 'status');
  assert.ok(['polite', 'assertive'].includes(app.ids.projectLoadState.getAttribute('aria-live')));
  assert.equal(app.ids.projectSearch.getAttribute('type'), 'search');
  assert.equal(app.ids.projectSearch.getAttribute('aria-controls'), 'projectGrid');
  assert.ok(app.ids.projectShareUrl.hasAttribute('readonly'));
  assert.equal(app.ids.projectShareStatus.getAttribute('role'), 'status');
  assert.equal(state(app), 'loading');
  assert.equal(app.ids.projectGrid.children.length, 0);
  assert.equal(app.ids.projectCount.textContent.trim(), '');
  assert.equal(app.ids.projectTools.hidden, true);
  categoryDefault(app, 'actual initial HTML while fetch is pending');
  assert.equal(app.calls[0].url, 'assets/projects.json');
  assert.equal(app.calls[0].options.cache, 'no-cache');
  assert.ok(app.calls[0].options.signal instanceof AbortSignal, 'fetch must receive a real abort signal');
  assert.equal(app.calls[0].options.signal.aborted, false);
  app.pending[0].reject(new Error('test cleanup'));
  await app.flush();
});

const failures = [
  ['network rejection', { error: 'offline' }],
  ['HTTP failure', { status: 503, data: valid() }],
  ['JSON parse failure', { jsonError: true }],
  ['unknown schema', { data: { schemaVersion: 2, replaceExisting: true, projects: [] } }],
  ['missing project list', { data: { schemaVersion: 1, replaceExisting: true } }],
  ['null document', { data: null }],
  ['malformed record among valid records', { data: payload([project('valid'), { id: 'missing-cover', title: '잘못된 항목' }]) }],
  ['duplicate project IDs', { data: payload([project('duplicate'), project('duplicate', { title: '다른 행사' })]) }],
  ['external cover URL', { data: payload([project('safe'), project('unsafe', { cover: { src: 'https://example.test/remote.jpg', alt: '경로만 잘못된 사진' } })]) }],
  ['traversal gallery URL', { data: payload([project('safe'), project('unsafe', { gallery: [{ src: 'assets/projects/../private.jpg', alt: '경로만 잘못된 사진' }] })]) }],
  ['invalid month', { data: payload([{ id: 'invalid-month', title: '잘못된 월', year: 2024, month: 13, category: '공연', cover: photo('invalid-month') }]) }],
];
for (const [name, failure] of failures) test(`${name}: atomic error state and successful user retry`, async () => {
  const app = await start([failure, { data: valid() }]);
  assert.equal(state(app), 'error'); noResultLeak(app);
  assert.ok(app.ids.projectLoadMessage.textContent.trim(), 'error must explain the unavailable data');
  await app.click('projectRetry');
  assert.equal(app.calls.length, 2, 'retry click must make a fresh request');
  assert.equal(state(app), 'ready');
  assert.equal(cards(app).length, 3);
  assert.equal(app.ids.projectTools.hidden, false);
  assert.equal(app.ids.projectEmpty.hidden, true);
  assert.match(app.ids.projectCount.textContent, /3건.*4장/);
});

test('empty successful list has its own state and can be retried', async () => {
  const app = await start([{ data: payload([]) }, { data: valid() }]);
  assert.equal(state(app), 'empty'); noResultLeak(app);
  assert.ok(app.ids.projectLoadMessage.textContent.trim());
  await app.click('projectRetry');
  assert.equal(state(app), 'ready');
  assert.equal(cards(app).length, 3);
});

test('consecutive failed retries remain usable until a later recovery', async () => {
  const app = await start([{ error: 'offline' }, { jsonError: true }, { data: valid() }]);
  assert.equal(state(app), 'error'); noResultLeak(app);
  await app.click('projectRetry');
  assert.equal(state(app), 'error'); noResultLeak(app);
  assert.equal(app.calls.length, 2);
  await app.click('projectRetry');
  assert.equal(state(app), 'ready');
  assert.equal(app.calls.length, 3);
  assert.equal(cards(app).length, 3);
});

test('refresh failure clears previously successful cards/counts and restores URL filters after recovery', async () => {
  const app = await start([{ data: valid() }, { pending: true }, { data: valid() }]);
  categoryDefault(app, 'successful initial response');
  await app.change('projectYear', '2024');
  assert.deepEqual(visibleTitles(app), ['ACC 야외 공연']);
  await app.click('projectRetry');
  assert.equal(state(app), 'loading');
  assert.equal(app.ids.projectGrid.children.length, 0);
  assert.equal(app.ids.projectCount.textContent.trim(), '');
  assert.equal(app.ids.projectTools.hidden, true);
  assert.equal(app.ids.projectEmpty.hidden, true);
  app.pending[0].reject(new Error('connection lost after a prior success'));
  await app.flush();
  assert.equal(state(app), 'error'); noResultLeak(app);
  await app.click('projectRetry');
  assert.equal(state(app), 'ready');
  assert.equal(cards(app).length, 3, 'recovery must not duplicate cards');
  categoryDefault(app, 'successful retry response');
  assert.equal(app.ids.projectYear.value, '2024');
  assert.deepEqual(visibleTitles(app), ['ACC 야외 공연']);
  assert.equal(new Set(app.ids.projectYear.options.map(option => option.value)).size, app.ids.projectYear.options.length, 'retry must not duplicate filter options');
});

test('timeout actually aborts fetch; retry recovers without stale cards', async () => {
  const app = await start([{ pending: true }, { data: valid() }]);
  assert.equal(state(app), 'loading');
  app.clock.advance(120000); await app.flush();
  assert.equal(app.calls[0].options.signal.aborted, true, 'timeout must abort rather than only change a label');
  assert.equal(state(app), 'error'); noResultLeak(app);
  await app.click('projectRetry');
  assert.equal(state(app), 'ready');
  assert.equal(cards(app).length, 3);
  assert.equal(app.calls.length, 2);
});

test('timeout also covers a stalled JSON response body after headers', async () => {
  const app = await start([{ jsonPending: true, data: valid() }, { data: valid() }]);
  assert.equal(app.calls[0].jsonRequested, true);
  assert.equal(state(app), 'loading');
  app.clock.advance(120000); await app.flush();
  assert.equal(app.calls[0].options.signal.aborted, true);
  assert.equal(state(app), 'error'); noResultLeak(app);
  await app.click('projectRetry');
  assert.equal(state(app), 'ready');
  assert.equal(cards(app).length, 3);
});

test('NFKC case folding and AND search spans title/location/role', async () => {
  const app = await loaded();
  await app.input('projectSearch', 'acc 광주 음향');
  assert.deepEqual(visibleTitles(app), ['ＡＣＣ 무대 ＆ 영상', 'ACC 야외 공연']);
  await app.input('projectSearch', 'Ａｃｃ 무대 조명');
  assert.deepEqual(visibleTitles(app), ['ＡＣＣ 무대 ＆ 영상']);
  assert.match(app.ids.projectCount.textContent, /1건.*2장/);
  await app.input('projectSearch', '여수 음향');
  assert.equal(visible(app).length, 0, 'OR matching would incorrectly include beta');
  assert.equal(app.ids.projectEmpty.hidden, false);
  assert.equal(state(app), 'ready', 'zero search results are not a data loading error');
  assert.equal(app.ids.projectTools.hidden, false);
  await app.click('projectFilterReset');
  assert.equal(app.ids.projectSearch.value, '');
  assert.equal(app.ids.projectYear.value, 'all');
  assert.equal(app.ids.projectCategory.value, 'all');
  categoryDefault(app, 'reset after search and category filtering');
  assert.equal(visible(app).length, 3);
  assert.equal(app.ids.projectEmpty.hidden, true);
});

test('URL query round trips reserved characters and preserves unrelated parameters', async () => {
  const app = await loaded();
  const input = '<img src=x onerror=alert(1)> & + # / " 한글';
  await app.input('projectSearch', input);
  assert.equal(app.location.searchParams.get('p_q'), input);
  assert.equal(app.location.searchParams.get('v'), 'keep');
  assert.equal(app.location.hash, '#projects');
  assert.equal(app.historyCalls.at(-1).method, 'replace');
  const category = '포럼·회의 & 공개+행사';
  await app.change('projectCategory', category);
  assert.equal(app.location.searchParams.get('p_category'), category);
  assert.equal(app.historyCalls.at(-1).method, 'push');
  assert.equal(app.document.querySelectorAll('[onerror]').length, 0);
  assert.ok(!app.document.innerHtmlWrites.some(value => value.includes(input)), 'search must not become raw HTML');
});

test('initial URL filters apply after asynchronous data arrives', async () => {
  const params = new URLSearchParams({ v: 'preserve', p_q: 'ACC', p_year: '2024', p_category: '공연' });
  const app = await loaded({ url: `https://example.test/fineinc-website/?${params}#projects` });
  assert.equal(app.ids.projectSearch.value, 'ACC');
  assert.equal(app.ids.projectYear.value, '2024');
  assert.equal(app.ids.projectCategory.value, '공연');
  assert.deepEqual(visibleTitles(app), ['ACC 야외 공연']);
  assert.equal(app.location.searchParams.get('v'), 'preserve');
});

test('push/replace history supports back/forward and reset restoration', async () => {
  const app = await loaded();
  await app.input('projectSearch', '광주');
  const afterTyping = app.history.length;
  await app.input('projectSearch', '광주 음향');
  assert.equal(app.history.length, afterTyping, 'typing replaces current entry');
  await app.change('projectYear', '2024');
  assert.equal(app.history.length, afterTyping + 1);
  assert.deepEqual(visibleTitles(app), ['ACC 야외 공연']);
  app.history.back(); await app.flush();
  assert.equal(app.ids.projectYear.value, 'all');
  assert.equal(app.ids.projectSearch.value, '광주 음향');
  assert.equal(visible(app).length, 2);
  app.history.forward(); await app.flush();
  assert.equal(app.ids.projectYear.value, '2024');
  assert.equal(visible(app).length, 1);
  await app.click('projectFilterReset');
  assert.equal(visible(app).length, 3);
  assert.equal(app.location.searchParams.has('p_q'), false);
  assert.equal(app.location.searchParams.has('p_year'), false);
  assert.equal(app.location.searchParams.get('v'), 'keep');
  assert.equal(app.historyCalls.at(-1).method, 'push');
  app.history.back(); await app.flush();
  assert.equal(app.ids.projectYear.value, '2024');
  assert.equal(app.ids.projectSearch.value, '광주 음향');
  assert.equal(visible(app).length, 1);
});

for (const mode of ['success', 'reject', 'missing']) test(`share current filters: clipboard ${mode}`, async () => {
  const app = await loaded({ clipboard: mode, url: 'https://example.test/fineinc-website/?v=keep&email=fixture%40example.test&private_token=fixture-secret&utm_campaign=unrelated' });
  await app.input('projectSearch', 'ACC & 영상');
  await app.change('projectYear', '2026');
  await app.change('projectCategory', '포럼·회의 & 공개+행사');
  assert.equal(app.location.searchParams.get('v'), 'keep');
  assert.equal(app.location.searchParams.get('email'), 'fixture@example.test', 'history must preserve unrelated parameters');
  assert.equal(app.location.searchParams.get('private_token'), 'fixture-secret', 'history is distinct from sanitized sharing');
  assert.equal(app.location.searchParams.get('utm_campaign'), 'unrelated');
  await app.click('projectFilterShare');
  assert.ok(app.ids.projectShareStatus.textContent.trim());
  const sharedValue = mode === 'success' ? app.writes[0] : app.ids.projectShareUrl.value;
  const shared = new URL(sharedValue);
  assert.deepEqual([...shared.searchParams.keys()].sort(), ['p_category', 'p_q', 'p_year', 'v']);
  assert.equal(shared.searchParams.get('v'), 'keep');
  assert.equal(shared.searchParams.get('p_q'), 'ACC & 영상');
  assert.equal(shared.searchParams.get('p_year'), '2026');
  assert.equal(shared.searchParams.get('p_category'), '포럼·회의 & 공개+행사');
  assert.equal(shared.searchParams.has('email'), false);
  assert.equal(shared.searchParams.has('private_token'), false);
  assert.equal(shared.searchParams.has('utm_campaign'), false);
  assert.equal(shared.hash, '#projects');
  assert.equal(shared.origin, app.location.origin);
  assert.equal(shared.pathname, app.location.pathname);
  if (mode !== 'success') {
    assert.equal(app.ids.projectShareUrl.hidden, false);
    assert.equal(effectivelyVisible(app.ids.projectShareUrl), true);
  }
  assert.equal(app.location.searchParams.get('private_token'), 'fixture-secret', 'sharing must not mutate current browser history');
  assert.equal(app.calls.length, 1, 'sharing must not send the link to an external service');
});

test('untrusted project text remains text through cards and gallery controls', async () => {
  const unsafe = '<img src=x onerror=alert(1)>';
  const app = await start([{ data: payload([project('untrusted', { title: unsafe, location: '<script>alert(2)</script>', role: unsafe, gallery: [photo('untrusted'), photo('second')] })]) }]);
  const opener = app.ids.projectGrid.querySelector('.project-photo-open');
  const title = app.ids.projectGrid.querySelector('.project-title-button');
  assert.equal(title.textContent, unsafe); assert.equal(title.children.length, 0);
  assert.equal(app.document.querySelectorAll('[onerror]').length, 0);
  opener.click();
  assert.equal(app.ids.projectDialog.open, true);
  assert.equal(app.ids.projectDialogTitle.textContent, unsafe);
  assert.equal(app.ids.projectDialogTitle.children.length, 0);
  assert.equal(app.document.querySelectorAll('[onerror]').length, 0, 'gallery metadata must remain text');
  assert.ok(!app.document.innerHtmlWrites.some(value => value.includes(unsafe) || value.includes('<script>alert(2)</script>')));
  assert.equal(app.ids.projectImageNumber.textContent, '1 / 2');
  app.ids.projectImageNext.click(); assert.equal(app.ids.projectImageNumber.textContent, '2 / 2');
  const event = app.ids.projectDialog.emit('keydown', { key: 'ArrowLeft' });
  assert.equal(event.defaultPrevented, true);
  assert.equal(app.ids.projectImageNumber.textContent, '1 / 2');
  app.ids.projectImagePrev.click(); assert.equal(app.ids.projectImageNumber.textContent, '2 / 2');
  app.ids.projectThumbnails.children[0].click();
  assert.equal(app.ids.projectImageNumber.textContent, '1 / 2');
  assert.equal(app.ids.projectThumbnails.children[0].getAttribute('aria-pressed'), 'true');
  app.ids.projectDialogClose.click();
  assert.equal(app.ids.projectDialog.open, false);
  assert.equal(app.document.body.classList.contains('project-dialog-open'), false);
  assert.equal(app.document.activeElement, opener);
});

test('year/month precision is retained without inventing exact days', async () => {
  const app = await loaded();
  const list = cards(app);
  list[1].querySelector('.project-photo-open').click();
  assert.ok(app.ids.projectDialogMeta.textContent.startsWith('2025'));
  assert.ok(!app.ids.projectDialogMeta.textContent.startsWith('2025.01'));
  app.ids.projectDialogClose.click();
  list[2].querySelector('.project-photo-open').click();
  assert.ok(app.ids.projectDialogMeta.textContent.startsWith('2024.07'));
  assert.ok(!app.ids.projectDialogMeta.textContent.startsWith('2024.07.01'));
});

test('real production JSON retains all 47 projects, 122 photos and date precision', async () => {
  const data = JSON.parse(fs.readFileSync(path.join(root, 'assets/projects.json'), 'utf8'));
  assert.equal(data.projects.length, 47);
  assert.equal(data.projects.filter(project => project.startDate).length, 42);
  assert.equal(data.projects.filter(project => !project.startDate && project.month).length, 2);
  assert.equal(data.projects.filter(project => !project.startDate && !project.month).length, 3);
  const app = await start([{ data }]);
  assert.equal(state(app), 'ready'); assert.equal(cards(app).length, 47);
  assert.match(app.ids.projectCount.textContent, /47건.*122장/);
  await app.change('projectYear', '2025');
  assert.equal(visible(app).length, 14);
});

(async () => {
  for (const { name, fn } of tests) {
    try { await fn(); checks.push({ name, passed: true }); console.log(`PASS ${name}`); }
    catch (error) { checks.push({ name, passed: false, error: error.stack }); console.error(`FAIL ${name}\n${error.stack}`); }
  }
  const report = { passed: checks.every(row => row.passed), total: checks.length, passedCount: checks.filter(row => row.passed).length, failedCount: checks.filter(row => !row.passed).length, usesBrowser: false, usesNetwork: false, productionDataMutated: false, sourceSha256: require('node:crypto').createHash('sha256').update(fs.readFileSync(sourcePath)).digest('hex'), limitations: ['DOM simulation does not prove layout, rendering, native dialog focus trapping, or mobile browser clipboard permissions.'], checks };
  fs.mkdirSync(artifact, { recursive: true });
  fs.writeFileSync(path.join(artifact, 'results.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(`${report.passedCount}/${report.total} checks passed; ${path.join(artifact, 'results.json')}`);
  if (!report.passed) process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; });
