-- Hogyankell – emlékeztető-időzítő (5 percenként lefuttatja a send-reminders függvényt)
-- Csak akkor futtasd, ha a send-reminders függvény már él (útmutató 7. lépés).
-- Írd át a PROJEKT-AZONOSITO részt a saját projekted azonosítójára (a Project URL eleje,
-- pl. https://abcdefghijkl.supabase.co esetén: abcdefghijkl), aztán Run.

create extension if not exists pg_cron;
create extension if not exists pg_net;

select cron.unschedule(jobid) from cron.job where jobname = 'hogyankell-emlekezteto';

select cron.schedule(
  'hogyankell-emlekezteto',
  '*/5 * * * *',
  $$
  select net.http_post(
    url := 'https://PROJEKT-AZONOSITO.supabase.co/functions/v1/send-reminders',
    headers := jsonb_build_object('Content-Type', 'application/json', 'x-cron-secret', 'IDE_A_CRON_SECRET'),
    body := '{}'::jsonb
  );
  $$
);

-- Ellenőrzés: ott van-e az időzítő?
select jobid, jobname, schedule from cron.job;
