import time
from google.cloud import bigquery

# In-memory query caching
BQ_CACHE = {}  # Normalized SQL -> (timestamp, response_dict)
TRENDS_CACHE = {}  # (term, location) -> (timestamp, response_dict)
CACHE_TTL = 600  # 10 minutes in seconds

def query_bigquery(sql_query: str) -> dict:
    """Runs a read-only SQL query against the ACME media performance database.

    Use this tool to analyze historical metrics of ACME's media library,
    such as views, likes, shares, and sentiment scores of past podcast episodes.

    Args:
        sql_query: A valid BigQuery SELECT SQL query. Only SELECT queries are allowed.

    Returns:
        A dictionary containing the status and either query results or error details.
    """
    # Safety Check: only allow SELECT queries
    clean_query = sql_query.strip().lower()
    if not clean_query.startswith("select"):
        return {"status": "error", "message": "Only SELECT queries are allowed for safety and auditing reasons."}

    # Restrict to allowed tables/datasets
    if "delete" in clean_query or "drop" in clean_query or "insert" in clean_query or "update" in clean_query:
         return {"status": "error", "message": "Mutating queries are strictly prohibited."}

    # Normalize whitespace for consistent cache hits
    normalized_query = " ".join(clean_query.split())
    now = time.time()
    if normalized_query in BQ_CACHE:
        timestamp, cached_res = BQ_CACHE[normalized_query]
        if now - timestamp < CACHE_TTL:
            return cached_res

    client = bigquery.Client()
    try:
        query_job = client.query(sql_query)
        results = query_job.result()
        rows = [dict(row) for row in results]
        res = {"status": "success", "rows": rows}
        BQ_CACHE[normalized_query] = (now, res)
        return res
    except Exception as e:
        return {"status": "error", "message": str(e)}

NEIGHBOR_MAP = {
    "singapore": ["malaysia", "indonesia", "thailand", "philippines"],
    "malaysia": ["singapore", "indonesia", "thailand"],
    "vietnam": ["thailand", "philippines", "indonesia"],
    "thailand": ["malaysia", "vietnam", "indonesia"],
    "philippines": ["indonesia", "singapore", "malaysia"],
    "indonesia": ["singapore", "malaysia", "philippines"],
    "japan": ["south korea", "taiwan"],
    "south korea": ["japan", "taiwan"],
    "united kingdom": ["ireland", "france", "germany"],
    "germany": ["france", "netherlands", "austria", "switzerland"],
    "france": ["united kingdom", "germany", "belgium", "spain"],
}

