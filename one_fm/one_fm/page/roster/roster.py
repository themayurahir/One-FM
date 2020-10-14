import frappe
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate
import itertools
import pandas as pd
import numpy as np
import time
from frappe import _
import json

@frappe.whitelist(allow_guest=True)
def get_staff(assigned=1, employee_id=None, employee_name=None, company=None, project=None, site=None, shift=None, department=None, designation=None):
	date = cstr(add_to_date(nowdate(), days=1))
	conds = ""

	if employee_name:
		conds += 'and emp.employee_name="{name}" '.format(name=employee_name)
	if department:
		conds += 'and emp.department="{department}" '.format(department=department)	
	if designation:
		conds += 'and emp.designation="{designation}" '.format(designation=designation)
	if company:
		conds += 'and emp.company="{company}" '.format(company=company)
		
	if project:
		conds += 'and emp.project="{project}" '.format(project=project)
	if site:
		conds += 'and emp.site="{site}" '.format(site=site)
	if shift:
		conds += 'and emp.name="{shift}" '.format(shift=shift)

	if not cint(assigned):
		data = frappe.db.sql("""
			select 
				distinct emp.name, emp.employee_id, emp.employee_name, emp.image, emp.one_fm_nationality as nationality, usr.mobile_no, usr.name as email, emp.designation, emp.department, emp.project
			from `tabEmployee` as emp, `tabUser` as usr
			where 
			emp.project is NULL
			and emp.site is NULL
			and emp.shift is NULL
			and emp.user_id=usr.name
			{conds}
		""".format(date=date, conds=conds), as_dict=1)
		return data

	data = frappe.db.sql("""
		select 
			distinct emp.name, emp.employee_id, emp.employee_name, emp.image, emp.one_fm_nationality as nationality, usr.mobile_no, usr.name as email, emp.designation, emp.department, emp.shift, emp.site, emp.project
		from `tabEmployee` as emp, `tabUser` as usr
		where 
		emp.project is not NULL
		and emp.site is not NULL
		and emp.shift is not NULL
		and emp.user_id=usr.name
		{conds}
	""".format(date=date, conds=conds), as_dict=1)
	return data

@frappe.whitelist(allow_guest=True)
def get_staff_filters_data():
	company = frappe.get_list("Company", limit_page_length=9999)
	projects = frappe.get_list("Project", limit_page_length=9999)
	sites = frappe.get_list("Operations Site", limit_page_length=9999)
	shifts = frappe.get_list("Operations Shift", limit_page_length=9999)
	departments = frappe.get_list("Department", limit_page_length=9999)
	designations = frappe.get_list("Designation", limit_page_length=9999)

	return {
		"company": company,
		"projects": projects,
		"sites": sites,
		"shifts": shifts,
		"departments": departments,
		"designations": designations
	}

