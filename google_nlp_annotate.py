#! /usr/bin/env python
# Adds NLP annotations to json file
'''
Created on Oct 13, 2016

@author: pglendenning
'''

import os, sys, json, requests
from optparse import OptionParser
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials

def get_service():
    '''Build a client to the Google Cloud Natural Language API.'''
    credentials = GoogleCredentials.get_application_default()
    return discovery.build('language', 'v1beta1', credentials=credentials)


def get_request_body(text, syntax=True, entities=True, sentiment=False):
    ''' Creates the body of the request to the language api in
    order to get an appropriate api response
    '''
    body = {
        'document': {
            'type': 'PLAIN_TEXT',
            'content': text,
        },
        'features': {
            'extract_syntax': syntax,
            'extract_entities': entities,
            'extract_document_sentiment': sentiment,
        },
        'encoding_type': 'UTF32'
    }
    return body


def die(msg):
    print('Error: %s' % msg)
    sys.exit(1)


if __name__ == '__main__':
    print('Word Problem NLP Annotations')

    # Parse command line
    usage = '%prog [[options] /path/to/input/file.json'
    parser = OptionParser(usage)
    parser.add_option('-o', '--output', type='string', dest='outfile', help='Set output file. Default is stdout.')
    parser.add_option('-c', '--compact', action='store_true', dest='compact', help='compact json output.')
    options, args = parser.parse_args()
    if args is None or len(args) == 0:
        die('no file to process')

    with open(args[0], 'rt') as fd:
        wordprobs = json.load(fd)

    service = get_service()
    for prob in wordprobs:
        body = get_request_body(prob['sQuestion'])
        request = service.documents().annotateText(body=body)
        response = request.execute(num_retries=3)
        prob['nlp'] = response

    if options.outfile is None:
        if options.compact:
            json.dump(wordprobs, fp=sys.stdout)
        else:
            json.dump(wordprobs, fp=sys.stdout, indent=2)
    else:
        with open(options.outfile, 'w') as fd:
            if options.compact:
                json.dump(wordprobs, fp=fd)
            else:
                json.dump(wordprobs, fp=fd, indent=2)