def check_google_trends(term: str = None, location: str = None) -> dict:
    """Queries the Google Trends public dataset in BigQuery.

    Use this tool to either check the popularity of a specific keyword/term,
    or to fetch the overall top trending terms for a given location to discover popular topics.

    Args:
        term: Optional. The search term or keyword to check popularity for (e.g. 'artificial intelligence').
              If omitted, the overall top trending terms for the location will be returned.
        location: Optional. The location name to filter trends by (e.g., country name like 'United Kingdom', 
                  state name like 'California', or US DMA metro area like 'New York NY').

    Returns:
        A dictionary containing the trending status, rank, recent search scores, and location details.
    """
    cache_key = (term.lower() if term else None, location.lower() if location else None)
    now = time.time()
    if cache_key in TRENDS_CACHE:
        timestamp, cached_res = TRENDS_CACHE[cache_key]
        if now - timestamp < CACHE_TTL:
            return cached_res

    client = bigquery.Client()
    
    # Brainstorm search term synonyms to maximize top-25 Google Trends matching
    search_terms = []
    if term:
        t_clean = term.lower().strip()
        search_terms.append(t_clean)
        # Expand common synonyms/acronyms
        if t_clean in ["ai", "artificial intelligence"]:
            search_terms = ["ai", "artificial intelligence"]
        elif t_clean in ["climate change", "global warming", "climate"]:
            search_terms = ["climate change", "global warming", "climate"]

    def run_query(loc_val: str, query_type: str) -> list:
        # Build parameterized LIKE conditions dynamically
        term_conditions = " OR ".join([f"LOWER(term) LIKE @term_{i}" for i in range(len(search_terms))])
        
        if query_type == "international_term":
            query = f"""
                SELECT
                  term,
                  FORMAT_DATE('%Y-%m-%d', week) AS week,
                  CAST(LEAST(MAX(COALESCE(score, (26 - rank) * 4)), 100) AS INT64) AS score,
                  @location AS country_name,
                  '' AS region_name
                FROM `bigquery-public-data.google_trends.international_top_terms`
                WHERE ({term_conditions})
                  AND (LOWER(country_name) = @location OR LOWER(region_name) = @location)
                  AND week >= DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
                GROUP BY term, week
                ORDER BY week DESC
                LIMIT 12
            """
            params = [bigquery.ScalarQueryParameter("location", "STRING", loc_val.lower())]
            for i, t in enumerate(search_terms):
                params.append(bigquery.ScalarQueryParameter(f"term_{i}", "STRING", f"%{t}%"))

        elif query_type == "dma_term":
            query = f"""
                SELECT
                  term,
                  FORMAT_DATE('%Y-%m-%d', week) AS week,
                  CAST(LEAST(MAX(COALESCE(score, (26 - rank) * 4)), 100) AS INT64) AS score,
                  dma_name,
                  '' AS region_name
                FROM `bigquery-public-data.google_trends.top_terms`
                WHERE ({term_conditions})
                  AND LOWER(dma_name) LIKE @location
                  AND week >= DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
                GROUP BY term, week, dma_name
                ORDER BY week DESC
                LIMIT 12
            """
            params = [bigquery.ScalarQueryParameter("location", "STRING", f"%{loc_val.lower()}%")]
            for i, t in enumerate(search_terms):
                params.append(bigquery.ScalarQueryParameter(f"term_{i}", "STRING", f"%{t}%"))

        elif query_type == "international_top":
            query = """
                SELECT term, rank, score, week, country_name, region_name
                FROM `bigquery-public-data.google_trends.international_top_terms`
                WHERE (LOWER(country_name) = @location OR LOWER(region_name) = @location)
                ORDER BY week DESC, rank ASC
                LIMIT 5
            """
            params = [
                bigquery.ScalarQueryParameter("location", "STRING", loc_val.lower())
            ]
        elif query_type == "dma_top":
            query = """
                SELECT term, rank, score, week, dma_name
                FROM `bigquery-public-data.google_trends.top_terms`
                WHERE LOWER(dma_name) LIKE @location
                ORDER BY week DESC, rank ASC
                LIMIT 5
            """
            params = [
                bigquery.ScalarQueryParameter("location", "STRING", f"%{loc_val.lower()}%")
            ]
        elif query_type == "global_term":
            query = f"""
                WITH TopCountries AS (
                  SELECT country_name
                  FROM `bigquery-public-data.google_trends.international_top_terms`
                  WHERE ({term_conditions})
                    AND week >= DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
                  GROUP BY country_name
                  ORDER BY MAX(COALESCE(score, (26 - rank) * 4)) DESC
                  LIMIT 5
                )
                SELECT
                  MAX(t.term) AS term,
                  FORMAT_DATE('%Y-%m-%d', t.week) AS week,
                  CAST(LEAST(MAX(COALESCE(t.score, (26 - t.rank) * 4)), 100) AS INT64) AS score,
                  t.country_name,
                  '' AS region_name
                FROM `bigquery-public-data.google_trends.international_top_terms` t
                INNER JOIN TopCountries tc ON t.country_name = tc.country_name
                WHERE ({term_conditions})
                  AND t.week >= DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
                GROUP BY t.week, t.country_name
                ORDER BY t.week DESC, score DESC
                LIMIT 60
            """
            params = []
            for i, t in enumerate(search_terms):
                params.append(bigquery.ScalarQueryParameter(f"term_{i}", "STRING", f"%{t}%"))
        else: # global_top
            query = """
                SELECT term, rank, score, week, country_name, region_name
                FROM `bigquery-public-data.google_trends.international_top_terms`
                ORDER BY week DESC, rank ASC
                LIMIT 5
            """
            params = []
            
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        query_job = client.query(query, job_config=job_config)
        return [dict(row) for row in query_job.result()]

    try:
        rows = []
        queried_location = location
        is_fallback = False
        fallback_msg = None

        if location:
            q_types = ["international_term", "dma_term"] if term else ["international_top", "dma_top"]
            for qt in q_types:
                try:
                    rows = run_query(location, qt)
                    if rows:
                        break
                except Exception:
                    continue
            
            if not rows and location.lower() in NEIGHBOR_MAP:
                for neighbor in NEIGHBOR_MAP[location.lower()]:
                    for qt in q_types:
                        try:
                            rows = run_query(neighbor, qt)
                            if rows:
                                queried_location = neighbor
                                is_fallback = True
                                fallback_msg = f"No data found for '{location}'. Falling back to neighboring region '{neighbor}'."
                                break
                        except Exception:
                            continue
                    if rows:
                        break
        else:
            if not term:
                rows = run_query(None, "global_top")
            else:
                rows = run_query(None, "global_term")

        for row in rows:
            if 'week' in row and row['week'] is not None:
                row['week'] = str(row['week'])

        # Sort chronologically for frontend line charts
        if rows and any('week' in r for r in rows):
            rows = sorted(rows, key=lambda x: x.get('week', ''))

        if not rows:
            loc_msg = f" in '{location}'" if location else ""
            term_msg = f" for '{term}'" if term else " overall"
            res = {
                "status": "success",
                "message": f"No recent trend data found{term_msg}{loc_msg}.",
                "rows": []
            }
            TRENDS_CACHE[cache_key] = (now, res)
            return res
            
        res = {"status": "success", "rows": rows}
        if is_fallback:
            res["message"] = fallback_msg
            res["fallback_location"] = queried_location
        TRENDS_CACHE[cache_key] = (now, res)
        return res
    except Exception as e:
        return {"status": "error", "message": str(e)}
