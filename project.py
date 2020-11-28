from collections import defaultdict 
from test_cases import tests_generator

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

			self.curr_time = 0
			self.start_time = {} # dictionary with key = transaction no, value = start time
			self.end_time = {}
			self.status = [self.UP for x in range(self.num_of_sites + 1)] # 0 - down 1 - up normally 2 - just recovered
			self.is_read_only = [False] * (self.num_of_sites + 1)
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

				print("transaction to be aborted: ", self.deadlock_detect()) # deadlock detectionn happens at the beginning of the tick
				self.write(args[0], args[1], int(args[2]))
			elif name == "end":
				assert len(args) == 1

				# deadlock detection
				t_abort = self.deadlock_detect()
				print("transaction to be aborted: ", self.deadlock_detect()) # deadlock detectionn happens at the beginning of the tick
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
			# print("	site to access: ", site_to_access)

			# send write rquest to each site
			success = True
			for site in site_to_access:
				response = self.sites[site].write(transaction, var, value)

				if response != "success":
					success = False
					break
				# else:
					# print("write %s = %d to site %d succeeded" %(var, value, site))

			if success == False:
				# print("%s waits for %s" %(transaction, response))
				# wait - add to waiting instruction, update wait for graph
				self.waiting.append(self.Instruction("write", [transaction, var, value]))
				self.waits_for.append((transaction, response)) # first waits for second
				return False

			return True

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

		############# DEADLOCK SESSION ###############
		# TODO: create a dead lock detector class
		def isCyclicUtil(self, graph, v, visited, recStack):
			visited[v] = True
			recStack[v] = True

			for neighbour in graph[v]:
				if visited[neighbour] == False:
					if self.isCyclicUtil(graph, neighbour, visited, recStack) == True:
						return True
				elif recStack[neighbour] == True:
					return True

			recStack[v] = False
			return False

		# return the transaction to be aborted if there is a cycle or 
		# none if there is no cycle
		def isCyclic(self, graph, num_of_vertices):
			visited = [False] * (num_of_vertices + 1)
			recStack = [False] * (num_of_vertices + 1)
			for node in range(1, num_of_vertices + 1):
				if visited[node] == False:
					if self.isCyclicUtil(graph, node, visited, recStack) == True:
						# find the youngest transaction to abort
						# print("recStack: ", recStack)
						max_start_time = 0
						result = None
						for i, val in enumerate(recStack):
							if val == False:
								continue
							transaction = "T" + str(i)
							if self.start_time[transaction] > max_start_time:
								max_start_time = self.start_time[transaction]
								result = transaction

						return result
			return None


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

			return self.isCyclic(graph, len(vertices))


		################### END ########################
		



		def print_state(self):
			print("start time: ", self.start_time)
			print("status: ", self.status)
			# print("is read only: ", self.is_read_only)
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
				self.commit_vals = {}  # key: variable ("x1") value: pair of val and commit time 
				self.lock_table = {} # key: variable ("x1") value: (lock, transaction) 0 - read lock 1 - write lock, (todo: shared lock)

				# initialize commit_vals
				for i in range(1, self.num_of_var + 1):
					if i % 2 == 0 or i % 10 + 1 == self.number:
						var = "x" + str(i)
						self.commit_vals[var] = (i * 10, 0)

			def write(self, transaction, x, val):
				if x in self.lock_table:
					return self.lock_table[x][1] # transaction that holds the lock

				self.lock_table[x] = (self.WLOCK, transaction)
				self.curr_vals[x] = val
				return "success"
			
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
					self.commit_vals[variable] = (val, time)

				self.curr_vals.clear()

			def print_commit_vals(self):
				for var, (val, time) in self.commit_vals.items():
					print ("%s: %d," % (var, val), end = " ")
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

