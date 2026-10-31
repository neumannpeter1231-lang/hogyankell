-- Hogyankell – kommentek a posztok alatt
-- Supabase → SQL Editor → New query → másold be az egészet → Run. Többször is lefuttatható.
-- A kommentek a docs táblában vannak: path = comments/<poszt>/<id>, coll = comments/<poszt>.

-- Olvasás: minden meghívott látja a kommenteket.
drop policy if exists "comments read" on public.docs;
create policy "comments read" on public.docs for select to authenticated
  using (coll like 'comments/%' and public.is_member());

-- Írás: csak a saját nevében, legfeljebb 300 karakter.
drop policy if exists "comments create" on public.docs;
create policy "comments create" on public.docs for insert to authenticated
  with check (
    coll like 'comments/%'
    and path like coll || '/%'
    and owner = auth.uid()
    and data ->> 'by' = auth.uid()::text
    and length(coalesce(data ->> 'text', '')) between 1 and 300
    and public.is_member()
  );

-- Törlés: mindenki csak a saját kommentjét.
drop policy if exists "comments delete own" on public.docs;
create policy "comments delete own" on public.docs for delete to authenticated
  using (coll like 'comments/%' and owner = auth.uid());
