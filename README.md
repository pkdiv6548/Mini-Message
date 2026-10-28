# Mini Message

A small learning web app built with HTML, CSS, JavaScript and Supabase Auth/Postgres.

## Features
- Email/password registration and login
- Save, list and delete messages
- `public.mini_messages` table
- Row Level Security limits each user to their own records
- Static hosting compatible with Cloudflare Pages

## Zero-budget setup

### 1. Supabase database
1. Open the Supabase project used by this app.
2. In **SQL Editor**, run [`supabase/schema.sql`](supabase/schema.sql).
3. In **Authentication → URL Configuration**, set the Site URL to the deployed `https://<project>.pages.dev` URL and add local development URLs to the Redirect URLs list if needed.

### 2. Supabase browser configuration
Update `config.js` with the Supabase project URL and **publishable/anon** key:

```js
window.APP_CONFIG = {
  SUPABASE_URL: "https://YOUR_PROJECT.supabase.co",
  SUPABASE_ANON_KEY: "YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY"
};
```

A publishable/anon key is designed for browser use when Row Level Security is correctly configured. Never put a Supabase `service_role` key or other secret in frontend files or Git history.

### 3. Deploy with Cloudflare Pages
1. In Cloudflare Dashboard, open **Workers & Pages → Create → Pages → Connect to Git**.
2. Connect GitHub and choose `pkdiv6548/Mini-Message`, branch `main`.
3. For this plain static site, set **Build command** to blank and **Build output directory** to `/` (repository root).
4. Create the Pages project. Every push to `main` can then trigger a deployment.
5. Open the generated `https://<project>.pages.dev` URL and test registration/login and message CRUD.

The repository contains `.github/workflows/deploy.yml` for static-file and accidental-secret checks. Cloudflare Pages performs the actual website deployment; the workflow does not publish to GitHub Pages.

## Local testing
Open `index.html` via VS Code Live Server, or use any static HTTP server. Avoid opening it via `file://`, because authentication/network behavior and browser origin settings are easier to validate over HTTP.

## Troubleshooting
- If login fails, verify the Supabase project URL/key and Auth URL configuration.
- If table access fails, run `supabase/schema.sql` and verify that RLS is enabled and the policies belong to `authenticated` users.
- Do not disable RLS to fix a permissions error.

## Cost policy
Keep this project at ₹0. Do not enable paid plans or billing without explicit approval. The app currently uses Supabase for authentication/database and Cloudflare Pages for static hosting; it does not yet implement a Cloudflare Workers/D1 backend.
