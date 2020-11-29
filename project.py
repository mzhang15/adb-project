from collections import defaultdict 

class DB:

	def __init__(self):
		self.tm = self.TM()
		
	class TM:
		
		# status constants
		# DOWN = 0
		# UP = 1
		# RECOVER = 2
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
			self.is_read_only = {} # key: transaction, value: True/False
			self.waiting = [] # accumulate waiting command
			self.waits_for = [] # wait-for edges, used for deadlock detection
			self.accessed_sites = defaultdict(list) # key: transaction, value: list of sites a transaction has accessed
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
				self.fail(args[0])
			elif name == "recover":
				assert len(args) == 1
				self.recover(args[0])
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

		# based on variable, return sites that have its copy
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

		# handle write instruction
		# Output: True - means succeeded, False - means failed, should wait
		def write(self, transaction, var, value):
			# distribute it to sites
			site_to_access = self.get_sites_to_access(var)

			# send write rquest to each site
			is_waiting = False
			for site in site_to_access:
				response = self.sites[site].write(transaction, var, value)

				if response == "success":
					print("write %s = %d to site %d succeeded" %(var, value, site))
					self.accessed_sites[transaction].append(site)
				elif response == "fail":
					print("site %s is down, unable to write" % site)
				else:
					is_waiting = True
					break
					

			if is_waiting == True:
				# print("%s waits for %s" %(transaction, response))
				# wait - add to waiting instruction, update wait for graph
				# TODO: release locks
				self.waiting.append(self.Instruction("write", [transaction, var, value]))
				for t in response:
					self.waits_for.append((transaction, t)) # first waits for second
				return False

			return True

		# TODO: to handle normal read
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

					if result == "fail":
						print("site %d is down, cannot read" % site)
					elif result != None:
						print("%s: %d" % (var, result))
						self.accessed_sites[transaction].append(site)
						return True

				# all sites failed
				self.waiting.append(Instruction('read_only', [transaction, var]))
				return False

			# normal read
			# odd vs even variable
			# odd: read from a site; even: try site one by one, return first 
			site_to_access = self.get_sites_to_access(var)

			for site in site_to_access:
				result = self.sites[site].read(transaction, var)
				if result != "fail" and type(result) is int:
					print("%s: %d" % (var, result))
					return True

			# all sites failed, then T must wait
			self.waiting.append(Instruction('read', [transaction, var]))
			assert type(result) is list
			for t in result:
				self.waits_for.append(transaction, t)
			return False

		def fail(self, site):
			site = int(site)
			# erase lock table + curr_vals?
			self.sites[site].fail()
		
			# check if a transactionn has accessed this site, if so, abort it right away
			for t in self.accessed_sites:
				if site in accessed_sites[t]:
					self.transaction_status[t] = self.ABORT

		def recover(self, site):
			self.sites[int(site)].recover()

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

			DOWN = 0
			UP = 1
			RECOVER = 2
			# TODO: creat lock class and acqure and release method
			class LOCK:
				def __init__(self, type, transaction):
					self.type = type
					self.transactions = set() # set: transactions holding the lock

					self.transactions.add(transaction)

				# def acqure(self, transaction):
				# 	if self.type == WLOCK:
				# 		if not self.transactions:
				# 			self.transactions.add(transaction)
				# 			return True
				# 		return False
				# 	elif self.type == RLOCK:

			def __init__(self, site_no):
				self.number = site_no
				self.status = self.UP
				self.num_of_var = 20
				self.curr_vals = {} # is a map: has key means try to write to it, when site is down, erase its value but leave the key. 
				self.commit_vals = defaultdict(list)  # dictionary of list(sorted by time) - key: variable ("x1") value: a list of pairs of val and commit time 
				self.lock_table = {} # key: variable ("x1") value: (lock, transaction) 0 - read lock 1 - write lock, (todo: shared lock)
				self.waiting_list = defaultdict(list) # waiting to acquire locks on var: key - var, value - list of Lock(type, transactionn)

				# initialize commit_vals and curr_vals
				for i in range(1, self.num_of_var + 1):
					if i % 2 == 0 or i % 10 + 1 == self.number:
						var = "x" + str(i)
						self.commit_vals[var].append((i * 10, 0))
						self.curr_vals[var] = i * 10

			def fail(self):
				self.status = self.DOWN
				self.lock_table.clear()
				self.waiting_list.clear()

			def recover(self):
				self.status = self.RECOVER



			# handle write request
			# TODO: change site's status from recover to up after a successful write
			# Output: "fail" - site is down, "success" - write succeeded, or list of conflictinng transaction
			def write(self, transaction, x, val):
				# if site is up or recovered, write request can proceed
				if self.status == self.DOWN:
					return "fail"

				if x in self.lock_table:
					# if it's the same transaction and hold a write lock, then can proceed
					# else return the conflicting transaction
					if transaction in self.lock_table[x].transactions: # lock held by same transaction
						if self.lock_table[x].type == self.WLOCK: # hold a write lock already
							self.curr_vals[x] = val
							return "success"
						# hold a read lock
						if len(self.lock_table[x].transactions) == 1: # not a shared lock
							# promote lock and proceed
							self.lock_table[x].type = self.WLOCK
							self.curr_vals[x] = val
							return "success"

						# a shared read lock -> need to wait
						self.waiting_list[var].append(self.LOCK(self.WLOCK, transaction))
						conflict_transactions = []
						for t in self.lock_table[x].transactions:
							if t != transaction:
								conflict_transactions.append(t)
						return conflict_transactions

					# other transactions holding a lock on x
					self.waiting_list[var].append(self.LOCK(self.WLOCK, transaction))
					conflict_transactions = self.lock_table[var].transactions
					return conflict_transactions # transaction that holds the lock

				# no lock on x
				self.lock_table[x] = self.LOCK(self.WLOCK, transaction)
				self.curr_vals[x] = val
				return "success"

			# Output: "fail" - site is down or just recovered, value - if succeeded (guranteed to return one)
			def read_only(self, var, begin_time):
				if self.status == self.DOWN or self.status == self.RECOVER:
					return "fail"

				history = self.commit_vals[var]
				print("history: ", history)

				# return the lastest val: last val in the list whose commit time is < begin_time
				for i in range(len(history)):
					if history[i][1] < begin_time:
						if i == len(history) - 1 or history[i + 1][1] > begin_time:
							return history[i][0]

			# Output: "fail" - site is down or just recovered, value - if succeeded, or list of conflicting transactions
			def read(self, transaction, var):
				if self.status == self.DOWN or self.status == self.RECOVER:
					return "fail"

				if var not in self.lock_table: # no lock on var -> acqure RLOCK
					self.lock_table[var] = (self.LOCK(self.RLOCK, transaction))

					# TODO: curr_val don't have this key
					return self.curr_vals[var]

				conflict_transactions = []

				# there is a lock on var
				if self.lock_table[var].type == self.WLOCK:
					# check if it's same transaction, if so proceed
					if self.lock_table[var].transactions[0] == transaction:
						return self.curr_vals[var]
					# write lock on var held by different transaction
					conflict_transactions.append(self.lock_table[var].transactions[0])
					self.waiting_list[var].append(self.LOCK(self.RLOCK, transaction))
					
					# TODO: Q: iterate through all waiting lock and figure out conflicts?
					return conflict_transactions # return the conflicting transaction

				# there is a read lock on var
				if transaction in self.lock_table[var].transactions: # already held the read lock
					return self.curr_vals[var]

				# read lock held by others
				if not self.waiting_list[var]: # no waiting locks
					self.lock_table[var].transactions.add(transaction) # acquire shared read lock on var
					return self.curr_vals[var]

				# there are waiting locks
				self.waiting_list[var].append(self.LOCK(self.RLOCK, transaction))
				conflict_transactions.extend(self.lock_table[var].transactions)
				# Q: do i need to lock all waiting locks to add conflicts?

				return conflict_transactions

			
			def print_state(self):
				print("    status: ", self.status)
				print("    curr_vals: ", self.curr_vals)
				# print("	   commit values: ", self.commit_vals)
				print("    lock table: ", self.lock_table)


			def release_locks(self, transaction):
				# release locks
				for var, lock in self.lock_table.copy().items():
					if transaction in lock.transactions:
						self.lock_table[var].transactions.remove(transaction)
						if not self.lock_table[var].transactions: # empty
							self.lock_table.pop(var)

				# todo: update waiting_list

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
	db = DB()

	# read a file line by line
	f = open("input.txt", "r")
	for line in f:
		db.tm.read_in_instruction(line)

	db.querystate()


if __name__ == "__main__":
    main()

