
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
import requests  
import io
import csv
import json
from datetime import datetime, timedelta
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, abort, session, jsonify, make_response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = 'bookmark-secret-key'  


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@34.139.8.30/proj1part2
#
# For example, if you had username ab1234 and password 123123, then the following line would be:
#
#     DATABASEURI = "postgresql://ab1234:123123@34.139.8.30/proj1part2"
#
# Modify these with your own credentials you received from TA!
DATABASE_USERNAME = "ly2665" 
DATABASE_PASSWRD = "493592"   
DATABASE_HOST = "34.139.8.30"
DATABASEURI = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWRD}@{DATABASE_HOST}/proj1part2"

engine = create_engine(DATABASEURI)


@app.before_request
def before_request():
	"""
	This function is run at the beginning of every web request 
	(every time you enter an address in the web browser).
	We use it to setup a database connection that can be used throughout the request.

	The variable g is globally accessible.
	"""
	try:
		g.conn = engine.connect()
	except:
		print("uh oh, problem connecting to database")
		import traceback; traceback.print_exc()
		g.conn = None

@app.teardown_request
def teardown_request(exception):
	"""
	At the end of the web request, this makes sure to close the database connection.
	If you don't, the database could run out of memory!
	"""
	try:
		g.conn.close()
	except Exception as e:
		pass


def address_to_bbl_geoclient(house_number, street, borough):
	"""
	Convert NYC address to BBL using Geoclient API  
	Inputs:
	- house_number: Street number 
	- street: Street name 
	- borough: Borough name (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
	Returns BBL result or None if not found
	"""
	API_KEY = os.environ.get('NYC_GEOCLIENT_API_KEY', 'dfb4a2fde414449cb4f86b99552e34c6')
	url = "https://api.nyc.gov/geo/geoclient/v1/address.json"
	
	headers = {
		'Ocp-Apim-Subscription-Key': API_KEY
	}
	params = {
		'houseNumber': house_number,
		'street': street,
		'borough': borough
	}
	
	response = requests.get(url, headers=headers, params=params, timeout=5)
	if response.status_code != 200:
		return None
	
	data = response.json()
	resp = data.get('address', {})
	bbl_str = resp.get('bbl')
	
	if not bbl_str:
		return None
	
	borough_code = int(bbl_str[0])
	block_code = int(bbl_str[1:6])
	lot_code = int(bbl_str[6:10])
	
	return {
		'bbl': f"{borough_code}-{block_code}-{lot_code}",
		'borough_code': borough_code,
		'block_code': block_code,
		'lot_code': lot_code,
		'borough_name': resp.get('boroughName', ''),
		'address': f"{resp.get('houseNumber', '')} {resp.get('firstStreetNameNormalized', '')}".strip()
	}


def parse_bbl(bbl_string):
	try:
		borough, block, lot = bbl_string.split('-')
		return {
			'borough_code': int(borough),
			'block_code': int(block),
			'lot_code': int(lot)
		}
	except (ValueError, AttributeError):
		return None


