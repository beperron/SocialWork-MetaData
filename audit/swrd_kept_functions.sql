CREATE OR REPLACE FUNCTION public.search_papers_by_embedding(query_embedding vector, match_limit integer DEFAULT 10, min_similarity double precision DEFAULT 0.0)
 RETURNS TABLE(paper_id integer, similarity double precision, title text, abstract text, publication_year integer, journal_name text)
 LANGUAGE plpgsql
AS $function$
BEGIN
    RETURN QUERY
    SELECT 
        p.id as paper_id,
        1 - (e.nomic_modernbert <=> query_embedding) as similarity,
        p.title,
        p.abstract,
        p.publication_year,
        j.name as journal_name
    FROM title_abstract_embeddings e
    INNER JOIN papers p ON e.paper_id = p.id
    LEFT JOIN journals j ON p.journal_id = j.id
    WHERE 1 - (e.nomic_modernbert <=> query_embedding) >= min_similarity
    ORDER BY similarity DESC  -- This should order by similarity descending!
    LIMIT match_limit;
END;
$function$
;
CREATE OR REPLACE FUNCTION public.search_papers_semantic(query_embedding vector, match_count integer DEFAULT 10, filter_abstracts boolean DEFAULT false)
 RETURNS TABLE(id integer, title text, abstract text, publication_year integer, times_cited integer, journal_id integer, journal_name text, similarity double precision)
 LANGUAGE plpgsql
AS $function$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.title,
        p.abstract,
        p.publication_year,
        p.times_cited,
        p.journal_id,
        j.name as journal_name,
        1 - (e.title_abstract_embedding <=> query_embedding) as similarity
    FROM title_abstract_embeddings e
    JOIN papers p ON e.paper_id = p.id
    LEFT JOIN journals j ON p.journal_id = j.id
    WHERE 
        CASE 
            WHEN filter_abstracts THEN p.abstract IS NOT NULL
            ELSE true
        END
    ORDER BY e.title_abstract_embedding <=> query_embedding
    LIMIT match_count;
END;
$function$
;
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$function$
;
