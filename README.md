# Mini Message

A small learning web app using HTML, CSS, JavaScript and Supabase Auth/Postgres.

## Features
- Email/password register and login
- Save, list and delete messages
- One application table: `public.mini_messages`
- Row Level Security restricts records to the signed-in owner

## Setup
1. In Supabase SQL Editor, run `supabase/schema.sql`.
2. Set the Project URL and publishable key in `config.js`.
3. Open `index.html` using VS Code Live Server or deploy the repository as a static site.
4. Configure Supabase Auth URL settings for the local and deployed site if email confirmation is enabled.

Only use the publishable/anon key in browser code. Never put a service-role or secret key in this repository.