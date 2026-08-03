-- Two-step correction for the one genuine collision in the v1.1 patch.
--
-- Row 88020 currently holds 10.18060/23600. Crossref says that DOI belongs to
-- '"Just a Job?" An Assessment of Precarious Employment Trajectories', which is
-- the title of row 114805 — not 88020, which is 'The effect of government
-- grants on private giving to East Asian nonprofits'.
--
-- So the PRE-EXISTING row is the mis-assigned one. Resolving the collision the
-- obvious way (dropping 114805's correction and leaving 88020 alone) would make
-- the error permanent and leave the correct article without its DOI.
--
-- RUN THIS BEFORE apply_doi_corrections.sql, and only after confirming 88020's
-- real DOI. It is left NULL here rather than guessed: nulling is recoverable,
-- and a wrong DOI is what caused this.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f fix_88020_first.sql
--
-- Afterwards, add 114805 back to the patch:
--   update swrd.papers set doi = '10.18060/23600'
--    where id = 114805 and doi = 'dc/8492984d69';

begin;

-- Release the DOI from the row that should not hold it.
update swrd.papers
   set doi = null
 where id = 88020
   and doi = '10.18060/23600';

do $$
declare n int;
begin
  select count(*) into n from swrd.papers where id = 88020 and doi is null;
  if n <> 1 then
    raise exception 'row 88020 not in the expected state — inspect before proceeding';
  end if;
  raise notice 'row 88020 released; find its correct DOI and set it separately';
end $$;

commit;
