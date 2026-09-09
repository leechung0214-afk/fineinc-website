const header = document.querySelector('.site-header');
const progress = document.querySelector('.scroll-progress span');
const menuBtn = document.querySelector('.menu-btn');
const mobileNav = document.querySelector('.mobile-nav');

function onScroll(){
  const y = window.scrollY;
  header.classList.toggle('scrolled', y > 20);
  const doc = document.documentElement;
  const max = doc.scrollHeight - doc.clientHeight;
  progress.style.width = `${max ? (y / max) * 100 : 0}%`;
}
window.addEventListener('scroll', onScroll, {passive:true});
onScroll();

menuBtn?.addEventListener('click', () => {
  const open = mobileNav.classList.toggle('open');
  menuBtn.setAttribute('aria-expanded', String(open));
  menuBtn.textContent = open ? 'CLOSE' : 'MENU';
});
mobileNav?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
  mobileNav.classList.remove('open');
  menuBtn.setAttribute('aria-expanded','false');
  menuBtn.textContent = 'MENU';
}));

const io = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if(entry.isIntersecting){
      entry.target.classList.add('is-visible');
      io.unobserve(entry.target);
    }
  });
}, {threshold:.12, rootMargin:'0px 0px -6% 0px'});
document.querySelectorAll('.reveal').forEach(el => io.observe(el));

const form = document.getElementById('projectForm');
const formStatus = document.getElementById('formStatus');
form?.addEventListener('submit', (e) => {
  e.preventDefault();
  formStatus.textContent = '문의 폼 디자인은 완료되었습니다. 실제 발송은 회사 이메일/서버 연결 후 활성화됩니다.';
});
