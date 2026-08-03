-- Reverse v1.2 using ONLY swrd_archive. Reads no file and no git object.
--
-- As written this ROLLS BACK: it is the proof, run after applying, that the
-- archive is sufficient on its own. To actually revert, change the final
-- 'rollback;' to 'commit;'.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f restore_from_archive_v1_2.sql
begin;

create temporary table _snap_pa on commit drop as select * from swrd.paper_authors;
create temporary table _snap_p  on commit drop as
  select id, journal_id from swrd.papers;

-- 1. undo the corresponding-author promotion
update swrd.paper_authors pa set is_corresponding = a.was_corresponding
  from swrd_archive.promoted_corresponding_v1_2 a
 where pa.paper_id = a.paper_id and pa.author_id = a.author_id;

-- 2. put the deleted credits back, created_at and all
insert into swrd.paper_authors (paper_id, author_id, "position", is_corresponding, created_at)
select paper_id, author_id, "position", is_corresponding, created_at
  from swrd_archive.removed_paper_authors_v1_2
on conflict do nothing;

-- 3. send the reassigned articles back to their original journal
update swrd.papers p set journal_id = a.from_journal_id
  from swrd_archive.reassigned_papers_v1_2 a
 where p.id = a.paper_id and p.journal_id = a.to_journal_id;

do $$
declare pa_now int; p_moved int;
begin
  select count(*) into pa_now from swrd.paper_authors;
  select count(*) into p_moved from swrd.papers p
    join swrd_archive.reassigned_papers_v1_2 a on a.paper_id = p.id
   where p.journal_id = a.from_journal_id;
  raise notice 'paper_authors now % (pre-fix was 241766)', pa_now;
  raise notice 'articles back in their original journal: % of 1194', p_moved;
  if pa_now <> 241766 then raise exception 'link count did not return to 241766'; end if;
  if p_moved <> 1194   then raise exception 'only % articles reverted', p_moved; end if;
  raise notice 'ARCHIVE ALONE FULLY REVERSES v1.2';
end $$;

rollback;
