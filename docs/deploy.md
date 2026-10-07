# Deploy

The site is a Next.js app with a server route at `/api/chat`. Chat needs that route. A static export cannot hold the Gemini key or run the tools.

## Vercel project

1. Import `accomplish999/crude-oil` as a Next.js project.
2. Build command: `npm run build`. Install command: `npm ci`.
3. Set `GEMINI_API_KEY` for Production and Preview. Leave it encrypted. Do not prefix it with `NEXT_PUBLIC_`.
4. Set `NEXT_PUBLIC_SITE_URL` to the origin users type, with no trailing slash.
5. Leave `NEXT_PUBLIC_BASE_PATH` empty when the project has its own host. Set it to `/crude-oil` only when this build is mounted under that prefix. The value is read at build time. Change it, then redeploy.

Python is not part of the Vercel build. The snapshot in `data/` is what the site renders.

## Refresh

`.github/workflows/refresh.yml` runs on weekdays at 11:15 UTC, on Wednesday at 14:30 and 15:30 UTC (EIA 10:30 New York, both daylight and standard time), and on Friday at 19:30 and 20:30 UTC (CFTC 15:30 New York, both). GitHub may start a cron late.

Order: ingest, `scripts/verify.py`, studies, books, notebooks, downloads, changelog, unit tests. A failed step does not commit. The alert job opens or comments on a GitHub issue titled `Data refresh failed`.

A push to `main` redeploys when the Vercel Git integration is connected. Set the repository secret `VERCEL_DEPLOY_HOOK` if you also want an explicit deploy hook, for example so the parent host picks up a new build.

## How accompli.sh/crude-oil should be wired

`accompli.sh` is Vercel project `prj_fthkEwBugIw4TLh2zCoOOiwqwXEF` on team `accomplishs-projects`.

What is live today:

- `https://accompli.sh/` is that Next app.
- `https://accompli.sh/position-sizer/` is proxied to GitHub Pages. The response carries both `server: Vercel` and `x-github-request-id`, and the HTML is the Pages site.
- `https://accompli.sh/research` returns the parent app's 404. The research repository is a separate static Next export. It is not attached to the domain yet.
- `https://accompli.sh/crude-oil` returns the same 404.

This repository cannot edit the parent project's rewrites from here (project route API returns not found, deployment list returns forbidden). Add the rewrite on project `prj_fthkEwBugIw4TLh2zCoOOiwqwXEF`:

```json
{
  "rewrites": [
    {
      "source": "/crude-oil",
      "destination": "https://PROJECT.vercel.app/crude-oil"
    },
    {
      "source": "/crude-oil/:path*",
      "destination": "https://PROJECT.vercel.app/crude-oil/:path*"
    }
  ]
}
```

Replace `PROJECT` with the production host of this Vercel project. Build this app with `NEXT_PUBLIC_BASE_PATH=/crude-oil` and `NEXT_PUBLIC_SITE_URL=https://accompli.sh` so asset URLs, the chat fetch, and canonical links include the prefix.

If the rewrite strips the prefix (destination has no `/crude-oil`), leave `NEXT_PUBLIC_BASE_PATH` empty and accept that HTML from the child will point at the child host. That breaks the public URL. Keep the prefix on both sides.

The same shape is what `/research` still needs: a rewrite to the research project's host, plus a `basePath` of `/research` on that static export if it is not already built with one. Until that rewrite exists, `accompli.sh/research` stays a 404 even though the repository is ready.

## Local production build

```bash
npm ci
npm run build
npm start
```

Chat returns local tool answers until `GEMINI_API_KEY` is set in the environment.
