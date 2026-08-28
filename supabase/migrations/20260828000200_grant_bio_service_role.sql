grant usage on schema public to service_role;
grant select, insert, update, delete on table
  public.sources,
  public.documents,
  public.benchmarks,
  public.entries,
  public.entry_benchmarks,
  public.source_runs
to service_role;
grant usage, select on sequence public.source_runs_id_seq to service_role;
