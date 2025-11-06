#!/usr/bin/env python3
"""
Clean CSV files to remove rows that violate database constraints.
This script will modify the CSV files in place (creates backups first).
"""

import csv
import os
from datetime import datetime
from typing import List, Dict

# Current date for validation
CURRENT_DATE = datetime(2025, 10, 13).date()

def backup_file(filepath: str) -> None:
    """Create a backup of the original file."""
    backup_path = filepath + '.backup'
    if os.path.exists(filepath):
        with open(filepath, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        print(f"✅ Backup created: {backup_path}")

def clean_property_csv(filepath: str) -> None:
    """Clean property.csv by removing rows with invalid constraints."""
    print("\n" + "="*70)
    print("CLEANING property.csv")
    print("="*70)
    
    backup_file(filepath)
    
    valid_rows = []
    invalid_count = 0
    reasons = {
        'invalid_gross_sqft': 0,
        'invalid_land_sqft': 0,
        'invalid_year_built': 0,
        'missing_required': 0
    }
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        for row in reader:
            is_valid = True
            
            # Check required fields
            if not row['property_id'] or not row['geographic_id'] or not row['property_address']:
                reasons['missing_required'] += 1
                is_valid = False
                continue
            
            # Check gross_sqft > 0 (if not empty)
            if row['gross_sqft'].strip():
                try:
                    gross_sqft = float(row['gross_sqft'])
                    if gross_sqft <= 0:
                        reasons['invalid_gross_sqft'] += 1
                        is_valid = False
                except ValueError:
                    reasons['invalid_gross_sqft'] += 1
                    is_valid = False
            
            # Check land_sqft > 0 (if not empty)
            if row['land_sqft'].strip():
                try:
                    land_sqft = float(row['land_sqft'])
                    if land_sqft <= 0:
                        reasons['invalid_land_sqft'] += 1
                        is_valid = False
                except ValueError:
                    reasons['invalid_land_sqft'] += 1
                    is_valid = False
            
            # Check year_built between 1700 and 2025 (if not empty)
            if row['year_built'].strip():
                try:
                    year_built = int(row['year_built'])
                    if year_built < 1700 or year_built > 2025:
                        reasons['invalid_year_built'] += 1
                        is_valid = False
                except ValueError:
                    # Non-numeric year (like "RES", "COM-A", etc.)
                    reasons['invalid_year_built'] += 1
                    is_valid = False
            
            # Check residential_units >= 0 (if not empty)
            if row['residential_units'].strip():
                try:
                    res_units = int(row['residential_units'])
                    if res_units < 0:
                        is_valid = False
                except ValueError:
                    is_valid = False
            
            # Check commercial_units >= 0 (if not empty)
            if row['commercial_units'].strip():
                try:
                    com_units = int(row['commercial_units'])
                    if com_units < 0:
                        is_valid = False
                except ValueError:
                    is_valid = False
            
            if is_valid:
                valid_rows.append(row)
            else:
                invalid_count += 1
    
    # Write cleaned data
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(valid_rows)
    
    print(f"✅ Original rows: {len(valid_rows) + invalid_count}")
    print(f"✅ Valid rows: {len(valid_rows)}")
    print(f"❌ Removed rows: {invalid_count}")
    print(f"\nBreakdown of removed rows:")
    print(f"  - Invalid gross_sqft: {reasons['invalid_gross_sqft']}")
    print(f"  - Invalid land_sqft: {reasons['invalid_land_sqft']}")
    print(f"  - Invalid year_built: {reasons['invalid_year_built']}")
    print(f"  - Missing required fields: {reasons['missing_required']}")

def clean_sale_csv(filepath: str) -> None:
    """Clean sale.csv by removing rows with invalid constraints."""
    print("\n" + "="*70)
    print("CLEANING sale.csv")
    print("="*70)
    
    backup_file(filepath)
    
    valid_rows = []
    invalid_count = 0
    reasons = {
        'invalid_price': 0,
        'future_date': 0,
        'missing_required': 0
    }
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        for row in reader:
            is_valid = True
            
            # Check required fields
            if not row['sale_id'] or not row['property_id'] or not row['sale_price'] or not row['sale_date']:
                reasons['missing_required'] += 1
                is_valid = False
                continue
            
            # Check sale_price > 0
            try:
                sale_price = float(row['sale_price'])
                if sale_price <= 0:
                    reasons['invalid_price'] += 1
                    is_valid = False
            except ValueError:
                reasons['invalid_price'] += 1
                is_valid = False
            
            # Check sale_date <= current_date
            try:
                sale_date = datetime.strptime(row['sale_date'], '%Y-%m-%d').date()
                if sale_date > CURRENT_DATE:
                    reasons['future_date'] += 1
                    is_valid = False
            except ValueError:
                reasons['future_date'] += 1
                is_valid = False
            
            if is_valid:
                valid_rows.append(row)
            else:
                invalid_count += 1
    
    # Write cleaned data
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(valid_rows)
    
    print(f"✅ Original rows: {len(valid_rows) + invalid_count}")
    print(f"✅ Valid rows: {len(valid_rows)}")
    print(f"❌ Removed rows: {invalid_count}")
    print(f"\nBreakdown of removed rows:")
    print(f"  - Invalid sale_price (≤ 0): {reasons['invalid_price']}")
    print(f"  - Future sale_date: {reasons['future_date']}")
    print(f"  - Missing required fields: {reasons['missing_required']}")

def clean_service_request_csv(filepath: str) -> None:
    """Clean service_request.csv by removing rows with invalid constraints."""
    print("\n" + "="*70)
    print("CLEANING service_request.csv")
    print("="*70)
    
    backup_file(filepath)
    
    valid_rows = []
    invalid_count = 0
    reasons = {
        'future_created_date': 0,
        'future_closed_date': 0,
        'closed_before_created': 0,
        'invalid_status': 0,
        'missing_required': 0
    }
    
    valid_statuses = {'Open', 'Pending', 'In Progress', 'Closed', 'Cancelled'}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        for row in reader:
            is_valid = True
            
            # Check required fields
            if not row['service_request_id'] or not row['geographic_id'] or not row['agency_code'] or not row['created_date'] or not row['status']:
                reasons['missing_required'] += 1
                is_valid = False
                continue
            
            # Check status is valid
            if row['status'] not in valid_statuses:
                reasons['invalid_status'] += 1
                is_valid = False
                continue
            
            # Check created_date <= current_date
            try:
                created_date = datetime.strptime(row['created_date'], '%Y-%m-%d').date()
                if created_date > CURRENT_DATE:
                    reasons['future_created_date'] += 1
                    is_valid = False
            except ValueError:
                reasons['future_created_date'] += 1
                is_valid = False
            
            # Check closed_date <= current_date (if not empty)
            if row['closed_date'].strip():
                try:
                    closed_date = datetime.strptime(row['closed_date'], '%Y-%m-%d').date()
                    if closed_date > CURRENT_DATE:
                        reasons['future_closed_date'] += 1
                        is_valid = False
                    
                    # Check closed_date >= created_date
                    if is_valid and closed_date < created_date:
                        reasons['closed_before_created'] += 1
                        is_valid = False
                except ValueError:
                    reasons['future_closed_date'] += 1
                    is_valid = False
            
            if is_valid:
                valid_rows.append(row)
            else:
                invalid_count += 1
    
    # Write cleaned data
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(valid_rows)
    
    print(f"✅ Original rows: {len(valid_rows) + invalid_count}")
    print(f"✅ Valid rows: {len(valid_rows)}")
    print(f"❌ Removed rows: {invalid_count}")
    print(f"\nBreakdown of removed rows:")
    print(f"  - Future created_date: {reasons['future_created_date']}")
    print(f"  - Future closed_date: {reasons['future_closed_date']}")
    print(f"  - Closed before created: {reasons['closed_before_created']}")
    print(f"  - Invalid status: {reasons['invalid_status']}")
    print(f"  - Missing required fields: {reasons['missing_required']}")

def main():
    """Main function to clean all CSV files."""
    base_dir = "/Users/jasmineyen/Downloads"
    
    print("="*70)
    print("CSV CLEANING SCRIPT")
    print("="*70)
    print(f"Working directory: {base_dir}")
    print(f"Current date for validation: {CURRENT_DATE}")
    print("\nThis script will:")
    print("  1. Create .backup files for all CSVs")
    print("  2. Remove rows that violate database constraints")
    print("  3. Overwrite the original CSV files with clean data")
    print("="*70)
    
    input("\nPress Enter to continue...")
    
    # Clean files that have constraint violations
    files_to_clean = [
        ('property.csv', clean_property_csv),
        ('sale.csv', clean_sale_csv),
        ('service_request.csv', clean_service_request_csv),
    ]
    
    for filename, clean_func in files_to_clean:
        filepath = os.path.join(base_dir, filename)
        if os.path.exists(filepath):
            clean_func(filepath)
        else:
            print(f"\n⚠️  WARNING: {filename} not found at {filepath}")
    
    # Check files that should be OK (just report)
    print("\n" + "="*70)
    print("CHECKING OTHER CSV FILES (should be OK)")
    print("="*70)
    
    ok_files = ['agency.csv', 'resolution.csv', 'geographic_area.csv']
    for filename in ok_files:
        filepath = os.path.join(base_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                row_count = sum(1 for row in reader) - 1  # Exclude header
            print(f"✅ {filename}: {row_count} rows (no cleaning needed)")
        else:
            print(f"⚠️  {filename}: NOT FOUND")
    
    print("\n" + "="*70)
    print("CLEANING COMPLETE!")
    print("="*70)
    print("\n✅ Your CSV files are now ready for database import!")
    print("✅ Original files have been backed up with .backup extension")
    print("\nNext steps:")
    print("  1. Upload cleaned CSV files to /home/ly2665/")
    print("  2. Run your schema: psql -f schema1.sql")
    print("  3. Import data: \\COPY <table> FROM '/home/ly2665/<file>.csv' WITH CSV HEADER;")

if __name__ == "__main__":
    main()
