-- Hogyankell – „Minden adatom törlése” (GDPR 17. cikk, törléshez való jog)
-- Supabase → SQL Editor → New query → másold be az egészet → Run. Többször is lefuttatható.
-- A bejelentkezett felhasználó a Profil → Adataim → „Minden adatom törlése” gombbal hívja meg.
-- Az invites táblában lévő meghívó (e-mail-cím) megmarad, azt Péter kezeli (kérésre onnan is törli).

create or replace function public.delete_my_data()
returns void
language plpgsql security definer
set search_path = public
as $$
declare
  uid uuid := auth.uid();
begin
  if uid is null then raise exception 'not signed in'; end if;

  -- saját haladás, liga-sor, saját kihívások és kommentek
  delete from public.docs
   where owner = uid
      or path like 'data/users/' || uid::text || '/%'
      or path = 'league/' || uid::text
      or (coll = 'challenges' and data ->> 'by' = uid::text)
      or (coll like 'comments/%' and data ->> 'by' = uid::text);

  -- a saját eredmény kivétele mások kihívásaiból
  update public.docs
     set data = data - ('r_' || uid::text), updated_at = now()
   where coll = 'challenges' and data ? ('r_' || uid::text);

  delete from public.push_subs where user_id = uid;
  delete from public.reminders where user_id = uid;
  delete from public.profiles  where id = uid;

  -- végül maga a fiók (a fenti táblák a fiókra hivatkoznak, ez a maradékot is viszi)
  delete from auth.users where id = uid;
end;
$$;

revoke all on function public.delete_my_data() from public;
revoke execute on function public.delete_my_data() from anon;
grant execute on function public.delete_my_data() to authenticated;
