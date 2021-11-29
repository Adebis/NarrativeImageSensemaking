import os
import sys

import time

import json
import pickle
import requests

from database_manager import DatabaseManager

# Root directory
ROOT_DIRECTORY = os.path.abspath("../")

# A class that handles queries to external knowledge.
class ExternalKnowledgeQuerier:

    # The database manager object.
    database_manager = None
    
    # A dictionary of ConceptNet concepts.
    # Key = lowercase concept string (just the english word)
    # Value = a dictionary consisting of:
    #   'predicates': every predicate whose subject or object are
    #   this concept.
    #   'queried': whether ConceptNet has been queried for this
    #   concept. Either True or False.
    #   'name': the name of the concept. Equal to its key.
    concepts = dict()

    # Count the total number of queries made
    query_count = 0

    def __init__(self):
        print("Initializing ExternalKnowledgeQuerier")
        # Make the database manager object
        self.database_manager = DatabaseManager()

        self.query_count = 0
    # end __init__

    # Query ConceptNet for a word. Adds the words' predicates
    # and other information to the databases if they are not
    # already present.
    # Returns the string that is used to identify this concept
    # in the database.
    def QueryConceptNet(self, input_word):
        # What relationships we're actually searching for.
        # Referential:
        #   IsA, PartOf, HasA, DefinedAs, MannerOf
        # Causal:
        #   UsedFor, CapableOf, Causes, HasSubevent,
        #   HasFirstSubevent, HasLastSubevent
        # Affective:
        #   MotivatedByGoal, ObstructedBy, Desires,
        #   CausesDesire
        # Spatial:
        #   AtLocation, LocatedNear
        # Temporal:
        #   Mostly shares with Causal
        # 17 relationships total
        valid_relationships = ['IsA', 'PartOf', 'HasA',
                               'DefinedAs', 'MannerOf',
                               'UsedFor', 'CapableOf', 'Causes',
                               'HasSubevent', 'HasFirstSubevent',
                               'HasLastSubevent',
                               'MotivatedByGoal', 'ObstructedBy',
                               'Desires', 'CausesDesire',
                               'AtLocation', 'LocatedNear']
        
        #print("Querying concepts for: " + str(input_word))
        query_result = None

        # Get the cleaned version of the concept word.
        input_lower = self.CleanWord(input_word)
        
        # Check to see if the word is in the database
        # by fetching it.
        # If the return value is an empty list, it's not
        # in the database.
        sql_select_response = self.database_manager.select_row('concepts',
                                                               ['name'],
                                                               [input_lower])
        existing_concept = False
        if len(sql_select_response) > 0:
            # Check if it's been queried in ConceptNet.
            if sql_select_response[0][1] == 1:
                # If so, flag it as an existing concept.
                existing_concept = True
            # end if
        # end if

        # If this is NOT an existing concept that has already been
        # queried in ConceptNet, query it in ConceptNet.
        if not existing_concept:
            # Otherwise, query from the public API
            print("Not in cache, querying API for " + input_lower)
            # Form the API query
            # URL of the api we are querying.
            # http://api.conceptnet.io is the public API.
            # test_query = 'http://api.conceptnet.io/query?node=/c/en/dog&rel=/r/CapableOf'
            # If an EC2 instance is made this will be the instance's url.
            api_url = 'http://api.conceptnet.io/query?'
            # Form the concept net URI for the input word.
            cn_uri = self.ParseToURI('c', 'en', input_lower)
            # 'node' is a URI that must match either the start
            # or the end. 
            node_text = 'node=' + cn_uri

            # If the total query count + the number of
            # queries this loop is going to make would
            # go over the 120 requests/minute limit, wait
            # for 65 seconds before continuing.
            if self.query_count % 120 + len(valid_relationships) >= 120:
                print("Approaching rate limit. Sleeping for 65 seconds.")
                time.sleep(65)
                print("hey :) 65 seconds elapsed. Waking up.")
            try:
                # Try to add the searched for concept to the concepts
                # database so we can mark it as queried.
                self.MaybeAddConceptToDatabase(input_lower, 1)
                # Search for each of a restricted set of relationships.
                for relationship in valid_relationships:
                    print("Querying relationship " + relationship)
                    relation_text = 'rel=/r/' + relationship
                    query_uri_body = (api_url +
                                      node_text +
                                      "&" + relation_text)
                    # Make the query
                    query_result = requests.get(query_uri_body).json()

                    # Print query results
                    print("Query: " + query_uri_body)
                    print("Edges found: " + str(len(query_result['edges'])))
                    for edge in query_result['edges']:
                        if not edge_found:
                            edge_found = True
                        #print("    " + str(edge))
                        # Store the edge in the concepts cache.
                        self.AddEdgeToDatabase(edge, input_lower)
                    # end for
                    # Update total query count
                    self.query_count += 1
                # end for
                print("Total query count: " + str(self.query_count))
            # end try
            except:
                e = sys.exc_info()[0]
                print("Error while querying: " + str(e) + ". Waiting 65 seconds " +
                      "and trying to query concept again")
                time.sleep(65)
                print("hey :) 65 seconds elapsed. Waking up" +
                      " and trying query again.")
                return self.QueryConceptNet(input_word)
            # end except
        # end if

        return input_lower
    # end QueryConceptNet

    

    # Add an edge from a query to the database.
    def AddEdgeToDatabase(self, input_edge, input_concept):
        predicate_dict = dict()
        # Get the raw URI data for the relationship,
        # its start concept, and its end concept.
        #print("Input Edge: " + str(input_edge))
        start = input_edge['start']['@id']
        end = input_edge['end']['@id']
        rel = input_edge['rel']['@id']
        weight = input_edge['weight']
        # Parse the URIs into their constituent parts.
        parsed_start = self.ParseFromURI(start)
        parsed_end = self.ParseFromURI(end)
        parsed_rel = self.ParseFromURI(rel)
        # Make a dictionary to return this information.
        # Get the source concept's name
        predicate_dict['source'] = parsed_start['word']
        # Get the relationship's name
        predicate_dict['relationship'] = parsed_rel['word']
        # Get the target concept's name
        predicate_dict['target'] = parsed_end['word']
        predicate_dict['weight'] = weight
        # Add the predicate to the database.
        self.AddPredicateToDatabase(input_predicate, input_concept)
        return None
    # end method AddEdgeToDatabase
    # Add a single predicate to the database. 
    # Input: predicate_in, the predicate dictionary to make a row
    #           for in the predicates table.
    #       queried_concept, the name of the concept which was queried
    #           to get this predicate. 
    def AddPredicateToDatabase(self, predicate_in, queried_concept):
        # Add the source and target concepts to the concepts table
        #   if it's not there.
        
        # Check if the source concept's in the concepts table.
        # Clean the source and target names as well. 
        source_concept = self.CleanWord(predicate_in['source'])
        relationship = predicate_in['relationship']
        target_concept = self.CleanWord(predicate_in['target'])
        # Clean the queried concept as well just in case
        queried_concept = self.CleanWord(queried_concept)
        weight = predicate_in['weight']
        source_queried = 0
        target_queried = 0
        # Mark which concept is the queried one.
        if source_concept == queried_concept:
            source_queried = 1
            target_queried = 0
        elif target_concept == queried_concept:
            source_queried = 0
            target_queried = 1
        else:
            print("Error adding predicate to database: queried concept is neither source nor target.")
        # end elif
        self.MaybeAddConceptToDatabase(source_concept, source_queried)
        self.MaybeAddConceptToDatabase(target_concept, target_queried)

        # Insert the predicate into the predicates table.
        # Make sure it's not a duplicate.
        # Fetch any rows that match the source, relationship, and target.
        select_return = self.database_manager.select_row('predicates',
                                                         ['source', 'relationship', 'target'],
                                                         [source_concept, relationship, target_concept])
        # If any rows were found, that means this predicate is a duplicate.
        # If no rows were found, add this row to the database.
        if len(select_return) == 0:
            row_data = (queried_concept, source_concept, relationship, target_concept, weight)
            self.database_manager.insert_row('predicates', row_data)
        # end if
        return None
    # end method AddPredicateToDatabase

    # Try to add a concept to the concepts database if it is
    # not already there. 
    def MaybeAddConceptToDatabase(self, concept, queried):
        # Clean the input
        concept = self.CleanWord(concept)
        # Check if the concept's in the concepts table.
        select_return = self.database_manager.select_row('concepts',
                                                         ['name'],
                                                         [concept])
        # If not, add it.
        if len(select_return) < 0:
            row_data = [concept, queried]
            self.database_manager.insert_row('concept', row_data)
        return None
    # end MaybeAddConceptToDatabase
    
    # Given a concept word, return a list of predicate dictionaries
    # consisting of: 
    #   'source': name of the source concept.
    #   'target': name of the target concept.
    #   'relationship': name of the relationship
    #       between the source and target concepts.
    #   'weight': float weight of the relationship from ConceptNet.
    def GetPredicates(self, concept_word):
        # Clean the input
        concept_word = self.CleanWord(concept_word)
        predicates = list()

        # First, query concept net for the word in case
        # it is not already in the database.
        database_name = self.QueryConceptNet(concept_word)

        # The predicates for the concept are now in the
        # database if there are any at all.
        
        # Return a dictionary with:
        #   ['predicates']['name']
        #       put (source, relationship, predicate, weight) into each
        #       entry of the 'predicates' list
        return_dict = dict()
        return_dict['predicates'] = None
        return_dict['name'] = database_name
        # Get its predicates from the database.
        sql_select_predicates = list()
        # Get all rows where the concept is the source.
        source_predicates = self.database_manager.select_row('predicates',
                                                            ['source'],
                                                            [database_name])
        # Get all rows where the concept is the target.
        target_predicates = self.database_manager.select_row('predicates',
                                                            ['target'],
                                                            [database_name])
        sql_select_predicates.extend(source_predicates)
        sql_select_predicates.extend(target_predicates)
        # Each entry in the predicates list is a dictionary with:
        #   source, relationship, target, weight
        for sql_predicate in sql_select_predicates:
            predicate_dict = dict()
            predicate_dict['source'] = sql_predicate[1]
            predicate_dict['relationship'] = sql_predicate[2]
            predicate_dict['target'] = sql_predicate[3]
            predicate_dict['weight'] = sql_predicate[4]
            predicates.append(predicate_dict)
        # end for

        return_dict['predicates'] = predicates
        
        return return_dict
    # end GetPredicates

    # Parse a concept-net URI into its three constituent parts:
    # /type/language/word
    #   type (c = concept, r = relationship, etc.)
    #   language (en, ja, etc.)
    #   word (text of the concept)
    def ParseFromURI(self, input_uri):
        # Split the URI by /
        split_uri = input_uri.split('/')
        # if the length of the split is >3, then it's a concept.
        if len(split_uri) > 3:
            parsed_uri = {'type': split_uri[1],
                          'language': split_uri[2],
                          'word': split_uri[3]}
        else:
            parsed_uri = {'type': split_uri[1],
                          'word': split_uri[2]}
        return parsed_uri
    # end ParseFromURI
    # Parse a type, language, and word into a concept net URI.
    def ParseToURI(self, input_type, input_language, input_word):
        uri = '/' + input_type + '/' + input_language + '/' + input_word
        return uri
    # end ParseToURI

    # Standardize the given concept word and return its
    # cleaned form. 
    def CleanWord(self, concept_word):
        if not isinstance(concept_word, str):
            print("input " + str(concept_word) + " is not a string.")
        
        cleaned_word = ""
        
        # First, lower-case the word.
        cleaned_word = concept_word.lower()
        # Then, remove all apostrophes
        cleaned_word = cleaned_word.replace("'", "")
        # Next, replace all spaces with underscores
        cleaned_word = cleaned_word.replace(" ", "_")

        return cleaned_word
    # end CleanWord

    # Given a concept, get its embedding value. 
    def GetEmbedding(self, concept_word):
        # First, clean the word so we can look it up accurately
        cleaned_word = self.CleanWord(concept_word)
        # Next, search for it in the embeddings table.
        select_result = self.database_manager.select_row('embeddings',
                                                         ['name'],
                                                         [cleaned_word])
        # DEBUG
        #print("embedding obtained for " + cleaned_word + ", select result length: " + str(len(select_result)))
        embedding = list()
        if len(select_result) > 0:
            # If there is an embedding from the results, set it.
            embedding = select_result[0][1:]
        # If no embedding was found, return an empty list.
        return embedding
    # end GetEmbedding
                
def main():
    print ("This is the main in external_knowledge_querier")
    
    cn_querier = ExternalKnowledgeQuerier()

    result = cn_querier.GetEmbedding('dog')
    
    for item in result[0]:
        print(str(item))

# end main

if __name__ == '__main__':
    main()
