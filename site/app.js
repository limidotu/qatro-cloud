export function normalizeRepository(value) {
  const repo = String(value || '').trim();
  if (!/^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})\/[A-Za-z0-9_.-]{1,100}$/.test(repo)) return null;
  if (repo.split('/')[1] === '.' || repo.split('/')[1] === '..') return null;
  return repo;
}

export function workflowUrl(repository, action) {
  const repo = normalizeRepository(repository);
  if (!repo || !['start', 'stop', 'status'].includes(action)) return null;
  return `https://github.com/${repo}/actions/workflows/${action}.yml`;
}

if (typeof document !== 'undefined') {
  const $ = (selector) => document.querySelector(selector);
  let config = { repository: '', cloudReady: false };
  let savedRepository = '';
  try { savedRepository = localStorage.getItem('qatro.repository') || ''; } catch { /* Storage is optional. */ }

  function render() {
    const repo = normalizeRepository(savedRepository || config.repository);
    // A custom repository needs its own completed cloud setup.
    const ready = config.cloudReady === true && repo === normalizeRepository(config.repository);
    $('#repository').value = repo || '';
    $('#connection-status').textContent = ready ? 'Controls connected' : 'Setup pending';
    $('#connection-status').classList.toggle('connected', ready);
    $('#connection-description').textContent = ready
      ? 'Server controls are ready. The cloud gateway is connected to Discord, but replies still need a test.'
      : 'Server controls will be available after their connection is tested.';
    $('#setup-notice').hidden = ready;
    $('#repo-label').textContent = repo || 'QATRO / PERSONAL CLOUD';
    for (const action of ['start', 'stop', 'status']) {
      const el = $(`#${action}`);
      el.setAttribute('aria-disabled', String(!ready));
      if (ready) { el.href = workflowUrl(repo, action); el.removeAttribute('tabindex'); }
      else { el.removeAttribute('href'); el.tabIndex = -1; }
    }
  }

  $('#settings-button').addEventListener('click', () => $('#settings').showModal());
  $('#settings form').addEventListener('submit', (event) => {
    if (event.submitter?.value !== 'cancel') { event.preventDefault(); $('#save-settings').click(); }
  });
  $('#save-settings').addEventListener('click', () => {
    const repo = normalizeRepository($('#repository').value);
    if (!repo) { $('#settings-error').textContent = 'Use the format your-name/qatro-cloud.'; return; }
    $('#settings-error').textContent = '';
    savedRepository = repo;
    try { localStorage.setItem('qatro.repository', repo); } catch { /* Keep the in-memory choice. */ }
    render();
    $('#settings').close();
  });
  render();
  fetch('./config.json', { cache: 'no-store' })
    .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
    .then((value) => { config = value; render(); })
    .catch(() => { $('#setup-notice').textContent = 'The connection settings could not load. Refresh the page to try again.'; });
}