@frappe.whitelist(allow_guest=True)
def get_roster_view(start_date, end_date, all=1, assigned=0, scheduled=0, project=None, site=None, shift=None, department=None, post_type=None, limit_start=0, limit_page_length=25):
	# Roster filters
	st = time.time()

	master_data = {}
	formatted_data = []
	formatted_employee_data = {}
	post_count_data = {}
	post_types_list = []
	filters = {
		'date': ['between', (start_date, end_date)]
	}
	# if project:
	# 	filters.update({'project': project})	
	# if site:
	# 	filters.update({'site': site})	
	# if shift:
	# 	filters.update({'shift': shift})	
	# if department:
	# 	filters.update({'department': department})	
	if post_type:
		filters.update({'post_type': post_type})	
	print("97", filters)
	fields = ["employee", "employee_name", "date", "post_type", "post_abbrv", "employee_availability", "shift"]
	
	if all:
		employee_filters = {}
		if project:
			employee_filters.update({'project': project})
		if site:
			employee_filters.update({'site': site})	
		if shift:
			employee_filters.update({'shift': shift})	
		if department:
			employee_filters.update({'department': department})

		employees = frappe.get_list("Employee", employee_filters, ["employee", "employee_name"], order_by="employee_name asc" ,limit_start=limit_start, limit_page_length=limit_page_length)
		print(employees)
		employee_filters.update({'date': ['between', (start_date, end_date)], 'post_status': 'Planned'})
		if department:
			employee_filters.pop('department', None)
		if post_type:
			employee_filters.update({'post_type': post_type})

		print(employee_filters)
		post_types_list = frappe.get_list("Post Schedule", employee_filters, ["post_type", "post_abbrv"])
		if post_type:
			employee_filters.pop('post_type', None)
		employee_filters.pop('date')
		employee_filters.pop('post_status')
		
		for key, group in itertools.groupby(post_types_list, key=lambda x: (x['post_abbrv'], x['post_type'])):
			post_list = []
			for date in	pd.date_range(start=start_date, end=end_date):
				post_filters = employee_filters
				post_filters.update({'date': cstr(date).split(" ")[0], 'post_type': key[1]})

				post_filled_count = frappe.get_list("Employee Schedule", post_filters)

				post_filters.update({"post_status": "Planned"})
				post_schedule_count = frappe.get_list("Post Schedule", post_filters)
				post_filters.pop("post_status", None)

				count = cstr(len(post_schedule_count))+"/"+cstr(len(post_filled_count))
				post_list.append({'count': count, 'post_type': key[0], 'date': cstr(date).split(" ")[0] })

			post_count_data.update({key[0]: post_list })
		master_data.update({'post_types_data': post_count_data})

		for key, group in itertools.groupby(employees, key=lambda x: (x['employee'], x['employee_name'])):
			schedule_list = []				
			for date in	pd.date_range(start=start_date, end=end_date):
				filters.update({'date': cstr(date).split(" ")[0], 'employee': key[0]})
				schedule = frappe.get_value("Employee Schedule", filters, fields, order_by="date asc, employee_name asc", as_dict=1)
				if not schedule:
					schedule = {
						'employee': key[0],
						'employee_name': key[1],
						'date': cstr(date).split(" ")[0]
					}
				schedule_list.append(schedule)
			formatted_employee_data.update({key[1]: schedule_list})
		master_data.update({'employees_data': formatted_employee_data})

	elif scheduled:
		data = frappe.get_list("Employee Schedule", filters, fields, order_by="date asc, employee_name asc",limit_page_length=50)
		for key, group in itertools.groupby(data, key=lambda x: (x['post_type'],x['post_abbrv'])):
			print(key)
	elif not scheduled:
		pass
	elif assigned:
		pass
	elif not assigned:
		pass
	print(master_data)
	et = time.time()
	print("------------------------------------------------------------------------------------------")
	print("Time", et-st)
	return master_data

@frappe.whitelist(allow_guest=True)
def get_post_view(start_date, end_date,  project=None, site=None, shift=None, post_type=None, active_posts=1, limit_start=0, limit_page_length=25):
	filters = {}
	if project:
		filters.update({'project': project})	
	if site:
		filters.update({'site': site})	
	if shift:
		filters.update({'site_shift': shift})	
	if post_type:
		filters.update({'post_template': post_type})	

	post_list = frappe.get_list("Operations Post", filters, "name", order_by="name asc", limit_start=limit_start, limit_page_length=limit_page_length)
	# print(post_list)
	fields = ['name', 'post', 'post_type','date', 'post_status', 'site', 'shift', 'project']	
	
	master_data = {}
	filters.pop('post_template', None)
	filters.pop('site_shift', None)
	if post_type:
		filters.update({'post_type': post_type})
	if shift:
		filters.update({'shift': shift})		
	for key, group in itertools.groupby(post_list, key=lambda x: (x['name'])):
		# filters.update({
			# 'date': ['between', (start_date, end_date)],
			# 'post_status': ['=', 'Planned'] if active_posts else ['in', ('Post Off', 'Suspended', 'Cancelled')]
		# })
		# data = frappe.get_list("Post Schedule", filters, fields, order_by="post asc, date asc")
		schedule_list = []
		for date in	pd.date_range(start=start_date, end=end_date):
			filters.update({'date': cstr(date).split(" ")[0], 'post': key})
			schedule = frappe.get_value("Post Schedule", filters, fields, order_by="post asc, date asc", as_dict=1)
			# print(filters, schedule)
			# print("----------------------------------------------------------------------------------------")
			# print("----------------------------------------------------------------------------------------")
			if not schedule:
				schedule = {
					'post': key,
					'date': cstr(date).split(" ")[0]
				}
			schedule_list.append(schedule)
		master_data.update({key: schedule_list})
	
	# print(master_data)
	return master_data

