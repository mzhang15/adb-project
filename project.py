
class DB:

	def __init__(self):
		self.tm = self.TM()
		
	class TM:
		
		# status constants
		DOWN = 0
		UP = 1
		RECOVER = 2

		# initialize TM: start time, end time, is site up array, is read-only array, waiting commands, wait for
		def __init__(self):
			self.num_of_sites = 10
			self.sites = [self.DM() for i in range(self.num_of_sites + 1)]

			self.curr_time = 0
			self.start_time = {} # dictionary with key = transaction no, value = start time
			self.end_time = {}
			self.status = [self.UP for x in range(self.num_of_sites + 1)] # 0 - down 1 - up normally 2 - just recovered
			self.is_read_only = [False] * (self.num_of_sites + 1)
			self.waiting = [] # accumulate waiting command
			self.waits_for = [] # wait-for edges, used for deadlock detection
			self.accessed_sites = {} # key: transaction, value: list of sites it has accessed



		def read_in_instruction(self, line):
			# increment time
			self.curr_time += 1
			print(self.curr_time)

			# parse instruction
			l = line.index("(")
			r = line.index(")")
			name = line[0:l]
			args = line[l + 1:r].split(",")

			if name == "begin": 
				assert len(args) == 1
				self.begin(args[0], self.curr_time)
			elif name == "beginRO":
				assert len(args) == 1
				self.beginRO(args[0], self.curr_time)
			elif name == "R":
				assert len(args) == 2
				print(name)
			elif name == "W":
				assert len(args) == 3
				self.write(args[0], args[1], args[2])
			elif name == "end":
				assert len(args) == 1
				print(name)
			elif name == "fail":
				assert len(args) == 1
				print(name)
			elif name == "recover":
				assert len(args) == 1
				print(name)
			elif name == "dump":
				print(name)
			else:
				print("Error: unknown command ", name)

			print(args)

		def begin(self, transaction, time):
			# just record its begin time
			self.start_time[transaction] = time

		def beginRO(self, transaction, time):
			self.start_time[transaction] = time
			t_idx = int(transaction[1:])
			self.is_read_only[t_idx] = True

		def write(self, transaction, var, value):
			# distribute it to sites
			site_to_access = []
			x_idx = int(var[1:])
			if x_idx % 2 == 1:
				site_to_access.append(x_idx % 10 + 1)
			else:
				for i in range(1, self.num_of_sites + 1):
					site_to_access.append(i)
			print("	site to access: ", site_to_access)

			# send write rquest to each site
			# for site in site_to_access:
			# 	response = self.sites[site].write(x_idx, value)

			# 	if response == false:
					# wait - add to waiting instruction, update wait for graph 

		# def deadlock_detect():


		def print_state(self):
			print("start time: ", self.start_time)
			print("status: ", self.status)
			print("is read only: ", self.is_read_only)

	
		# inner class of TM
		class DM:

			def __init__(self):
				self.num_of_var = 20
				self.curr_vals = {} # is a map: has key means try to write to it, when site is down, erase its value but leave the key. 
				self.commit_vals = [(x * 10, 0) for x in range(self.num_of_var + 1)]
				self.lock_table = {}

			def write(self, x, val):
				return True
			
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
		# print("Sites: ")
		# for s in self.sites:
		# 	s.print_state()


def main():
	# create a DB
	db = DB()

	# read a file line by line
	f = open("input.txt", "r")
	for line in f:
		db.tm.read_in_instruction(line)

	db.querystate()


if __name__ == "__main__":
    main()