def get_bbl_data(borough_code, block_code, lot_code, start_date=None, end_date=None):
	"""
	Get service requests and property sales summary for a specific BBL
	"""
	# Get geographic_id from BBL
	geo_query = """
		SELECT geographic_id, borough_name 
		FROM Geographic_Area 
		WHERE borough_code = :borough AND block_code = :block AND lot_code = :lot
	"""
	cursor = g.conn.execute(text(geo_query), {
		'borough': borough_code,
		'block': block_code,
		'lot': lot_code
	})
	geo_row = cursor.fetchone()
	cursor.close()
	
	if not geo_row:
		return None
	
	geographic_id = geo_row[0]
	borough_name = geo_row[1]
	bbl = f"{borough_code}-{block_code}-{lot_code}"
	
	# Date filtering
	date_filter_service_request = ""
	date_filter_sale = ""
	date_params = {'geo_id': geographic_id}
	
	if start_date:
		date_filter_service_request += " AND created_date >= :start_date"
		date_filter_sale += " AND s.sale_date >= :start_date"
		date_params['start_date'] = start_date
	if end_date:
		date_filter_service_request += " AND created_date <= :end_date"
		date_filter_sale += " AND s.sale_date <= :end_date"
		date_params['end_date'] = end_date
	
	# Total service requests 
	total_service_request_query = f"""
		SELECT COUNT(*), 
		       SUM(CASE WHEN status IN ('Open', 'Pending', 'In Progress') THEN 1 ELSE 0 END) as active
		FROM Service_Request 
		WHERE geographic_id = :geo_id {date_filter_service_request}
	"""
	cursor = g.conn.execute(text(total_service_request_query), date_params)
	sr_total_row = cursor.fetchone()
	cursor.close()
	total_requests = sr_total_row[0] if sr_total_row else 0
	total_active = sr_total_row[1] if sr_total_row else 0
	
	# Service Requests by Complaint Type 
	service_request_by_complaint_query = f"""
		SELECT ct.complaint_type_name, COUNT(*) as count,
		       SUM(CASE WHEN sr.status IN ('Open', 'Pending', 'In Progress') THEN 1 ELSE 0 END) as active_count
		FROM Service_Request sr
		JOIN Complaint_Type ct ON sr.complaint_type_id = ct.complaint_type_id
		WHERE sr.geographic_id = :geo_id {date_filter_service_request}
		GROUP BY ct.complaint_type_name
		ORDER BY count DESC
	"""
	cursor = g.conn.execute(text(service_request_by_complaint_query), date_params)
	complaint_types = []
	for row in cursor:
		complaint_types.append({
			'type': row[0],
			'count': row[1],
			'active_count': row[2]
		})
	cursor.close()
	
	# Property sale prices
	sales_query = f"""
		SELECT s.sale_price, s.sale_date, p.property_address
		FROM Sale s
		JOIN Property p ON s.property_id = p.property_id
		WHERE p.geographic_id = :geo_id {date_filter_sale}
		ORDER BY s.sale_date DESC
	"""
	cursor = g.conn.execute(text(sales_query), date_params)
	sales = []
	for row in cursor:
		sales.append({
			'price': float(row[0]),
			'date': row[1],
			'address': row[2]
		})
	cursor.close()
	
	# Sale price statistics 
	if sales:
		stats_query = f"""
			SELECT 
				PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY s.sale_price) as median_price,
				MIN(s.sale_price) as min_price,
				MAX(s.sale_price) as max_price
			FROM Sale s
			JOIN Property p ON s.property_id = p.property_id
			WHERE p.geographic_id = :geo_id {date_filter_sale}
		"""
		cursor = g.conn.execute(text(stats_query), date_params)
		stats_row = cursor.fetchone()
		cursor.close()
		median_price = float(stats_row[0])
		min_price = float(stats_row[1])
		max_price = float(stats_row[2])
	else:
		median_price = 0
		min_price = 0
		max_price = 0
	
	return {
		'bbl': bbl,
		'borough_name': borough_name,
		'borough_code': borough_code,
		'block_code': block_code,
		'lot_code': lot_code,
		'total_requests': total_requests,
		'total_active': total_active,
		'complaint_types': complaint_types,
		'sales': sales,
		'num_sales': len(sales),
		'median_sale_price': median_price,
		'min_sale_price': min_price,
		'max_sale_price': max_price
	}


