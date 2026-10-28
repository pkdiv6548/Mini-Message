# Mini Message

A small learning web app built with HTML, CSS, JavaScript and Supabase Auth/Postgres.

## Features
- Email/password registration and login
- Save, list and delete messages
- `public.mini_messages` table
- Row Level Security limits each user to their own records
- Static hosting on Cloudflare Pages

## Zero-budget setup

### 1. Supabase database
1. Open the Supabase project used by this app.
2. In **SQL Editor**, run [`supabase/schema.sql`](supabase/schema.sql).
3. In **Authentication → URL Configuration**, set the Site URL to `https://mini-message.pages.dev` after the site is deployed. Add local development URLs to Redirect URLs when testing locally.

### 2. Supabase browser configuration
Update `config.js` and `public/config.js` with the Supabase project URL and **publishable/anon** key:

```js
window.APP_CONFIG = {
  SUPABASE_URL: "https://YOUR_PROJECT.supabase.co",
  SUPABASE_ANON_KEY: "YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY"
};
```

A publishable/anon key is designed for browser use when Row Level Security (RLS) is configured correctly. Never put a Supabase `service_role` key or another server secret in frontend files or Git history.

### 3. Cloudflare Pages deployment through GitHub Actions
The Cloudflare Pages project `mini-message` has been created in the connected Cloudflare account. The public website files live in `public/`, so the database schema and development files are not part of the deployed site.

To allow GitHub Actions to deploy:
1. In Cloudflare Dashboard, create an API token with **Account → Cloudflare Pages → Edit** permission. Scope it to the account that owns this Pages project.
2. In GitHub, open **Settings → Secrets and variables → Actions → New repository secret**.
3. Add `CLOUDFLARE_API_TOKEN` with the token you just created.
4. Add `CLOUDFLARE_ACCOUNT_ID` with your Cloudflare Account ID. The connected account ID for this project is `a9b08391a849a2e0804f6c93bb65c251`.
5. Open the repository **Actions** tab and run **Mini Message CI/CD**, or push a commit to `main`.

The workflow checks required files and JavaScript syntax. It deploys `public/` to `mini-message.pages.dev` when both GitHub Actions secrets exist. Until they are configured, the workflow intentionally skips deployment and displays a warning. Do not paste the API token into code, issues, or chat.

Cloudflare's Git-provider connection endpoint returned an internal installation error during setup, so the repository is configured to deploy through GitHub Actions rather than relying on that connection.

### 4. Local testing
Open `index.html` from the repository root with VS Code Live Server, or use any static HTTP server. For testing the exact deploy output, serve the `public/` directory. Avoid `file://` URLs because browser-origin and authentication settings are easier to validate over HTTP.

## Troubleshooting
- If login fails, verify the Supabase project URL/key and Auth URL configuration.
- If table access fails, run `supabase/schema.sql` and verify that RLS is enabled and the policies belong to `authenticated` users.
- Do not disable RLS to fix a permissions error.
- If Cloudflare deployment is skipped, confirm both GitHub repository Actions secrets are present and re-run the workflow.

## Cost policy
Keep this project at ₹0. Do not enable paid plans or billing without explicit approval. This app currently uses Supabase for authentication/database and Cloudflare Pages for static hosting; it does not yet implement a Cloudflare Workers/D1 backend.
