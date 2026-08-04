-- Repair 44 corrupted author-name strings.
-- Mojibake decode, footnote digits, trailing commas, doubled spaces.
-- No linkage changes: paper_authors joins on author_id.
-- Each UPDATE matches on the CURRENT name, so the patch is idempotent and a
-- row that moved since generation is skipped rather than clobbered.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f fix_strings.sql

begin;

create schema if not exists swrd_archive;
create table if not exists swrd_archive.renamed_authors_v1_4 (
  author_id int not null, old_name text not null, new_name text not null,
  kind text not null, archived_at timestamptz not null default now());

insert into swrd_archive.renamed_authors_v1_4 (author_id, old_name, new_name, kind)
values
  (115215, 'Darlene  Chalmers', 'Darlene Chalmers', 'doubled_space'),
  (115228, 'Erinn  Barry', 'Erinn Barry', 'doubled_space'),
  (115233, 'Francisco J.  Lozornio', 'Francisco J. Lozornio', 'doubled_space'),
  (115276, 'Larry  Nackerud', 'Larry Nackerud', 'doubled_space'),
  (115322, 'Sarah R.  Bussey', 'Sarah R. Bussey', 'doubled_space'),
  (115326, 'Shannon  Vokes', 'Shannon Vokes', 'doubled_space'),
  (115352, 'Walter WAI TAK  Chan', 'Walter WAI TAK Chan', 'doubled_space'),
  (125590, 'Eybalin1, Dominique', 'Eybalin, Dominique', 'footnote_digit'),
  (125664, 'Labra1, Oscar', 'Labra, Oscar', 'footnote_digit'),
  (141120, 'Eybalin1, Dominique', 'Eybalin, Dominique', 'footnote_digit'),
  (141194, 'Labra1, Oscar', 'Labra, Oscar', 'footnote_digit'),
  (138906, 'Filip CoussÃ©e', 'Filip Coussée', 'mojibake'),
  (138921, 'VÃ©ronique Simon', 'Véronique Simon', 'mojibake'),
  (138944, 'ZoÃ« Clark', 'Zoë Clark', 'mojibake'),
  (139107, 'Vesna LeskoÅ¡ek', 'Vesna Leskošek', 'mojibake'),
  (139205, 'ZoÃ« Clark', 'Zoë Clark', 'mojibake'),
  (139249, 'Filip CoussÃ©e', 'Filip Coussée', 'mojibake'),
  (139347, 'Viktorija BarÅ¡auskiene', 'Viktorija Baršauskiene', 'mojibake'),
  (139439, 'MaÃ«l Dif-Pradalier', 'Maël Dif-Pradalier', 'mojibake'),
  (139625, 'Vesna LeskoÅ¡ek', 'Vesna Leskošek', 'mojibake'),
  (139988, 'RogÃ©rio Adolfo de Moura', 'Rogério Adolfo de Moura', 'mojibake'),
  (140379, 'Stefan MorÃ©n', 'Stefan Morén', 'mojibake'),
  (151101, 'Filip CoussÃ©e', 'Filip Coussée', 'mojibake'),
  (151116, 'VÃ©ronique Simon', 'Véronique Simon', 'mojibake'),
  (151138, 'ZoÃ« Clark', 'Zoë Clark', 'mojibake'),
  (151275, 'Vesna LeskoÅ¡ek', 'Vesna Leskošek', 'mojibake'),
  (151422, 'Viktorija BarÅ¡auskiene', 'Viktorija Baršauskiene', 'mojibake'),
  (151476, 'MaÃ«l Dif-Pradalier', 'Maël Dif-Pradalier', 'mojibake'),
  (151741, 'RogÃ©rio Adolfo de Moura', 'Rogério Adolfo de Moura', 'mojibake'),
  (151838, 'Stefan MorÃ©n', 'Stefan Morén', 'mojibake'),
  (158852, 'Filip CoussÃ©e', 'Filip Coussée', 'mojibake'),
  (158867, 'VÃ©ronique Simon', 'Véronique Simon', 'mojibake'),
  (158889, 'ZoÃ« Clark', 'Zoë Clark', 'mojibake'),
  (159026, 'Vesna LeskoÅ¡ek', 'Vesna Leskošek', 'mojibake'),
  (159173, 'Viktorija BarÅ¡auskiene', 'Viktorija Baršauskiene', 'mojibake'),
  (159227, 'MaÃ«l Dif-Pradalier', 'Maël Dif-Pradalier', 'mojibake'),
  (159492, 'RogÃ©rio Adolfo de Moura', 'Rogério Adolfo de Moura', 'mojibake'),
  (159589, 'Stefan MorÃ©n', 'Stefan Morén', 'mojibake'),
  (120566, 'Dietz, Tracy J,', 'Dietz, Tracy J', 'trailing_comma'),
  (127625, 'Chan, Wing-tai,', 'Chan, Wing-tai', 'trailing_comma'),
  (127633, 'Chan, Wing-tai,', 'Chan, Wing-tai', 'trailing_comma'),
  (143155, 'Chan, Wing-tai,', 'Chan, Wing-tai', 'trailing_comma'),
  (143163, 'Chan, Wing-tai,', 'Chan, Wing-tai', 'trailing_comma'),
  (164706, 'Earner,', 'Earner', 'trailing_comma');

do $$
declare live int;
begin
  select count(*) into live from swrd.authors a
    join swrd_archive.renamed_authors_v1_4 r
      on r.author_id = a.id and r.old_name = a.name;
  if live <> 44 then
    raise exception 'preflight: expected 44 rows carrying the old name, found %', live;
  end if;
end $$;

