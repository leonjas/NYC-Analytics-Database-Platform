-- ============================================================================
-- THREE INTERESTING QUERIES FOR NYC PROPERTY AND SERVICE REQUEST DATABASE
-- ============================================================================
-- Author: Database Project Part 2
-- Date: October 13, 2025
-- Features: Multi-table joins, aggregation, WHERE-clause conditions
-- ============================================================================

-- ============================================================================
-- QUERY 1: Average Property Sale Price by Borough
-- ============================================================================
-- Description: Calculate the average sale price and number of sales for each 
-- borough in 2024. Uses multi-table JOIN, aggregation (AVG, COUNT), and 
-- WHERE clause filtering.
-- ============================================================================

SELECT 
    ga.borough_code,
    COUNT(s.sale_id) AS total_sales,
    AVG(s.sale_price) AS avg_sale_price,
    MIN(s.sale_price) AS min_sale_price,
    MAX(s.sale_price) AS max_sale_price
FROM 
    Sale s
    JOIN Property p ON s.property_id = p.property_id
    JOIN Geographic_Area ga ON p.geographic_id = ga.geographic_id
WHERE 
    s.sale_date >= '2024-01-01' 
    AND s.sale_date <= '2024-12-31'
GROUP BY 
    ga.borough_code
ORDER BY 
    avg_sale_price DESC;


-- ============================================================================
-- QUERY 2: Service Request Count by Agency and Status
-- ============================================================================
-- Description: Count how many service requests each agency handles and break 
-- down by status (Open, Closed, etc.). Uses JOIN, aggregation (COUNT), 
-- GROUP BY, and WHERE clause.
-- ============================================================================

SELECT 
    a.agency_code,
    a.agency_name,
    sr.status,
    COUNT(*) AS request_count
FROM 
    Service_Request sr
    JOIN Agency a ON sr.agency_code = a.agency_code
WHERE 
    sr.created_date >= '2024-01-01'
GROUP BY 
    a.agency_code, a.agency_name, sr.status
ORDER BY 
    a.agency_code, request_count DESC;


-- ============================================================================
-- QUERY 3: Properties with Multiple Sales in 2024
-- ============================================================================
-- Description: Find properties that were sold more than once in 2024, showing
-- property details and sale information. Uses multi-table JOIN, aggregation
-- (COUNT), HAVING clause, and WHERE conditions.
-- ============================================================================

SELECT 
    p.property_id,
    p.property_address,
    ga.borough_code,
    ga.block_code,
    ga.lot_code,
    COUNT(s.sale_id) AS number_of_sales,
    MIN(s.sale_price) AS first_sale_price,
    MAX(s.sale_price) AS last_sale_price
FROM 
    Property p
    JOIN Geographic_Area ga ON p.geographic_id = ga.geographic_id
    JOIN Sale s ON p.property_id = s.property_id
WHERE 
    s.sale_date >= '2024-01-01' 
    AND s.sale_date <= '2024-12-31'
GROUP BY 
    p.property_id, p.property_address, ga.borough_code, ga.block_code, ga.lot_code
HAVING 
    COUNT(s.sale_id) > 1
ORDER BY 
    number_of_sales DESC, last_sale_price DESC;


-- ============================================================================
-- END OF QUERIES
-- ============================================================================

-- To run these queries, copy and paste them one at a time into your PostgreSQL
-- session, or run the entire file with:
-- \i /home/ly2665/interesting_queries.sql
