(() => {
  'use strict';

  const grid = document.getElementById('projectGrid');
  const tools = document.getElementById('projectTools');
  const count = document.getElementById('projectCount');
  const yearFilter = document.getElementById('projectYear');
  const categoryFilter = document.getElementById('projectCategory');
  const empty = document.getElementById('projectEmpty');
  const dialog = document.getElementById('projectDialog');
  if (!grid || !tools || !dialog) return;

  const image = document.getElementById('projectDialogImage');
  const thumbnails = document.getElementById('projectThumbnails');
  const previous = document.getElementById('projectImagePrev');
  const next = document.getElementById('projectImageNext');
  let projects = [];
  let activeProject = null;
  let activePhoto = 0;
  let lastOpener = null;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function localImagePath(path) {
    return typeof path === 'string' && /^assets\/projects\/[a-zA-Z0-9_./-]+\.(?:jpe?g|png|webp)$/i.test(path) && !path.includes('..');
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

  function validProject(project) {
    return project && typeof project.id === 'string' && project.id.length > 0 &&
      typeof project.title === 'string' && project.title.length > 0 &&
      (/^\d{4}-\d{2}-\d{2}$/.test(project.startDate || '') ||
        (/^\d{4}$/.test(String(project.year || '')) && !project.endDate &&
          (!project.month || (Number.isInteger(project.month) && project.month >= 1 && project.month <= 12)))) &&
      (!project.endDate || /^\d{4}-\d{2}-\d{2}$/.test(project.endDate)) &&
      typeof project.category === 'string' && project.category.length > 0 &&
      project.cover && localImagePath(project.cover.src);
  }

  function projectPhotos(project) {
    const photos = [project.cover, ...(Array.isArray(project.gallery) ? project.gallery : [])];
    const seen = new Set();
    return photos.filter(photo => photo && localImagePath(photo.src) && !seen.has(photo.src) && seen.add(photo.src));
  }

  function showPhoto(index) {
    if (!activeProject) return;
    const photos = projectPhotos(activeProject);
    activePhoto = (index + photos.length) % photos.length;
    const photo = photos[activePhoto];
    image.src = photo.src;
    image.alt = photo.alt || `${activeProject.title} 현장 사진 ${activePhoto + 1}`;
    document.getElementById('projectImageCaption').textContent = image.alt;
    document.getElementById('projectImageDescription').textContent = image.alt;
    document.getElementById('projectImageNumber').textContent = `${activePhoto + 1} / ${photos.length}`;
    [...thumbnails.children].forEach((button, position) => button.setAttribute('aria-pressed', String(position === activePhoto)));
    previous.hidden = photos.length <= 1;
    next.hidden = photos.length <= 1;
  }

  function openProject(project, opener) {
    activeProject = project;
    lastOpener = opener;
    document.getElementById('projectDialogTitle').textContent = project.title;
    document.getElementById('projectDialogCategory').textContent = project.category;
    document.getElementById('projectDialogMeta').textContent = [dateText(project), project.location, project.role].filter(Boolean).join(' · ');
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
    cover.alt = project.cover.alt || `${project.title} 현장`;
    cover.loading = 'lazy';
    cover.decoding = 'async';
    if (/^\d+(?:\.\d+)?% \d+(?:\.\d+)?%$/.test(project.cover.position || '')) cover.style.objectPosition = project.cover.position;
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

  function filterProjects() {
    let visible = 0;
    let photos = 0;
    grid.querySelectorAll('.project-photo-card').forEach((card, index) => {
      const show = (yearFilter.value === 'all' || card.dataset.year === yearFilter.value) &&
        (categoryFilter.value === 'all' || card.dataset.category === categoryFilter.value);
      card.hidden = !show;
      if (show) { visible += 1; photos += projectPhotos(projects[index]).length; }
    });
    count.textContent = `수행 프로젝트 ${visible}건 · 현장 사진 ${photos}장`;
    empty.hidden = visible !== 0;
  }

  function addOptions(select, values) {
    values.forEach(value => {
      const option = element('option', '', value);
      option.value = value;
      select.append(option);
    });
  }

  document.getElementById('projectDialogClose').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) { const bounds = dialog.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close(); } });
  dialog.addEventListener('close', () => { document.body.classList.remove('project-dialog-open'); lastOpener?.focus(); });
  dialog.addEventListener('keydown', event => { if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); showPhoto(activePhoto + (event.key === 'ArrowLeft' ? -1 : 1)); } });
  previous.addEventListener('click', () => showPhoto(activePhoto - 1));
  next.addEventListener('click', () => showPhoto(activePhoto + 1));
  yearFilter.addEventListener('change', filterProjects);
  categoryFilter.addEventListener('change', filterProjects);

  fetch('assets/projects.json', { cache: 'no-cache' })
    .then(response => { if (!response.ok) throw new Error('Project data unavailable'); return response.json(); })
    .then(data => {
      if (data.schemaVersion !== 1 || !Array.isArray(data.projects)) return;
      projects = data.projects.filter(validProject).sort((a, b) => dateSortKey(b).localeCompare(dateSortKey(a)));
      if (!projects.length) return;
      if (data.replaceExisting === true) grid.replaceChildren();
      const cards = document.createDocumentFragment();
      projects.forEach(project => cards.append(makeCard(project)));
      grid.prepend(cards);
      addOptions(yearFilter, [...new Set(projects.map(projectYear))].sort().reverse());
      addOptions(categoryFilter, [...new Set(projects.map(project => project.category))].sort((a, b) => a.localeCompare(b, 'ko')));
      tools.hidden = false;
      if (data.replaceExisting === true) document.getElementById('projectNote').hidden = true;
      filterProjects();
    })
    .catch(() => { /* Keep the existing portfolio visible if data cannot be loaded. */ });
})();
