const menu = document.querySelector('.menu');
const nav = document.querySelector('#navigation');
function setMenu(open) {
  menu.setAttribute('aria-expanded', String(open));
  nav.classList.toggle('open', open);
  menu.querySelector('span').textContent = open ? '−' : '＋';
}
menu.addEventListener('click', () => setMenu(menu.getAttribute('aria-expanded') !== 'true'));
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && nav.classList.contains('open')) {
    setMenu(false);
    menu.focus();
  }
});
nav.querySelectorAll('a').forEach(link => {
  if (link.getAttribute('href') === location.pathname) link.setAttribute('aria-current', 'page');
  link.addEventListener('click', () => setMenu(false));
});
const desktop = matchMedia('(min-width: 1041px)');
desktop.addEventListener('change', event => { if (event.matches) setMenu(false); });

const focusContent = {
  skills: ['01', 'Make the next rep matter.', 'Work on your basketball skills with coaching that challenges you to learn, practice, and improve.'],
  athletic: ['02', 'Build the athlete behind the game.', 'Combine basketball skill work with strength and speed training to support your development as an athlete.'],
  mindset: ['03', 'Grow beyond the court.', 'Learn to respond to challenges, stay focused, and support your teammates. Mental toughness and character are part of the work.']
};
const tabs = [...document.querySelectorAll('[data-focus]')];
function activateTab(tab) {
  tabs.forEach(item => {
    item.setAttribute('aria-selected', String(item === tab));
    item.tabIndex = item === tab ? 0 : -1;
  });
  const [number, title, copy] = focusContent[tab.dataset.focus];
  const panel = document.querySelector('#focus-panel');
  panel.setAttribute('aria-labelledby', tab.id);
  panel.querySelector('.focus-number').textContent = number;
  panel.querySelector('h3').textContent = title;
  panel.querySelector('p').textContent = copy;
}
tabs.forEach((tab, index) => {
  tab.tabIndex = index === 0 ? 0 : -1;
  tab.addEventListener('click', () => activateTab(tab));
  tab.addEventListener('keydown', event => {
    let next;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    if (next !== undefined) {
      event.preventDefault();
      activateTab(tabs[next]);
      tabs[next].focus();
    }
  });
});

const form = document.querySelector('#inquiry');
if (form) {
  const interest = new URLSearchParams(location.search).get('interest');
  if ([...form.elements.interest.options].some(option => option.value === interest)) {
    form.elements.interest.value = interest;
  }
  form.addEventListener('submit', event => {
    event.preventDefault();
    const data = new FormData(form);
    const value = key => String(data.get(key) || '').trim();
    const athleteDetails = [
      value('athlete') ? `Athlete: ${value('athlete')}` : '',
      value('age') ? `Age: ${value('age')}` : ''
    ].filter(Boolean).join('\n');
    const body = [
      'Hi Coach Will,',
      `I’m interested in ${value('interest')}.`,
      `Name: ${value('name')}\nReply email: ${value('email')}`,
      athleteDetails,
      value('message'),
      `Thanks,\n${value('name')}`
    ].filter(Boolean).join('\n\n');
    document.querySelector('#email-body').textContent = body;
    document.querySelector('#email-link').href = `mailto:p2vacademy@gmail.com?subject=${encodeURIComponent('P2V inquiry: ' + value('interest'))}&body=${encodeURIComponent(body)}`;
    const preview = document.querySelector('#email-preview');
    preview.hidden = false;
    preview.focus({ preventScroll: true });
    preview.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'nearest' });
    document.querySelector('#copy-status').textContent = '';
  });
  form.addEventListener('input', () => { document.querySelector('#email-preview').hidden = true; });
  document.querySelector('#copy-email').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(document.querySelector('#email-body').textContent);
      document.querySelector('#copy-status').textContent = 'Message copied.';
    } catch {
      document.querySelector('#copy-status').textContent = 'Select the message above to copy it manually.';
    }
  });
}
