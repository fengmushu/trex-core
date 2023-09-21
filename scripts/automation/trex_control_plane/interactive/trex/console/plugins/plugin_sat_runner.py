#!/usr/bin/env python3
#coding=utf-8 

from trex.console.plugins import *
from trex.attenuators.attenuator import * 	# AttenGroup, AttenUnit, atten_adaura
from trex.attenuators.usbtty_geehy import * 	# tty_dio_rotray, tty_usb_geehy

import pprint
import xlsxwriter
import random
import math

USE_ATTEN_HP33321_SX 	= 0
USE_ATTEN_ADAURA 	= 1
ATTEN_SELECTION_DEF	= USE_ATTEN_ADAURA
'''Step Attenuator selection for test runner and XLSX sheets plugin'''
XLSX_HEADER_OFFSET 	= 1
'''Datasets lable'''
XLSX_SECTION_OFFSET 	= 6
'''Section blank line'''
STEP_SAMPLE_COUNT 	= 1
'''The smaple count of each attenuator step'''
DEF_STA_IP_ADDR		= '192.168.10.230'
'''The ip addr of station'''
DEF_STA_PASSWD		= 'admin'
'''The webui passwd of station'''
DEF_ATTEN_VALUE		= 0

class SatRunner_Plugin(ConsolePlugin):
	def plugin_description(self):
		return 'Simple example'

	def __init__(self):
		super(SatRunner_Plugin, self).__init__()
		self.console = None
		self.rpc_router = None
		self.sta_addr = DEF_STA_IP_ADDR
		self.sta_passwd = DEF_STA_PASSWD
		self.time_fraction = 0
		self.time_fraction_passed = 0
		self.xlsx = {}
		self.atten_selection = ATTEN_SELECTION_DEF
		self.dir_report = '/home/trex/report/'
		self.header_offset = XLSX_HEADER_OFFSET
		self.section_offset = XLSX_SECTION_OFFSET
		self.update_ts_subfix()
		self.init_atten_group()
		self.atten.set_group_value(DEF_ATTEN_VALUE)
		self.init_sta_rpc()
		self.rotate = tty_dio_rotray(None)
		self.rotate.set_break(0)
		self.rotate.set_break(1)
		self.rotate.set_original()
		self.beep_ding()
		self.prepared = False

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

	def update_ts_subfix(self):
		self.subfix_time = time.strftime("%Y-%m-%d-%H%M%S", time.localtime())
		return self.subfix_time

	def update_ts(self):
		self.ts = time.time()
		return self.ts

	def build_xlsx(self, filename):
		ts = time.localtime()
		dir_date = time.strftime("%Y-%m-%d", ts)
		dir_name = "{0}/{1}/".format(self.dir_report, dir_date)
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
			link_quality = ['LinkQ', ]
			throughput = ['Throughput, {}°'.format(angle), ]
			for db, sample in samples.items():
				atten.append(db)
				total = 0
				xtps = sample[0]
				for snapshot in xtps:
					total += snapshot
				average = total / len(xtps)
				throughput.append(average)
				link_quality.append(sample[1][0])
				signal_lvl.append(sample[1][1])
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
			sheet_dataraw.write_column('D{:d}'.format(offset), link_quality)

			ds_atten  = "='DataRaw'!$A${:d}:$A${:d}".format(offset + 1, offset + len(atten) - 1)
			ds_line_thoughput = "='DataRaw'!$B${:d}:$B${:d}".format(offset + 1, offset + len(throughput) - 1)
			ds_line_rssi = "='DataRaw'!$C${:d}:$C${:d}".format(offset + 1, offset + len(signal_lvl) - 1)

			# update to combin chart
			chart_comb = book.add_chart({'type': 'line'})
			chart_comb.add_series({
				'categories': ds_atten, 
				'values': ds_line_thoughput,
				'name': "='DataRaw'!$B{:d}".format(offset),
				})
			chart_comb.add_series({
				'values': ds_line_rssi,
				'name': "='DataRaw'!$C{:d}".format(offset),
				'y2_axis': True,
			})
			sheet_dataraw.insert_chart('F{:d}'.format(offset), chart_comb)

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
			self.atten = atten_adaura("ADAURA-63", None)
			self.atten_base_value = 10
			self.atten.dump()
		elif atten == USE_ATTEN_HP33321_SX:
			# Hp3X-SC/SD/SG serises
			ser = tty_usb_geehy(None)
			atten_sc = atten_unit("HP33321-SC", 3, [20, 40, 10])
			atten_sd = atten_unit("HP33321-SD", 3, [30, 40, 5])
			atten_sg = atten_unit("HP33321-SG", 3, [20, 5, 10])
			# init group
			atten_gp_sc_sg = atten_group("SC-SG", ser, [atten_sg, atten_sc])
			# atten_gp_sc_sg.dump()
			self.atten = atten_gp_sc_sg
			self.atten_base_value = 15
			self.atten.dump()
		else:
			print("Not supported attenuator: {}".format(atten))
			raise Exception("Attenuator type '{}' not supported".format(atten))

	def init_sta_rpc(self):
		''' setup openwrt rpc '''
		from openwrt_luci_rpc import OpenWrtRpc

		try:
			router = OpenWrtRpc(self.sta_addr, 'root', self.sta_passwd)
			if not router.is_logged_in():
				print("OpenWrt-RPC: login failed\n", color='red')
				return False
		except:
			print("OpenWrt-RPC: {} connection failed\n".format(self.sta_addr), color='red')
			return False
		hosts = router.get_all_connected_devices()
		print(hosts)
		self.rpc_router = router
		return True

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

		self.update_ts_subfix()
		self.build_xlsx("report-{0}.xlsx".format(self.subfix_time, file_report))

	def do_show(self):
		''' dump info '''
		self.trex_client._show_global_stats()
		stats = self.trex_client.get_stats(ports=[0, 1, 2, 3], sync_now = True)
		# print(json.dumps(stats, indent = 4, separators=(',', ': '), sort_keys = True))
		self.json_dump(stats['global'])

	def do_atten(self):
		''' dump current attenuator grop '''
		self.atten.dump()

	def json_dump(self, o):
		print(json.dumps(o, indent=2, separators=(',', ': '), sort_keys = True))

	def run_samples(self, samples, intval):
		self.beep_short()
		time.sleep(1)
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
			print('{}'.format('x'))
		return rx_bps

	def update_rssi(self):
		rssi = -127
		if self.rpc_router != None:
			linkq, _, rssi = self.rpc_router.get_rssi()

		print("Link quality: {} with rssi: {}".format(linkq, rssi), color='red')
		return [linkq, rssi]

	def update_processbar(self):
		self.time_fraction_passed += 1
		time_passed = int(self.update_ts()- self.ts_start)
		time_needed = int(time_passed * self.time_fraction / self.time_fraction_passed)
		self.time_needed = time_needed
		self.time_passed = time_passed
		print("Progress bar {}:{} as {:.2f}% ".format(time_passed, time_needed - time_passed,\
					        100 * time_passed / time_needed), color='green', format='blink')
		return self.time_passed, self.time_needed

	def gen_report(self):
		report_name = self.build_xlsx("{0}-{1}-{2}-{3}.xlsx".format(self.test_prefix, self.update_ts_subfix(), self.subfix_mode, self.subfix_rota))
		self.beep_long()
		print("Test report: {}".format(report_name))

	def do_prepare(self, atten_start, atten_step, atten_stop, continuous, atten_value, precision, time_intval, rota_angles, auto_report, test_prefix):
		'''
  		  prepare there's two mode: 
			- mode continuous run with specified attenuator value, will get the report of throughput by time;
			- mode step down the attenuator from start to stop, will get the report of throughput by attenuator value;
			- both these two mode can run with diffirent angles;
		'''
		if continuous == 0:
			self.atten_range = range(atten_start, atten_stop, atten_step)
			self.atten_range_len = len(self.atten_range)
			self.precision = int(time_intval / precision)
			self.sample_intv = time_intval
			time_fraction = math.ceil((atten_stop - atten_start) / atten_step)
			self.subfix_mode = "Atten-{}-{}-{}-{}".format(atten_start, atten_step, atten_stop, time_intval)
			print("Test and report, atten from {0} step {1} to {2}".format(atten_start, atten_step, atten_stop))
			print("Target: {0} cut to 5*X = {1}".format(atten_stop, int(atten_stop / 5) * 5), color='red')
			print("  Angle {}: {}".format(type(rota_angles), rota_angles), color='green')
			print("  Atten group: from {:d} to {:d} step: {:d} intv: {:d} sec, {:d}.\n".format(atten_start, atten_stop, atten_step, time_intval, time_fraction))
		else:
			self.atten_range_len = 1
			self.atten_range = [atten_value, ]
			self.precision = precision
			self.sample_intv = int(continuous / precision)
			time_fraction = math.ceil(continuous / precision)
			self.subfix_mode = "Contu-{}-{}".format(continuous, atten_value)
			print("Run continuous scan: {:d} secs, {:d}".format(continuous, time_fraction), color='green', format='bold')

		self.test_prefix = test_prefix
		self.continuous = continuous
		self.time_fraction = time_fraction
		self.time_fraction_passed = 0
		self.ts_start = None
		if atten_value == 0:
			atten_value = atten_start
		self.atten_value = atten_value
  
		if type(rota_angles) == list:
			self.time_fraction *= len(rota_angles)
			self.subfix_rota = "Rota-{}-{}-{}".format(len(rota_angles), self.rotate.get_angle(rota_angles[0]), self.rotate.get_angle(rota_angles[-1]))
			for idx in range(0, len(rota_angles), 1):
				point = rota_angles[idx]
				if point > 15:
					rota_angles[idx] = self.rotate.get_point(point)
					print("transform {} to {}".format(point, rota_angles[idx]))
		else:
			rota_angles = [rota_angles,]
			self.subfix_rota = ""
		self.rota_angles = rota_angles
		print("Rotar angles:{}".format(self.rota_angles))

		self.rota_angle_idx = 0
		self.rota_angle_len = len(rota_angles)
		self.atten_range_idx = 0
		self.xlsx = {}
		self.auto_report = auto_report
		self.prepared = True

	def do_run_next(self) -> int:
		''' on point per start trigger '''
		if self.prepared != True:
			print("Call prepare first", color="red")
			return 0

		if self.ts_start == None:
			# start
			self.ts_start = self.update_ts()
			self.update_ts_subfix()
			self.rotate.set_original()

		# run one sample
		if self.atten_range_idx == 0:
			# first point
			self.atten.set_group_value(DEF_ATTEN_VALUE)
			if self.init_sta_rpc() != True:
				print("Openwrt RPC link loss\n", color="red")
			time.sleep(10)
			self.atten_samples = {}

		cur_atten = self.atten_range[self.atten_range_idx]
		self.atten.set_group_value(cur_atten)

		rxbps = self.run_samples(self.precision, self.sample_intv)
		self.atten_samples.update({self.atten_base_value + cur_atten: [rxbps[:], self.update_rssi()]})

		self.atten_range_idx += 1
		if self.atten_range_idx == self.atten_range_len:
			# finished one angle/round
			self.atten_range_idx = 0
			point = self.rota_angles[self.rota_angle_idx]
			angle = self.rotate.get_angle(point)
			self.rotate.set_value(point)
			self.xlsx.update({angle: self.atten_samples})
			self.update_processbar()
			self.rota_angle_idx += 1
			if self.rota_angle_idx < self.rota_angle_len:
				return 1
			else:
				# finised
				# self.json_dump(self.xlsx)
				if self.auto_report != 0:
					self.gen_report()
				print("Finished\n", color='green', format='bold')
				return 0

	def do_run_all(self):
		''' run all test step '''
		while self.do_run_next() != 0:
			print("~")

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
			ds_meta = {}
			for at in attens:
				base = []
				for sample in range(1, 10, 1):
					base.append(random.randint(100000000, 200000000) / at)
				ds_meta.update({at: [base[:], -127]})
			ds_ut.update({ag: ds_meta.copy()})
		self.xlsx = ds_ut
		self.update_ts_subfix()
		self.build_xlsx("unitest-{0}-{1}.xlsx".format("report", self.subfix_time))

	def do_unit_test_rpc(self):
		''' unit test for OpenWrt-RPC subsystem '''
		from openwrt_luci_rpc import OpenWrtRpc

		router = OpenWrtRpc(DEF_STA_IP_ADDR, 'root', DEF_STA_PASSWD)
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

		print(router.get_rssi(None))

	def echo(self, fname):
		''' play audio <fname> '''
		try:
			from pygame import mixer

			mixer.init()
			mixer.music.load("../audio/{}".format(fname))
			mixer.music.play()
			while mixer.music.get_busy():
				''' wait for music to finish playing '''
				time.sleep(1)
			mixer.music.stop()
			mixer.quit()
		except Exception as e:
			print(e)
			print("Beep error, ignored\n", color='yellow')

	def beep_short(self):
		self.echo('beep-short.mp3')

	def beep_long(self):
		''' beep long '''
		self.echo('beep-long.mp3')

	def beep_ding(self):
		''' beep ding '''
		self.echo('ding.mp3')

	def do_unit_test_audio(self):
		''' unit test for wav,mp3 '''
		# os.system('pwd')
		self.beep_short()
		self.beep_ding()
		self.beep_long()
