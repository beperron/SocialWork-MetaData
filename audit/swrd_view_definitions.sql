CREATE VIEW author_publication_stats AS 
 SELECT a.id,
    a.name,
    a.orcid,
    count(DISTINCT pa.paper_id) AS publication_count,
    count(DISTINCT
        CASE
            WHEN pa."position" = 1 THEN pa.paper_id
            ELSE NULL::integer
        END) AS first_author_count,
    count(DISTINCT
        CASE
            WHEN pa.is_corresponding THEN pa.paper_id
            ELSE NULL::integer
        END) AS corresponding_author_count
   FROM authors a
     LEFT JOIN paper_authors pa ON a.id = pa.author_id
  GROUP BY a.id, a.name, a.orcid;

CREATE VIEW database_summary AS 
 SELECT ( SELECT count(*) AS count
           FROM papers) AS total_papers,
    ( SELECT count(*) AS count
           FROM authors) AS total_authors,
    ( SELECT count(*) AS count
           FROM organizations) AS total_organizations,
    ( SELECT count(*) AS count
           FROM journals) AS total_journals,
    ( SELECT count(DISTINCT papers.doi) AS count
           FROM papers
          WHERE papers.doi IS NOT NULL) AS papers_with_doi,
    ( SELECT count(*) AS count
           FROM papers
          WHERE papers.data_source = 'WoS'::text) AS wos_papers,
    ( SELECT count(*) AS count
           FROM papers
          WHERE papers.data_source = 'Scopus'::text) AS scopus_papers,
    ( SELECT avg(papers.times_cited) AS avg
           FROM papers) AS avg_citations,
    ( SELECT max(papers.times_cited) AS max
           FROM papers) AS max_citations,
    ( SELECT min(papers.publication_year) AS min
           FROM papers
          WHERE papers.publication_year IS NOT NULL) AS earliest_year,
    ( SELECT max(papers.publication_year) AS max
           FROM papers
          WHERE papers.publication_year IS NOT NULL) AS latest_year;

CREATE VIEW highly_cited_papers AS 
 SELECT p.id,
    p.doi,
    p.title,
    p.abstract,
    p.publication_year,
    p.journal_id,
    p.times_cited,
    p.document_type,
    p.data_source,
    p.wos_uid,
    p.scopus_eid,
    p.open_access,
    p.volume,
    p.issue,
    p.pages,
    p.created_at,
    p.updated_at,
    j.name AS journal_name,
    string_agg(a.name, ', '::text ORDER BY pa."position") AS author_names
   FROM papers p
     LEFT JOIN journals j ON p.journal_id = j.id
     LEFT JOIN paper_authors pa ON p.id = pa.paper_id
     LEFT JOIN authors a ON pa.author_id = a.id
  WHERE p.times_cited > 50
  GROUP BY p.id, p.doi, p.title, p.abstract, p.publication_year, p.journal_id, p.times_cited, p.document_type, p.data_source, p.wos_uid, p.scopus_eid, p.open_access, p.volume, p.issue, p.pages, p.created_at, p.updated_at, j.name;

CREATE VIEW organization_collaborations AS 
 SELECT o1.id AS org1_id,
    o1.name AS org1_name,
    o2.id AS org2_id,
    o2.name AS org2_name,
    count(DISTINCT aa1.paper_id) AS collaboration_count
   FROM author_affiliations aa1
     JOIN author_affiliations aa2 ON aa1.paper_id = aa2.paper_id AND aa1.organization_id < aa2.organization_id
     JOIN organizations o1 ON aa1.organization_id = o1.id
     JOIN organizations o2 ON aa2.organization_id = o2.id
  GROUP BY o1.id, o1.name, o2.id, o2.name;

CREATE VIEW papers_with_journals AS 
 SELECT p.id,
    p.doi,
    p.title,
    p.abstract,
    p.publication_year,
    p.journal_id,
    p.times_cited,
    p.document_type,
    p.data_source,
    p.wos_uid,
    p.scopus_eid,
    p.open_access,
    p.volume,
    p.issue,
    p.pages,
    p.created_at,
    p.updated_at,
    j.name AS journal_name,
    j.publisher AS journal_publisher
   FROM papers p
     LEFT JOIN journals j ON p.journal_id = j.id;

CREATE VIEW publication_trends AS 
 SELECT papers.publication_year,
    count(*) AS paper_count,
    count(DISTINCT papers.journal_id) AS journal_count,
    count(DISTINCT
        CASE
            WHEN papers.data_source = 'WoS'::text THEN papers.id
            ELSE NULL::integer
        END) AS wos_count,
    count(DISTINCT
        CASE
            WHEN papers.data_source = 'Scopus'::text THEN papers.id
            ELSE NULL::integer
        END) AS scopus_count,
    avg(papers.times_cited) AS avg_citations,
    max(papers.times_cited) AS max_citations
   FROM papers
  WHERE papers.publication_year IS NOT NULL
  GROUP BY papers.publication_year
  ORDER BY papers.publication_year DESC;

