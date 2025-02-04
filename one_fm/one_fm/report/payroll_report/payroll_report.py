# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import *
import datetime

def execute(filters=None):
	if not filters: filters = {}

	if not (filters.month and filters.year):
		msgprint(_("Please select month and year"), raise_exception=1)

	columns, data =  get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	return [
		{
			"label": ("Employee ID"),
			"fieldname": "employee_id",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"label": ("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": ("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 120,
		},
		{
			"label": ("Work Permit Salary"),
			"fieldname": "work_permit_salary",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": ("Base Salary"),
			"fieldname": "base",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": ("Civil ID"),
			"fieldname": "one_fm_civil_id",
			"options": "Journal Entry",
			"width": 140,
		},
		{
			"label": ("Shoon File"),
			"fieldname": "shoon_file",
			"fieldtype": "Link",
			"options": "PAM File",
			"width": 120,
		},
		{
			"label": ("Bank Account"),
			"fieldname": "bank_ac_no",
			"fieldtype": "Link",
			"options": "Bank Account",
			"width": 120,
		},
		{
			"label": ("Start Date"),
			"fieldname": "start_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": ("End Date"),
			"fieldname": "end_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": ("No. Of Days(Current Month)"),
			"fieldname": "days_in_period",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Holiday List"),
			"fieldname": "holiday_list",
			"fieldtype": "Link",
			"options": "Holiday List",
			"width": 120,
		},
		{
			"label": ("Shift/Non-Shift Worker"),
			"fieldname": "shift_work_type",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": ("Theoretical Working Days"),
			"fieldname": "theoretical_working_days",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Day off Type"),
			"fieldname": "day_off_category",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": ("Days Off(Employee Docs)"),
			"fieldname": "number_of_days_off",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": ("Theoretical Days Off"),
			"fieldname": "theoretical_days_off",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Actual Working Days(Roster)"),
			"fieldname": "number_of_working_days",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Days Off (Roster)"),
			"fieldname": "do_roster",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("OT Days Off (Roster)"),
			"fieldname": "do_ot",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Present Days (Attendance)"),
			"fieldname": "working_days",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},

		{
			"label": ("Present OT Days (Attendence)"),
			"fieldname": "ot",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Sick Leave"),
			"fieldname": "sl",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Annual Leave"),
			"fieldname": "al",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Other Leave"),
			"fieldname": "ol",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("No. of Absent"),
			"fieldname": "ab",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
		{
			"label": ("Public Holidays"),
			"fieldname": "public_holidays",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": ("Total"),
			"fieldname": "total",
			"fieldtype": "Int",
			"default": 0,
			"width": 180,
		},
	]

def get_data(filters):
	data = []
	if not filters:
		return

	report_date = str(filters["year"]) + "-" + str(filters["month"]) + "-1"

	first_day_of_month = str(get_first_day(report_date))
	last_day_of_month = str(get_last_day(report_date))
	query = frappe.db.sql(f"""
		SELECT DISTINCT e.name as employee_id, e.employee_name, e.project, e.work_permit_salary, e.one_fm_civil_id, e.bank_ac_no,
		e.day_off_category, e.shift_working as shift_work_type, e.holiday_list, e.number_of_days_off , e.pam_file_number as shoon_file, ssa.base, pe.start_date, pe.end_date,
		COUNT(at.employee) as working_days
		FROM `tabEmployee` e JOIN `tabSalary Structure Assignment` ssa ON e.name=ssa.employee
			JOIN `tabPayroll Employee Detail` ped ON e.name=ped.employee
			JOIN `tabPayroll Entry` pe ON pe.name=ped.parent
			JOIN `tabAttendance` at ON at.employee=e.name
		WHERE ssa.docstatus=1 AND pe.end_date BETWEEN '{first_day_of_month}' and '{last_day_of_month}'
			AND at.attendance_date BETWEEN pe.start_date AND pe.end_date
			AND at.roster_type='Basic'
			AND pe.salary_slips_created=1
		GROUP BY e.name
		ORDER BY e.name ASC
	""", as_dict=1)

	payroll_cycle = get_payroll_cycle(filters)
	employee_list = get_employee_list(query)

	ot_dict = frappe._dict({})
	attendance_by_employee = get_attendance(payroll_cycle, employee_list)

	for i in query:
		i.days_in_period = (i.end_date - i.start_date).days + 1
		att_project = attendance_by_employee.get(i.employee_id)
		if att_project:
			i.working_days = att_project['working_days']
			i.ot = att_project['ot']
			i.do_ot = att_project['do_ot']
			i.sl = att_project['sl']
			i.al = att_project['al']
			i.ol = att_project['ol']
			i.ab = att_project['ab']
			i.do_roster = att_project['do_roster']

		if i.shift_work_type == 1:
			i.shift_work_type = "Shift Worker"
			i.theoretical_days_off = theoretical_days_off(i.day_off_category, i.number_of_days_off, i.start_date, i.end_date)
		else:
			i.shift_work_type = "Non-Shift Worker"
			count_holiday_date = frappe.db.sql(f"""Select count(holiday_date) as days_off from `tabHoliday` h
												WHERE h.parent = '{i.holiday_list}' 
												AND h.holiday_date BETWEEN '{i.start_date}' AND '{i.end_date}' 
	 											AND h.weekly_off = 1""", as_dict=1)
			i.theoretical_days_off = count_holiday_date[0].days_off
			i.do_roster = 0

		i.theoretical_working_days = i.days_in_period - i.theoretical_days_off
		i.total = i.working_days + i.sl + i.al + i.ol + i.ab
		i.number_of_working_days = ((i.end_date-i.start_date).days)+1 - (i.do_roster + i.do_ot)

	if not query:
		frappe.msgprint(("No Payroll Submitted or Salary Slip Created from the Payroll Entry this month!"), alert=True, indicator="Blue")

	return query

def get_employee_list(query):
	employee = []
	for q in query:
		if q.employee_id not in employee:
			employee.append(q.employee_id)
	return employee


def get_payroll_cycle(filters):
	settings = frappe.get_doc("HR and Payroll Additional Settings")
	default_date = settings.payroll_date


	end_date = datetime.date(int(filters["year"]), int(filters["month"]), int(default_date))
	payroll_cycle = {
		'Other': {
			'start_date': add_days(add_months(datetime.date(int(filters["year"]),int(filters["month"]), int(default_date)), -1), -1),
			'end_date': datetime.date(int(filters["year"]), int(filters["month"]), int(default_date))

			}
		}

	for row in settings.project_payroll_cycle:
		if row.payroll_start_day == 'Month Start':
			row.payroll_start_day = 1
		payroll_cycle[row.project] = {

			'start_date':add_days(add_months(datetime.date(int(filters["year"]), int(filters["month"]), int(row.payroll_start_day)), -1), -1),
			'end_date':datetime.date(int(filters["year"]), int(filters["month"]), int(row.payroll_start_day)),
		}

	return payroll_cycle

def theoretical_days_off(day_off_category, number_of_days_off, start_date, end_date):
	if day_off_category == "Monthly":
		return number_of_days_off
	else:
		no_of_days = end_date - start_date
		weeks = no_of_days.days // 7
		return weeks * number_of_days_off

def get_attendance(projects, employee_list):
	attendance_dict = {}
	present_dict = {}
	working_days = {}
	ot_dict = {}
	leave_dict = {}
	absent_dict = {}
	day_off_dict = {}

	all_project = frappe.db.get_list("Project", pluck="name")

	for key, value in projects.items():
		if key in all_project:
			all_project.remove(key)

	all_project = tuple(all_project)

	for e in employee_list:
		attendance_dict[e]={'working_days': 0,'number_of_days_off':0, 'ot': 0, 'sl':0, 'al':0, 'ab':0, 'ol':0, 'do_ot':0, 'do_roster':0}

	for key, value in projects.items():
		start_date = projects[key]['start_date']
		end_date = projects[key]['end_date']

		condition = ""
		if key != "Other":
			condition += f" AND e.project='{key}' "
		else:
			condition += f" AND e.project IN {all_project} "

		present_list = frappe.db.sql(f"""
			SELECT at.employee, COUNT(*) as working_days FROM `tabAttendance` at JOIN `tabEmployee` e ON e.name=at.employee
			WHERE at.attendance_date BETWEEN '{start_date}' AND '{end_date}'
			AND at.status IN ("Present", "Work From Home")
			AND at.roster_type='Basic'
			{condition}
			GROUP BY at.employee
		""", as_dict=1)

		attendance_list_ot = frappe.db.sql(f"""SELECT 
								e.name AS employee,
								COUNT(CASE WHEN es.employee_availability = 'Day Off' THEN 1 END) AS do_roster,
								COUNT(CASE WHEN es.day_off_ot = 1 THEN 1 END) AS do_ot,
								COUNT(CASE WHEN a.status IN ('Present', 'Work From Home') AND a.roster_type = 'Over-Time' THEN 1 END) AS ot
								FROM 
								`tabEmployee` e
								LEFT JOIN `tabEmployee Schedule` es ON e.name = es.employee AND es.date BETWEEN '{start_date}' AND '{end_date}'
								LEFT JOIN `tabAttendance` a ON e.name = a.employee AND a.attendance_date BETWEEN '{start_date}' AND '{end_date}'
								GROUP BY 
								e.name;""", as_dict=1)

		attendance_leave_details = frappe.db.sql(f"""
			SELECT at.employee, at.leave_type, COUNT(at.leave_type) AS leave_count FROM `tabAttendance` at JOIN `tabEmployee` e ON e.name=at.employee
				WHERE at.status = "On Leave"
				AND at.attendance_date BETWEEN '{start_date}' AND '{end_date}'
				{condition}
				Group by at.leave_type;
			""", as_dict=1)

		attendance_absent = frappe.db.sql(f"""
			SELECT at.employee, COUNT(at.employee) as absent FROM `tabAttendance` at JOIN `tabEmployee` e ON e.name=at.employee
				WHERE at.status = "Absent"
				AND at.attendance_date BETWEEN '{start_date}' AND '{end_date}'
				{condition}
				Group by at.employee;
			""", as_dict=1)

		day_off_list = frappe.db.sql(f"""
			SELECT es.employee, COUNT(es.employee) as number_of_days_off FROM `tabEmployee Schedule` es JOIN `tabEmployee` e ON e.name=es.employee
				WHERE es.employee_availability = "Day Off"
				AND es.date BETWEEN '{start_date}' AND '{end_date}'
				{condition}
				Group by es.employee;
			""", as_dict=1)
		print(attendance_list_ot)
		for row in present_list:
			present_dict[row.employee] = row.working_days

		for row in attendance_list_ot:
			ot_dict[row.employee] = {'ot':row.ot,'do_ot':row.do_ot, 'do_roster':row.do_roster}

		for row in attendance_absent:
			absent_dict[row.employee] = row.absent

		for row in day_off_list:
			day_off_dict[row.employee] = row.number_of_days_off

		for row in attendance_leave_details:
			if row.leave_type not in ['Sick Leave', 'Annual Leave']:
				row.leave_type = "Other Leave"
			leave_dict[row.employee] = {'leave_type' : row.leave_type, 'leave_count':row.leave_count}

	for row in attendance_dict:
		if present_dict.get(row):
			attendance_dict[row]['working_days'] = present_dict.get(row)

		if ot_dict.get(row):
			attendance_dict[row]['ot'] = ot_dict.get(row)["ot"]
			attendance_dict[row]['do_ot'] = ot_dict.get(row)["do_ot"]

		if day_off_dict.get(row):
			attendance_dict[row]['number_of_days_off'] = day_off_dict.get(row)

		if leave_dict.get(row):
			if leave_dict.get(row)["leave_type"] == "Sick Leave":
				attendance_dict[row]['sl'] = leave_dict.get(row)["leave_count"]
			if leave_dict.get(row)["leave_type"] == "Annual Leave":
				attendance_dict[row]['al'] = leave_dict.get(row)["leave_count"]
			if leave_dict.get(row)["leave_type"] == "Other Leave":
				attendance_dict[row]['ol'] = leave_dict.get(row)["leave_count"]
		if absent_dict.get(row):
			attendance_dict[row]['ab'] = absent_dict.get(row)
	return attendance_dict

@frappe.whitelist()
def get_attendance_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(attendance_date) from tabAttendance ORDER BY YEAR(attendance_date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)
