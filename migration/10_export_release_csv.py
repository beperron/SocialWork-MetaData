#!/usr/bin/env python3
"""Export versioned CSV data releases from the live database.

Usage:
    python migration/10_export_release_csv.py v1.1

Reads the direct Postgres connection string from .env (TGT=...), exports the
same file sets as data release v1.0 (schemas unchanged), writes a versioned
README.txt into each archive, and produces:

    dist/swrd-database-csv-<version>.zip
    dist/sswr-database-csv-<version>.zip

Then publish with:
    gh release create data-<version> dist/*.zip \
        --title "Data Release <version> — <Month Year>" --notes-file <notes.md>

and update the version badge on index.html, the README "Current data release"
line, and docs/DATA_CHANGELOG.md.
"""
import csv, datetime, io, os, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# ---------------------------------------------------------------- queries
SWRD = {
    "swrd_articles": """
        select p.id, p.doi, p.title, p.abstract, p.publication_year,
               j.name as journal, p.document_type, p.open_access,
               p.volume, p.issue, p.pages, p.is_empirical, p.research_method
        from swrd.papers p join swrd.journals j on j.id = p.journal_id
        where p.publication_year >= 1989 and p.is_scientific and p.abstract is not null
        order by p.id""",
    "swrd_additional_records_1989-2025": """
        select p.id, p.doi, p.title, p.abstract, p.publication_year,
               j.name as journal, p.document_type,
               p.is_scientific, p.is_empirical, p.research_method
        from swrd.papers p join swrd.journals j on j.id = p.journal_id
        where p.publication_year >= 1989
          and not (p.is_scientific and p.abstract is not null)
        order by p.id""",
    "swrd_supplement_1920-1988": """
        select p.id, p.doi, p.title, p.abstract, p.publication_year,
               j.name as journal, p.document_type
        from swrd.papers p join swrd.journals j on j.id = p.journal_id
        where p.publication_year < 1989
        order by p.id""",
    "swrd_journals": "select id, name, publisher from swrd.journals order by id",
    "swrd_authors": "select id, name, orcid from swrd.authors order by id",
    "swrd_paper_authors": """
        select paper_id, author_id, position, is_corresponding
        from swrd.paper_authors order by paper_id, position""",
    "swrd_organizations": "select id, name from swrd.organizations order by id",
    "swrd_author_affiliations": """
        select paper_id, author_id, organization_id
        from swrd.author_affiliations order by paper_id, author_id""",
}

SSWR = {
    "sswr_presentations": """
        select id, year, title, abstract, format, methodology, author_count
        from sswr.papers order by id""",
    "sswr_authors": "select id, name, total_papers from sswr.authors order by id",
    "sswr_paper_authors": """
        select paper_id, author_id, name as name_as_printed, author_order,
               institution_normalized, position_normalized, country_normalized
        from sswr.paper_authors order by paper_id, author_order""",
}

# Row-count invariants checked at export time. Update alongside intentional
# data changes; a mismatch means the query or the data drifted unexpectedly.
EXPECTED = {"swrd_articles": 62602, "sswr_presentations": 23793, "sswr_authors": 21209}

README_SWRD = """The Social Work Research Database (SWRD) — CSV export {version}
Exported {date} · https://beperron.github.io/SocialWork-MetaData/

FILES
  swrd_articles.csv                     THE SWRD: {n_articles:,} research articles with
                                        abstracts, 1989-2025 — the corpus described
                                        in Perron, Victor, & Qi (2026).
  swrd_additional_records_1989-2025.csv Further records from the same journals
                                        and years lacking abstracts or classified
                                        non-scientific.
  swrd_supplement_1920-1988.csv         Historical records; substantially
                                        incomplete — treat counts as lower bounds.
  swrd_journals.csv                     The journal population list.
  swrd_authors.csv                      Author names AS PUBLISHED (not disambiguated).
  swrd_paper_authors.csv                Paper–author links with byline position.
  swrd_organizations.csv                Affiliation strings as reported.
  swrd_author_affiliations.csv          Paper–author–organization links.

JOINS: paper_authors.paper_id -> articles.id · paper_authors.author_id -> authors.id
       author_affiliations.organization_id -> organizations.id

NOT INCLUDED: semantic embeddings (regenerable; see the project page).

VERSION: {version}. Data are corrected and extended through numbered releases;
see https://github.com/beperron/SocialWork-MetaData/releases and
docs/DATA_CHANGELOG.md for what changed in each version.

CITE: Perron, B. E., Victor, B. G., & Qi, Z. (2026). Evolution of social work
knowledge production over 35 years. Research on Social Work Practice.
https://doi.org/10.1177/10497315261416833
"""

