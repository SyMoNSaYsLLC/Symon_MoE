const API_BASE = '/api';

const healthStatus = document.getElementById('healthStatus');
const workerStatus = document.getElementById('workerStatus');
const jobsEl = document.getElementById('jobs');
const modelsEl = document.getElementById('models');
const scanModelsBtn = document.getElementById('scanModelsBtn');

async function getJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `Request failed: ${response.status}`);
  }
  return data;
}

function renderJobs(jobs) {
  if (!jobs.length) {
    jobsEl.textContent = 'No jobs yet.';
    return;
  }

  jobsEl.innerHTML = jobs
    .slice()
    .reverse()
    .map(
      (job) => `
        <article>
          <strong>${job.job_type}</strong> ${job.id}<br />
          <span class="status-pill">${job.status}</span>
          <div>Worker: ${job.worker || 'n/a'}</div>
          <div>${job.error ? `Error: ${job.error}` : ''}</div>
          <details>
            <summary>Logs (${job.logs.length})</summary>
            <pre>${job.logs.join('\n')}</pre>
          </details>
          ${job.result ? `<div>Result: ${job.result.artifact_name}</div>` : ''}
        </article>
      `
    )
    .join('');
}

function renderModels(scan) {
  const rawList = scan.raw_models
    .map(
      (m) =>
        `<li>${m.name} - llm:${m.ready_for_llm ? 'ready' : 'missing config.json'}, diffusion:${m.ready_for_diffusion ? 'ready' : 'missing .safetensors'}</li>`
    )
    .join('');

  const converted = scan.converted_artifacts.map((m) => `<li>${m.name}</li>`).join('');
  const migrated = scan.migrated_artifacts.map((m) => `<li>${m.name}</li>`).join('');

  modelsEl.innerHTML = `
    <div><strong>Raw models</strong><ul>${rawList || '<li>None</li>'}</ul></div>
    <div><strong>Converted artifacts</strong><ul>${converted || '<li>None</li>'}</ul></div>
    <div><strong>Migrated artifacts</strong><ul>${migrated || '<li>None</li>'}</ul></div>
    <div><small>Metadata file: ${scan.storage_contract.metadata_file}</small></div>
  `;
}

async function refreshHealth() {
  try {
    const health = await getJson(`${API_BASE}/health`);
    healthStatus.textContent = `API: ${health.status} | models root: ${health.models_root}`;
  } catch (error) {
    healthStatus.textContent = `API error: ${error.message}`;
  }
}

async function refreshWorkers() {
  try {
    const data = await getJson(`${API_BASE}/workers/status`);
    const rows = Object.entries(data.workers)
      .map(([name, worker]) => `
        <tr>
          <td>${name}</td>
          <td>${worker.type || '-'}</td>
          <td>${worker.queued ?? 0}</td>
          <td>${worker.current_job || 'idle'}</td>
        </tr>
      `)
      .join('');
    workerStatus.innerHTML = `
      <table>
        <thead><tr><th>Worker</th><th>Type</th><th>Queued</th><th>Current</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (error) {
    workerStatus.textContent = `Worker status unavailable: ${error.message}`;
  }
}

async function refreshJobs() {
  try {
    const data = await getJson(`${API_BASE}/jobs`);
    renderJobs(data.jobs || []);
  } catch (error) {
    jobsEl.textContent = `Jobs unavailable: ${error.message}`;
  }
}

async function scanModels() {
  try {
    const scan = await getJson(`${API_BASE}/models/discover`);
    renderModels(scan);
  } catch (error) {
    modelsEl.textContent = `Model scan failed: ${error.message}`;
  }
}

scanModelsBtn.addEventListener('click', scanModels);

document.getElementById('conversionForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = {
    model_name: form.get('model_name').trim(),
    architecture: form.get('architecture'),
    outtype: form.get('outtype').trim() || 'q8_0',
  };

  const outputName = form.get('output_name').trim();
  if (outputName) payload.output_name = outputName;

  const sourceFile = form.get('source_file').trim();
  if (sourceFile) payload.source_file = sourceFile;

  try {
    await getJson(`${API_BASE}/jobs/conversion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    event.target.reset();
    await Promise.all([scanModels(), refreshJobs(), refreshWorkers()]);
  } catch (error) {
    alert(`Conversion request failed: ${error.message}`);
  }
});

document.getElementById('migrationForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = {
    sources: [
      { architecture: 'llama', artifact_name: form.get('llama_artifact').trim() },
      { architecture: 'qwen2', artifact_name: form.get('qwen2_artifact').trim() },
      { architecture: 'mistral', artifact_name: form.get('mistral_artifact').trim() },
    ],
    target_name: form.get('target_name').trim(),
  };

  if (payload.sources.some((source) => !source.artifact_name)) {
    alert('All three source artifacts are required for migration.');
    return;
  }

  try {
    await getJson(`${API_BASE}/jobs/migration`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    await Promise.all([scanModels(), refreshJobs(), refreshWorkers()]);
  } catch (error) {
    alert(`Migration request failed: ${error.message}`);
  }
});

setInterval(() => {
  refreshWorkers();
  refreshJobs();
  scanModels();
}, 5000);

refreshHealth();
refreshWorkers();
refreshJobs();
scanModels();