@frappe.whitelist()
def get_filtered_post_types(doctype, txt, searchfield, start, page_len, filters):
	shift = filters.get('shift')
	return frappe.db.sql("""
		select distinct post_template
		from `tabOperations Post` 
		where site_shift="{shift}"
	""".format(shift=shift))
	
@frappe.whitelist()
def schedule_staff(employees, shift, post_type):
	try:
		# print(employees, shift, site, post_type, project)
		for employee in json.loads(employees):
			print(getdate(employee["date"]).strftime('%A'))
			# print(employee["employee"], employee["date"])
			if frappe.db.exists("Employee Schedule", {"employee": employee["employee"], "date": employee["date"]}):
				roster = frappe.get_doc("Employee Schedule", {"employee": employee["employee"], "date": employee["date"]})
			else:
				roster = frappe.new_doc("Employee Schedule")
				roster.employee = employee["employee"]
				roster.date = employee["date"]
			roster.shift = shift
			roster.employee_availability = "Working"
			roster.post_type = post_type
			print(roster.as_dict())
			roster.save(ignore_permissions=True)
		return True
	except Exception as e:
		frappe.log_error(e)
		frappe.throw(_(e))

@frappe.whitelist()
def schedule_leave(employees, leave_type, start_date, end_date):
	try:
		for employee in json.loads(employees):
			for date in	pd.date_range(start=start_date, end=end_date):
				print(employee["employee"], date.date())
				if frappe.db.exists("Employee Schedule", {"employee": employee["employee"], "date": employee["date"]}):
					roster = frappe.get_doc("Employee Schedule", {"employee": employee["employee"], "date": employee["date"]})
					roster.shift = None
					roster.shift_type = None
					roster.project = None
					roster.site = None
				else:
					roster = frappe.new_doc("Employee Schedule")
					roster.employee = employee["employee"]
					roster.date = employee["date"]
				roster.employee_availability = leave_type
				roster.save(ignore_permissions=True)
	except Exception as e:
		print(e)
		return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist(allow_guest=True)
def unschedule_staff(employees, start_date, end_date=None, never_end=0):
	try:
		print(employees, start_date, never_end)
		for employee in json.loads(employees):
			if never_end:
				print(never_end, start_date)
				rosters = frappe.get_all("Employee Schedule", {"employee": employee["employee"],"date": ('>=', start_date)})
				for roster in rosters:
					frappe.delete_doc("Employee Schedule", roster.name, ignore_permissions=True)
			for date in	pd.date_range(start=start_date, end=end_date):
				print(employee["employee"], date.date())
				if frappe.db.exists("Employee Schedule", {"employee": employee["employee"], "date":  cstr(date.date())}):
					roster = frappe.get_doc("Employee Schedule", {"employee": employee["employee"], "date":  cstr(date.date())})
					frappe.delete_doc("Employee Schedule", roster.name, ignore_permissions=True)

	except Exception as e:
		print(e)
		return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist()
def edit_post(posts, values):
	args = frappe._dict(json.loads(values))
	print(args, posts)
	if args.post_status == "Cancel Post":
		frappe.enqueue(cancel_post, posts=posts, args=args, queue='short')
	elif args.post_status == "Suspend Post":
		frappe.enqueue(suspend_post, posts=posts, args=args, queue='short')
	elif args.post_status == "Post Off":
		frappe.enqueue(post_off, posts=posts, args=args, queue='short')
	

