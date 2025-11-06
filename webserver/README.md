# COMS W4111 Project 1 Part 3 - README

## 1. PostgreSQL Account Name

ly2665

## 2. Web Application URL

http://35.231.81.235:8111

## 3. Implementation

We implemented all features from the Part 1 proposal. First, users can enter an address with house number and street, select a borough from a dropdown menu, and optionally select a time window. One new feature during this process is that we integrated the NYC Geoclient API to convert NYC addresses into BBL (Borough-Block-Lot) identifiers. Users are then guided to an analytics dashboard presenting service request and property sale statistics for the specific BBL that the address belongs to. The statistics include the total number of service requests, the number of active requests, the total number of property sales, and sale price statistics (median, max, min). Additionally, the dashboard shows a pie chart visualizing service requests by complaint type, and time series line graphs displaying both service requests and property sales over the selected period.

Users can bookmark and compare BBLs of interest. The bookmark page displays all saved BBLs' service request and property sale statistics, and users can remove bookmarks as needed. In the compare page, the first address is pre-filled from the search page for convenience, and users can enter a second address to compare service request and property sale information. Users can also export CSV files, including service request by complaint type data and sale data.

   
## 4. Interesting Database Operations

### Analytics Page

The Analytics page displays comprehensive analytics dashboard including service request statistics and property sale statistics and visualizations for a specific BBL within a selected time period.

### Operation 1: Property Sales Statistics

Users enter a house number and street name, select a borough, and optionally choose a date range with start_date and end_date fields on the search page. The NYC Geoclient API converts the address to BBL. The BBL components (borough_code, block_code, lot_code) are used to query the Geographic_Area table to find the corresponding `geographic_id`. This `geo_id` then filters properties in the Property table through a JOIN with the Sale table, and `start_date` and `end_date` parameters filter sales by transaction date.

This query is interesting because it calculates median, minimum, and maximum sale prices using a JOIN between the Sale and Property tables. The Property table connects to Geographic_Area via `geographic_id`, which links sales transactions to specific geographic locations. The query demonstrates date filtering where users can analyze different time periods.

**Query:**
```sql
SELECT 
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY s.sale_price) as median_price,
    MIN(s.sale_price) as min_price,
    MAX(s.sale_price) as max_price
FROM Sale s
JOIN Property p ON s.property_id = p.property_id
WHERE p.geographic_id = :geo_id 
  AND s.sale_date >= :start_date 
  AND s.sale_date <= :end_date
```


### Operation 2: Service Request by Complaint Type

Users follow the same input flow as Operation 1 on the search page. The BBL components (borough_code, block_code, lot_code) are used to query the Geographic_Area table to find the corresponding `geographic_id`. This `geo_id` then filters the Service_Request table by location, and the `start_date` and `end_date` parameters filter by complaint creation date. Results are displayed as an ordered list showing complaint type names with counts and active counts.

This query is interesting because it uses GROUP BY to organize individual service requests into meaningful complaint type categories, and employs a JOIN with the Complaint_Type table to display complaint type names. It uses CASE WHEN to calculate active service requests with status Open, Pending, or In Progress, which is meaningful for identifying unresolved issues.

**Query:**
```sql
SELECT ct.complaint_type_name, 
       COUNT(*) as count,
       SUM(CASE WHEN sr.status IN ('Open', 'Pending', 'In Progress') 
           THEN 1 ELSE 0 END) as active_count
FROM Service_Request sr
JOIN Complaint_Type ct ON sr.complaint_type_id = ct.complaint_type_id
WHERE sr.geographic_id = :geo_id 
  AND created_date >= :start_date 
  AND created_date <= :end_date
GROUP BY ct.complaint_type_name
ORDER BY count DESC
```

The Analytics page is interesting because it combines many sophisticated database operations that work together to integrate service request data and property sale information in a single view. This integration is valuable because users previously had no platform to analyze both neighborhood service quality and real estate market trends for a specific BBL simultaneously.


### Compare Page

The Compare page displays side-by-side comparison of service request and property sale statistics for two different BBLs.

Users follow the same input flow as the Analytics page, but enter two addresses instead of one. For each address, users enter a house number and street name, and select a borough. The date range is inherited from the first address. Each address is converted to a BBL via NYC Geoclient API. The BBL components (borough_code, block_code, lot_code) are used to query the Geographic_Area table to find the corresponding `geographic_id` for each property. These two `geo_id` values then filter both the Property/Sale tables and Service_Request table, and the same `start_date` and `end_date` parameters apply to both addresses. Results are displayed side-by-side showing total requests, complaint types with counts, active request counts, and sale price statistics.

This page is interesting because it applies the two operations (Property Sales Statistics and Service Request by Complaint Type) twice in sequence. The same complex query pattern executes twice with different `geographic_id` parameters. The side-by-side presentation makes it meaningful for identifying neighborhood trends between two different BBLs.