def get_time_series_data(borough_code, block_code, lot_code, start_date, end_date, metric_type):
	"""
	Get time-series data (service_requests, sales) for trends view
	"""
	geo_query = """
		SELECT geographic_id FROM Geographic_Area 
		WHERE borough_code = :borough AND block_code = :block AND lot_code = :lot
	"""
	cursor = g.conn.execute(text(geo_query), {
		'borough': borough_code,
		'block': block_code,
		'lot': lot_code
	})
	geo_row = cursor.fetchone()
	cursor.close()
	
	if not geo_row:
		return []
	
	geographic_id = geo_row[0]
	
	# Time series for service requests or sales
	if metric_type == 'service_requests':
		query = """
			SELECT DATE_TRUNC('month', created_date) as month, COUNT(*) as count
			FROM Service_Request
			WHERE geographic_id = :geo_id 
			  AND created_date >= :start_date 
			  AND created_date <= :end_date
			GROUP BY DATE_TRUNC('month', created_date)
			ORDER BY month
		"""
	elif metric_type == 'sales':  
		query = """
			SELECT DATE_TRUNC('month', s.sale_date) as month, 
			       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY s.sale_price) as median_price,
			       COUNT(*) as count
			FROM Sale s
			JOIN Property p ON s.property_id = p.property_id
			WHERE p.geographic_id = :geo_id 
			  AND s.sale_date >= :start_date 
			  AND s.sale_date <= :end_date
			GROUP BY DATE_TRUNC('month', s.sale_date)
			ORDER BY month
		"""
	
	cursor = g.conn.execute(text(query), {
		'geo_id': geographic_id,
		'start_date': start_date,
		'end_date': end_date
	})
	
	data_by_month = {}
	for row in cursor:
		month = row[0].strftime('%Y-%m')
		if metric_type == 'service_requests':
			data_by_month[month] = row[1]
		elif metric_type == 'sales':
			data_by_month[month] = float(row[1])
	cursor.close()
	
	start = datetime.strptime(start_date, '%Y-%m-%d')
	end = datetime.strptime(end_date, '%Y-%m-%d')

	results = []
	current = start
	while current <= end:
		month = current.strftime('%Y-%m')
		if metric_type == 'service_requests':
			results.append({'month': month, 'count': data_by_month.get(month, 0)})
		elif metric_type == 'sales':
			median = data_by_month.get(month)
			results.append({'month': month, 'median_price': median, 'count': 1 if median else 0})
		
		if current.month == 12:
			current = current.replace(year=current.year + 1, month=1)
		else:
			current = current.replace(month=current.month + 1)
	
	return results



@app.route('/')
def index():
	"""
	request is a special object that Flask provides to access web request information:

	request.method:   "GET" or "POST"
	request.form:     if the browser submitted a form, this contains the data in the form
	request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

	See its API: https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data
	"""
	return render_template("index.html")


@app.route('/search', methods=['POST'])
def search():
	"""
	Search page - accepts house number, street name, and borough.
	Optional time window selection.
	"""
	house_number = request.form.get('house_number', '').strip()
	street = request.form.get('street', '').strip()
	borough = request.form.get('borough', '').strip()
	start_date = request.form.get('start_date', '')
	end_date = request.form.get('end_date', '')
	
	if not house_number or not street or not borough:
		abort(400, "Please enter house number, street name, and select borough")
	
	bbl_result = address_to_bbl_geoclient(house_number, street, borough)
	
	if not bbl_result:
		abort(404, f"No matching address found for: {house_number} {street}, {borough}")
	
	bbl = bbl_result['bbl']
	return redirect(f"/analytics/{bbl}?start_date={start_date}&end_date={end_date}")


@app.route('/analytics/<bbl>')
def analytics(bbl):
	"""
	Service requests and property sales dashboard with time filtering for a specific BBL
	"""
	bbl_parsed = parse_bbl(bbl)
	if not bbl_parsed:
		abort(400, "Invalid BBL format. Use format: borough-block-lot (e.g., 1-100-10)")
	
	start_date = request.args.get('start_date', '')
	end_date = request.args.get('end_date', '')
	
	if not end_date:
		end_date = '2024-12-31'
	if not start_date:
		start_date = '2024-01-01'
	
	data = get_bbl_data(
		bbl_parsed['borough_code'],
		bbl_parsed['block_code'],
		bbl_parsed['lot_code'],
		start_date,
		end_date
	)
	
	if not data:
		abort(404, f"BBL {bbl} not found in database")
	
	bookmarks = session.get('bookmarks', [])
	is_bookmarked = bbl in bookmarks
	
	complaint_types = data['complaint_types']
	if len(complaint_types) > 5:
		chart_data = complaint_types[:5]
		other_total = 0
		for ct in complaint_types[5:]:
			other_total += ct['count']
		chart_data.append({'type': 'Other', 'count': other_total})
	else:
		chart_data = complaint_types
	
	return render_template("analytics.html", 
	                      data=data,
	                      start_date=start_date,
	                      end_date=end_date,
	                      is_bookmarked=is_bookmarked,
	                      complaint_data=chart_data)


