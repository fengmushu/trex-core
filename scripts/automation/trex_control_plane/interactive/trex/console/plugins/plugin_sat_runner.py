#!/usr/bin/env python3

from trex.console.plugins import *
from trex.attenuators.attenuator import * 	# AttenGroup, AttenUnit, AttenAdaura
from trex.attenuators.usbtty_geehy import * 	# ttyDioRotary, ttyUsbGeehy

import pprint
import xlsxwriter

USE_ATTEN_ADAURA = False

'''
Step Attenuator test runner and XLSX sheets plugin
'''

class SatRunner_Plugin(ConsolePlugin):
	def plugin_description(self):
		return 'Simple example'

	def __init__(self):
		super(SatRunner_Plugin, self).__init__()
		self.console = None
		if USE_ATTEN_ADAURA:
			# Adaura-63: 0-63db, 0.5db step
			self.atten = AttenAdaura("ADAURA-63", None)
		else:
			# Hp3X-SC/SD/SG serises
			ser = ttyUsbGeehy(None)
			atten_sc = AttenUnit("HP33321-SC", 3, [20, 40, 10])
			atten_sd = AttenUnit("HP33321-SD", 3, [30, 40, 5])
			atten_sg = AttenUnit("HP33321-SG", 3, [20, 5, 10])
			# init group
			atten_gp_sc_sg = AttenGroup("SC-SG", ser, [atten_sg, atten_sc])
			# atten_gp_sc_sg.Dump()
			self.atten = atten_gp_sc_sg
		self.rotate = ttyDioRotary(None)
		self.table_xlsx = {}
		self.dir_report = '/home/trex/report/'
		self.update_timestamp()

	# used to init stuff
	def plugin_load(self):
		# Adding arguments to be used at do_* functions
		self.add_argument('-f', '--file', action = 'store', nargs = '?', default = 'test_report.xlsx', type = str, required = False, 
			dest = 'file_report', # <----- variable name to be used
				help = 'file name to creat xlsx report')
		
		self.add_argument('-d', '--dir', action = 'store', nargs = '?', default = '/home/trex/report/', type = str, required = False, 
			dest = 'dir_report', # <----- variable name to be used
				help = 'directory to creat xlsx reports')

		self.add_argument('-p', '--prefix', action = 'store', nargs = '?', default = 'AX3000K-DL', type = str, required = False, 
			dest = 'test_prefix', # <----- variable name to be used
				help = 'file name prefix to creat xlsx report')

		self.add_argument('-s', '--start', action = 'store', nargs='?', default = 20, type=int, required = False, 
			dest = "atten_start", 
				help = "init atten value")

		self.add_argument('-t', '--step', action = 'store', nargs='?', default = 5, type=int, required=False,
			dest = "atten_step", 
				help = "atten step up/down value")

		self.add_argument('-e', '--end', action = 'store', nargs = "?", default = 60, type = int, required=False,
			dest = "atten_end", 
				help = "atten end/stop/keep value")

		self.add_argument('-i', '--intv', action = 'store', nargs = "?", default = 10, type = int, required=False,
			dest = "time_intval", 
				help = "auto atten time intval sec")

		self.add_argument('-r', '--angles', action = 'store', nargs = "*", default = 0, type = int, required=False,
			dest = "rota_angles", 
				help = "set the angle to rotate,  <point: 0-11> or <angle: 0-30-60-90...>: from 0-360°, each step 30°")

		self.add_argument('-a', '--auto-report', action = 'store', nargs = "?", default = 1, type = int, required=False,
			dest = "auto_report", 
				help = "auto generate test report xlsx")

		if self.console is None:
			raise TRexError("Trex console must provided")

	def update_timestamp(self):
		self.time_prefix = time.strftime("%Y-%m-%d-%H%M%S", time.localtime())

	def build_xlsx(self, filename):
		ts = time.localtime()
		dir_date = time.strftime("%Y-%m-%d", ts)
		dir_name = "{0}/{1}".format(self.dir_report, dir_date)
		try:
			import os
			os.popen('mkdir -p {}'.format(dir_name))
		except Exception as e:
			print(e)

		book = xlsxwriter.Workbook("{0}/{1}".format(dir_name, filename))
		tab_angles = self.table_xlsx
		for angle, samples in tab_angles.items():
			shtname = "angle-{}".format(angle)
			sheet = book.add_worksheet(shtname)
			chart = book.add_chart({'type': 'line'})
			atten 	= ['attenuator', ]
			througput = ['throughput', ]
			for db, rxbps in samples.items():
				atten.append(db)
				total = 0
				for snapshot in rxbps:
					total += snapshot
				average = total / len(rxbps)
				througput.append(average)
			sheet.write_column('A1', atten)
			sheet.write_column('B1', througput)
			row_dbs  = '={}!$A$2:$A${:d}'.format(shtname, len(atten) + 1)
			row_thpt = '={}!$B$2:$B${:d}'.format(shtname, len(througput) + 1)
			chart.add_series({
				'categories': row_dbs, 
				'values': row_thpt,
				'name': '={}!$A1'.format(shtname)
				})
			chart.set_x_axis({'name': "db"})
			sheet.insert_chart('D1', chart)
		book.close()

	# We build argparser from do_* functions, stripping the "do_" from name
	def do_report(self, dir_report, file_report): # <------ name was registered in plugin_load
		''' dump statistics to sheets file '''
		
		# overwrite default report dir
		if os.access(dir_report, os.F_OK):
			self.dir_report = dir_report

		self.trex_client.logger.info('Sheets will dump to: {0}/{1}!'.format(
				self.dir_report, bold(file_report.capitalize()))) # <--- trex_client is set implicitly

		self.update_timestamp()
		self.build_xlsx("report-{0}.xlsx".format(self.time_prefix, file_report))

	def do_show(self):
		''' dump info '''
		self.trex_client._show_global_stats()
		stats = self.trex_client.get_stats(ports=[0, 1], sync_now = True)
		# print(json.dumps(stats, indent = 4, separators=(',', ': '), sort_keys = True))
		self.json_dump(stats['global'])

	def do_atten(self):
		''' dump current attenuator grop '''
		self.atten.Dump()

	def json_dump(self, o):
		print(json.dumps(o, indent=2, separators=(',', ': '), sort_keys = True))

	def run_point_atten(self, start, step, end, intval):
		# reset to start, waiting for ready
		self.atten.SetGroupValue(start)
		time.sleep(5)

		tab_rxbps = {}
		for av in range(start, end, step):
			self.atten.SetGroupValue(av)
			stat_count = 10
			real_intval = intval / stat_count
			rx_bps = []
			for tv in range(0, stat_count, 1):
				# limit update rate
				if tv % 4 == 0:
					self.trex_client._show_global_stats()

				# collection stats
				stats = self.trex_client.get_stats(ports=[0, 1], sync_now=True)
				# self.json_dump(stats['global']) --- trace
				# rx samples to Mbps
				rx_bps.append(int(stats['global']['rx_bps'] / 1000000))
				time.sleep(real_intval)
			# combin
			tab_rxbps.update({av: rx_bps[:]})

		return tab_rxbps

	def do_run(self, atten_start, atten_step, atten_end, time_intval, rota_angles, auto_report, test_prefix):
		''' report '''
		print("test and report, atten from {0} step {1} to {2}".format(atten_start, atten_step, atten_end))
		print("Target: {0} cut to 5*X = {1}".format(atten_end, int(atten_end / 5) * 5), color='red')
		print("  Angle list: {}".format(rota_angles), color='green')
		print("  Atten Group: from {:d} to {:d} step:{:d} intv: {:d} sec.\n".format(atten_start, atten_end, atten_step, time_intval))

		# transform
		if type(rota_angles) == 'list':
			for idx in range(0, len(rota_angles), 1):
				point = rota_angles[idx]
				if point > 15:
					rota_angles[idx] = self.rotate.GetPoint(point)
					print("transform {} to {}\n".format(point, rota_angles[idx]))
		else:
			rota_angles = []

		tab_rota={}
		if len(rota_angles) == 0:
			samples = self.run_point_atten(atten_start, atten_step, atten_end, time_intval)
			tab_rota[0] = samples
		else:
			for point in rota_angles:
				angle = self.rotate.GetAngle(point)
				print("rotate to angle: {}".format(angle))
				self.rotate.SetValue(point)
				samples = self.run_point_atten(atten_start, atten_step, atten_end, time_intval)
				tab_rota[angle] = samples

		# self.json_dump(table_rxbps) # --- trace
		self.table_xlsx = tab_rota

		if auto_report == 1:
			self.update_timestamp()
			self.build_xlsx("auto-{0}-{1}.xlsx".format(self.time_prefix, test_prefix))

	def set_plugin_console(self, trex_console):
		self.console = trex_console
