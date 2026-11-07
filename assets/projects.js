(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  const grid = byId('projectGrid');
  const tools = byId('projectTools');
  const count = byId('projectCount');
  const yearFilter = byId('projectYear');
  const categoryFilter = byId('projectCategory');
  const search = byId('projectSearch');
  const empty = byId('projectEmpty');
  const loadState = byId('projectLoadState');
  const loadMessage = byId('projectLoadMessage');
  const retry = byId('projectRetry');
  const publicLink = byId('projectPublicLink');
  const shareStatus = byId('projectShareStatus');
  const shareUrl = byId('projectShareUrl');
  const dialog = byId('projectDialog');
  if (![grid, tools, count, yearFilter, categoryFilter, search, empty, loadState,
    loadMessage, retry, publicLink, shareStatus, shareUrl, dialog].every(Boolean)) return;

  const image = byId('projectDialogImage');
  const thumbnails = byId('projectThumbnails');
  const previous = byId('projectImagePrev');
  const next = byId('projectImageNext');
  const filterKeys = { query: 'p_q', year: 'p_year', category: 'p_category' };
  let projects = [];
  let activeProject = null;
  let activePhoto = 0;
  let lastOpener = null;
  let controller = null;
  let generation = 0;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function localImagePath(path) {
    return typeof path === 'string' &&
      /^assets\/projects\/[a-zA-Z0-9_./-]+\.(?:jpe?g|png|webp)$/i.test(path) &&
      path.split('/').every(part => part && part !== '.' && part !== '..');
  }

  function nonempty(value, limit) {
    return typeof value === 'string' && value.trim().length > 0 && value.length <= limit;
  }

  function validDate(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const parsed = new Date(value + 'T00:00:00Z');
    return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
  }

  function validPhoto(photo) {
    return photo && localImagePath(photo.src) && nonempty(photo.alt, 400) &&
      (photo.position === undefined || /^\d+(?:\.\d+)?% \d+(?:\.\d+)?%$/.test(photo.position));
  }

  function validProject(project) {
    if (!project || typeof project.id !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}$/.test(project.id) ||
      !nonempty(project.title, 300) || !nonempty(project.category, 100) || !validPhoto(project.cover)) return false;
    if (project.role !== undefined && (typeof project.role !== 'string' || project.role.length > 1000)) return false;
    if (project.location !== undefined && (typeof project.location !== 'string' || project.location.length > 500)) return false;
    if (project.gallery !== undefined && (!Array.isArray(project.gallery) || !project.gallery.every(validPhoto))) return false;
    if (project.startDate !== undefined) {
      if (!validDate(project.startDate)) return false;
      if (project.endDate !== undefined && (!validDate(project.endDate) || project.endDate < project.startDate)) return false;
    } else if (!Number.isInteger(project.year) || project.year < 1000 || project.year > 9999 ||
      project.endDate !== undefined ||
      (project.month !== undefined && (!Number.isInteger(project.month) || project.month < 1 || project.month > 12))) return false;
    return true;
  }

  function validateData(data) {
    if (!data || data.schemaVersion !== 1 || data.replaceExisting !== true || !Array.isArray(data.projects)) throw new Error('invalid-data');
    const ids = new Set();
    data.projects.forEach(project => {
      if (!validProject(project) || ids.has(project.id)) throw new Error('invalid-data');
      ids.add(project.id);
    });
    return data.projects;
  }

  function projectYear(project) {
    return project.startDate ? project.startDate.slice(0, 4) : String(project.year);
  }
  function dateSortKey(project) {
    return project.startDate || `${projectYear(project)}-${String(project.month || 0).padStart(2, '0')}-00`;
  }
  function dateText(project) {
    if (!project.startDate) return project.month ? `${projectYear(project)}.${String(project.month).padStart(2, '0')}` : projectYear(project);
    const start = project.startDate.replaceAll('-', '.');
    return project.endDate && project.endDate !== project.startDate ? `${start} – ${project.endDate.replaceAll('-', '.')}` : start;
  }
  function projectPhotos(project) {
    const seen = new Set();
    return [project.cover, ...(project.gallery || [])].filter(photo => !seen.has(photo.src) && seen.add(photo.src));
  }

  function showPhoto(index) {
    if (!activeProject) return;
    const photos = projectPhotos(activeProject);
    activePhoto = (index + photos.length) % photos.length;
    const photo = photos[activePhoto];
    image.src = photo.src;
    image.alt = photo.alt;
    byId('projectImageCaption').textContent = photo.alt;
    byId('projectImageDescription').textContent = photo.alt;
    byId('projectImageNumber').textContent = `${activePhoto + 1} / ${photos.length}`;
    [...thumbnails.children].forEach((button, position) => button.setAttribute('aria-pressed', String(position === activePhoto)));
    previous.hidden = photos.length <= 1;
    next.hidden = photos.length <= 1;
  }

  function openProject(project, opener) {
    activeProject = project;
    lastOpener = opener;
    byId('projectDialogTitle').textContent = project.title;
    byId('projectDialogCategory').textContent = project.category;
    byId('projectDialogMeta').textContent = [dateText(project), project.location, project.role].filter(Boolean).join(' · ');
    thumbnails.replaceChildren();
    projectPhotos(project).forEach((photo, position) => {
      const button = element('button');
      button.type = 'button';
      button.setAttribute('aria-label', `${position + 1}번째 사진 보기`);
      button.setAttribute('aria-pressed', 'false');
      const thumbnail = element('img');
      thumbnail.src = photo.src;
      thumbnail.alt = '';
      thumbnail.loading = 'lazy';
      button.append(thumbnail);
      button.addEventListener('click', () => showPhoto(position));
      thumbnails.append(button);
    });
    showPhoto(0);
    dialog.showModal();
    document.body.classList.add('project-dialog-open');
  }

  function makeCard(project) {
    const card = element('article', 'project-card project-photo-card');
    card.dataset.year = projectYear(project);
    card.dataset.category = project.category;
    const visual = element('div', 'project-visual');
    const open = element('button', 'project-photo-open');
    open.type = 'button';
    open.setAttribute('aria-label', `${project.title} 현장 사진 보기`);
    const cover = element('img');
    cover.src = project.cover.src;
    cover.alt = project.cover.alt;
    cover.loading = 'lazy';
    cover.decoding = 'async';
    if (project.cover.position) cover.style.objectPosition = project.cover.position;
    open.append(cover, element('span', 'project-label', project.category), element('span', 'project-photo-cta', `사진 ${projectPhotos(project).length}장 보기 ↗`));
    open.addEventListener('click', () => openProject(project, open));
    visual.append(open);
    const info = element('div', 'project-info');
    const title = element('h3');
    const titleButton = element('button', 'project-title-button', project.title);
    titleButton.type = 'button';
    titleButton.addEventListener('click', () => openProject(project, titleButton));
    title.append(titleButton);
    info.append(element('span', '', projectYear(project)), title, element('p', 'project-date', [dateText(project), project.location].filter(Boolean).join(' · ')));
    if (project.role) info.append(element('p', 'project-role', project.role));
    card.append(visual, info);
    return card;
  }

  function normalize(value) {
    return String(value || '').normalize('NFKC').toLocaleLowerCase('ko-KR');
  }
  function filterProjects() {
    if (loadState.dataset.state !== 'ready') return;
    const words = normalize(search.value.trim()).split(/\s+/).filter(Boolean);
    let visible = 0;
    let photos = 0;
    grid.querySelectorAll('.project-photo-card').forEach((card, index) => {
      const project = projects[index];
      const haystack = normalize([project.title, project.location, project.role].filter(Boolean).join(' '));
      const show = (yearFilter.value === 'all' || card.dataset.year === yearFilter.value) &&
        (categoryFilter.value === 'all' || card.dataset.category === categoryFilter.value) &&
        words.every(word => haystack.includes(word));
      card.hidden = !show;
      if (show) { visible += 1; photos += projectPhotos(project).length; }
    });
    count.textContent = `수행 프로젝트 ${visible}건 · 현장 사진 ${photos}장`;
    empty.hidden = visible !== 0;
  }

  function readFilters() {
    const params = new URL(window.location.href).searchParams;
    const year = params.get(filterKeys.year) || 'all';
    return {
      query: (params.get(filterKeys.query) || '').slice(0, 160),
      year: /^\d{4}$/.test(year) ? year : 'all',
      category: (params.get(filterKeys.category) || 'all').slice(0, 100)
    };
  }
  function setOptions(select, values, label) {
    const all = element('option', '', label);
    all.value = 'all';
    select.replaceChildren(all);
    values.forEach(value => {
      const option = element('option', '', value);
      option.value = value;
      select.append(option);
    });
  }
  function selectRequested(select, value, label) {
    if (![...select.children].some(option => option.value === value)) {
      const option = element('option', '', `${label}: ${value}`);
      option.value = value;
      select.append(option);
    }
    select.value = value;
  }
  function restoreFilters() {
    const filters = readFilters();
    search.value = filters.query;
    selectRequested(yearFilter, filters.year, '요청한 연도');
    selectRequested(categoryFilter, filters.category, '요청한 분야');
    filterProjects();
  }
  function filtersUrl() {
    const url = new URL(window.location.href);
    const values = [[filterKeys.query, search.value.trim()], [filterKeys.year, yearFilter.value], [filterKeys.category, categoryFilter.value]];
    values.forEach(([key, value]) => {
      if (!value || value === 'all') url.searchParams.delete(key);
      else url.searchParams.set(key, value);
    });
    url.hash = 'projects';
    return url;
  }
  function sharingUrl() {
    const current = filtersUrl();
    const url = new URL(current.origin + current.pathname);
    ['v', ...Object.values(filterKeys)].forEach(key => {
      if (current.searchParams.has(key)) url.searchParams.set(key, current.searchParams.get(key));
    });
    url.hash = 'projects';
    return url;
  }
  function clearShare() {
    shareStatus.textContent = '';
    shareUrl.hidden = true;
    shareUrl.value = '';
  }
  function changeFilters(mode) {
    filterProjects();
    clearShare();
    const url = filtersUrl();
    if (url.href !== window.location.href) window.history[mode + 'State'](null, '', url.href);
  }

  search.addEventListener('input', () => changeFilters('replace'));
  yearFilter.addEventListener('change', () => changeFilters('push'));
  categoryFilter.addEventListener('change', () => changeFilters('push'));
  byId('projectFilterReset').addEventListener('click', () => {
    search.value = '';
    yearFilter.value = 'all';
    categoryFilter.value = 'all';
    changeFilters('push');
    search.focus();
  });
  window.addEventListener('popstate', () => { restoreFilters(); clearShare(); });
  byId('projectFilterShare').addEventListener('click', async () => {
    if (loadState.dataset.state !== 'ready') return;
    const url = sharingUrl().href;
    clearShare();
    try {
      if (!navigator.clipboard?.writeText) throw new Error('clipboard-unavailable');
      await navigator.clipboard.writeText(url);
      if (loadState.dataset.state === 'ready' && sharingUrl().href === url) shareStatus.textContent = '현재 검색·필터 링크를 복사했습니다.';
    } catch {
      if (loadState.dataset.state !== 'ready' || sharingUrl().href !== url) return;
      shareUrl.value = url;
      shareUrl.hidden = false;
      shareUrl.focus();
      shareUrl.select();
      shareStatus.textContent = '아래 주소를 선택했습니다. 복사해서 공유해 주세요.';
    }
  });

  byId('projectDialogClose').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target === dialog) {
      const bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    }
  });
  dialog.addEventListener('close', () => { document.body.classList.remove('project-dialog-open'); lastOpener?.focus(); });
  dialog.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      showPhoto(activePhoto + (event.key === 'ArrowLeft' ? -1 : 1));
    }
  });
  previous.addEventListener('click', () => showPhoto(activePhoto - 1));
  next.addEventListener('click', () => showPhoto(activePhoto + 1));

  const initialHash = window.location.hash;
  let userNavigated = false;
  const markNavigation = () => { userNavigated = true; };
  ['wheel', 'touchstart', 'pointerdown', 'keydown'].forEach(type =>
    window.addEventListener(type, markNavigation, { once: true, passive: true }));

  function showState(state, message) {
    loadState.dataset.state = state;
    loadMessage.textContent = message;
    grid.setAttribute('aria-busy', String(state === 'loading'));
    retry.disabled = state === 'loading';
    retry.textContent = state === 'loading' ? '불러오는 중…' : state === 'error' ? '다시 시도' : '목록 다시 확인';
  }
  async function loadProjects() {
    const request = ++generation;
    controller?.abort();
    controller = new AbortController();
    const activeController = controller;
    let timedOut = false;
    projects = [];
    grid.replaceChildren();
    tools.hidden = true;
    count.textContent = '';
    empty.hidden = true;
    byId('projectNote').hidden = true;
    publicLink.hidden = true;
    clearShare();
    showState('loading', '공개 실적 목록을 불러오고 있습니다.');
    const timeout = setTimeout(() => { timedOut = true; activeController.abort(); }, 12000);
    try {
      const response = await fetch('assets/projects.json', { cache: 'no-cache', signal: activeController.signal });
      if (!response.ok) throw new Error('network-response');
      const data = await response.json();
      if (request !== generation) return;
      projects = validateData(data).slice().sort((a, b) => dateSortKey(b).localeCompare(dateSortKey(a)));
      if (!projects.length) {
        showState('empty', '현재 공개된 실적이 없습니다. 새 실적이 공개되면 이곳에서 확인할 수 있습니다.');
        return;
      }
      const cards = document.createDocumentFragment();
      projects.forEach(project => cards.append(makeCard(project)));
      grid.replaceChildren(cards);
      setOptions(yearFilter, [...new Set(projects.map(projectYear))].sort().reverse(), '전체 연도');
      setOptions(categoryFilter, [...new Set(projects.map(project => project.category))].sort((a, b) => a.localeCompare(b, 'ko')), '전체 분야');
      const checked = new Intl.DateTimeFormat('ko-KR', {
        year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Seoul'
      }).format(new Date());
      showState('ready', `실적 목록 확인 완료 · ${checked} (한국시간)`);
      tools.hidden = false;
      byId('projectNote').hidden = false;
      restoreFilters();
      if (initialHash && !userNavigated && window.location.hash === initialHash) {
        byId(initialHash.slice(1))?.scrollIntoView({ behavior: 'instant', block: 'start' });
      }
    } catch {
      if (request !== generation) return;
      projects = [];
      grid.replaceChildren();
      count.textContent = '';
      tools.hidden = true;
      empty.hidden = true;
      const message = window.location.protocol === 'file:'
        ? '이 미리보기에서는 실적 목록을 불러올 수 없습니다. 공개 홈페이지에서 확인해 주세요.'
        : navigator.onLine === false
          ? '인터넷 연결이 끊겨 실적을 불러오지 못했습니다. 연결을 확인한 뒤 다시 시도해 주세요.'
          : timedOut
            ? '실적을 불러오는 시간이 길어지고 있습니다. 연결을 확인한 뒤 다시 시도해 주세요.'
            : '실적 목록을 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.';
      publicLink.hidden = window.location.protocol !== 'file:';
      showState('error', message);
    } finally {
      clearTimeout(timeout);
    }
  }
  retry.addEventListener('click', loadProjects);
  loadProjects();
})();
