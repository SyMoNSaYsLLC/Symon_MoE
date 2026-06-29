const API_IMAGE = '/api/image';
const POLL_INTERVAL = 2000;

const modelSelect  = document.getElementById('modelSelect');
const promptInput  = document.getElementById('promptInput');
const negPromptInput = document.getElementById('negPromptInput');
const widthInput   = document.getElementById('widthInput');
const heightInput  = document.getElementById('heightInput');
const stepsInput   = document.getElementById('stepsInput');
const cfgInput     = document.getElementById('cfgInput');
const seedInput    = document.getElementById('seedInput');
const generateBtn  = document.getElementById('generateBtn');
const jobStatus    = document.getElementById('jobStatus');
const gallery      = document.getElementById('gallery');
const emptyState   = document.getElementById('emptyState');

// ---- Load models ---------------------------------------------------------

(async () => {
  try {
    const data = await (await fetch(`${API_IMAGE}/models`)).json();
    const models = data.models || [];
    modelSelect.innerHTML = models.length
      ? models.map((m) => `<option value="${escapeAttr(m.name)}">${escapeHtml(m.name)}</option>`).join('')
      : '<option value="">No GGUF diffusion models found</option>';
  } catch {
    modelSelect.innerHTML = '<option value="">Models unavailable</option>';
  }
})();

// ---- Generate ------------------------------------------------------------

generateBtn.addEventListener('click', generate);

async function generate() {
  const prompt = promptInput.value.trim();
  if (!prompt) { alert('Please enter a prompt.'); return; }

  const model = modelSelect.value;
  if (!model) { alert('No model selected.'); return; }

  generateBtn.disabled = true;
  jobStatus.textContent = 'Submitting job…';

  const payload = {
    prompt,
    negative_prompt: negPromptInput.value.trim(),
    model,
    width:     parseInt(widthInput.value,  10),
    height:    parseInt(heightInput.value, 10),
    steps:     parseInt(stepsInput.value,  10),
    cfg_scale: parseFloat(cfgInput.value),
    seed:      parseInt(seedInput.value, 10),
  };

  try {
    const resp = await fetch(API_IMAGE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const { job_id } = await resp.json();
    jobStatus.textContent = `Job queued (${job_id.slice(0, 8)})…`;
    pollJob(job_id);
  } catch (err) {
    jobStatus.textContent = `Error: ${err.message}`;
    generateBtn.disabled = false;
  }
}

async function pollJob(jobId) {
  const timer = setInterval(async () => {
    try {
      const resp = await fetch(`${API_IMAGE}/jobs/${jobId}`);
      const job  = await resp.json();
      jobStatus.textContent = `Job ${jobId.slice(0, 8)}: ${job.status}`;

      if (job.status === 'done') {
        clearInterval(timer);
        generateBtn.disabled = false;
        addToGallery(job.output);
      } else if (job.status === 'failed') {
        clearInterval(timer);
        generateBtn.disabled = false;
        jobStatus.textContent = `Failed: ${job.error || 'unknown error'}`;
      }
    } catch {
      clearInterval(timer);
      generateBtn.disabled = false;
    }
  }, POLL_INTERVAL);
}

function addToGallery(outputPath) {
  emptyState.classList.add('hidden');
  const img = document.createElement('img');
  img.src = `/models/${outputPath}`;
  img.className = 'gallery-image';
  img.alt = 'Generated image';

  const dl = document.createElement('a');
  dl.href = img.src;
  dl.download = outputPath.split('/').pop();
  dl.className = 'gallery-dl';
  dl.title = 'Download';
  dl.textContent = '⬇ Download';

  const wrapper = document.createElement('div');
  wrapper.className = 'gallery-item';
  wrapper.appendChild(img);
  wrapper.appendChild(dl);
  gallery.prepend(wrapper);
}

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function escapeAttr(s) {
  return String(s).replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
