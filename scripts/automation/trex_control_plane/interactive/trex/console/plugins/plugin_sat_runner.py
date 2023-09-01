#!/usr/bin/env python3
#coding=utf-8 

from trex.console.plugins import *
from trex.attenuators.attenuator import * 	# AttenGroup, AttenUnit, AttenAdaura
from trex.attenuators.usbtty_geehy import * 	# ttyDioRotary, ttyUsbGeehy

import pprint
import xlsxwriter
import random

USE_ATTEN_HP33321_SX 	= 0
USE_ATTEN_ADAURA 	= 1
ATTEN_SELECTION_DEF	= USE_ATTEN_HP33321_SX
'''Step Attenuator selection for test runner and XLSX sheets plugin'''
XLSX_HEADER_OFFSET = 1
'''Datasets lable'''
XLSX_SECTION_OFFSET = 6
'''Section blank line'''
STEP_SAMPLE_COUNT = 1
'''The smaple count of each attenuator step'''
DEF_STA_IP_ADDR='192.168.10.200'
'''The ip addr of station'''
DEF_STA_PASSWD='admin'
'''The webui passwd of station'''

class SatRunner_Plugin(ConsolePlugin):
	def plugin_description(self):
		return 'Simple example'

	def __init__(self):
		super(SatRunner_Plugin, self).__init__()
		self.console = None
		self.rpc_router = None
		self.xlsx = {}
		self.atten_selection = ATTEN_SELECTION_DEF
		self.dir_report = '/home/trex/report/'
		self.header_offset = XLSX_HEADER_OFFSET
		self.section_offset = XLSX_SECTION_OFFSET
		self.rotate = ttyDioRotary(None)
		self.update_timestamp()
		self.init_atten_group()

	# used to init stuff
	def plugin_load(self):
		# Adding arguments to be used at do_* functions
		self.add_argument('-f', '--file', action = 'store', nargs = '?', default = 'test_report.xlsx', type = str, required = False, 
			dest = 'file_report', # <----- variable name to be used
				help = 'file name to creat xlsx report')
		
		self.add_argument('-d', '--dir', action = 'store', nargs = '?', default = '/home/trex/report/', type = str, required = False, 
			dest = 'dir_report', # <----- variable name to be used
				help = 'directory to creat xlsx reports')

		self.add_argument('--prefix', action = 'store', nargs = '?', default = 'anonymous', type = str, required = False, 
			dest = 'test_prefix', # <----- variable name to be used
				help = 'file name prefix to creat xlsx report')

		self.add_argument('--start', action = 'store', nargs='?', default = 0, type=int, required = False, 
			dest = "atten_start", 
				help = "init atten value")

		self.add_argument('--step', action = 'store', nargs='?', default = 5, type=int, required=False,
			dest = "atten_step", 
				help = "atten step up/down value")

		self.add_argument('--stop', action = 'store', nargs = "?", default = 60, type = int, required=False,
			dest = "atten_stop", 
				help = "atten stop and keep value")

		self.add_argument('--intv', action = 'store', nargs = "?", default = 10, type = int, required=False,
			dest = "time_intval", 
				help = "auto atten time intval sec")

		self.add_argument('--angles', action = 'store', nargs = "*", default = 0, type = int, required=False,
			dest = "rota_angles", 
				help = "set the angle to rotate,  <point: 0 1 2 3 4 ... 11> or <angle: 0 30 60 90 ... 360>: from 0-360°, each step 30°")

		self.add_argument('--auto-report', action = 'store', nargs = "?", default = 1, type = int, required=False,
			dest = "auto_report", 
				help = "auto generate test report xlsx")

		self.add_argument('--continuous', action = 'store', nargs = "?", default = 0, type = int, required=False,
			dest = "continuous", 
				help = "countinuous mode run 'N' sec, and with sample precision/sec")

		self.add_argument('--atten-value', action='store', nargs = "?", default = 0, type = int, required=False,
			dest = "atten_value", 
				help = "set default runtime attenuator value")

		self.add_argument('--precision', action='store', nargs='?', default = STEP_SAMPLE_COUNT, type = int, required=False,
			dest = "precision", 
				help = "the sample precision default 1/sec")

		self.add_argument('--atten-selection', action='store', nargs='?', default = USE_ATTEN_ADAURA, type = int, required=True,
			dest = "atten_selection",
				help = "0: 'HP33321-SX', 1 <default>: 'Adaura 0-63db, stop 0.5'")

		self.add_argument('--sta-addr', action='store', nargs='?', default = DEF_STA_IP_ADDR, type = str, required=False,
			dest = "sta_addr",
				help = 'the ip address of station (wlan-client)')

		self.add_argument('--sta-passwd', action = 'store', nargs='?', default = DEF_STA_PASSWD, type = str, required=False,
			dest = "sta_passwd",
				help = "the webui login passwd of station (wlan-client)")

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
		keep_angle_scan_atten = self.xlsx
		'''
		first page is graphic report
		'''
		sheet_dashboard = book.add_worksheet("Dashboard")
		sheet_dataraw = book.add_worksheet("DataRaw")
		chart_radar = book.add_chart({'type': 'radar', 'subtype': 'with_markers'})

		# angle -> atten -> average
		offset = self.header_offset
		keep_atten_scan_angle = {}
		angles = keep_angle_scan_atten.keys()
		point_idx = 0
		for angle, samples in keep_angle_scan_atten.items():
			atten 	= ['Atten|Time', ]
			signal_lvl = ['Rssi', ]
			throughput = ['Throughput, {}°'.format(angle), ]
			for db, sample in samples.items():
				atten.append(db)
				total = 0
				xtps=sample[0]
				rssi=sample[1]
				for snapshot in xtps:
					total += snapshot
				average = total / len(xtps)
				throughput.append(average)
				signal_lvl.append(rssi)
				''' =DataRaw!$B$2,DataRaw!$B$11,DataRaw!$B$20,DataRaw!$B$29,DataRaw!$B$38,DataRaw!$B$47 '''
				if not db in keep_atten_scan_angle:
					keep_atten_scan_angle[db] = {}
				if point_idx == 0:
					keep_atten_scan_angle[db].update({angle: "='DataRaw'!$B${:d}".format(offset + len(atten) - 1 )})
				else:
					keep_atten_scan_angle[db].update({angle: ",'DataRaw'!$B${:d}".format(offset + len(atten) - 1 )})

			sheet_dataraw.write_column('A{:d}'.format(offset), atten)
			sheet_dataraw.write_column('B{:d}'.format(offset), throughput)
			sheet_dataraw.write_column('C{:d}'.format(offset), signal_lvl)

			ds_atten  = "='DataRaw'!$A${:d}:$A${:d}".format(offset + 1, offset + len(atten) - 1)
			ds_line_thoughput = "='DataRaw'!$B${:d}:$B${:d}".format(offset + 1, offset + len(throughput) - 1)
			ds_line_rssi = "='DataRaw'!$C${:d}:$C${:d}".format(offset + 1, offset + len(signal_lvl) - 1)

			chart_tput = book.add_chart({'type': 'line'})
			chart_tput.add_series({
				'categories': ds_atten, 
				'values': ds_line_thoughput,
				'name': "='DataRaw'!$B{:d}".format(offset),
				})
			chart_tput.set_x_axis({'name': "Atten|Time"})
			sheet_dataraw.insert_chart('D{:d}'.format(offset), chart_tput)

			chart_rssi = book.add_chart({'type': 'line'})
			chart_rssi.add_series({
				'categories': ds_atten, 
				'values': ds_line_rssi,
				'name': "='DataRaw'!$C{:d}".format(offset),
				})
			chart_rssi.set_x_axis({'name': "Atten|Time"})
			sheet_dataraw.insert_chart('K{:d}'.format(offset), chart_rssi)

			offset += len(atten) + self.section_offset
			point_idx += 1

		# build radar chart
		offset = self.header_offset
		v_angles = ["Angle",]
		v_angles.extend(angles)
		sheet_dashboard.write_column('A{:d}'.format(offset), v_angles)
		''' =Dashboard!$A$2:$A$8 '''
		ds_angles = "='Dashboard'!$A${:d}:$A${:d}".format(offset + 1, offset + len(angles))

		chart_radar.set_x_axis({'name': "Angle"})
		for db, angs in keep_atten_scan_angle.items():
			ds_angle_throughput = ""
			for angle, ds in angs.items():
				ds_angle_throughput += ds
			# print(ds_angle_throughput)
			chart_radar.add_series({
				'categories': ds_angles,
				"values": ds_angle_throughput,
				"name": "{} db|sec".format(db)
			})
		sheet_dashboard.insert_chart('D1', chart_radar)
		book.close()
		return dir_name + filename

	def init_atten_group(self):
		atten = self.atten_selection
		if atten == USE_ATTEN_ADAURA:
			# Adaura-63: 0-63db, 0.5db step
			self.atten = AttenAdaura("ADAURA-63", None)
			self.atten_base_value = 10
			self.atten.Dump()
		elif atten == USE_ATTEN_HP33321_SX:
			# Hp3X-SC/SD/SG serises
			ser = ttyUsbGeehy(None)
			atten_sc = AttenUnit("HP33321-SC", 3, [20, 40, 10])
			atten_sd = AttenUnit("HP33321-SD", 3, [30, 40, 5])
			atten_sg = AttenUnit("HP33321-SG", 3, [20, 5, 10])
			# init group
			atten_gp_sc_sg = AttenGroup("SC-SG", ser, [atten_sg, atten_sc])
			# atten_gp_sc_sg.Dump()
			self.atten = atten_gp_sc_sg
			self.atten_base_value = 15
			self.atten.Dump()
		else:
			print("Not supported attenuator: {}".format(atten))
			raise Exception("Attenuator type '{}' not supported".format(atten))

	def init_sta_rpc(self):
		''' setup openwrt rpc '''
		from openwrt_luci_rpc import OpenWrtRpc

		router = OpenWrtRpc(self.sta_addr, 'root', self.sta_passwd)
		if not router.is_logged_in():
			print("rpc: login failed\n", color='red')
			return
		self.rpc_router = router

	def do_setup(self, atten_selection, sta_addr, sta_passwd):
		''' setup base vars of current system '''
		if atten_selection == USE_ATTEN_ADAURA:
			print("atten selection is 'ADAURA-63'")
		else:
			print("atten selection is 'HP33321-SX'")
		self.atten_selection = atten_selection
		self.init_atten_group()

		self.sta_addr = sta_addr
		self.sta_passwd = sta_passwd
		self.init_sta_rpc()

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
		stats = self.trex_client.get_stats(ports=[0, 1, 2, 3], sync_now = True)
		# print(json.dumps(stats, indent = 4, separators=(',', ': '), sort_keys = True))
		self.json_dump(stats['global'])

	def do_atten(self):
		''' dump current attenuator grop '''
		self.atten.Dump()

	def json_dump(self, o):
		print(json.dumps(o, indent=2, separators=(',', ': '), sort_keys = True))

	def run_samples(self, samples, intval):
		rx_bps = []
		for tv in range(0, samples, 1):
			# limit update rate
			if tv % 5 == 0:
				self.trex_client._show_global_stats()

			# collection stats
			stats = self.trex_client.get_stats(ports=[0, 1, 2, 3], sync_now=True)
			# stats = self.trex_client.get_stats(ports=[2, 3], sync_now=True)
			# stats = self.trex_client.get_stats(sync_now=True)
			# self.json_dump(stats['global']) --- trace
			# rx samples to Mbps
			rx_bps.append(int(stats['global']['rx_bps'] / 1000000))
			time.sleep(intval)
		return rx_bps

	def update_rssi(self):
		rssi = -127
		if self.rpc_router != None:
			rssi = self.rpc_router.get_rssi()
		return rssi

	def run_point_atten(self, start, step, stop, intval, cont, atten_def, precision):
		''' reset to default, waiting for ready '''
		print("Reset default atten...")
		self.atten.SetGroupValue(atten_def)
		time.sleep(15)

		tab_rxbps = {}
		if cont == 0:
			for av in range(start, stop, step):
				self.atten.SetGroupValue(av)
				rx_bps = self.run_samples(precision, intval / precision)
				tab_rxbps.update({self.atten_base_value + av: [rx_bps[:], self.update_rssi()]})
		else:
			for sp in range(0, cont, precision):
				print("Sample round: {}".format(sp), color='red')
				rx_bps = self.run_samples(precision, 1)
				tab_rxbps.update({sp: [rx_bps[:], self.update_rssi()]})
		return tab_rxbps

	def do_run(self, atten_start, atten_step, atten_stop, continuous, atten_value, precision, time_intval, rota_angles, auto_report, test_prefix):
		'''
		<run testor> there's two mode: 
			- mode continuous run with specified attenuator value, will get the report of throughput by time;
			- mode step down the attenuator from start to stop, will get the report of throughput by attenuator value;
			- both these two mode can run with diffirent angles;
		'''
		if continuous == 0:
			print("Test and report, atten from {0} step {1} to {2}".format(atten_start, atten_step, atten_stop))
			print("Target: {0} cut to 5*X = {1}".format(atten_stop, int(atten_stop / 5) * 5), color='red')
			print("  Angle {}: {}".format(type(rota_angles), rota_angles), color='green')
			print("  Atten group: from {:d} to {:d} step: {:d} intv: {:d} sec.\n".format(atten_start, atten_stop, atten_step, time_intval))
		else:
			print("Run continuous scan: {:d} secs".format(continuous), color='green', format='bold')

		if atten_value == 0:
			atten_value = atten_start

		# transform
		if type(rota_angles) == list:
			for idx in range(0, len(rota_angles), 1):
				point = rota_angles[idx]
				if point > 15:
					rota_angles[idx] = self.rotate.GetPoint(point)
					print("transform {} to {}".format(point, rota_angles[idx]))
		else:
			rota_angles = []

		self.rotate.SetOriginal()
		print("Rotar angles:{}".format(rota_angles))
		ds_rota={}
		if len(rota_angles) == 0:
			samples = self.run_point_atten(atten_start, atten_step, atten_stop, time_intval, continuous, atten_value, precision)
			ds_rota[0] = samples
		else:
			self.rotate.SetValue(0)
			time.sleep(5)
			for point in rota_angles:
				angle = self.rotate.GetAngle(point)
				print("Rotar to angle: {}".format(angle), color='green', format='bold')
				self.rotate.SetValue(point)
				samples = self.run_point_atten(atten_start, atten_step, atten_stop, time_intval, continuous, atten_value, precision)
				ds_rota[angle] = samples
		# finished, resotre default values
		# self.rotate.SetOriginal()
		self.atten.SetGroupValue(atten_value)
		# self.json_dump(ds_rota) # --- trace
		self.xlsx = ds_rota

		report_name = ""
		if auto_report == 1:
			self.update_timestamp()
			report_name = self.build_xlsx("{0}-{1}-{2}-{3}-{4}.xlsx".format(test_prefix, self.time_prefix, atten_start, atten_step, atten_stop))

		try:
			self.beep()
		except:
			print("Test finished, beep not supported", color='yellow')
		print("Test report: {}".format(report_name))

	def set_plugin_console(self, trex_console):
		self.console = trex_console

	def do_unit_test_report(self):
		''' unit test, for reporter, rotray, attenuator... '''
		ds_ut = {}
		ds_rota = []

		angles = [0, 30, 60, 90, 120, 150, 180]
		attens = [15, 20, 25, 30, 35, 40, 45, 50]
		for ag in angles:
			''' data sets link this '''
			ds_meta = {
				#  '15': [100000, 200000, 300000, 400000, 500000, 600000],
				#  '20': [80000, 200000, 300000, 400000, 500000, 60000],
				#  '25': [70000, 200000, 300000, 400000, 500000, 6000],
				#  '30': [60000, 200000, 300000, 400000, 50000, 6000],
				#  '35': [50000, 200000, 300000, 400000, 5000, 600 ],
				#  '40': [40000, 200000, 300000, 400000, 500, 600],
				#  '45': [30000, 200000, 300000, 400, 500, 600],
			}
			for at in attens:
				base = []
				for sample in range(1, 10, 1):
					base.append(random.randint(100000000, 200000000) / at)
				ds_meta.update({at: base})
			ds_ut.update({ag: ds_meta.copy()})
		self.xlsx = ds_ut
		self.update_timestamp()
		self.build_xlsx("unitest-{0}-{1}.xlsx".format("report", self.time_prefix))

	def do_unit_test_rpc(self):
		''' unit test for RPC subsystem '''
		from openwrt_luci_rpc import OpenWrtRpc

		router = OpenWrtRpc('192.168.10.200', 'root', 'admin')
		if not router.is_logged_in():
			print("rpc: login failed\n", color='red')
			return

		device_dict = []
		result = router.get_all_connected_devices(True)
		for device in result:
			mac = device.mac
			name = device.hostname
			# convert class to a dict
			device_dict.append(device._asdict())
		print(device_dict)

		print(router.get_rssi())

	def beep(self):
		''' beep '''
		from pygame import mixer

		mixer.init()
		mixer.music.load("../audio/dididiba.mp3")
		mixer.music.play()
		while mixer.music.get_busy():  # wait for music to finish playing
			time.sleep(1)
		mixer.music.stop()

	def do_unit_test_audio(self):
		''' unit test for wav,mp3 '''
		# os.system('pwd')
		self.beep()
