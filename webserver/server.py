
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

engine = create_engine(DATABASEURI, poolclass=NullPool)


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
	Get monthly time-series data for charts
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
	else:
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
	
	data_dict = {}
	for row in cursor:
		month = row[0].strftime('%Y-%m')
		if metric_type == 'service_requests':
			data_dict[month] = {'count': row[1]}
		else:
			data_dict[month] = {'median_price': float(row[1]), 'count': row[2]}
	cursor.close()
	
	start = datetime.strptime(start_date, '%Y-%m-%d')
	end = datetime.strptime(end_date, '%Y-%m-%d')
	
	all_months = []
	current = start
	while current <= end:
		all_months.append(current.strftime('%Y-%m'))
		if current.month == 12:
			current = current.replace(year=current.year + 1, month=1)
		else:
			current = current.replace(month=current.month + 1)
	
	results = []
	for month_str in all_months:
		if month_str in data_dict:
			result = {'month': month_str}
			result.update(data_dict[month_str])
			results.append(result)
		elif metric_type == 'service_requests':
			results.append({'month': month_str, 'count': 0})
		else:
			results.append({'month': month_str, 'median_price': None, 'count': 0})
	
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
	
	# Get first address for compare pre-fill
	first_address = ''
	if data['sales']:
		first_address = data['sales'][0]['address']
	
	return render_template("analytics.html", 
	                      data=data,
	                      start_date=start_date,
	                      end_date=end_date,
	                      is_bookmarked=is_bookmarked,
	                      complaint_data=chart_data,
	                      first_address=first_address)


@app.route('/compare', methods=['GET', 'POST'])
def compare():
	"""
	Compare data summary for two properties
	"""
	if request.method == 'GET':
		house_number1 = request.args.get('house_number1', '')
		street1 = request.args.get('street1', '')
		borough1 = request.args.get('borough1', '')
		start_date = request.args.get('start_date', '')
		end_date = request.args.get('end_date', '')
		return render_template("compare.html", 
		                      house_number1=house_number1, 
		                      street1=street1, 
		                      borough1=borough1,
		                      start_date=start_date, 
		                      end_date=end_date)
	
	start_date = request.form.get('start_date', '')
	end_date = request.form.get('end_date', '')
	
	bbl_result1 = address_to_bbl_geoclient(
		request.form.get('house_number1', ''),
		request.form.get('street1', ''),
		request.form.get('borough1', '')
	)
	bbl1 = parse_bbl(bbl_result1['bbl'])
	
	bbl_result2 = address_to_bbl_geoclient(
		request.form.get('house_number2', ''),
		request.form.get('street2', ''),
		request.form.get('borough2', '')
	)
	bbl2 = parse_bbl(bbl_result2['bbl'])
	
	data1 = get_bbl_data(bbl1['borough_code'], bbl1['block_code'], bbl1['lot_code'], start_date, end_date)
	data2 = get_bbl_data(bbl2['borough_code'], bbl2['block_code'], bbl2['lot_code'], start_date, end_date)
	
	return render_template("compare.html", data1=data1, data2=data2, start_date=start_date, end_date=end_date)


@app.route('/trends/<bbl>')
def trends(bbl):
	"""
	Get time-series data for charts
	"""
	bbl_parsed = parse_bbl(bbl)
	start_date = request.args.get('start_date', '2024-01-01')
	end_date = request.args.get('end_date', '2024-12-31')
	metric_type = request.args.get('type', 'service_requests')
	
	data = get_time_series_data(
		bbl_parsed['borough_code'],
		bbl_parsed['block_code'],
		bbl_parsed['lot_code'],
		start_date,
		end_date,
		metric_type
	)
	
	return jsonify(data)


@app.route('/export/<bbl>')
def export_csv(bbl):
	"""
	Export data as CSV
	"""
	bbl_parsed = parse_bbl(bbl)
	start_date = request.args.get('start_date', '')
	end_date = request.args.get('end_date', '')
	export_type = request.args.get('type', 'complaints')
	
	data = get_bbl_data(
		bbl_parsed['borough_code'],
		bbl_parsed['block_code'],
		bbl_parsed['lot_code'],
		start_date,
		end_date
	)
	
	if not data:
		abort(404)
	
	output = io.StringIO()
	writer = csv.writer(output)
	
	if export_type == 'complaints':
		writer.writerow(['Complaint Type', 'Total Count', 'Active Count'])
		for ct in data['complaint_types']:
			writer.writerow([ct['type'], ct['count'], ct['active_count']])
	elif export_type == 'sales':
		writer.writerow(['Address', 'Sale Price', 'Sale Date'])
		for sale in data['sales']:
			writer.writerow([sale['address'], sale['price'], sale['date']])
	
	response = make_response(output.getvalue())
	response.headers['Content-Type'] = 'text/csv'
	response.headers['Content-Disposition'] = f'attachment; filename={bbl}_{export_type}.csv'
	
	return response


@app.route('/bookmark/<bbl>', methods=['POST'])
def bookmark(bbl):
	"""
	Add or remove BBL from bookmarks
	"""
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
	"""
	View all bookmarked BBLs
	"""
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
