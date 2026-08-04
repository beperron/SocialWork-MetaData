-- Restore 99 surnames truncated at 8 characters by the legacy WoS
-- ingest (SCHUERMA.JR -> Schuerman, John R.). Each repair comes from the
-- author's OWN paper's Crossref record: family name extends the stem, every
-- initial agrees, exactly one candidate on the paper, and all of the row's
-- papers agree on the form. No linkage changes.
--
--   psql "$TGT" -v ON_ERROR_STOP=1 -f fix_truncated.sql

begin;

create schema if not exists swrd_archive;
create table if not exists swrd_archive.renamed_authors_v1_4 (
  author_id int not null, old_name text not null, new_name text not null,
  kind text not null, archived_at timestamptz not null default now());

insert into swrd_archive.renamed_authors_v1_4 (author_id, old_name, new_name, kind)
values
  (9183, 'LINGERFE.NB', 'Lingerfelt, Neverlyn B.', 'wos_truncated'),
  (9191, 'CHEVALIE.M', 'Chevalier, Millie', 'wos_truncated'),
  (9219, 'GETTLEMA.ME', 'Gettleman, Marvin E.', 'wos_truncated'),
  (9226, 'GOLDSMIT.J', 'Goldsmith, Jeff', 'wos_truncated'),
  (9229, 'GRONEWOL.DH', 'Gronewold, David H.', 'wos_truncated'),
  (9241, 'HOKENSTA.MC', 'Hokenstad, Merl C.', 'wos_truncated'),
  (9244, 'SCHUERMA.JR', 'Schuerman, John R.', 'wos_truncated'),
  (9256, 'KEITHLUC.A', 'Keith-Lucas, Alan', 'wos_truncated'),
  (9273, 'MANDELBA.A', 'Mandelbaum, Arthur', 'wos_truncated'),
  (9323, 'RABINOVI.H', 'Rabinovitz, Helene', 'wos_truncated'),
  (9324, 'RABINOWI.HN', 'Rabinowitz, Howard N.', 'wos_truncated'),
  (9331, 'ROSENBER.ML', 'Rosenberg, Marvin L.', 'wos_truncated'),
  (9332, 'ROSENFEL.HM', 'Rosenfeld, Herbert M.', 'wos_truncated'),
  (9340, 'ROSENFEL.JM', 'Rosenfeld, Jona M.', 'wos_truncated'),
  (9341, 'SCHREIBE.P', 'Schreiber, Paul', 'wos_truncated'),
  (9342, 'SCHREINE.K', 'Schreiner, Kathryn', 'wos_truncated'),
  (9347, 'SHNIDERM.CM', 'Shniderman, Craig M.', 'wos_truncated'),
  (9358, 'OFLAHERT.K', 'O''Flaherty, Kevin', 'wos_truncated'),
  (9369, 'PARSONAG.WH', 'Parsonage, William H.', 'wos_truncated'),
  (9386, 'SILVERMA.G', 'Silverman, Gerald', 'wos_truncated'),
  (9389, 'ALEXANDE.LB', 'Alexander, Leslie B.', 'wos_truncated'),
  (9392, 'AMBROSIN.S', 'Ambrosino, Salvatore', 'wos_truncated'),
  (9399, 'BROSKOWS.A', 'Broskowski, Anthony', 'wos_truncated'),
  (9400, 'BRANDWEI.R', 'Brandwein, Ruth', 'wos_truncated'),
  (9476, 'PIZZITOL.D', 'Pizzitola, Dee', 'wos_truncated'),
  (9481, 'GARFINKE.I', 'Garfinkel, Irwin', 'wos_truncated'),
  (9493, 'GREENWOO.E', 'Greenwood, Ernest', 'wos_truncated'),
  (9501, 'HALLOWIT.D', 'Hallowitz, David', 'wos_truncated'),
  (9503, 'HAMMERMA.J', 'Hammerman, Jerome', 'wos_truncated'),
  (9508, 'HASELKOR.F', 'Haselkorn, Florence', 'wos_truncated'),
  (9512, 'HENLLANJ.DA', 'Henllan-Jones, David A.', 'wos_truncated'),
  (9560, 'MCCARTNE.KH', 'McCartney, Kenneth H.', 'wos_truncated'),
  (9589, 'SLASINSK.JF', 'Slasinski, John F.', 'wos_truncated'),
  (9637, 'SILVERST.S', 'Silverstein, Sandra', 'wos_truncated'),
  (9659, 'WASSERMA.H', 'Wasserman, Harry', 'wos_truncated'),
  (9660, 'WASSERMA.WG', 'Wasserman, Wilma G.', 'wos_truncated'),
  (9667, 'WHITTAKE.JK', 'Whittaker, James K.', 'wos_truncated'),
  (9668, 'WHITTING.R', 'Whittington, Ronaele', 'wos_truncated'),
  (9674, 'WOODROOF.K', 'Woodroofe, Kathleen', 'wos_truncated'),
  (9680, 'ZIMBALIS.SE', 'Zimbalist, Sidney E.', 'wos_truncated'),
  (9695, 'STEINBUR.TW', 'Steinburn, Thomas W.', 'wos_truncated'),
  (9708, 'SHELLHAS.LJ', 'Shellhase, Leslie J.', 'wos_truncated'),
  (9818, 'KNICKMEY.R', 'Knickmeyer, Robert', 'wos_truncated'),
  (9850, 'MCCORMIC.MJ', 'McCormick, Mary J.', 'wos_truncated'),
  (9869, 'FELDSTEI.DM', 'Feldstein, David M.', 'wos_truncated'),
  (9910, 'LIEBERMA.D', 'Lieberman, Dina', 'wos_truncated'),
  (9921, 'SCHOTTLA.CI', 'Schottland, Charles I.', 'wos_truncated'),
  (9933, 'SILVERMA.PR', 'Silverman, Phyllis Rolfe', 'wos_truncated'),
  (9939, 'SOMERVIL.DB', 'Somerville, Dora B.', 'wos_truncated'),
  (9982, 'ZIMMERMA.JH', 'Zimmerman, Jerome H.', 'wos_truncated'),
  (10033, 'DIEDERIC.TA', 'Diederich, Thomas A.', 'wos_truncated'),
  (10053, 'GOLDMEIE.J', 'Goldmeier, John', 'wos_truncated'),
  (10066, 'HARDCAST.DA', 'Hardcastle, David A.', 'wos_truncated'),
  (10081, 'KILPATRI.DM', 'Kilpatrick, Dee Morgan', 'wos_truncated'),
  (10085, 'KRAHENBU.V', 'Krahenbuhl, Verena', 'wos_truncated'),
  (10142, 'ROMANYSH.JM', 'Romanyshyn, John M.', 'wos_truncated'),
  (10143, 'ROSENBLA.A', 'Rosenblatt, Aaron', 'wos_truncated'),
  (10203, 'WOODWORT.ME', 'Woodworth, Mary E.', 'wos_truncated'),
  (93405, 'KOMAROVS.M', 'Komarovsky, Mirra', 'wos_truncated'),
  (93406, 'MCCRACKE.JM', 'McCracken, James M.', 'wos_truncated'),
  (93458, 'STERNBAC.JC', 'Sternbach, Jack C.', 'wos_truncated'),
  (93508, 'SCHAEFFE.A', 'Schaeffer, Alice', 'wos_truncated'),
  (93549, 'HERTZBER.LJ', 'Hertzberg, Leonard J.', 'wos_truncated'),
  (93552, 'RODRIGUE.R', 'Rodriguez, Rodolfo', 'wos_truncated'),
  (93558, 'KRISTENS.A', 'Kristenson, Avis', 'wos_truncated'),
  (93562, 'BRAGINSK.BM', 'Braginsky, Benjamin M.', 'wos_truncated'),
  (93701, 'HASENFEL.Y', 'Hasenfeld, Yeheskel', 'wos_truncated'),
  (93707, 'RUSSELLL.SP', 'Russell-Lacy, Steven P.', 'wos_truncated'),
  (93709, 'ORFANIDI.MM', 'Orfanidis, Monica McGoldrick', 'wos_truncated'),
  (93711, 'BLOKSBER.LM', 'Bloksberg, Leonard M.', 'wos_truncated'),
  (93712, 'ROSENBER.C', 'Rosenberg, Charles', 'wos_truncated'),
  (93755, 'CALLICUT.JW', 'Callicutt, James W.', 'wos_truncated'),
  (93810, 'SHAINLIN.A', 'Shainline, Anne', 'wos_truncated'),
  (93816, 'ROTHENBE.E', 'Rothenberg, Elaine', 'wos_truncated'),
  (93821, 'HERNANDE.A', 'Hernandez, Ascension', 'wos_truncated'),
  (93861, 'ROSENFEL.E', 'Rosenfeld, Eva', 'wos_truncated'),
  (93917, 'WALDFOGE.D', 'Waldfogel, Diana', 'wos_truncated'),
  (93921, 'GIOVANNO.J', 'Giovannone, Jean', 'wos_truncated'),
  (93983, 'WESTHEIM.R', 'Westheimer, Ruth', 'wos_truncated'),
  (94041, 'BLACKBUR.CW', 'Blackburn, Clark W.', 'wos_truncated'),
  (94080, 'SCHROEDE.LO', 'Schroeder, Leila Obier', 'wos_truncated'),
  (94132, 'HOLMSTRU.E', 'Holmstrup, Elizabeth', 'wos_truncated'),
  (94190, 'AUSLANDE.H', 'Auslander, Helene', 'wos_truncated'),
  (94255, 'SCHEUNEM.YR', 'Scheunemann, Yolanda R.', 'wos_truncated'),
  (94364, 'BRECHENS.DM', 'Brechenser, Donn M.', 'wos_truncated'),
  (94428, 'LOEWENST.SF', 'Loewenstein, Sophie F.', 'wos_truncated'),
  (94430, 'GEANAKOP.E', 'Geanakoplos, Effie', 'wos_truncated'),
  (94544, 'HIRSCHLE.H', 'Hirschler, Helene', 'wos_truncated'),
  (94583, 'ROSENBLA.D', 'Rosenblatt, Daniel', 'wos_truncated'),
  (94585, 'FESTINGE.TB', 'Festinger, Trudy Bradley', 'wos_truncated'),
  (94589, 'LIVINGST.JB', 'Livingstone, John B.', 'wos_truncated'),
  (94646, 'PARKINSO.G', 'Parkinson, Geoffrey', 'wos_truncated'),
  (94649, 'VOGELFAN.M', 'Vogelfanger, Martin', 'wos_truncated'),
  (94651, 'BIRDWHIS.RL', 'Birdwhistell, Ray L.', 'wos_truncated'),
  (94788, 'WOJCIECH.S', 'Wojciechowski, Sophie', 'wos_truncated'),
  (94790, 'DAUGHERT.WK', 'Daugherty, W. Keith', 'wos_truncated'),
  (94830, 'NEUGEBOR.B', 'Neugeboren, Bernard', 'wos_truncated'),
  (94858, 'SCHNEIDE.J', 'Schneider, Jane', 'wos_truncated'),
  (94908, 'SONDHEIM.R', 'Sondheimer, Ruth', 'wos_truncated');

