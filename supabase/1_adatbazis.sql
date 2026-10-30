-- Hogyankell zárt teszt – adatbázis
-- Supabase → SQL Editor → New query → másold be az egészet → Run.
-- Többször is lefuttatható, nem töröl adatot.

-- 1) Meghívottak listája: csak az itt szereplő e-mail címekkel lehet belépni.
create table if not exists public.invites (
  email text primary key,
  note text,
  created_at timestamptz not null default now()
);

-- 2) Nevek a ligához és a kihívásokhoz.
create table if not exists public.profiles (
  id uuid primary key references auth.users on delete cascade,
  name text not null default '',
  updated_at timestamptz not null default now()
);

-- 3) Az app adatai (haladás, liga, kihívások) egy közös táblában, útvonal szerint.
create table if not exists public.docs (
  path text primary key,
  coll text not null,
  owner uuid references auth.users on delete cascade default auth.uid(),
  data jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
create index if not exists docs_coll_idx on public.docs (coll);

-- 4) Értesítések: feliratkozások és emlékeztető-beállítások.
create table if not exists public.push_subs (
  endpoint text primary key,
  user_id uuid not null references auth.users on delete cascade default auth.uid(),
  sub jsonb not null,
  created_at timestamptz not null default now()
);
create table if not exists public.reminders (
  user_id uuid primary key references auth.users on delete cascade default auth.uid(),
  tz text not null default 'Europe/Budapest',
  cfg jsonb not null default '{}'::jsonb,
  sent jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- Meghívott-e a bejelentkezett felhasználó?
create or replace function public.is_member()
returns boolean
language sql stable security definer
set search_path = public
as $$
  select exists (
    select 1 from public.invites
    where lower(email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;

-- Kihívás eredményének beírása: mindenki csak a saját sorát írhatja, mást nem írhat át.
create or replace function public.challenge_result(p_code text, p_score int)
returns void
language plpgsql security definer
set search_path = public
as $$
begin
  if not public.is_member() then raise exception 'not a member'; end if;
  if p_score < 0 or p_score > 10 then raise exception 'bad score'; end if;
  update public.docs
     set data = data || jsonb_build_object('r_' || auth.uid()::text,
                  jsonb_build_object('s', p_score, 'at', (extract(epoch from now()) * 1000)::bigint)),
         updated_at = now()
   where path = 'challenges/' || upper(p_code)
     and not (data ? ('r_' || auth.uid()::text))
     and data ->> 'by' <> auth.uid()::text;
end;
$$;

grant execute on function public.is_member() to authenticated;
grant execute on function public.challenge_result(text, int) to authenticated;
revoke execute on function public.challenge_result(text, int) from anon;

-- Sorszintű védelem
alter table public.invites   enable row level security;
alter table public.profiles  enable row level security;
alter table public.docs      enable row level security;
alter table public.push_subs enable row level security;
alter table public.reminders enable row level security;

-- invites: a felhasználók nem látják és nem írják (Péter a Table Editorban kezeli).
drop policy if exists "profiles read" on public.profiles;
create policy "profiles read" on public.profiles for select to authenticated using (public.is_member());
drop policy if exists "profiles write own" on public.profiles;
create policy "profiles write own" on public.profiles for insert to authenticated with check (id = auth.uid() and public.is_member());
drop policy if exists "profiles update own" on public.profiles;
create policy "profiles update own" on public.profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

-- Saját adatok: data/users/<saját id>/...
drop policy if exists "own data" on public.docs;
create policy "own data" on public.docs for all to authenticated
  using (path like 'data/users/' || auth.uid()::text || '/%' and public.is_member())
  with check (path like 'data/users/' || auth.uid()::text || '/%' and coll = 'data/users/' || auth.uid()::text and public.is_member());

-- Liga: mindenki látja, mindenki csak a saját sorát írja.
drop policy if exists "league read" on public.docs;
create policy "league read" on public.docs for select to authenticated
  using (coll = 'league' and public.is_member());
drop policy if exists "league insert own" on public.docs;
create policy "league insert own" on public.docs for insert to authenticated
  with check (coll = 'league' and path = 'league/' || auth.uid()::text and public.is_member());
drop policy if exists "league update own" on public.docs;
create policy "league update own" on public.docs for update to authenticated
  using (coll = 'league' and path = 'league/' || auth.uid()::text)
  with check (coll = 'league' and path = 'league/' || auth.uid()::text);

-- Kihívások: mindenki látja; létrehozni csak a saját nevében lehet; eredményt a challenge_result() ír.
drop policy if exists "challenges read" on public.docs;
create policy "challenges read" on public.docs for select to authenticated
  using (coll = 'challenges' and public.is_member());
drop policy if exists "challenges create" on public.docs;
create policy "challenges create" on public.docs for insert to authenticated
  with check (coll = 'challenges' and path ~ '^challenges/[A-Z0-9]{5}$' and data ->> 'by' = auth.uid()::text and public.is_member());

-- Értesítések: mindenki csak a sajátját látja és írja.
drop policy if exists "own subs" on public.push_subs;
create policy "own subs" on public.push_subs for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid() and public.is_member());
drop policy if exists "own reminders" on public.reminders;
create policy "own reminders" on public.reminders for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid() and public.is_member());

-- Hozzáférés a bejelentkezett felhasználóknak (a fenti szabályok szerint).
grant usage on schema public to authenticated;
grant select, insert, update, delete on public.docs, public.profiles, public.push_subs, public.reminders to authenticated;
