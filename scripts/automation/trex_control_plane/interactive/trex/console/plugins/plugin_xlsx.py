#!/usr/bin/env python3

from trex.console.plugins import *
from trex.attenuators.attenuator import AttenGroup, AttenUnit
from trex.attenuators.usbtty import SerialttyUSB

import pprint
# import serial

'''
XLSX sheets plugin
'''

class Xlsx_Plugin(ConsolePlugin):
	def plugin_description(self):
		return 'Simple example'

	def __init__(self):
		super(Xlsx_Plugin, self).__init__()
		self.console = None
		self.Ser = SerialttyUSB(None)
		atten_sc = AttenUnit("HP33321-SC", 3, [20, 40, 10])
		atten_sd = AttenUnit("HP33321-SD", 3, [30, 40, 5])
		atten_sg = AttenUnit("HP33321-SG", 3, [20, 5, 10])
		# init group
		atten_gp_sc_sg = AttenGroup("SC-SG", self.Ser, [atten_sg, atten_sc])
		# atten_gp_sc_sg.Dump()
		self.atten_group = atten_gp_sc_sg


	# used to init stuff
	def plugin_load(self):
		# Adding arguments to be used at do_* functions
		self.add_argument('-f', '--file', action = 'store', nargs = '?', default = 'test_report.xlsx', type = str, required = True, 
			dest = 'xlsx_report', # <----- variable name to be used
				help = 'file name to creat xlsx report')
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

		if self.console is None:
			raise TRexError("Trex console must provided")

	# We build argparser from do_* functions, stripping the "do_" from name
	def do_xlsx(self, xlsx_report): # <------ name was registered in plugin_load
		''' dump statistics to sheets file '''
		self.trex_client.logger.info('Sheets will dump to: %s!' % bold(xlsx_report.capitalize())) # <--- trex_client is set implicitly

	def do_show(self):
		''' dump info '''
		stats = self.trex_client.get_stats(ports=[0, 1], sync_now = True)
		# print(json.dumps(stats, indent = 4, separators=(',', ': '), sort_keys = True))
		print(json.dumps(stats['global'], indent=2, separators=(',', ': '), sort_keys = True))

	def do_show_atten(self):
		''' dump current attenuator grop '''
		self.atten_group.Dump()

	def do_test_process(self, atten_start, atten_step, atten_end, time_intval):
		''' report '''
		print("test and report, atten from {0} step {1} to {2}".format(atten_start, atten_step, atten_end))

		# init status
		self.atten_group.SetValue(atten_start)
		time.sleep(10)

		print("Target: {0} cut to 5*X = {1}".format(atten_end, int(atten_end / 5) * 5))
		print("  Atten Group: from {:d} to {:d} step:{:d} intv: {:d} sec.\n".format(atten_start, atten_end, atten_step, time_intval))
		for av in range(atten_start, atten_end + 5, atten_step):
			self.atten_group.SetValue(av)
			time.sleep(time_intval)

	def set_plugin_console(self, trex_console):
		self.console = trex_console
