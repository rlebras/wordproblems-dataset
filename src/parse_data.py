import json
from pprint import pprint
import networkx as nx
import matplotlib.pyplot as plot

'''
	This file will parse the questions json file and build a knowledge graph
	20 October 2016
	tommy.tracy@gmail.com
'''

# Example filename containing the questions, NLP and answers
filename = "../dolphin_t2_final_annotated.json"

# Read the json file and return a json object
def readjson(filename):
	with open(filename) as jsonfile:
		jsonObj = json.load(jsonfile)
	return jsonObj

# Take an NLP and return the tokens (in some format)
def tokenize(nlp):
	tokens = nlp['tokens']
	#for token in tokens:
	#	dumpToken(token, False)
	return tokens

def dumpToken(token, pretty=True):
	if pretty:
		print json.dumps(token, sort_keys=True, indent=2)
	else:
		print json.dumps(token, sort_keys=True)
	return

class tokenNode():
	def __init__(self, index, lemma, pos):
		self.index = index
		self.lemma = lemma
		self.pos = pos

	# Still need to implement this
    #def __str__(self):
    #    return self.name

def generateTokenGraph(tokens):

	G = nx.Graph()

	index = 0
	edges = []
	nodes = []

	for token in tokens:

		pos = token['partOfSpeech']['tag']

		# Grab the Dependency Graph Edge
		dependencyEdge =  token['dependencyEdge']
		headIndex = dependencyEdge['headTokenIndex']
		edgeLabel = dependencyEdge['label']

		# Keep track of the edge and increment index
		edges.append((index, headIndex, edgeLabel))

		lemma =  token['lemma']

		# Node representing each token
		tn = tokenNode(index, lemma, pos)
		nodes.append(tn)

		# Keep track of edges and add at the end
		# We do this because we might not have a
		# node to link to yet
		G.add_node(tn)

		# Increment node index
		index += 1

	# Go through each edge and add edges and edge attribute
	for edge in edges:
		G.add_edge(nodes[edge[0]], nodes[edge[1]])

	return G


def dumpNLP(nlp):
	print json.dumps(nlp, sort_keys=True, indent=2)
	return

# Main Function
if __name__ == "__main__":

	jsonObj = readjson(filename)

	# Iterate through all problems
	for problem in jsonObj:

		# Grab the NLP
		nlp = problem['nlp']

		# Tokenize
		tokens = tokenize(nlp)

		#for token in tokens:
		#	print token

		#print dumpToken(tokens)

		# Let's make a graph!
		tokenGraph = generateTokenGraph(tokens)
		nx.draw(tokenGraph)
		plot.draw()

		# Grab the rest of the problem
		question = problem['sQuestion']
		solutions = problem['lSolutions']
		equations = problem['lEquations']
