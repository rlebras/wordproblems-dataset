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

# Dictionary of parts of speech to look out for
pos_dict = {'VERB': ['NSUBJ', 'ATTR'], 'NOUN': ['NUM']}

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
class tokenNode:
	def __init__(self, index, content, lemma, pos):
		self.index = index
		self.content = content
		self.lemma = lemma
		self.pos = pos

	def __str__(self):
		return "Index: %d, Content: %d, Lemma: %s, POS: %s" % \
			(self.index, self.content, self.lemma, self.pos)

# triple object
class triple:
	def __init__(self,verb):
		self.subjects = []
		self.verb = verb
		self.attribute = []
		self.type = None
		self.nodes = None

	def __str__(self):
		string = 'Subjects: \n'
		for subject in self.subjects:
			string += self.nodes[subject[0]].lemma + " " + str(self.nodes[subject[1]].lemma) +'\n'
		string += "Verbs: \n"
		string += self.nodes[self.verb].content + '\n'
		string += "Attributes: \n"
		for attr in self.attribute:
			string += str(self.nodes[attr].content) + '\n'
		string += "Type: " + self.type + '\n'

		return string


# Generate the toke graph
def generateTokenGraph(tokens):

	G = nx.Graph()
	triples = []
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

		print "%s (%s) -> %d, " % (content, pos, headIndex)

		# Add the edge to the graph; if nodes aren't
		# already in the graph, they're added (neat)
		G.add_edge(currentIndex, headIndex, label=edgeLabel)

		# Node representing each token
		nodes.append(tokenNode(currentIndex, content, lemma, pos))

		# Increment node index
		currentIndex += 1

	# Go through each edge and add edges and edge attribute

	count = 1
	verb = ''
	attribute = []

	# Iterate through all nodes
	for node in nodes:

		# Base each triple around a verb
		if node.pos == 'VERB':
			#print(node.content+" is a VERB")
			#print("Edges associated with this token")

			tr = triple(node.index)
			for edge in G.edges(node.index, data='label'):

				partner = nodes[edge[1]]
				relationship = edge[2]

				#print "Relationship: " + relationship + \
				#	", Partner: "+ partner.content+ "("+partner.pos+")"

				#Found the nominal subject
				if relationship == "NSUBJ":
					#print "Found NSUBJ"
					subject = partner.index
					#print subject

					for edge in G.edges(partner.index, data='label'):

						partner = nodes[edge[1]]
						relationship = edge[2]

						#print "Relationship: " + relationship + \
						#	", Partner: " + partner.content + "(" + \
						#	partner.pos + ")"

						if relationship == "NUM":
							#print "Found Num"
							count = partner.index
							#print count

					#print "Appending subject: %d, %s" % (count, subject)
					tr.subjects.append((count, subject))

				if relationship == "ATTR":
					#print "Found ATTR"
					attribute = partner.index
					#print attribute
					(tr.attribute).append(attribute)

				if relationship == "P":
					if partner.content == "?":
						tr.type = "Q" # This is a question
					elif partner.content == ".":
						tr.type = "S" # Statement
					else:
						print("**ERROR: Not handling this correctly")

					# reset count
					count = 1

			tr.nodes = nodes
			triples.append(tr)

	return triples

# Dump the NLP
def dumpNLP(nlp):
	print json.dumps(nlp, sort_keys=True, indent=2)
	return

# Main Function
if __name__ == "__main__":

	jsonObj = readjson(filename)

	counter = 4
	# Iterate through all problems
	for problem in jsonObj:

		# Grab the NLP
		nlp = problem['nlp']

		# Tokenize
		tokens = tokenize(nlp)

		# Let's make a graph!
		triples = generateTokenGraph(tokens)

		for tr in triples:
			print tr

		# Grab the rest of the problem
		#question = problem['sQuestion']
		#solutions = problem['lSolutions']
		#equations = problem['lEquations']

		if counter == 0:
			exit()
		else:
			counter = counter - 1
