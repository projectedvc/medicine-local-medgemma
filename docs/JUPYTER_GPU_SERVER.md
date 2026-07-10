# Jupyter GPU server

This is the supported MVP layout:

```text
browser -> application backend -> 127.0.0.1:8005 -> MedGemma GPU
```

The browser must never call the GPU API directly. For a remote backend, put a
machine-to-machine authenticated private network or tunnel between the backend
and the GPU server; do not expose port 8005 without an API key.

## 1. Verify the allocation

```bash
nvidia-smi --query-gpu=index,name,memory.total,memory.free --format=csv,noheader
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.device_count())"
```

`google/medgemma-4b-it` fits on one 44 GB GPU. If two GPUs are assigned, prefer
one full model replica per GPU for throughput. Do not split this 4B model across
two GPUs merely because both are available.

## 2. Clone the project and create the runtime

If the repository is not present yet, clone the deployment branch. If it is
already present (especially with local changes), do not clone over it.

```bash
mkdir -p "$HOME/work"
cd "$HOME/work"
git clone --branch stabledesign https://github.com/projectedvc/medicine-local-medgemma.git
cd medicine-local-medgemma
```

The GPU image must already contain a CUDA-compatible PyTorch build. Reuse it in
an isolated environment and install the remaining API/model packages:

```bash
cd "$HOME/work/medicine-local-medgemma"
python -m venv --system-site-packages .venv-gpu
. .venv-gpu/bin/activate
python -m pip install --upgrade pip
python -m pip install -r scripts/gpu_api_requirements.txt
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

## 3. Download a pinned model snapshot

Accept the HAI-DEF terms on the Hugging Face model page, copy its full commit
SHA, then authenticate and download that exact snapshot:

```bash
hf auth login
MODEL_COMMIT_SHA=replace_with_full_hugging_face_commit_sha
hf download google/medgemma-4b-it --revision "$MODEL_COMMIT_SHA"
```

Never put `HF_TOKEN`, tunnel tokens, JWT secrets, or API keys in a notebook,
Git, shell history, Dockerfile, URL, or frontend environment variable. Once the
model is cached, keep `LOCAL_FILES_ONLY=true` for normal starts.

Use a full Hugging Face commit SHA as `MODEL_COMMIT_SHA`, not the mutable
`main` name. `/healthz` records the resolved model revision plus the Torch and
Transformers versions so each inference can be traced to a reproducible runtime.

## 4. Configure and start the GPU API

The service binds to loopback, loads one model copy, and accepts a bounded JSON
request containing `image_base64`. It decodes JPEG/PNG and DICOM in memory.

```bash
mkdir -p "$HOME/.config/medicine-gpu"
nano "$HOME/.config/medicine-gpu/inference.env"
```

For a backend on the same Jupyter server, put this in the file (replace the
revision value):

```dotenv
PYTHON_BIN=$HOME/work/medicine-local-medgemma/.venv-gpu/bin/python
MODEL_ID=google/medgemma-4b-it
MODEL_REVISION=replace_with_full_hugging_face_commit_sha
LOCAL_FILES_ONLY=true
CUDA_VISIBLE_DEVICES=0
HOST=127.0.0.1
PORT=8005
ALLOW_UNAUTHENTICATED_LOCAL=true
```

Then protect the file and start the service. `restart` reloads the same file,
so model, CUDA, revision, and authentication settings are not lost.

```bash
chmod 600 "$HOME/.config/medicine-gpu/inference.env"
cd "$HOME/work/medicine-local-medgemma"
chmod 700 scripts/gpu_inference_service.sh
bash scripts/gpu_inference_service.sh start

bash scripts/gpu_inference_service.sh status
nvidia-smi
```

The log contains operational events only and is written to
`.runtime/gpu-inference/service.log`. The service disables HTTP access logs and
does not log prompts, image bytes, filenames, or model output.

Stop or restart it with:

```bash
bash scripts/gpu_inference_service.sh stop
bash scripts/gpu_inference_service.sh restart
```

## 5. Point the backend at the local service

For a backend running in the same Jupyter server:

```dotenv
AI_PROVIDER=http
AI_SERVICE_URL=http://127.0.0.1:8005/generate
AI_ALLOW_MOCK=false
AI_MODEL_VERSION=google/medgemma-4b-it
```

Restart the backend after changing its environment. A production backend also
needs a unique `JWT_SECRET`, managed Postgres, strict `ALLOWED_ORIGINS`, object
storage/retention rules, and backups.

If the backend runs elsewhere, set a long random `GPU_API_KEY` on the GPU
service and make the backend send `Authorization: Bearer ...`. Protect the
route with a private network or a named tunnel plus machine-to-machine access
policy. Keep the key only in the two server-side secret stores.

`ALLOW_UNAUTHENTICATED_LOCAL=true` is only for a backend on the same server.
Never publish that unauthenticated loopback port through a tunnel. For a remote
backend, remove this flag and set `GPU_API_KEY` before starting the service.

For a Cloudflare Access protected tunnel, the backend also needs
`AI_SERVICE_CF_ACCESS_CLIENT_ID` and `AI_SERVICE_CF_ACCESS_CLIENT_SECRET`.

## 6. Operational limits

- Run only one Uvicorn worker per GPU/model copy.
- Requests are serialized and wait at most `QUEUE_WAIT_SECONDS` (5 by default).
- Request, decoded-image, pixel, prompt, and output limits are configurable via
  environment variables.
- DICOM windowing applies modality, VOI, and presentation transforms when they
  are present. Compressed transfer syntaxes require the optional decoder
  packages listed in `scripts/gpu_api_requirements.txt`; validate the exact
  modalities and transfer syntaxes used by your institution before rollout.
- Use only synthetic or properly de-identified studies until every storage,
  hosting, logging, backup, and tunnel provider is approved for the applicable
  medical-data rules.
- MedGemma output is research decision support, not a diagnosis. A radiologist
  must review every result; generated confidence is not a calibrated clinical
  probability. This API strips model-generated confidence/probability fields
  and marks confidence as unvalidated until a separate scoring and calibration
  study is completed.
- `nohup` survives closing the terminal, but not a JupyterHub pod/server restart
  or idle culling. Production requires an administrator-managed service account,
  dedicated pod/VM, persistent volume, and automatic restart policy.

## 7. Recommended public architecture

For an MVP, use a static Vercel frontend, a persistent Render backend, and a
named Cloudflare Tunnel that exposes the loopback GPU service only to that
backend through Cloudflare Access. Add Access service-token headers and the
independent `GPU_API_KEY`. For large or
long-running jobs, the production target should be an outbound GPU worker that
pulls job IDs from a durable queue and fetches an encrypted object by a short-
lived signed URL; this avoids a public GPU endpoint and survives temporary GPU
server outages.

The current MVP service intentionally uses only GPU 0. A second visible GPU
requires a second service instance with its own runtime directory/port and a
real load balancer (or vLLM data parallel); it is not used automatically.

Before building the Vercel frontend, set the project environment variable
`VITE_API_URL=https://your-backend.example.com` for Production and Preview.
The frontend build intentionally fails when this value is missing; the previous
hard-coded ngrok rewrite has been removed. On the backend, set
`ALLOWED_ORIGINS` to the exact Vercel domains that may call it.
