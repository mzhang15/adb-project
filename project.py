from collections import defaultdict 

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
			self.accessed_sites = {} # key: transaction, value: list of sites a transaction has accessed



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

				print("transaction to be aborted: ", self.deadlock_detect()) # deadlock detectionn happens at the beginning of the tick
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
			success = True
			for site in site_to_access:
				response = self.sites[site].write(transaction, var, value)

				if response != "success":
					success = False
					break
				else:
					print("write %s = %d to site %d succeeded" %(var, value, site))

			if success == False:
				print("%s waits for %s" %(transaction, response))
				# wait - add to waiting instruction, update wait for graph
				self.waiting.append(self.Instruction("write", [transaction, var, value]))
				self.waits_for.append((transaction, response)) # first waits for second


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

			def __init__(self):
				self.num_of_var = 20
				self.curr_vals = {} # is a map: has key means try to write to it, when site is down, erase its value but leave the key. 
				self.commit_vals = [(x * 10, 0) for x in range(self.num_of_var + 1)]
				self.lock_table = {} # key: variable ("x1") value: (lock, transaction) 0 - read lock 1 - write lock, (todo: shared lock)

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
		# initialize variables' values
		# def initialize():

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