# Query parameters in GET requests
# Reference: https://flask.palletsprojects.com/en/2.3.x/quickstart/#accessing-request-data
@app.route('/compare', methods=['GET', 'POST'])
def compare():
	"""
	Side-by-side comparison of two addresses
	"""
	# Get bbl1 and dates from query params (from analytics page link)
	bbl1_param = request.args.get('bbl1', '') if request.method == 'GET' else None
	start_date_param = request.args.get('start_date', '')
	end_date_param = request.args.get('end_date', '')
	
	# Parse bbl1 to get address info if provided
	bbl1_info = None
	if bbl1_param:
		bbl1_parsed = parse_bbl(bbl1_param)
		if bbl1_parsed:
			data = get_bbl_data(
				bbl1_parsed['borough_code'],
				bbl1_parsed['block_code'],
				bbl1_parsed['lot_code']
			)
			if data:
				bbl1_info = {
					'bbl': bbl1_param,
					'borough_name': data['borough_name']
				}
	
	if request.method == 'POST':
		# Check if bbl1 was pre-filled
		bbl1_prefilled = request.form.get('bbl1_prefilled', '').strip()
		
		if bbl1_prefilled:
			# Use pre-filled BBL for address 1
			bbl1_parsed = parse_bbl(bbl1_prefilled)
			if not bbl1_parsed:
				return render_template("compare.html", 
				                      error="Invalid pre-filled BBL",
				                      bbl1_info=bbl1_info,
				                      start_date=start_date_param,
				                      end_date=end_date_param)
			
			# Only need address 2
			house_number2 = request.form.get('house_number2', '').strip()
			street2 = request.form.get('street2', '').strip()
			borough2 = request.form.get('borough2', '').strip()
			
			if not all([house_number2, street2, borough2]):
				return render_template("compare.html", 
				                      error="Please provide the second address",
				                      bbl1_info=bbl1_info,
				                      start_date=start_date_param,
				                      end_date=end_date_param)
			
			# Convert address 2 to BBL
			bbl_result2 = address_to_bbl_geoclient(house_number2, street2, borough2)
			if not bbl_result2:
				return render_template("compare.html", 
				                      error=f"Address 2 not found: {house_number2} {street2}, {borough2}",
				                      bbl1_info=bbl1_info,
				                      start_date=start_date_param,
				                      end_date=end_date_param)
			
			bbl2_parsed = parse_bbl(bbl_result2['bbl'])
		else:
			# Get both address inputs
			house_number1 = request.form.get('house_number1', '').strip()
			street1 = request.form.get('street1', '').strip()
			borough1 = request.form.get('borough1', '').strip()
			
			house_number2 = request.form.get('house_number2', '').strip()
			street2 = request.form.get('street2', '').strip()
			borough2 = request.form.get('borough2', '').strip()
			
			if not all([house_number1, street1, borough1, house_number2, street2, borough2]):
				return render_template("compare.html", 
				                      error="Please provide both complete addresses",
				                      bbl1_info=bbl1_info,
				                      start_date=start_date_param,
				                      end_date=end_date_param)
			
			# Convert addresses to BBLs
			bbl_result1 = address_to_bbl_geoclient(house_number1, street1, borough1)
			bbl_result2 = address_to_bbl_geoclient(house_number2, street2, borough2)
			
			if not bbl_result1:
				return render_template("compare.html", 
				                      error=f"Address 1 not found: {house_number1} {street1}, {borough1}",
				                      bbl1_info=bbl1_info,
				                      start_date=start_date_param,
				                      end_date=end_date_param)
			if not bbl_result2:
				return render_template("compare.html", 
				                      error=f"Address 2 not found: {house_number2} {street2}, {borough2}",
				                      bbl1_info=bbl1_info,
				                      start_date=start_date_param,
				                      end_date=end_date_param)
			
			bbl1_parsed = parse_bbl(bbl_result1['bbl'])
			bbl2_parsed = parse_bbl(bbl_result2['bbl'])
		
		# Use provided dates or defaults from params
		start_date = request.form.get('start_date', start_date_param)
		end_date = request.form.get('end_date', end_date_param)
	else:
		# GET request - show form with pre-filled bbl1 if provided
		return render_template("compare.html", 
		                      bbl1_info=bbl1_info,
		                      start_date=start_date_param,
		                      end_date=end_date_param)
	
	# Set default dates
	if not end_date:
		end_date = '2024-12-31'
	if not start_date:
		start_date = '2024-01-01'
	
	data1 = get_bbl_data(
		bbl1_parsed['borough_code'],
		bbl1_parsed['block_code'],
		bbl1_parsed['lot_code'],
		start_date,
		end_date
	)
	
	data2 = get_bbl_data(
		bbl2_parsed['borough_code'],
		bbl2_parsed['block_code'],
		bbl2_parsed['lot_code'],
		start_date,
		end_date
	)
	
	if not data1 or not data2:
		return render_template("compare.html", 
		                      error="One or both addresses not found in database",
		                      bbl1_info=bbl1_info,
		                      start_date=start_date,
		                      end_date=end_date)
	
	return render_template("compare.html",
	                      data1=data1,
	                      data2=data2,
	                      start_date=start_date,
	                      end_date=end_date)