README_SSWR = """The SSWR Conference Database — CSV export {version}
Exported {date} · https://beperron.github.io/SocialWork-MetaData/

FILES
  sswr_presentations.csv   All {n_pres:,} presentations, every SSWR annual
                           conference 2005-2026, with full abstracts and
                           methodology labels.
  sswr_authors.csv         {n_auth:,} CANONICAL author identities (disambiguated
                           across years).
  sswr_paper_authors.csv   Authorship: name as printed, byline order,
                           normalized institution and country, plus the link
                           to the canonical author.

JOINS: paper_authors.paper_id -> presentations.id
       paper_authors.author_id -> authors.id

NOT INCLUDED: semantic embeddings (regenerable; see the project page).

VERSION: {version}. Data are corrected and extended through numbered releases;
see https://github.com/beperron/SocialWork-MetaData/releases and
docs/DATA_CHANGELOG.md for what changed in each version.

CITE: Perron, B. E., Victor, B. G., & Qi, Z. (2026). AI-assisted curation of
conference scholarship. arXiv. https://doi.org/10.48550/arXiv.2603.06814
(in press, Journal of the Society for Social Work and Research)
"""


def read_tgt():
    for line in open(os.path.join(REPO, ".env")):
        if line.startswith("TGT="):
            return line.strip().split("=", 1)[1]
    sys.exit(".env has no TGT= connection string")


def export_csv(conn, name, query):
    q = " ".join(query.split())
    out = subprocess.run(
        ["psql", conn, "-v", "ON_ERROR_STOP=1", "-c",
         f"\\copy ({q}) to stdout with (format csv, header true)"],
        capture_output=True, text=True,
        env={**os.environ, "PGGSSENCMODE": "disable", "PGSSLMODE": "require"})
    if out.returncode != 0:
        sys.exit(f"{name}: psql failed:\n{out.stderr}")
    rows = out.stdout.count("\n") - 1
    if name in EXPECTED and rows != EXPECTED[name]:
        sys.exit(f"{name}: got {rows:,} rows, expected {EXPECTED[name]:,} — refusing to package")
    print(f"  {name}.csv  {rows:,} rows")
    return out.stdout, rows


def build(version):
    conn = read_tgt()
    date = datetime.date.today().isoformat()
    dist = os.path.join(REPO, "dist")
    os.makedirs(dist, exist_ok=True)
    for db, queries, readme_tpl in (("swrd", SWRD, README_SWRD), ("sswr", SSWR, README_SSWR)):
        zpath = os.path.join(dist, f"{db}-database-csv-{version}.zip")
        print(f"{db.upper()} -> {zpath}")
        counts = {}
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for name, query in queries.items():
                data, rows = export_csv(conn, name, query)
                counts[name] = rows
                z.writestr(f"{name}.csv", data)
            readme = readme_tpl.format(
                version=version, date=date,
                n_articles=counts.get("swrd_articles", 0),
                n_pres=counts.get("sswr_presentations", 0),
                n_auth=counts.get("sswr_authors", 0))
            z.writestr("README.txt", readme)
    print("\nDone. Publish with:")
    print(f'  gh release create data-{version} dist/*-{version}.zip '
          f'--title "Data Release {version} — {datetime.date.today():%B %Y}" --notes "..."')
    print("Then update: index.html version badge · README current-release line · docs/DATA_CHANGELOG.md")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].startswith("v"):
        sys.exit("usage: python migration/10_export_release_csv.py v1.1")
    build(sys.argv[1])
