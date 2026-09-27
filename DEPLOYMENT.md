# Deploy frontend and backend separately

## Render backend

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint** and connect the repository. Render reads the root `render.yaml` and creates the Python web service with `backend/` as its root directory.
3. Enter `GEMINI_API_KEY` when prompted. Set `FRONTEND_ORIGINS` to the exact Vercel site origin, for example `https://sales-recording-using-ocr.vercel.app` (no trailing slash). For multiple Vercel preview origins, provide a comma-separated list of exact origins.
4. Wait for the service health check to pass at `/health`, then copy the service URL, such as `https://invoice-ocr-api.onrender.com`.

The Render build installs Poppler for PDF support. Image upload does not require Poppler.

## Vercel frontend

1. Edit `frontend/js/config.js` and replace the placeholder with the Render service URL. Do not add a trailing slash.
2. In Vercel, import the same repository and set **Root Directory** to `frontend`.
3. Select **Other** as the framework preset. Leave the build command empty and set the output directory to `.` if Vercel asks for one.
4. Deploy the site, then copy its production origin (for example, `https://invoice-ocr.vercel.app`).
5. In Render, set `FRONTEND_ORIGINS` to that exact origin (or a comma-separated list including it) and redeploy the backend. Do not add `null`; it is an opaque origin sent by local files or sandboxed pages and is intentionally rejected.

The frontend calls the Render API directly. Keep the backend URL in `frontend/js/config.js` in sync if the Render service URL changes.

## Data storage

The current backend stores invoices in `backend/saved_invoices.json`. Render's default filesystem is ephemeral, so this local JSON data can be lost on restart or deploy. Use a persistent disk or move invoice storage to a database before relying on it for durable records.