def cancel_post(posts, args):
	print(posts, args)
	for post in json.loads(posts):
		project = frappe.get_value("Operations Post", post, "project")
		end_date = frappe.get_value("Contracts", {"project": project}, "end_date")

		for date in	pd.date_range(start=args.cancel_from_date, end=end_date):
			print(date.date())
			if frappe.db.exists("Post Schedule", {"date": cstr(date.date()), "post": post}):
				doc = frappe.get_doc("Post Schedule", {"date": cstr(date.date()), "post": post})
			else: 
				doc = frappe.new_doc("Post Schedule")
				doc.post = post
				doc.date = cstr(date.date())	
			doc.paid = args.suspend_paid
			doc.unpaid = args.suspend_unpaid
			doc.post_status = "Cancelled"
			doc.save()
	frappe.db.commit()

def suspend_post(posts, args):
	for post in json.loads(posts):
		for date in	pd.date_range(start=args.suspend_from_date, end=args.suspend_to_date):
			if frappe.db.exists("Post Schedule", {"date": cstr(date.date()), "post": post}):
				doc = frappe.get_doc("Post Schedule", {"date": cstr(date.date()), "post": post})
			else: 
				doc = frappe.new_doc("Post Schedule")
				doc.post = post
				doc.date = cstr(date.date())
			doc.paid = args.suspend_paid
			doc.unpaid = args.suspend_unpaid
			doc.post_status = "Suspended"
			doc.save()
	frappe.db.commit()

def post_off(posts, args):
	from one_fm.api.mobile.roster import month_range
	post_off_paid = args.post_off_paid
	post_off_unpaid = args.post_off_unpaid
	
	if args.repeat == "Does not repeat":
		for post in json.loads(posts):
			set_post_off(post["post"], post["date"], post_off_paid, post_off_unpaid)
	else:
		if args.repeat and args.repeat in ["Daily", "Weekly", "Monthly", "Yearly"]:
			end_date = args.repeat_till

			if args.repeat == "Daily":
				for post in json.loads(posts):
					for date in	pd.date_range(start=post["date"], end=end_date):
						set_post_off(post["post"], cstr(date.date()), post_off_paid, post_off_unpaid)

			elif args.repeat == "Weekly":
				week_days = []
				if args.sunday: week_days.append("Sunday")
				if args.monday: week_days.append("Monday")
				if args.tuesday: week_days.append("Tuesday")
				if args.wednesday: week_days.append("Wednesday")
				if args.thursday: week_days.append("Thursday")
				if args.friday: week_days.append("Friday")
				if args.saturday: week_days.append("Saturday")
				for post in json.loads(posts):
					for date in	pd.date_range(start=post["date"], end=end_date):
						if getdate(date).strftime('%A') in week_days:
							set_post_off(post["post"], cstr(date.date()), post_off_paid, post_off_unpaid)

			elif args.repeat == "Monthly":
				for post in json.loads(posts):
					for date in	month_range(post["date"], args.repeat_till):
						set_post_off(post["post"], cstr(date.date()), post_off_paid, post_off_unpaid)

			elif args.repeat == "Yearly":
				for date in	pd.date_range(start=post["date"], end=args.repeat_till, freq=pd.DateOffset(years=1)):
					set_post_off(post["post"], cstr(date.date()), post_off_paid, post_off_unpaid)
	frappe.db.commit()

def set_post_off(post, date, post_off_paid, post_off_unpaid):
	if frappe.db.exists("Post Schedule", {"date": date, "post": post}):
		doc = frappe.get_doc("Post Schedule", {"date": date, "post": post})
	else: 
		doc = frappe.new_doc("Post Schedule")
		doc.post = post
		doc.date = date
	doc.paid = post_off_paid
	doc.unpaid = post_off_unpaid
	doc.post_status = "Post Off"
	doc.save()
	