update swrd.authors set name = 'Darlene Chalmers' where id = 115215 and name = 'Darlene  Chalmers';
update swrd.authors set name = 'Erinn Barry' where id = 115228 and name = 'Erinn  Barry';
update swrd.authors set name = 'Francisco J. Lozornio' where id = 115233 and name = 'Francisco J.  Lozornio';
update swrd.authors set name = 'Larry Nackerud' where id = 115276 and name = 'Larry  Nackerud';
update swrd.authors set name = 'Sarah R. Bussey' where id = 115322 and name = 'Sarah R.  Bussey';
update swrd.authors set name = 'Shannon Vokes' where id = 115326 and name = 'Shannon  Vokes';
update swrd.authors set name = 'Walter WAI TAK Chan' where id = 115352 and name = 'Walter WAI TAK  Chan';
update swrd.authors set name = 'Eybalin, Dominique' where id = 125590 and name = 'Eybalin1, Dominique';
update swrd.authors set name = 'Labra, Oscar' where id = 125664 and name = 'Labra1, Oscar';
update swrd.authors set name = 'Eybalin, Dominique' where id = 141120 and name = 'Eybalin1, Dominique';
update swrd.authors set name = 'Labra, Oscar' where id = 141194 and name = 'Labra1, Oscar';
update swrd.authors set name = 'Filip Coussée' where id = 138906 and name = 'Filip CoussÃ©e';
update swrd.authors set name = 'Véronique Simon' where id = 138921 and name = 'VÃ©ronique Simon';
update swrd.authors set name = 'Zoë Clark' where id = 138944 and name = 'ZoÃ« Clark';
update swrd.authors set name = 'Vesna Leskošek' where id = 139107 and name = 'Vesna LeskoÅ¡ek';
update swrd.authors set name = 'Zoë Clark' where id = 139205 and name = 'ZoÃ« Clark';
update swrd.authors set name = 'Filip Coussée' where id = 139249 and name = 'Filip CoussÃ©e';
update swrd.authors set name = 'Viktorija Baršauskiene' where id = 139347 and name = 'Viktorija BarÅ¡auskiene';
update swrd.authors set name = 'Maël Dif-Pradalier' where id = 139439 and name = 'MaÃ«l Dif-Pradalier';
update swrd.authors set name = 'Vesna Leskošek' where id = 139625 and name = 'Vesna LeskoÅ¡ek';
update swrd.authors set name = 'Rogério Adolfo de Moura' where id = 139988 and name = 'RogÃ©rio Adolfo de Moura';
update swrd.authors set name = 'Stefan Morén' where id = 140379 and name = 'Stefan MorÃ©n';
update swrd.authors set name = 'Filip Coussée' where id = 151101 and name = 'Filip CoussÃ©e';
update swrd.authors set name = 'Véronique Simon' where id = 151116 and name = 'VÃ©ronique Simon';
update swrd.authors set name = 'Zoë Clark' where id = 151138 and name = 'ZoÃ« Clark';
update swrd.authors set name = 'Vesna Leskošek' where id = 151275 and name = 'Vesna LeskoÅ¡ek';
update swrd.authors set name = 'Viktorija Baršauskiene' where id = 151422 and name = 'Viktorija BarÅ¡auskiene';
update swrd.authors set name = 'Maël Dif-Pradalier' where id = 151476 and name = 'MaÃ«l Dif-Pradalier';
update swrd.authors set name = 'Rogério Adolfo de Moura' where id = 151741 and name = 'RogÃ©rio Adolfo de Moura';
update swrd.authors set name = 'Stefan Morén' where id = 151838 and name = 'Stefan MorÃ©n';
update swrd.authors set name = 'Filip Coussée' where id = 158852 and name = 'Filip CoussÃ©e';
update swrd.authors set name = 'Véronique Simon' where id = 158867 and name = 'VÃ©ronique Simon';
update swrd.authors set name = 'Zoë Clark' where id = 158889 and name = 'ZoÃ« Clark';
update swrd.authors set name = 'Vesna Leskošek' where id = 159026 and name = 'Vesna LeskoÅ¡ek';
update swrd.authors set name = 'Viktorija Baršauskiene' where id = 159173 and name = 'Viktorija BarÅ¡auskiene';
update swrd.authors set name = 'Maël Dif-Pradalier' where id = 159227 and name = 'MaÃ«l Dif-Pradalier';
update swrd.authors set name = 'Rogério Adolfo de Moura' where id = 159492 and name = 'RogÃ©rio Adolfo de Moura';
update swrd.authors set name = 'Stefan Morén' where id = 159589 and name = 'Stefan MorÃ©n';
update swrd.authors set name = 'Dietz, Tracy J' where id = 120566 and name = 'Dietz, Tracy J,';
update swrd.authors set name = 'Chan, Wing-tai' where id = 127625 and name = 'Chan, Wing-tai,';
update swrd.authors set name = 'Chan, Wing-tai' where id = 127633 and name = 'Chan, Wing-tai,';
update swrd.authors set name = 'Chan, Wing-tai' where id = 143155 and name = 'Chan, Wing-tai,';
update swrd.authors set name = 'Chan, Wing-tai' where id = 143163 and name = 'Chan, Wing-tai,';
update swrd.authors set name = 'Earner' where id = 164706 and name = 'Earner,';

do $$
declare done int;
begin
  select count(*) into done from swrd.authors a
    join swrd_archive.renamed_authors_v1_4 r
      on r.author_id = a.id and r.new_name = a.name;
  if done <> 44 then
    raise exception 'expected 44 rows renamed, found %', done;
  end if;
  raise notice 'repaired 44 author-name strings';
end $$;

commit;
