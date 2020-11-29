from collections import defaultdict 
from test_cases import tests_generator
from deadlock_detect_util import build_graph, find_all_cycles

class DB:

	def __init__(self):
		self.tm = self.TM()
		
	class TM:
		
		# status constants
		DOWN = 0
		UP = 1
		RECOVER = 2
		COMMIT = 1
		ABORT = 0

		# initialize TM: start time, end time, is site up array, is read-only array, waiting commands, wait for
		def __init__(self):
			self.num_of_sites = 10
			self.sites = [self.DM(i) for i in range(self.num_of_sites + 1)]

			# TODO: create Transaction class and create a list of transactions
			# all of the following information should be stored inside the transaction
			self.curr_time = 0
			self.start_time = {} # dictionary with key = transaction, value = start time
			self.end_time = {}
			self.status = [self.UP for x in range(self.num_of_sites + 1)] # 0 - down 1 - up normally 2 - just recovered
			self.is_read_only = {} # key: transaction, value: True/False
			self.waiting = [] # accumulate waiting command
			self.waits_for = [] # wait-for edges, used for deadlock detection
			self.accessed_sites = {} # key: transaction, value: list of sites a transaction has accessed
			self.transaction_status = {} # either 1 - commit or 0 - abort



		def read_in_instruction(self, line):
			# increment time
			self.curr_time += 1
			# print(self.curr_time)

			# parse instruction
			l = line.index("(")
			r = line.index(")")
			name = line[0:l]
			args = line[l + 1:r].split(",")

			print(name, args)
			if name == "begin": 
				assert len(args) == 1
				self.begin(args[0], self.curr_time)
			elif name == "beginRO":
				assert len(args) == 1
				self.beginRO(args[0], self.curr_time)
			elif name == "R":
				assert len(args) == 2
				self.read(args[0], args[1])
			elif name == "W":
				assert len(args) == 3

				print("transactions to be aborted HHH: ", self.deadlock_detect()) # deadlock detectionn happens at the beginning of the tick
				self.write(args[0], args[1], int(args[2]))
			elif name == "end":
				assert len(args) == 1

				# deadlock detection
				to_abort_transactions = self.deadlock_detect()
				for t_abort in to_abort_transactions:
					print("transaction to be aborted HH: ", self.deadlock_detect()) # deadlock detectionn happens at the beginning of the tick
					if t_abort != None:
						self.abort(t_abort)
				self.retry()

				self.end(args[0])
			elif name == "fail":
				assert len(args) == 1
				print(name)
			elif name == "recover":
				assert len(args) == 1
				print(name)
			elif name == "dump":
				self.dump()
			else:
				print("Error: unknown command ", name)


		def begin(self, transaction, time):
			# just record its begin time
			self.start_time[transaction] = time
			self.is_read_only[transaction] = False

		def beginRO(self, transaction, time):
			self.start_time[transaction] = time
			self.is_read_only[transaction] = True

		# based on variable, return which sites have its copy
		# output: a list of site numbers
		def get_sites_to_access(self, var):
			site_to_access = []
			x_idx = int(var[1:])
			if x_idx % 2 == 1:
				site_to_access.append(x_idx % 10 + 1)
			else:
				for i in range(1, self.num_of_sites + 1):
					site_to_access.append(i)
			return site_to_access
			# print("	site to access: ", site_to_access)

		def write(self, transaction, var, value):
			# distribute it to sites
			site_to_access = self.get_sites_to_access(var)

			# send write rquest to each site
			success = True
			for site in site_to_access:
				response = self.sites[site].write(transaction, var, value)

				if response != "success":
					success = False
					break
				else:
					print("write %s = %d to site %d succeeded" %(var, value, site))

			if success == False:
				# print("%s waits for %s" %(transaction, response))
				# wait - add to waiting instruction, update wait for graph
				self.waiting.append(self.Instruction("write", [transaction, var, value]))
				self.waits_for.append((transaction, response)) # first waits for second
				return False

			return True

		# TODO:
		def read(self, transaction, var):
			# read-only: return committed value on or before the transaction started
			if self.is_read_only[transaction] == True:
				assert transaction in self.start_time
				begin_time = self.start_time[transaction]

				site_to_access = self.get_sites_to_access(var)
				print("site to access: ", site_to_access)
				print(begin_time)

				for site in site_to_access:
					result = self.sites[site].read_only(var, begin_time)
					# print(result)

					if result != None:
						print("%s: %d" % (var, result))
						return
				return

			# normal read
			# odd vs even variable
			# odd: read from a site; even: try site one by one, return first 
			site_to_access = self.get_sites_to_access(var)

			return

		def release_locks(self, t):
			for i in range(1, self.num_of_sites + 1):
				self.sites[i].release_locks(t)

		# return commit or abort
		def end(self, t):
			# release locks
			self.release_locks(t)

			# check if all sites t has accessed can commit, which means assign curr_vals to commit_vals
			# (may not need to do this since we already abort the transaction in fail instruction)
			if t in self.transaction_status and self.transaction_status[t] == self.ABORT: # abort
				print("%s aborts" % t)
				return
			
			self.transaction_status[t] = self.COMMIT # commit
			print("%s commits" % t)

			# commit values: assign curr_vals to commit_vals
			for i in range(1, self.num_of_sites + 1):
				self.sites[i].commit_values(self.curr_time)

		def dump(self):
			for i in range(1, self.num_of_sites + 1):
				print("site %d" % i, end = " - ")
				self.sites[i].print_commit_vals()



		# function: retry waiting commands recursivly
		# when to use: when lock table is changed (locks are released or erased), 
		def retry(self):
			if len(self.waiting) == 0:
				return

			command = self.waiting[0]
			if command.type == "write":
				assert len(command.args) == 3
				result = self.write(command.args[0], command.args[1], command.args[2])
				if result == True:
					# update waiting command
					self.waiting.pop(0)
					# retry next command
					self.retry()
			elif command.type == "read":
				assert len(command.args) == 2

		# Description: abort a transaction, release all locks it's holding, remove its waiting commands, and remove related waits-for edge
		def abort(self, transaction):
			# release locks
			self.release_locks(transaction) 

			# remove its waiting command
			for command in self.waiting:
				if command.args[0] == transaction:
					self.waiting.remove(command)

			# remove related waits-for edges
			for edge in self.waits_for:
				if edge[0] == transaction or edge[1] == transaction:
					self.waits_for.remove(edge)

			self.transaction_status[transaction] = self.ABORT # 0 means abort

		# todo doesnt need to be instance method
		def _youngest_transaction_from_ids(self, transaction_numbers):
			transactions_named = ['T'+str(x) for x in transaction_numbers]
			ts_w_start_times = [(t_id, self.start_time[t_id]) for t_id in transactions_named]
			sorted_ts = sorted(ts_w_start_times, key=lambda x: x[1], reverse=True)
			youngest = sorted_ts[0][0]
			return youngest

		# Detect if there is a deadlock
		# input: a list of wait-for edges
		# output: transaction to be aborted
		def deadlock_detect(self):
			# construct adjlist 
			graph = defaultdict(list)
			vertices = set() # each transaction is a vertex
			for edge in self.waits_for:
				node1 = int(edge[0][1:])
				node2 = int(edge[1][1:])
				graph[node1].append(node2) # only use transaction's number
				vertices.add(node1)
				vertices.add(node2)

			found_cycles = find_all_cycles(graph)
			# found_cycles is a list of lists; kill youngest from each cycle (each sublist)
			youngest_from_each_cycle = []
			for cycle in found_cycles:
				youngest_in_cycle = self._youngest_transaction_from_ids(cycle)
				youngest_from_each_cycle.append(youngest_in_cycle)
			return youngest_from_each_cycle



		def print_state(self):
			print("start time: ", self.start_time)
			print("status: ", self.status)
			print("is read only: ", self.is_read_only)
			print("waiting instruction: ", self.waiting)

			print("Sites:")
			for i in range(1, self.num_of_sites + 1):
				print("site %d: " % i)
				self.sites[i].print_state()

	

		# inner class of TM
		class Instruction:
			def __init__(self, type, args):
				self.type = type
				self.args = args

			def __repr__(self):
				return "%s(%s)" % (self.type, self.args)

			def __str__(self):
				return "%s(%s)" % (self.type, self.args)

		class DM:

			RLOCK = 0
			WLOCK = 1

			def __init__(self, site_no):
				self.number = site_no
				self.num_of_var = 20
				self.curr_vals = {} # is a map: has key means try to write to it, when site is down, erase its value but leave the key. 
				self.commit_vals = defaultdict(list)  # dictionary of list(sorted by time) - key: variable ("x1") value: a list of pairs of val and commit time 
				self.lock_table = {} # key: variable ("x1") value: (lock, transaction) 0 - read lock 1 - write lock, (todo: shared lock)

				# initialize commit_vals
				for i in range(1, self.num_of_var + 1):
					if i % 2 == 0 or i % 10 + 1 == self.number:
						var = "x" + str(i)
						self.commit_vals[var].append((i * 10, 0))

			def write(self, transaction, x, val):
				if x in self.lock_table:
					return self.lock_table[x][1] # transaction that holds the lock

				self.lock_table[x] = (self.WLOCK, transaction)
				self.curr_vals[x] = val
				return "success"

			def read_only(self, var, begin_time):
				history = self.commit_vals[var]
				print("history: ", history)

				# return the lastest val: last val in the list whose commit time is < begin_time
				for i in range(len(history)):
					if history[i][1] < begin_time:
						if i == len(history) - 1 or history[i + 1][1] > begin_time:
							return history[i][0]
				return None
			
			def print_state(self):
				print("    curr_vals: ", self.curr_vals)
				# print("	   commit values: ", self.commit_vals)
				print("    lock table: ", self.lock_table)


			def release_locks(self, transaction):
				for key, value in self.lock_table.copy().items():
					if value[1] == transaction:
						self.lock_table.pop(key)

			def commit_values(self, time):
				for variable, val in self.curr_vals.items():
					self.commit_vals[variable].append((val, time))

				self.curr_vals.clear()

			def print_commit_vals(self):
				for var in self.commit_vals:
					print ("%s: %d," % (var, self.commit_vals[var][-1][0]), end = " ")
				print("\n")

		# initialize variables' values
		# def initialize():

	# def fail(site):
		# erase lock table + curr_vals?

		# check if a transactionn has accessed this site, if so, abort it right away

	# def recover(site):

	def querystate(self):
		print("\nTransaction Manager State:")
		self.tm.print_state()
		# print("Sites: ")
		# for s in self.sites:
		# 	s.print_state()


def main():
	# create a DB

	# read a file line by line
	# f = open("input.txt", "r")
	# for line in f:
	# 	db.tm.read_in_instruction(line)
	# db.querystate()

	relevant_tests = set([1])

	for test_index_zero_based, (test_lines, lines_with_comments) in enumerate(tests_generator()):

		test_num = test_index_zero_based+1
		if test_num in relevant_tests:
			print(f'Test num {test_num}')
			db = DB()
			for line in test_lines:
				db.tm.read_in_instruction(line)
			db.querystate()

if __name__ == "__main__":
    main()