@app.route('/trends/<bbl>')
def trends(bbl):
	"""
	Time-series trends view for a BBL
	Returns JSON data for charting
	
	FLASK REFERENCES:
	- URL variable extraction: https://flask.palletsprojects.com/en/2.3.x/quickstart/#variable-rules
	- Query parameters (request.args): https://flask.palletsprojects.com/en/2.3.x/quickstart/#the-request-object
	- JSON responses with jsonify(): https://flask.palletsprojects.com/en/2.3.x/quickstart/#apis-with-json
	- HTTP status codes: https://flask.palletsprojects.com/en/2.3.x/quickstart/#about-responses
	
	PATTERN: JSON API endpoint
	This route returns JSON data instead of HTML templates. Used by JavaScript
	fetch() calls on the frontend to dynamically load chart data.
	"""
	bbl_parsed = parse_bbl(bbl)
	if not bbl_parsed:
		# Reference: Return JSON error with HTTP 400 status
		# https://flask.palletsprojects.com/en/2.3.x/quickstart/#about-responses
		return jsonify({'error': 'Invalid BBL format'}), 400
	
	# Reference: request.args.get() for query parameters with defaults
	# https://flask.palletsprojects.com/en/2.3.x/api/#flask.Request.args
	metric_type = request.args.get('type', 'service_requests')
	start_date = request.args.get('start_date', '')
	end_date = request.args.get('end_date', '')
	
	if not end_date:
		end_date = datetime.now().strftime('%Y-%m-%d')
	if not start_date:
		start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
	
	data = get_time_series_data(
		bbl_parsed['borough_code'],
		bbl_parsed['block_code'],
		bbl_parsed['lot_code'],
		start_date,
		end_date,
		metric_type
	)
	
	# Reference: jsonify() converts Python dict to JSON response
	# https://flask.palletsprojects.com/en/2.3.x/api/#flask.json.jsonify
	return jsonify(data)


