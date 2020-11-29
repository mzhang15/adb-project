# works cited:
# algorithm explanation for cycle detection draw from
# https://www.baeldung.com/cs/detecting-cycles-in-directed-graph

from enum import Enum
from collections import defaultdict

# returns adjacency list 
# format: dict
#	key: node
#	value: list of adjacent (connected) outgoing nodes of key node
def build_graph(waits_for_edges):
	d = defaultdict(list)
	for edge in waits_for_edges:
		start, end = edge
		d[start].append(end)
	return d

class Status(Enum):
    UNSEEN = 0
    SEEN = 1
    DONE = 2
# if we ever visit a node that has already been seen, that is a cycle
# should be called multiple times? imagine we find one cycle but there is another cycle that has even newer deadlock?
def find_all_cycles(graph, verbose=False):
	if verbose:
		print('gggg', graph)
	# some nodes may be terminal; thus we need to look at values as well as keys
	all_nodes = list(set(list(graph.keys()) + [node for nodes in graph.values() for node in nodes]))
	already_seen_map = {n: Status.UNSEEN for n in all_nodes}
	all_found_cycles = []

	for cur_root_node in list(graph.keys()):
		if already_seen_map[cur_root_node] == Status.DONE:
			continue
		else:
			already_seen_map[cur_root_node] = Status.SEEN
			# in a new subtree; init new stack
			cur_stack = [cur_root_node]
			cycle_detect_from(graph, already_seen_map, cur_stack, all_found_cycles)
	return all_found_cycles

#side effecting - updates all_found_cycles var in place
def cycle_detect_from(graph, already_seen_map, cur_stack, all_found_cycles):
	cur_root_node = cur_stack[-1]
	for out_node in graph[cur_root_node]:
		if already_seen_map[out_node] == Status.SEEN:
			# found cycle
			cycle_details = detail_and_append_found_cycle(out_node, cur_stack)
			all_found_cycles.append(cycle_details)
		elif already_seen_map[out_node] == Status.UNSEEN:
			already_seen_map[out_node] = Status.SEEN
			cur_stack.append(out_node)
			cycle_detect_from(graph, already_seen_map, cur_stack, all_found_cycles)
	already_seen_map[cur_stack[-1]] = Status.DONE
	cur_stack.pop()

def detail_and_append_found_cycle(origin_node, cur_stack):
	# print('xxxxx', origin_node, cur_stack)
	cycle_only_stack = []
	backwards_index = -1
	while cur_stack[backwards_index] != origin_node:
		cycle_only_stack.append(cur_stack[backwards_index])
		backwards_index -= 1
	cycle_only_stack.append(origin_node)
	return cycle_only_stack


# =============== TESTS ==================

def test_build_graph():
	gg = {1:[2], 2:[3], 3:[4], 4:[1,5], 5:[6],6:[7],7:[8],8:[9],9:[8, 10] } 
	edges = [(1,2), (2,3), (3,4), (4,1), (4,5), (5,6), (6,7), (7,8), (8,9), (9,8), (9,10)]
	by_hand = defaultdict(list, gg)
	from_func = build_graph(edges)
	print('by hand', sorted(by_hand.items()))
	print('from func', sorted(from_func.items()))
	assert(sorted(by_hand.items()) == sorted(from_func.items()))

def test_find_cycle():
	# has cycle for 1,2,3,4 and 8,9
	gg = {1:[2], 2:[3], 3:[4], 4:[1,5], 5:[6],6:[7],7:[8],8:[9],9:[8, 10] } 
	g = defaultdict(list, gg)
#	print('FIRST find_all_cycles(g)', find_all_cycles(g))

	# has cycle for 1,2,3,4 and 3,2 and 8,9
	gg = {1:[2], 2:[3], 3:[4, 2], 4:[1,5], 5:[6],6:[7],7:[8],8:[9],9:[8, 10] } 
	g = defaultdict(list, gg)
	print('SECOND find_all_cycles(g)', find_all_cycles(g))

def main():
	test_find_cycle()
#	test_build_graph()
if __name__ == '__main__':
	main()
