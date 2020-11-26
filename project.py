class TM:
	# initialize TM: start time, end time, is site up array, is read-only array, waiting commands, wait for
	def __init__(self):
		self.start_time = {} # dictionary with key = transaction no, value = start time
		self.end_time = {}
		self.status = [1 for x in range(10)] # 0 - down 1 - up normally 2 - just recovered
		self.is_read_only = [False] * 10
		self.waiting = [] # accumulate waiting command
		self.waits_for = [] # wait-for edges, used for deadlock detection
		self.accessed_sites = {} # key: transaction, value: list of sites it has accessed

	# def deadlock_detect():


class DM:
	def __init__(self):
		self.curr_vals = {} # is a map: has key means try to write to it, when site is down, erase its value but leave the key. 
		self.commit_vals = [x * 10 for x in range(11)]
		self.lock_table = {}
	
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

# def querystat():


def main():
	# setup 1 TM and 10 DM

	# read a file line by line
	f = open("input.txt", "r")
	for x in f:
		print(x)

if __name__ == "__main__":
    main()

