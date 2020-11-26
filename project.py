
class DB:

	def __init__(self):
		self.tm = self.TM()
		self.num_of_sites = 10
		self.sites = [self.DM() for i in range(self.num_of_sites + 1)]

	class TM:
		
		# status constants
		DOWN = 0
		UP = 1
		RECOVER = 2

		# initialize TM: start time, end time, is site up array, is read-only array, waiting commands, wait for
		def __init__(self):
			self.num_of_sites = 10
			self.start_time = {} # dictionary with key = transaction no, value = start time
			self.end_time = {}
			self.status = [self.UP for x in range(self.num_of_sites + 1)] # 0 - down 1 - up normally 2 - just recovered
			self.is_read_only = [False] * (self.num_of_sites + 1)
			self.waiting = [] # accumulate waiting command
			self.waits_for = [] # wait-for edges, used for deadlock detection
			self.accessed_sites = {} # key: transaction, value: list of sites it has accessed

		# def deadlock_detect():

		def print_state(self):
			print("status: ", self.status)
	
	class DM:

		def __init__(self):
			self.num_of_var = 20
			self.curr_vals = {} # is a map: has key means try to write to it, when site is down, erase its value but leave the key. 
			self.commit_vals = [x * 10 for x in range(self.num_of_var + 1)]
			self.lock_table = {}
		
		def print_state(self):
			print("commit values: ", self.commit_vals)
		# initialize variables' values
		# def initialize():

	# read a line from input file and determine what command it is
	# def read_in(line):


	# def begin(transaction, time):
		# just record its begin time

	# return the value
	# def read(transaction, val):

	# def read_only(transaction, var):

	# def write(transaction, var, value):

	# return commit or abort
	# def end(t):
		# release locks

		# check if all sites t has accessed can commit, which means assign curr_vals to commit_vals
		# (may not need to do this since we already abort the transaction in fail instruction)

		# commit values: assign curr_vals to commit_vals

	# def fail(site):
		# erase lock table + curr_vals?

		# check if a transactionn has accessed this site, if so, abort it right away

	# def recover(site):

	# def dump():

	def querystate(self):
		print("Transaction Manager State:")
		self.tm.print_state()
		print("Sites: ")
		for s in self.sites:
			s.print_state()


def main():
	# create a DB
	db = DB()

	# read a file line by line
	f = open("input.txt", "r")
	for x in f:
		print(x)

	db.querystate()


if __name__ == "__main__":
    main()

