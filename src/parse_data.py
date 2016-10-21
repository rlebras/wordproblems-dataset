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
	def __init__(self, lemma, pos):
		self.lemma = lemma
		self.pos = pos

	# Still need to implement this
    #def __str__(self):
    #    return self.name

def generateTokenGraph(tokens):

	G = nx.Graph()

	for token in tokens:

		pos = token['partOfSpeech']['tag']

		# Grab the Dependency Graph Edge
		#dependencyEdge =  token['dependencyEdge']

		lemma =  token['lemma']

		tn = tokenNode(lemma, pos)
		G.add_node(tn)

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

		#print dumpToken(tokens)

		# Let's make a graph!
		tokenGraph = generateTokenGraph(tokens)
		nx.draw(tokenGraph)
		plot.draw()

		exit(0)

		# Grab the rest of the problem
		question = problem['sQuestion']
		solutions = problem['lSolutions']
		equations = problem['lEquations']
