import json
from pprint import pprint
import networkx as nx
import matplotlib.pyplot as plot

'''
	This file will parse the questions json file and build
	a series of knowledge triples around each verb
	Marbles.ai
	20 October 2016
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
	return tokens

# Dump the tokens to the std::out
def dumpToken(token, pretty=True):
	if pretty:
		print json.dumps(token, sort_keys=True, indent=2)
	else:
		print json.dumps(token, sort_keys=True)
	return

# tokenNode object
class tokenNode():
	def __init__(self, index, content, lemma, pos):
		self.index = index
		self.content = content
		self.lemma = lemma
		self.pos = pos

# Generate the toke graph
def generateTokenGraph(tokens):

	G = nx.Graph()

	currentIndex = 0
	nodes = []

	for token in tokens:

		# Grab content, offset, part of speech, lemma
		content = token['text']['content']
		offset = token['text']['beginOffset']
		pos = token['partOfSpeech']['tag']
		lemma =  token['lemma']

		# Grab the Dependency Graph Edge
		dependencyEdge =  token['dependencyEdge']
		headIndex = dependencyEdge['headTokenIndex']
		edgeLabel = dependencyEdge['label']

		# Add the edge to the graph; if nodes aren't
		# already in the graph, they're added (neat)
		G.add_edge(currentIndex, headIndex, label=edgeLabel)

		# Node representing each token
		nodes.append(tokenNode(currentIndex, content, lemma, pos))

		# Increment node index
		currentIndex += 1

	# Go through each edge and add edges and edge attribute
	for node in nodes:
		if node.pos == 'VERB':
			print(node.content+" is a VERB")
			print("Edges associated with this token")

			for edge in G.edges(node.index, data='label'):
				partner = nodes[edge[1]]
				print "Partner: "+ partner.content+ "("+partner.pos+")"
	exit()

	return G

# Dump the NLP
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

		# Let's make a graph!
		tokenGraph = generateTokenGraph(tokens)

		# Grab the rest of the problem
		question = problem['sQuestion']
		solutions = problem['lSolutions']
		equations = problem['lEquations']

		exit()
