-- The one genuine collision in the v1.1 patch. Run BEFORE apply_doi_corrections.sql.
--
-- Row 88020 holds 10.18060/23600. Crossref says that DOI belongs to
-- '"Just a Job?" An Assessment of Precarious Employment Trajectories' -- which
-- is row 114805's article, not 88020's.
--
-- 88020 is 'The effect of government grants on private giving to East Asian
-- nonprofits'. Its real DOI is 10.18060/23464 -- but that is ALREADY held,
-- correctly, by row 101505, which is the same article. So 88020 is a duplicate
-- row that additionally holds someone else's identifier.
--
-- It is therefore nulled rather than reassigned: giving it 10.18060/23464 would
-- violate the unique index on doi, and inventing a different value would be
-- worse than leaving it empty. The duplicate row itself belongs to issue #3.
--
-- Order matters: 88020 must release 10.18060/23600 before 114805 can take it.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f fix_88020_first.sql

begin;

-- 1. Release the DOI 88020 should never have held. Left null: the article's
--    real DOI is on row 101505, and this row is a duplicate (issue #3).
update swrd.papers
   set doi = null
 where id = 88020
   and doi = '10.18060/23600';

-- 2. 114805 can now take the DOI that is actually its own.
update swrd.papers
   set doi = '10.18060/23600'
 where id = 114805
   and doi = 'dc/8492984d69';

do $$
declare a text; b text;
begin
  select doi into a from swrd.papers where id = 88020;
  select doi into b from swrd.papers where id = 114805;
  if a is not null or b <> '10.18060/23600' then
    raise exception 'unexpected end state: 88020=%, 114805=%', coalesce(a,'null'), b;
  end if;
  raise notice '88020 -> null (duplicate of 101505); 114805 -> %', b;
end $$;

commit;
