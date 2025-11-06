# COMS W4111 Project 1 Part 3 - README# NYC 311 Service Requests & Property Sales Web Application



## 1. PostgreSQL Account Information## Project Compliance

- **PostgreSQL Username:** ly2665✅ **Uses RAW SQL queries only** (no ORM functionality)  

- **Database Name:** proj1part2✅ **Provides access to all entities and relationships**:

- **Server:** 34.139.8.30:5432- Agency

- Resolution

## 2. Web Application URL- Geographic_Area

**[FILL IN YOUR VM IP ADDRESS HERE]**- Property

- Sale

Example: `http://YOUR_VM_IP:8111`- Service_Request



**Note:** The application runs on port 8111. Make sure your VM is running when submitting.## Setup Instructions



## 3. Implementation Status### 1. Update Database Credentials

Edit `server.py` lines 37-38 with your PostgreSQL credentials:

### Parts Implemented from Original Proposal:```python

- Property search by address (house number, street, borough)DATABASE_USERNAME = "your_username"  # Replace with your actual username

- Service request analytics for properties (311 complaints)DATABASE_PASSWRD = "your_password"   # Replace with your actual password

- Property sales history and trends```

- Time-based filtering (date range selection)

- Interactive charts for complaint types and trends over time### 2. Install Dependencies (Already Done)

- Bookmarking system for saving favorite propertiesThe required packages are already installed:

- Property comparison feature (side-by-side comparison)- flask

- BBL-based geographic area lookup using NYC Geoclient API- sqlalchemy

- Export functionality for sales and complaint data (CSV)- psycopg2-binary

- Median price calculations and gap-filled trend visualization

### 3. Run the Server

### Parts Not Implemented:```bash

**[IF ANY - Explain what was not implemented and why]**cd /Users/jasmineyen/Downloads/COMS4111_Project/webserver

- None - All proposed features were successfully implementedpython server.py

```

### Additional Features Implemented Beyond Proposal:

- Chart.js integration for pie charts showing complaint type distribution### 4. Access the Application

- Dynamic trend charts with gap-filling for months with no dataOpen your browser and go to: **http://localhost:8111**

- Session-based bookmarking (no login required)

- Responsive grid layouts for better user experience## Features

- Real-time BBL validation and address geocoding

- Median calculation for sales trends to handle outliers### Entity Views

- **Agencies** (`/agencies`) - View all agencies handling service requests

## 4. Two Most Interesting Database Operations- **Resolutions** (`/resolutions`) - View resolution descriptions

- **Geographic Areas** (`/geographic_areas`) - View BBL (Borough-Block-Lot) information

### Page 1: Analytics Dashboard (`/analytics/<bbl>`)- **Properties** (`/properties`) - View property details with links to individual pages

- **Sales** (`/sales`) - View recent property sales

**Purpose:**- **Service Requests** (`/service_requests`) - View 311 service requests

This page displays comprehensive analytics for a specific property identified by its BBL (Borough-Block-Lot number). Users can view service requests (311 complaints), property sales history, and trends over time with customizable date ranges.

### Relationship Views

**Database Operations:**- **Property Detail Page** (`/property/<id>`) - Shows property with its:

- Complex JOIN operations across multiple tables (service_request, complaint_type, complaint_descriptor, geographic_area, sale, property)  - Geographic Area relationship (BBL)

- Aggregation queries with GROUP BY to count complaint types  - All sales for that property (Property → Sale relationship)

- Date range filtering with BETWEEN clauses on created_date and sale_date  

- Subqueries to calculate median sale prices over time windows- **Service Request Detail Page** (`/service_request/<id>`) - Shows request with its:

- ORDER BY with LIMIT to show most recent transactions  - Agency relationship

  - Resolution relationship

**Input/Operation Flow:**  - Geographic Area relationship

1. User searches by address → NYC Geoclient API converts to BBL

2. BBL is parsed into borough_code, block_code, lot_code### Search Functionality

3. Multiple parallel queries execute:- Search properties by address

   - Get geographic area info (address, borough name, zip code)- Search service requests by complaint type

   - Count and group service requests by complaint type within date range

   - Retrieve recent property sales with date filtering## SQL Query Examples

   - Calculate monthly trends for both complaints and sales

4. Results are aggregated and rendered with Chart.js visualizationsAll routes use **raw SQL queries** with SQLAlchemy's `text()` function:



**Why Interesting:**```python

This operation is interesting because it combines spatial data (BBL geocoding), temporal filtering (date ranges), and multiple aggregation levels. The median calculation for sales trends is particularly clever - it handles outliers better than averages and requires window functions or creative subqueries. The page also demonstrates how to efficiently query multiple related entities without causing N+1 query problems.# Example: Listing properties with JOIN

