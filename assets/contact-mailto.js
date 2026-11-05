/* Preparation candidate: user-controlled mail app draft, no form submission service. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else {
    root.FineContactMailto = api;
    api.mount(root.document, {
      navigate: (uri) => root.location.assign(uri),
      writeText: root.navigator?.clipboard?.writeText
        ? (text) => root.navigator.clipboard.writeText(text)
        : null
    });
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const RECIPIENT = 'fine2211@naver.com';
  const MAX_MAILTO_LENGTH = 1800; // Conservative application threshold, not an OS guarantee.
  const LIMITS = { company: 100, name: 80, phone: 80, email: 254, type: 120, message: 5000 };
  function clean(value, key) {
    const text = String(value ?? '').replace(/\r\n?/g, '\n').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, '').trim();
    if (text.length > LIMITS[key]) throw new Error('입력 내용의 길이를 확인해 주세요.');
    return text;
  }
  function buildDraft(values = {}) {
    const v = Object.fromEntries(Object.keys(LIMITS).map((key) => [key, clean(values[key], key)]));
    if (!v.message) throw new Error('프로젝트 내용을 입력해 주세요.');
    const oneLine = (s) => s.replace(/[\r\n]+/g, ' ');
    const subject = '[FINE INC 문의] ' + oneLine(v.type || '프로젝트') + ' / ' + oneLine(v.company || v.name || '문의');
    const body = [
      '회사 / 기관명: ' + (v.company || '미입력'),
      '담당자: ' + (v.name || '미입력'),
      '연락처: ' + (v.phone || '미입력'),
      '이메일: ' + (v.email || '미입력'),
      '프로젝트 유형: ' + (v.type || '미입력'),
      '', '프로젝트 내용', v.message
    ].join('\n');
    const mailto = 'mailto:' + RECIPIENT + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
    const copyText = '받는사람: ' + RECIPIENT + '\n제목: ' + subject + '\n\n' + body;
    return { recipient: RECIPIENT, subject, body, mailto, copyText, useManualCopy: mailto.length > MAX_MAILTO_LENGTH };
  }
  function requestDraft(values, navigate) {
    const draft = buildDraft(values);
    if (draft.useManualCopy) return {
      state: 'manual_copy_needed', draft,
      message: '문의 내용이 길어 메일 초안을 자동으로 열지 않았습니다. 문의 내용을 복사한 뒤 메일 앱에 붙여 넣어 주세요.'
    };
    try {
      navigate(draft.mailto);
      return { state: 'draft_requested', draft, message: '메일 앱 열기를 요청했습니다. 메일 앱에서 내용을 확인한 뒤 직접 전송해 주세요.' };
    } catch {
      return { state: 'manual_copy_needed', draft, message: '메일 앱을 열지 못했습니다. 문의 내용을 복사해 메일 앱에 붙여 넣어 주세요.' };
    }
  }
  async function copyDraft(values, writeText, showManualCopy) {
    const draft = buildDraft(values);
    if (typeof writeText === 'function') {
      try {
        await writeText(draft.copyText);
        return { state: 'copied', draft, message: '문의 내용을 복사했습니다. 메일 앱에 붙여 넣고 직접 전송해 주세요.' };
      } catch { /* Permission or clipboard availability: show selectable text below. */ }
    }
    showManualCopy(draft.copyText);
    return { state: 'select_and_copy', draft, message: '아래 내용을 선택해 복사한 뒤 메일 앱에 붙여 넣어 주세요.' };
  }
  function mount(doc, dependencies = {}) {
    const form = doc?.getElementById('projectForm');
    const status = doc?.getElementById('formStatus');
    if (!form || !status || form.dataset.mailtoMounted === 'true') return null;
    form.dataset.mailtoMounted = 'true';
    const readValues = dependencies.readValues || (() => Object.fromEntries(new FormData(form)));
    const copyButton = doc.createElement('button');
    copyButton.type = 'button';
    copyButton.className = 'btn contact-copy-button';
    copyButton.textContent = '문의 내용 복사';
    const blankMail = doc.createElement('a');
    blankMail.href = 'mailto:' + RECIPIENT;
    blankMail.className = 'btn contact-open-mail';
    blankMail.textContent = '메일 앱 열기';
    const copyArea = doc.createElement('textarea');
    copyArea.readOnly = true;
    copyArea.rows = 10;
    copyArea.hidden = true;
    copyArea.className = 'contact-manual-copy';
    copyArea.setAttribute('aria-label', '복사할 문의 내용');
    status.before(copyButton, blankMail, copyArea);
    function showManualCopy(text) {
      copyArea.value = text;
      copyArea.hidden = false;
      copyArea.focus();
      copyArea.select();
    }
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      copyArea.hidden = true;
      try {
        const result = requestDraft(readValues(), dependencies.navigate);
        status.textContent = result.message;
        if (result.state === 'manual_copy_needed') showManualCopy(result.draft.copyText);
      } catch (error) { status.textContent = error.message; }
    });
    copyButton.addEventListener('click', async () => {
      copyButton.disabled = true;
      try {
        const result = await copyDraft(readValues(), dependencies.writeText, showManualCopy);
        status.textContent = result.message;
      } catch (error) { status.textContent = error.message; }
      finally { copyButton.disabled = false; }
    });
    return { copyButton, blankMail, copyArea };
  }
  return { RECIPIENT, MAX_MAILTO_LENGTH, buildDraft, requestDraft, copyDraft, mount };
});
