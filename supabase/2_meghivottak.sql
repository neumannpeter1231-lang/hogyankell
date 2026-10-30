-- Hogyankell – meghívottak felvétele
-- Írd át az e-mail címeket, a felesleges sorokat töröld, aztán Run.
-- Az első sorba a SAJÁT Google-fiókod címe kerüljön, különben te sem tudsz belépni.
-- Később a Table Editor → invites táblában is felvehetsz vagy törölhetsz címeket.

insert into public.invites (email, note) values
  ('IDE_A_SAJAT_GMAIL_CIMED@gmail.com', 'Péter'),
  ('haver1@gmail.com', 'Első tesztelő'),
  ('haver2@gmail.com', 'Második tesztelő')
on conflict (email) do nothing;

-- Ellenőrzés: kik vannak a listán?
select email, note, created_at from public.invites order by created_at;
