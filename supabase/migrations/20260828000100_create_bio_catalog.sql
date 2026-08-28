create table if not exists public.sources (
  id text primary key,
  name text not null,
  enabled boolean not null default true,
  cursor jsonb not null default '{}'::jsonb,
  last_success_at timestamptz,
  last_error text,
  updated_at timestamptz not null default now()
);

create table if not exists public.documents (
  id text primary key,
  source_id text not null references public.sources(id) on update cascade,
  source_record_id text not null,
  kind text not null check (kind in ('paper', 'evaluation_update')),
  title text not null,
  abstract text not null default '',
  authors jsonb not null default '[]'::jsonb,
  published_at timestamptz,
  updated_at_source timestamptz,
  identifiers jsonb not null default '{}'::jsonb,
  links jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  content_hash text not null,
  extraction_status text not null,
  extraction_error text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source_id, source_record_id)
);

create table if not exists public.benchmarks (
  id text primary key,
  name text not null,
  aliases jsonb not null default '[]'::jsonb,
  categories jsonb not null default '[]'::jsonb,
  access_status text not null default 'unknown'
    check (access_status in ('public', 'partial', 'restricted', 'private', 'unknown')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.entries (
  id text primary key,
  document_id text references public.documents(id) on update cascade,
  slug text not null unique,
  kind text not null check (kind in ('paper', 'evaluation_update')),
  title text not null,
  abstract text not null default '',
  authors jsonb not null default '[]'::jsonb,
  source text not null,
  published_at timestamptz,
  updated_at timestamptz,
  first_seen_at timestamptz not null,
  event_at timestamptz not null,
  priority text not null check (priority in ('P0', 'P1', 'P2')),
  categories jsonb not null default '[]'::jsonb,
  collection_status text not null check (collection_status in ('confirmed', 'watchlist')),
  access_status text not null check (access_status in ('public', 'partial', 'restricted', 'private', 'unknown')),
  license text not null default '',
  identifiers jsonb not null default '{}'::jsonb,
  links jsonb not null default '{}'::jsonb,
  evidence jsonb not null default '[]'::jsonb,
  related_benchmarks jsonb not null default '[]'::jsonb,
  related_agent_url text not null default '',
  evaluation_contexts jsonb not null default '[]'::jsonb,
  classification_reason text not null,
  match_score integer not null default 0,
  extraction_status text not null,
  extraction_error text not null default '',
  content_hash text not null,
  is_seed boolean not null default false
);

create table if not exists public.entry_benchmarks (
  entry_id text not null references public.entries(id) on delete cascade,
  benchmark_id text not null references public.benchmarks(id) on delete cascade,
  primary key (entry_id, benchmark_id)
);

create table if not exists public.source_runs (
  id bigint generated always as identity primary key,
  source_id text not null references public.sources(id) on update cascade,
  started_at timestamptz not null,
  finished_at timestamptz not null,
  status text not null check (status in ('success', 'partial', 'failed')),
  discovered integer not null default 0,
  published integer not null default 0,
  error text not null default '',
  details jsonb not null default '{}'::jsonb
);

create index if not exists entries_event_at_idx on public.entries (event_at desc);
create index if not exists entries_priority_idx on public.entries (priority);
create index if not exists entries_collection_status_idx on public.entries (collection_status);
create index if not exists documents_identifiers_gin on public.documents using gin (identifiers);

alter table public.sources enable row level security;
alter table public.documents enable row level security;
alter table public.benchmarks enable row level security;
alter table public.entries enable row level security;
alter table public.entry_benchmarks enable row level security;
alter table public.source_runs enable row level security;

revoke all on table public.sources from anon, authenticated;
revoke all on table public.documents from anon, authenticated;
revoke all on table public.benchmarks from anon, authenticated;
revoke all on table public.entries from anon, authenticated;
revoke all on table public.entry_benchmarks from anon, authenticated;
revoke all on table public.source_runs from anon, authenticated;
