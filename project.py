from collections import defaultdict 
import sys

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
			# TODO: change accessed_sites to be a dict of dict: outerkey - transaction innerkey: var value: list of sites a var has accessed
			self.accessed_sites = defaultdict(list) # key: transaction, value: list of sites a transaction has accessed
			self.accessed_sites2 = {} # key - transaction value - dict of key - var value - sites it writes to 
			self.transaction_status = {} # either 1 - commit or 0 - abort

			self.write_to = defaultdict(list) # key: transaction, value: list of variables it writes to



		def read_in_instruction(self, line):
			# increment time
			self.curr_time += 1
			# print(self.curr_time)

			# parse instruction
			l = line.index("(")
			r = line.index(")")
			name = line[0:l]
			args = line[l + 1:r].split(",")

			# get rid of white space of each argument
			for i in range(len(args)):
				args[i] = args[i].strip()

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

				# no need to run deadlock detection before write
				# t_abort = self.deadlock_detect()
				# print("transaction to be aborted: ", t_abort) # deadlock detectionn happens at the beginning of the tick
				# if t_abort != None:
				# 	self.abort(t_abort)
				# 	self.retry()

				self.write(args[0], args[1], int(args[2]))
			elif name == "end":
				assert len(args) == 1

				# deadlock detection
				t_abort = self.deadlock_detect()
				print("transaction to be aborted: ", self.deadlock_detect()) # deadlock detectionn happens at the beginning of the tick
				if t_abort != None:
					print("wait for edges before abort: ", self.waits_for)
					self.abort(t_abort)
					print("wait for edges after abort: ", self.waits_for)
					self.retry()

				self.end(args[0]) # 

				# retry waiting commands
				self.retry()
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
			self.write_to[transaction].append(var)

			# create a dictionary to remember those sites that a write request writes to
			if transaction not in self.accessed_sites2:
				self.accessed_sites2[transaction] = defaultdict(list)

			# distribute it to sites
			site_to_access = self.get_sites_to_access(var)

			# send write rquest to each site
			is_waiting = False
			for site in site_to_access:
				print("lock table before write: ", self.sites[site].lock_table)
				response = self.sites[site].write(transaction, var, value)
				print("lock table after write: ", self.sites[site].lock_table)

				if response == "success":
					print("write %s = %d to site %d succeeded" %(var, value, site))
					self.accessed_sites[transaction].append(site)
					self.accessed_sites2[transaction][var].append(site)
				elif response == "fail":
					print("site %s is down, unable to write" % site)
				else:
					is_waiting = True
					break
					

			if is_waiting == True:
				# print("%s waits for %s" %(transaction, response))
				# wait - add to waiting instruction, update wait for graph
				# TODO: release locks

				# because could retry command, so only add different command
				is_existed = False
				for command in self.waiting:
					if command.type == "write" and command.args == [transaction, var, value]:
						is_existed = True
						break

				if not is_existed:
					self.waiting.append(self.Instruction("write", [transaction, var, value]))
					assert type(response) is list
					print("%s should wait for %s" % (transaction, response))
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
						print("%s - %s: %d" % (transaction, var, result))
						self.accessed_sites[transaction].append(site)
						return True

				# all sites failed
				self.waiting.append(Instruction('read_only', [transaction, var]))
				return False

			# normal read
			# odd vs even variable
			# odd: read from a site; even: try site one by one, return first 
			site_to_access = self.get_sites_to_access(var)

			print("site to access: ", site_to_access)
			needs_wait = False
			for site in site_to_access:
				result = self.sites[site].read(transaction, var)
				if result != "fail" and type(result) is int:
					print("%s - %s: %d" % (transaction, var, result))
					self.accessed_sites[transaction].append(site)
					return True
				if type(result) is list: # return a list of conflicting transactions
					needs_wait = True
					break

			# all sites return fail or one of site return list of conflicting transaction, then T must wait
			self.waiting.append(self.Instruction('read', [transaction, var]))
			if needs_wait == True:
				assert type(result) is list
				print("%s should wait for %s" % (transaction, result))
				for t in result:
					self.waits_for.append((transaction, t))
			return False

		def fail(self, site):
			site = int(site)
			# erase lock table + curr_vals?
			self.sites[site].fail()
		
			# check if a transactionn has accessed this site, if so, abort it right away
			for t in self.accessed_sites:
				if site in self.accessed_sites[t]:
					self.abort(t)
					# self.transaction_status[t] = self.ABORT
					# TODO: should revert all commands

		def recover(self, site):
			self.sites[int(site)].recover()

		def release_locks(self, t):
			for i in self.accessed_sites[t]:
				self.sites[i].release_locks(t)

		# print commit or abort
		def end(self, t):
			# release locks
			self.release_locks(t)

			# check if all sites t has accessed can commit, which means assign curr_vals to commit_vals
			# (may not need to do this since we already abort the transaction in fail instruction)
			if t in self.transaction_status and self.transaction_status[t] == self.ABORT: # already aborted
				print("%s aborts" % t)
				# delete its waiting command
				for c in self.waiting:
					if c.args[0] == t:
						self.waiting.remove(c)
				return
			
			self.transaction_status[t] = self.COMMIT # commit
			print("%s commits" % t)

			# commit values: assign curr_vals to commit_vals
			self.commit_values(t)

			# updates waits-for edges: delete any edge that has other transactions wait for this transaction
			# Assumption: this transaction shouldnn't wait for any other transaction when it commits
			for edge in self.waits_for.copy():
				assert edge[0] != t
				if edge[1] == t:
					self.waits_for.remove(edge)

		# commit values that transaction has written to
		def commit_values(self, transaction):
			# site_to_access = set()
			var_been_written = self.write_to[transaction]

			for var in var_been_written:
				# sites_to_commit = self.get_sites_to_access(var)
				sites_to_commit = self.accessed_sites2[transaction][var]

				# filter out those sites that weren't accessed by this transaction
				# for site in sites_to_commit.copy():
				# 	if site not in self.accessed_sites[transaction]:
				# 		sites_to_commit.remove(site)
				# print("   sites to commit: ", sites_to_commit)
				for site in sites_to_commit:
					self.sites[site].commit_value(var, self.curr_time)


		def dump(self):
			for i in range(1, self.num_of_sites + 1):
				print("site %d" % i, end = " - ")
				self.sites[i].print_commit_vals()



		# function: retry waiting commands recursivly
		# when to use: when lock table is changed (locks are released or erased), 
		def retry(self):
			print("waiting command: ", self.waiting)
			if len(self.waiting) == 0:
				return

			# determine which transaction's commands to try first: the one that doesn't wait for anyone
			print("    waits for: ", self.waits_for)
			# adjlist = defaultdict(list)
			# for edge in self.waits_for:
			# 	adjlist[edge[0]].append(edge[1])
			# 	adjlist[edge[1]] = []

			# transactions_to_try = []
			# for key in adjlist:
			# 	if not adjlist[key]: # empty
			# 		transactions_to_try.append(key)
			# print("transactions to try: ", transactions_to_try)

			# commands_to_try = []
			# if not transactions_to_try: # only left with transactions that aren't waiting for any
			# 	commands_to_try = self.waiting
			# else:
			# 	for command in self.waiting:
			# 		if command.args[0] in transactions_to_try:
			# 			commands_to_try.append(command)

			# print("commands to try: ", commands_to_try)

			# select from waiting command, find which doesn't wait for anything
			commands_to_try = []
			for command in self.waiting:
				is_waiting = False
				for edge in self.waits_for:
					if command.args[0] == edge[0]: # this command's transaction is waiting for other transaction
						is_waiting = True
						break
				if is_waiting == False:
					commands_to_try.append(command)
			print("    commands to try: ", commands_to_try)

			for command in commands_to_try:
				print("retry %s" % command)
				if command.type == "write":
					assert len(command.args) == 3
					result = self.write(command.args[0], command.args[1], command.args[2])
					print("retry result: ", result)
					if result == True:
						# update waiting command
						self.waiting.remove(command)
						# retry next command
						self.retry()
					return
				elif command.type == "read":
					assert len(command.args) == 2
					result = self.read(command.args[0], command.args[1])
					if result == True:
						self.waiting.remove(command)
						self.retry()

		def revert_to_last_commit_val(self, transaction):
			for site in self.accessed_sites[transaction]:
				self.sites[site].revert_to_last_commit_value(transaction)

		# Description: abort a transaction, release all locks it's holding, remove its waiting commands, and remove related waits-for edge
		def abort(self, transaction):
			# revert back to last commit value
			self.revert_to_last_commit_val(transaction)
			# release locks
			self.release_locks(transaction) 

			# remove its waiting command
			for command in self.waiting:
				if command.args[0] == transaction:
					self.waiting.remove(command)

			# remove related waits-for edges
			for edge in self.waits_for.copy(): # when deleting elements in the list during the loop, size could change, so use copy
				if edge[0] == transaction or edge[1] == transaction:
					self.waits_for.remove(edge)

			self.transaction_status[transaction] = self.ABORT # 0 means abort

		############# DEADLOCK SESSION ###############
		# The algorithm and code are cited from website GeeksforGeeks: Dectect Cycle in a Directed Graph
		# link to the page is https://www.geeksforgeeks.org/detect-cycle-in-a-graph/

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
		def isCyclic(self, graph, vertices):
			visited = {}
			recStack = {}

			for v in vertices:
				visited[v] = False
				recStack[v] = False

			for node in vertices:
				if visited[node] == False:
					if self.isCyclicUtil(graph, node, visited, recStack) == True:
						# find the youngest transaction to abort
						# print("recStack: ", recStack)
						max_start_time = 0
						result = None
						for i, val in recStack.items():
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

			print("graph:", graph)
			print("num of vertices: ", vertices)
			return self.isCyclic(graph, vertices)


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
				def __repr__(self):
					return "%s(%s)" % (self.type, self.transactions)

				def __str__(self):
					return "%s(%s)" % (self.type, self.transactions)

			def __init__(self, site_no):
				self.number = site_no
				self.status = self.UP
				self.num_of_var = 20
				self.curr_vals = {} # is a map: has key means try to write to it, when site is down, erase its value but leave the key. 
				self.commit_vals = defaultdict(list)  # dictionary of list(sorted by time) - key: variable ("x1") value: a list of pairs of val and commit time 
				self.lock_table = {} # key: variable ("x1") value: lock(type, transaction) 0 - read lock 1 - write lock, (todo: shared lock)
				self.waiting_list = defaultdict(list) # waiting to acquire locks on var: key - var, value - list of Lock(type, transactionn)
				self.is_just_recovered = {} # key - var, value - true/false (used only for even variables)

				# initialize commit_vals, curr_vals, and is_recovered
				for i in range(1, self.num_of_var + 1):
					if i % 2 == 0 or i % 10 + 1 == self.number:
						var = "x" + str(i)
						self.commit_vals[var].append((i * 10, 0))
						self.curr_vals[var] = i * 10

						if i % 2 == 0:
							self.is_just_recovered[var] = False

			def fail(self):
				self.status = self.DOWN
				self.lock_table.clear()
				self.waiting_list.clear()

			def recover(self):
				self.status = self.RECOVER

				for var in self.is_just_recovered:
					self.is_just_recovered[var] = True



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
						print("    waiting list:", self.waiting_list[x])
						if len(self.lock_table[x].transactions) == 1: # not a shared read lock
							if not self.waiting_list[x]: # no other waiting
								self.lock_table[x].type = self.WLOCK
								self.curr_vals[x] = val
								return "success"

							# there is waiting locks

							# if current transaction is the first one in the waiting queue -> promote RLOCK to WLOCK and delete from waiting list
							if self.waiting_list[x][0].type == self.WLOCK and transaction in self.waiting_list[x][0].transactions:
								self.waiting_list[x].pop(0) # remove it from the waiting list
								self.lock_table[x].type = self.WLOCK
								self.curr_vals[x] = val
								return "success"

						if not self.waiting_list[x] and len(self.lock_table[x].transactions) == 1: # not a shared lock
							# promote lock and proceed
							self.lock_table[x].type = self.WLOCK
							self.curr_vals[x] = val
							return "success"

						# there are waiting locks and/or a shared read lock -> need to wait

						conflict_transactions = []
						# infer conflict from waiting list
						conflict_transactions.extend(self.infer_conflicts_from_waiting_locks(x))

						# infer conflict from shared read lock
						for t in self.lock_table[x].transactions:
							if t != transaction:
								conflict_transactions.append(t)
						# print("%s must waits for %s" % (transaction, conflict_transactions))

						self.waiting_list[x].append(self.LOCK(self.WLOCK, transaction))

						return conflict_transactions

					# other transactions holding a lock on x
					# infer conflict from waiting list
					conflict_transactions = self.infer_conflicts_from_waiting_locks(x)
					conflict_transactions.extend(self.lock_table[x].transactions)
					# print("%s must waits for %s" % (transaction, conflict_transactions))

					self.waiting_list[x].append(self.LOCK(self.WLOCK, transaction))
					# print("lock waiting list: ", self.waiting_list)

					return conflict_transactions # transaction that holds the lock

				# no lock on x
				self.lock_table[x] = self.LOCK(self.WLOCK, transaction)
				self.curr_vals[x] = val
				return "success"

			def infer_conflicts_from_waiting_locks(self, var):
				conflict_transactions = []
				for lock in self.waiting_list[var]:
					conflict_transactions.extend(lock.transactions)
				return conflict_transactions

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

			# handle recover cases
			# Output: "fail" - site is down or var just recovered, value - if succeeded, or list of conflicting transactions
			def read(self, transaction, var):
				if self.status == self.DOWN:
					return "fail"

				if self.status == self.RECOVER:
					x_idx = int(var[1:])
					if x_idx % 2 == 1: # odd variable(unreplicated) can be read directly
						return self.read_helper(transaction, var)
					
					if self.is_just_recovered[var] == True:
						return "fail"

					return self.read_helper(transaction, var)

				return self.read_helper(transaction, var)


			def read_helper(self, transaction, var):
				if var not in self.lock_table: # no lock on var -> acqure RLOCK
					self.lock_table[var] = (self.LOCK(self.RLOCK, transaction))

					# TODO: curr_val don't have this key
					return self.curr_vals[var]

				conflict_transactions = []

				# there is a lock on var
				if self.lock_table[var].type == self.WLOCK:
					# check if it's same transaction, if so proceed
					if transaction in self.lock_table[var].transactions:
						return self.curr_vals[var]
					# write lock on var held by different transaction
					conflict_transactions.extend(self.lock_table[var].transactions)
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
				print("    is just recovered: ", self.is_just_recovered)


			def release_locks(self, transaction):
				# release locks
				for var, lock in self.lock_table.copy().items():
					if transaction in lock.transactions:
						self.lock_table[var].transactions.remove(transaction)
						if not self.lock_table[var].transactions: # empty
							self.lock_table.pop(var)
				# todo: update waiting_list


			def revert_to_last_commit_value(self, transaction):
				for var, lock in self.lock_table.items():
					if transaction in lock.transactions and lock.type == self.WLOCK:
						self.curr_vals[var] = self.commit_vals[var][-1][0]

			# commit a specific variable at time t 
			def commit_value(self, var, time):
				self.commit_vals[var].append((self.curr_vals[var], time))
				# self.curr_vals.pop(var) # Q: do i need to clear the curr value?

				if var in self.is_just_recovered and self.is_just_recovered[var] == True:
					self.is_just_recovered[var] = False

				# if all replicated variables have a commit after the site recovers -> change site's status to UP
				is_all_variables_recovered = True
				for var, status in self.is_just_recovered.items():
					if status == True:
						is_all_variables_recovered = False
						break
				if is_all_variables_recovered:
					self.status = self.UP

			# no longer use
			def commit_values(self, time):
				for variable, val in self.curr_vals.items():
					self.commit_vals[variable].append((val, time))

					# handle recover case
					if variable in self.is_just_recovered and self.is_just_recovered[variable] == True:
						self.is_just_recovered[variable] == False;

				self.curr_vals.clear()

				# if all replicated variables have a commit after the site recovers -> change site's status to UP
				is_all_variables_recovered = True
				for var, status in self.is_just_recovered.items():
					if status == True:
						is_all_variables_recovered = False
						break
				if is_all_variables_recovered:
					self.status = self.UP

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
	in_file = sys.argv[1]
	# out_file = sys.argv[2]
	# create a DB
	db = DB()

	# read a file line by line
	f = open(in_file, "r")
	for line in f:
		db.tm.read_in_instruction(line)

	db.querystate()


if __name__ == "__main__":
    main()