do $$
declare live int;
begin
  select count(*) into live from swrd.authors a
    join swrd_archive.renamed_authors_v1_4 r
      on r.author_id = a.id and r.old_name = a.name
   where r.kind = 'wos_truncated';
  if live <> 99 then
    raise exception 'preflight: expected 99 rows carrying the old name, found %', live;
  end if;
end $$;

update swrd.authors set name = 'Lingerfelt, Neverlyn B.' where id = 9183 and name = 'LINGERFE.NB';
update swrd.authors set name = 'Chevalier, Millie' where id = 9191 and name = 'CHEVALIE.M';
update swrd.authors set name = 'Gettleman, Marvin E.' where id = 9219 and name = 'GETTLEMA.ME';
update swrd.authors set name = 'Goldsmith, Jeff' where id = 9226 and name = 'GOLDSMIT.J';
update swrd.authors set name = 'Gronewold, David H.' where id = 9229 and name = 'GRONEWOL.DH';
update swrd.authors set name = 'Hokenstad, Merl C.' where id = 9241 and name = 'HOKENSTA.MC';
update swrd.authors set name = 'Schuerman, John R.' where id = 9244 and name = 'SCHUERMA.JR';
update swrd.authors set name = 'Keith-Lucas, Alan' where id = 9256 and name = 'KEITHLUC.A';
update swrd.authors set name = 'Mandelbaum, Arthur' where id = 9273 and name = 'MANDELBA.A';
update swrd.authors set name = 'Rabinovitz, Helene' where id = 9323 and name = 'RABINOVI.H';
update swrd.authors set name = 'Rabinowitz, Howard N.' where id = 9324 and name = 'RABINOWI.HN';
update swrd.authors set name = 'Rosenberg, Marvin L.' where id = 9331 and name = 'ROSENBER.ML';
update swrd.authors set name = 'Rosenfeld, Herbert M.' where id = 9332 and name = 'ROSENFEL.HM';
update swrd.authors set name = 'Rosenfeld, Jona M.' where id = 9340 and name = 'ROSENFEL.JM';
update swrd.authors set name = 'Schreiber, Paul' where id = 9341 and name = 'SCHREIBE.P';
update swrd.authors set name = 'Schreiner, Kathryn' where id = 9342 and name = 'SCHREINE.K';
update swrd.authors set name = 'Shniderman, Craig M.' where id = 9347 and name = 'SHNIDERM.CM';
update swrd.authors set name = 'O''Flaherty, Kevin' where id = 9358 and name = 'OFLAHERT.K';
update swrd.authors set name = 'Parsonage, William H.' where id = 9369 and name = 'PARSONAG.WH';
update swrd.authors set name = 'Silverman, Gerald' where id = 9386 and name = 'SILVERMA.G';
update swrd.authors set name = 'Alexander, Leslie B.' where id = 9389 and name = 'ALEXANDE.LB';
update swrd.authors set name = 'Ambrosino, Salvatore' where id = 9392 and name = 'AMBROSIN.S';
update swrd.authors set name = 'Broskowski, Anthony' where id = 9399 and name = 'BROSKOWS.A';
update swrd.authors set name = 'Brandwein, Ruth' where id = 9400 and name = 'BRANDWEI.R';
update swrd.authors set name = 'Pizzitola, Dee' where id = 9476 and name = 'PIZZITOL.D';
update swrd.authors set name = 'Garfinkel, Irwin' where id = 9481 and name = 'GARFINKE.I';
update swrd.authors set name = 'Greenwood, Ernest' where id = 9493 and name = 'GREENWOO.E';
update swrd.authors set name = 'Hallowitz, David' where id = 9501 and name = 'HALLOWIT.D';
update swrd.authors set name = 'Hammerman, Jerome' where id = 9503 and name = 'HAMMERMA.J';
update swrd.authors set name = 'Haselkorn, Florence' where id = 9508 and name = 'HASELKOR.F';
update swrd.authors set name = 'Henllan-Jones, David A.' where id = 9512 and name = 'HENLLANJ.DA';
update swrd.authors set name = 'McCartney, Kenneth H.' where id = 9560 and name = 'MCCARTNE.KH';
update swrd.authors set name = 'Slasinski, John F.' where id = 9589 and name = 'SLASINSK.JF';
update swrd.authors set name = 'Silverstein, Sandra' where id = 9637 and name = 'SILVERST.S';
update swrd.authors set name = 'Wasserman, Harry' where id = 9659 and name = 'WASSERMA.H';
update swrd.authors set name = 'Wasserman, Wilma G.' where id = 9660 and name = 'WASSERMA.WG';
update swrd.authors set name = 'Whittaker, James K.' where id = 9667 and name = 'WHITTAKE.JK';
update swrd.authors set name = 'Whittington, Ronaele' where id = 9668 and name = 'WHITTING.R';
update swrd.authors set name = 'Woodroofe, Kathleen' where id = 9674 and name = 'WOODROOF.K';
update swrd.authors set name = 'Zimbalist, Sidney E.' where id = 9680 and name = 'ZIMBALIS.SE';
update swrd.authors set name = 'Steinburn, Thomas W.' where id = 9695 and name = 'STEINBUR.TW';
update swrd.authors set name = 'Shellhase, Leslie J.' where id = 9708 and name = 'SHELLHAS.LJ';
update swrd.authors set name = 'Knickmeyer, Robert' where id = 9818 and name = 'KNICKMEY.R';
update swrd.authors set name = 'McCormick, Mary J.' where id = 9850 and name = 'MCCORMIC.MJ';
update swrd.authors set name = 'Feldstein, David M.' where id = 9869 and name = 'FELDSTEI.DM';
update swrd.authors set name = 'Lieberman, Dina' where id = 9910 and name = 'LIEBERMA.D';
update swrd.authors set name = 'Schottland, Charles I.' where id = 9921 and name = 'SCHOTTLA.CI';
update swrd.authors set name = 'Silverman, Phyllis Rolfe' where id = 9933 and name = 'SILVERMA.PR';
update swrd.authors set name = 'Somerville, Dora B.' where id = 9939 and name = 'SOMERVIL.DB';
update swrd.authors set name = 'Zimmerman, Jerome H.' where id = 9982 and name = 'ZIMMERMA.JH';
update swrd.authors set name = 'Diederich, Thomas A.' where id = 10033 and name = 'DIEDERIC.TA';
update swrd.authors set name = 'Goldmeier, John' where id = 10053 and name = 'GOLDMEIE.J';
update swrd.authors set name = 'Hardcastle, David A.' where id = 10066 and name = 'HARDCAST.DA';
update swrd.authors set name = 'Kilpatrick, Dee Morgan' where id = 10081 and name = 'KILPATRI.DM';
update swrd.authors set name = 'Krahenbuhl, Verena' where id = 10085 and name = 'KRAHENBU.V';
update swrd.authors set name = 'Romanyshyn, John M.' where id = 10142 and name = 'ROMANYSH.JM';
update swrd.authors set name = 'Rosenblatt, Aaron' where id = 10143 and name = 'ROSENBLA.A';
update swrd.authors set name = 'Woodworth, Mary E.' where id = 10203 and name = 'WOODWORT.ME';
update swrd.authors set name = 'Komarovsky, Mirra' where id = 93405 and name = 'KOMAROVS.M';
update swrd.authors set name = 'McCracken, James M.' where id = 93406 and name = 'MCCRACKE.JM';
update swrd.authors set name = 'Sternbach, Jack C.' where id = 93458 and name = 'STERNBAC.JC';
update swrd.authors set name = 'Schaeffer, Alice' where id = 93508 and name = 'SCHAEFFE.A';
update swrd.authors set name = 'Hertzberg, Leonard J.' where id = 93549 and name = 'HERTZBER.LJ';
update swrd.authors set name = 'Rodriguez, Rodolfo' where id = 93552 and name = 'RODRIGUE.R';
update swrd.authors set name = 'Kristenson, Avis' where id = 93558 and name = 'KRISTENS.A';
update swrd.authors set name = 'Braginsky, Benjamin M.' where id = 93562 and name = 'BRAGINSK.BM';
update swrd.authors set name = 'Hasenfeld, Yeheskel' where id = 93701 and name = 'HASENFEL.Y';
update swrd.authors set name = 'Russell-Lacy, Steven P.' where id = 93707 and name = 'RUSSELLL.SP';
update swrd.authors set name = 'Orfanidis, Monica McGoldrick' where id = 93709 and name = 'ORFANIDI.MM';
update swrd.authors set name = 'Bloksberg, Leonard M.' where id = 93711 and name = 'BLOKSBER.LM';
update swrd.authors set name = 'Rosenberg, Charles' where id = 93712 and name = 'ROSENBER.C';
update swrd.authors set name = 'Callicutt, James W.' where id = 93755 and name = 'CALLICUT.JW';
update swrd.authors set name = 'Shainline, Anne' where id = 93810 and name = 'SHAINLIN.A';
update swrd.authors set name = 'Rothenberg, Elaine' where id = 93816 and name = 'ROTHENBE.E';
update swrd.authors set name = 'Hernandez, Ascension' where id = 93821 and name = 'HERNANDE.A';
update swrd.authors set name = 'Rosenfeld, Eva' where id = 93861 and name = 'ROSENFEL.E';
update swrd.authors set name = 'Waldfogel, Diana' where id = 93917 and name = 'WALDFOGE.D';
update swrd.authors set name = 'Giovannone, Jean' where id = 93921 and name = 'GIOVANNO.J';
update swrd.authors set name = 'Westheimer, Ruth' where id = 93983 and name = 'WESTHEIM.R';
update swrd.authors set name = 'Blackburn, Clark W.' where id = 94041 and name = 'BLACKBUR.CW';
update swrd.authors set name = 'Schroeder, Leila Obier' where id = 94080 and name = 'SCHROEDE.LO';
update swrd.authors set name = 'Holmstrup, Elizabeth' where id = 94132 and name = 'HOLMSTRU.E';
update swrd.authors set name = 'Auslander, Helene' where id = 94190 and name = 'AUSLANDE.H';
update swrd.authors set name = 'Scheunemann, Yolanda R.' where id = 94255 and name = 'SCHEUNEM.YR';
update swrd.authors set name = 'Brechenser, Donn M.' where id = 94364 and name = 'BRECHENS.DM';
update swrd.authors set name = 'Loewenstein, Sophie F.' where id = 94428 and name = 'LOEWENST.SF';
update swrd.authors set name = 'Geanakoplos, Effie' where id = 94430 and name = 'GEANAKOP.E';
update swrd.authors set name = 'Hirschler, Helene' where id = 94544 and name = 'HIRSCHLE.H';
update swrd.authors set name = 'Rosenblatt, Daniel' where id = 94583 and name = 'ROSENBLA.D';
update swrd.authors set name = 'Festinger, Trudy Bradley' where id = 94585 and name = 'FESTINGE.TB';
update swrd.authors set name = 'Livingstone, John B.' where id = 94589 and name = 'LIVINGST.JB';
update swrd.authors set name = 'Parkinson, Geoffrey' where id = 94646 and name = 'PARKINSO.G';
update swrd.authors set name = 'Vogelfanger, Martin' where id = 94649 and name = 'VOGELFAN.M';
update swrd.authors set name = 'Birdwhistell, Ray L.' where id = 94651 and name = 'BIRDWHIS.RL';
update swrd.authors set name = 'Wojciechowski, Sophie' where id = 94788 and name = 'WOJCIECH.S';
update swrd.authors set name = 'Daugherty, W. Keith' where id = 94790 and name = 'DAUGHERT.WK';
update swrd.authors set name = 'Neugeboren, Bernard' where id = 94830 and name = 'NEUGEBOR.B';
update swrd.authors set name = 'Schneider, Jane' where id = 94858 and name = 'SCHNEIDE.J';
update swrd.authors set name = 'Sondheimer, Ruth' where id = 94908 and name = 'SONDHEIM.R';

do $$
declare done int;
begin
  select count(*) into done from swrd.authors a
    join swrd_archive.renamed_authors_v1_4 r
      on r.author_id = a.id and r.new_name = a.name
   where r.kind = 'wos_truncated';
  if done <> 99 then
    raise exception 'expected 99 rows renamed, found %', done;
  end if;
  raise notice 'restored 99 truncated surnames';
end $$;

commit;