@app.route('/export/<bbl>')
def export_csv(bbl):
	"""
	Export analytics data as CSV
	
	FLASK REFERENCES:
	- URL variables: https://flask.palletsprojects.com/en/2.3.x/quickstart/#variable-rules
	- Query parameters: https://flask.palletsprojects.com/en/2.3.x/quickstart/#the-request-object
	- make_response() for custom responses: https://flask.palletsprojects.com/en/2.3.x/quickstart/#about-responses
	- Response headers: https://flask.palletsprojects.com/en/2.3.x/api/#flask.Response
	- abort() for error handling: https://flask.palletsprojects.com/en/2.3.x/quickstart/#redirects-and-errors
	
	PATTERN: CSV File Download
	This route generates a CSV file dynamically and sends it as a download.
	Uses make_response() with custom headers to trigger browser download.
	"""
	bbl_parsed = parse_bbl(bbl)
	if not bbl_parsed:
		# Reference: abort() raises HTTP error
		# https://flask.palletsprojects.com/en/2.3.x/api/#flask.abort
		abort(400, "Invalid BBL format")
	
	# Reference: request.args for query parameters
	# https://flask.palletsprojects.com/en/2.3.x/api/#flask.Request.args
	start_date = request.args.get('start_date', '')
	end_date = request.args.get('end_date', '')
	export_type = request.args.get('type', 'complaints')  # 'complaints' or 'sales'
	
	data = get_bbl_data(
		bbl_parsed['borough_code'],
		bbl_parsed['block_code'],
		bbl_parsed['lot_code'],
		start_date,
		end_date
	)
	
	if not data:
		abort(404)
	
	# Create CSV using Python's csv module
	output = io.StringIO()
	
	if export_type == 'complaints':
		writer = csv.writer(output)
		writer.writerow(['Complaint Type', 'Total Count', 'Active Count'])
		for ct in data['complaint_types']:
			writer.writerow([ct['type'], ct['count'], ct['active_count']])
	else:  # sales
		writer = csv.writer(output)
		writer.writerow(['Address', 'Sale Price', 'Sale Date'])
		for sale in data['sales']:
			writer.writerow([sale['address'], sale['price'], sale['date']])
	
	# Reference: make_response() creates custom Response object
	# https://flask.palletsprojects.com/en/2.3.x/api/#flask.make_response
	response = make_response(output.getvalue())
	
	# Reference: Setting response headers for file download
	# https://flask.palletsprojects.com/en/2.3.x/api/#flask.Response.headers
	response.headers['Content-Type'] = 'text/csv'
	response.headers['Content-Disposition'] = f'attachment; filename={bbl}_{export_type}.csv'
	
	return response


@app.route('/bookmark/<bbl>', methods=['POST'])
def bookmark(bbl):
	"""Add or remove BBL from bookmarks"""
	if 'bookmarks' not in session:
		session['bookmarks'] = []
	
	bookmarks = session['bookmarks']
	
	if bbl in bookmarks:
		bookmarks.remove(bbl)
		action = 'removed'
	else:
		bookmarks.append(bbl)
		action = 'added'
	
	session['bookmarks'] = bookmarks
	session.modified = True
	
	return jsonify({'status': 'success', 'action': action, 'bbl': bbl})


@app.route('/bookmarks')
def view_bookmarks():
	"""View all bookmarked BBLs"""
	bookmarks = session.get('bookmarks', [])
	
	bookmark_data = []
	for bbl in bookmarks:
		bbl_parsed = parse_bbl(bbl)
		if bbl_parsed:
			data = get_bbl_data(
				bbl_parsed['borough_code'],
				bbl_parsed['block_code'],
				bbl_parsed['lot_code']
			)
			if data:
				bookmark_data.append(data)
	
	return render_template("bookmarks.html", bookmarks=bookmark_data)


@app.route('/login')
def login():
	abort(401)
	# Your IDE may highlight this as a problem - because no such function exists (intentionally).
	# This code is never executed because of abort().
	this_is_never_executed()


if __name__ == "__main__":
	import click

	@click.command()
	@click.option('--debug', is_flag=True)
	@click.option('--threaded', is_flag=True)
	@click.argument('HOST', default='0.0.0.0')
	@click.argument('PORT', default=8111, type=int)
	def run(debug, threaded, host, port):
		"""
		This function handles command line parameters.
		Run the server using:

			python server.py

		Show the help text using:

			python server.py --help

		"""

		HOST, PORT = host, port
		print("running on %s:%d" % (HOST, PORT))
		app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

run()
