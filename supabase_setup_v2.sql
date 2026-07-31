-- Einmalig im Supabase SQL-Editor ausfuehren (Dashboard -> SQL Editor -> New query).
-- Diese zwei neuen Tabellen braucht der ueberarbeitete Code zusaetzlich zu den
-- bereits bestehenden Tabellen (Handelsgeschichte, chat_messages, Risiko_Log, system_knowledge).

-- 1) Denkprotokoll: jede Analyse, auch wenn nicht getradet wird
create table if not exists public.bot_thoughts (
  id bigint generated always as identity primary key,
  created_at timestamptz default now(),
  symbol text,
  direction text,
  confidence numeric,
  reasons text,
  ai_comment text
);
alter table public.bot_thoughts enable row level security;
create policy if not exists "service access" on public.bot_thoughts
  for all using (true) with check (true);

-- 2) Feature-Snapshot pro Trade, Grundlage fuer das Nachtraining
create table if not exists public.trade_features (
  id bigint generated always as identity primary key,
  trade_id bigint references public."Handelsgeschichte"(id),
  rsi_1h numeric,
  rsi_15m numeric,
  pattern_score numeric,
  confidence numeric,
  created_at timestamptz default now()
);
alter table public.trade_features enable row level security;
create policy if not exists "service access" on public.trade_features
  for all using (true) with check (true);
