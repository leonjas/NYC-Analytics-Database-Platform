create table Agency (
    agency_code Varchar(10) Primary Key,
    agency_name Varchar(60) not null  
);

create table Resolution (
    resolution_id Integer Primary Key,
    description Varchar(600)  
);

create table Geographic_Area (
	geographic_id Bigint Primary Key,
    borough_name Varchar(20) not null,
    borough_code Integer not null,
    block_code Integer not null,
    lot_code Integer not null,
    UNIQUE (borough_code, block_code, lot_code)
);

create table Property (
    property_id Integer Primary Key,
    geographic_id Bigint not null References Geographic_Area,
    property_address Varchar(200) not null,
    apartment_number Varchar(20),
    year_built Integer,
    gross_sqft numeric(10, 2),
    land_sqft numeric(10, 2),
    residential_units Integer,
    commercial_units Integer,
    UNIQUE (property_address, apartment_number),
    Check (gross_sqft > 0),
    Check (land_sqft > 0),
    Check (residential_units >= 0),
    Check (commercial_units >= 0),
    Check (year_built between 1700 and extract(year from current_date))
);

create table Sale (
    sale_id Integer Primary Key,
    property_id Integer not null References Property,
    sale_price numeric(12, 2) not null,
    sale_date Date not null,
    Check (sale_price > 0),
    Check (sale_date <= current_date)
);

create table Complaint_Type (
    complaint_type_id Integer Primary Key,
    complaint_type_name Varchar(50) not null,
    UNIQUE (complaint_type_name)  
);

create table Complaint_Descriptor (
    descriptor_id Integer Primary Key,
    descriptor_name Varchar(100)
);

create table Service_Request (
    service_request_id Integer Primary Key,
    geographic_id Bigint not null References Geographic_Area on delete cascade,
    resolution_id Integer References Resolution on delete set null,
	agency_code Varchar(10) not null References Agency on delete cascade,
    complaint_type_id Integer not null References Complaint_Type on delete cascade,
    descriptor_id Integer References Complaint_Descriptor on delete set null,
    incident_address Varchar(200),
    created_date Date not null,
    closed_date Date,
    update_date Date,
    status Varchar(20) not null,
    Check (closed_date >= created_date),
    Check (created_date <= current_date),
    Check (closed_date <= current_date),
    Check (status IN ('Open', 'Pending', 'In Progress', 'Closed', 'Cancelled'))
);