@frappe.whitelist()
def dayoff(employees, selected_dates=0, repeat=0, repeat_freq=None, week_days=[], repeat_till=None):
	from one_fm.api.mobile.roster import month_range
	print(employees, selected_dates, repeat, repeat_freq, week_days, type(week_days), repeat_till)
	if selected_dates:
		for employee in json.loads(employees):
			set_dayoff(employee["employee"], employee["date"])
	else:
		if repeat and repeat_freq in ["Daily", "Weekly", "Monthly", "Yearly"]:
			end_date = repeat_till

			if repeat_freq == "Daily":
				for employee in json.loads(employees):
					for date in	pd.date_range(start=employee["date"], end=end_date):
						frappe.enqueue(set_dayoff, employee["employee"], cstr(date.date()), queue='short')

			elif repeat_freq == "Weekly":
				for employee in json.loads(employees):
					for date in	pd.date_range(start=employee["date"], end=end_date):
						if getdate(date).strftime('%A') in week_days:
							frappe.enqueue(set_dayoff, employee["employee"], cstr(date.date()), queue='short')

			elif repeat_freq == "Monthly":
				for employee in json.loads(employees):
					for date in	month_range(employee["date"], repeat_till):
						frappe.enqueue(set_dayoff, employee["employee"], cstr(date.date()), queue='short')

			elif repeat_freq == "Yearly":
				for date in	pd.date_range(start=employee["date"], end=repeat_till, freq=pd.DateOffset(years=1)):
					frappe.enqueue(set_dayoff, employee["employee"], cstr(date.date()), queue='short')

def set_dayoff(employee, date):
	print((employee, date))
	if frappe.db.exists("Employee Schedule", {"date": date, "employee": employee}):
		doc = frappe.get_doc("Employee Schedule", {"date": date, "employee": employee})

	else:
		doc = frappe.new_doc("Employee Schedule")

	doc.employee = employee
	doc.date = date
	doc.shift = None
	doc.post_type = None
	doc.shift_type = None
	doc.site = None
	doc.project = None
	doc.employee_availability = "Day Off"
	doc.save()


@frappe.whitelist()
def assign_staff(employees, shift, post_type, assign_from, assign_date, assign_till_date):
	try:
		if assign_from == 'Immediately':
			assign_date = cstr(add_to_date(nowdate(), days=1))
		frappe.enqueue(assign_job, employees=employees, start_date=assign_date, end_date=assign_till_date, shift=shift, post_type=post_type, is_async=False, queue='long')
		return True
	except Exception as e:
		frappe.log_error(e)
		frappe.throw(_(e))

def assign_job(employees, start_date, end_date, shift, post_type):
	for employee in json.loads(employees):
		site, project = frappe.get_value("Operations Shift", shift, ["site", "project"])
		frappe.set_value("Employee", employee, "shift", shift)
		frappe.set_value("Employee", employee, "site", site)
		frappe.set_value("Employee", employee, "project", project)
		for date in	pd.date_range(start=start_date, end=end_date):

			if frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date())}):
				roster = frappe.get_doc("Employee Schedule", {"employee": employee, "date": cstr(date.date())})
			else:
				roster = frappe.new_doc("Employee Schedule")
				roster.employee = employee
				roster.date = cstr(date.date())
			roster.shift = shift
			roster.employee_availability = "Working"
			roster.post_type = post_type
			roster.save(ignore_permissions=True)

@frappe.whitelist(allow_guest=True)
def search_staff(key, search_term):
	conds = ""
	if key == "customer" and search_term:
		conds += 'and prj.customer like "%{customer}%" and emp.project=prj.name'.format(customer=search_term)
	elif key == "employee_id" and search_term:
		conds += 'and emp.employee_id like "%{employee_id}%" '.format(employee_id=search_term)
	elif key == "project" and search_term:
		conds += 'and emp.project like "%{project}%" '.format(project=search_term)
	elif key == "site" and search_term:
		conds += 'and emp.site like "%{site}%" '.format(site=search_term)
	elif key == "employee_name" and search_term:
		conds += 'and emp.employee_name like "%{name}%" '.format(name=search_term)

	data = frappe.db.sql("""
		select 
			distinct emp.name, emp.employee_id, emp.employee_name, emp.image, emp.one_fm_nationality as nationality, usr.mobile_no, usr.name as email, emp.designation, emp.department, emp.shift, emp.site, emp.project
		from `tabEmployee` as emp, `tabUser` as usr, `tabProject` as prj
		where 
		emp.user_id=usr.name
		{conds}
	""".format(conds=conds), as_dict=1)
	return data