query = """

**Sample Query (Complaint Type Aggregation):**    SELECT p.property_id, p.property_address, p.apartment_number, 

```sql           g.borough_code, g.block_code, g.lot_code

SELECT ct.type_name, COUNT(*) as count    FROM Property p

FROM service_request sr    JOIN Geographic_Area g ON p.geographic_id = g.geographic_id

JOIN complaint_type ct ON sr.complaint_type_id = ct.complaint_type_id    ORDER BY p.property_id

JOIN geographic_area ga ON sr.geographic_area_id = ga.geographic_area_id    LIMIT 100

WHERE ga.borough_code = :borough """

  AND ga.block_code = :block cursor = g.conn.execute(text(query))

  AND ga.lot_code = :lot```

  AND sr.created_date BETWEEN :start_date AND :end_date

GROUP BY ct.type_name```python

ORDER BY count DESC# Example: Search with parameters

```query = """

    SELECT property_id, property_address

### Page 2: Property Comparison (`/compare`)    FROM Property

    WHERE LOWER(property_address) LIKE LOWER(:term)

**Purpose:**    LIMIT 50

This page allows users to compare two properties side-by-side, viewing their complaint statistics, sales history, and geographic information simultaneously. Users can pre-fill one address from the analytics page or enter both manually."""

cursor = g.conn.execute(text(query), {'term': f'%{search_term}%'})

**Database Operations:**```

- Parallel execution of identical query patterns for two different BBLs

- Aggregation of complaint counts and types for each property## Technical Notes

- Retrieval of sales history with price statistics (min, max, median)

- Geographic area lookups with address normalization- **No ORM used**: All database interactions use raw SQL strings

- Statistical comparisons (total complaints, sale counts, price ranges)- **Parameterized queries**: Used to prevent SQL injection

- **Connection management**: Flask's `before_request` and `teardown_request` handle connections

**Input/Operation Flow:**- **Simple HTML templates**: Plain, functional interface (as per project requirements)

1. User enters two addresses (or one is pre-filled from analytics page)

2. Both addresses are geocoded to BBLs via NYC Geoclient API## Database Schema

3. Identical database operations run in parallel for both properties:

   - Get property and geographic area detailsThe application works with the following tables:

   - Aggregate complaint types and counts- `Agency` (agency_code, agency_name)

   - Retrieve sales transactions- `Resolution` (resolution_id, description)

   - Calculate summary statistics- `Geographic_Area` (geographic_id, borough_code, block_code, lot_code)

4. Results are displayed in a two-column layout for easy comparison- `Property` (property_id, geographic_id, property_address, ...)

- `Sale` (sale_id, property_id, sale_price, sale_date)

**Why Interesting:**- `Service_Request` (service_request_id, geographic_id, resolution_id, agency_code, complaint_type, descriptor, ...)

This operation is interesting because it demonstrates query reusability and parallel data retrieval. The same complex query pattern (get_bbl_data function) is executed twice with different parameters, showing good code organization. It also highlights the importance of indexing - comparing two properties means doubling the database load, so efficient indexes on (borough_code, block_code, lot_code) are crucial. The side-by-side presentation makes it easy to spot patterns like "properties in the same neighborhood have similar complaint types" or "sales prices differ significantly despite proximity."

All relationships (foreign keys) are properly queried using SQL JOINs.

**Sample Query (Get BBL Summary Data):**
```sql
SELECT 
    ga.address,
    ga.borough_name,
    ga.zip_code,
    COUNT(DISTINCT sr.service_request_id) as total_complaints,
    COUNT(DISTINCT s.sale_id) as total_sales,
    MIN(s.sale_price) as min_price,
    MAX(s.sale_price) as max_price
FROM geographic_area ga
LEFT JOIN service_request sr ON ga.geographic_area_id = sr.geographic_area_id
LEFT JOIN sale s ON ga.geographic_area_id = s.geographic_area_id
WHERE ga.borough_code = :borough 
  AND ga.block_code = :block 
  AND ga.lot_code = :lot
GROUP BY ga.address, ga.borough_name, ga.zip_code
```

## 5. Additional Notes
- The application uses SQLAlchemy as a database driver (NOT as an ORM)
- All queries are written in raw SQL using the text() function
- NullPool is configured to handle the shared database environment
- Session-based bookmarking persists across page loads
- The application handles database connection failures gracefully during peak usage

---

**Submitted by:** [YOUR NAME]  
**Group:** [YOUR GROUP NUMBER]  
**Date:** November 5, 2025
