# COMS W4111 Project README

## 1. PostgreSQL Account Name

ly2665

## 2. Web Application URL

http://35.231.81.235:8111

## 3. Implementation

We implemented all features from the Part 1 proposal. First, users can enter an address with house number and street, select a borough from a dropdown menu, and optionally select a time window. One new feature during this process is that we integrated the NYC Geoclient API to convert NYC addresses into BBL (Borough-Block-Lot) identifiers. Users are then guided to an analytics dashboard presenting service request and property sale statistics for the specific BBL that the address belongs to. The statistics include the total number of service requests, the number of active requests, the total number of property sales, and sale price statistics (median, max, min). Additionally, the dashboard shows a pie chart visualizing service requests by complaint type, and time series line graphs displaying both service requests and property sales over the selected period.

Users can bookmark and compare BBLs of interest. The bookmark page displays all saved BBLs' service request and property sale statistics, and users can remove bookmarks as needed. In the compare page, the first address is pre-filled from the search page for convenience, and users can enter a second address to compare service request and property sale information. Users can also export CSV files, including service request by complaint type data and sale data.

   
## 4. Database Operations

### Analytics Page

The Analytics page displays comprehensive analytics dashboard including service request statistics and property sale statistics and visualizations for a specific BBL within a selected time period.


### Compare Page

The Compare page displays side-by-side comparison of service request and property sale statistics for two different BBLs.

Users follow the same input flow as the Analytics page, but enter two addresses instead of one. For each address, users enter a house number and street name, and select a borough. The date range is inherited from the first address. Each address is converted to a BBL via NYC Geoclient API. The BBL components (borough_code, block_code, lot_code) are used to query the Geographic_Area table to find the corresponding `geographic_id` for each property. These two `geo_id` values then filter both the Property/Sale tables and Service_Request table, and the same `start_date` and `end_date` parameters apply to both addresses. Results are displayed side-by-side showing total requests, complaint types with counts, active request counts, and sale price statistics.
