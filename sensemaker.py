import requests
import os
import pickle
import json
import torch
import numpy as np
import copy
import random
import sys
import argparse
import difflib
from collections import deque

import xml.etree.ElementTree as ET

from knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeFactory
from hypothesis import Hypothesis, Evidence
from hypothesis_generator import HypothesisGenerator
from hypothesis_evaluator import HypothesisEvaluator
from visualizer import Visualizer
from external_knowledge_querier import ExternalKnowledgeQuerier
from constants import Constants as const
from output_writer import OutputWriter
from input_handler import InputReader


class SenseMaker:

    # Object class names keyed by their ID number.
    obj_name_map = dict()
    # Predicate class names keyed by their ID number.
    pred_name_map = dict()

    # A list of interpersonal relationships
    ip_relationships = list()

    # A dictionary mapping node ID tuples to the visual
    # similarity score between them.
    #   Key is a tuple of integers
    #   Value is a double similarity score
    similarity_scores = dict()

    # Image IDs (their filenames) mapped to their index
    #   in the current set.
    image_index_to_id = dict()
    image_id_to_index = dict()

    # A knowledge graph built from scene triplets.
    # The ID of each node is its key in this dictionary.
    knowledge_graph = dict()

    # Whether to print dense logs
    verbose = False

    # Random character names already used
    names_used = list()


    # An object that queries external knowledge.
    external_knowledge_querier = None

    # An object that creates KnowledgeGraphNodes
    node_factory = None
    
    def __init__(self, args_in):
        print("Initializing SenseMaker")

        print("args: " + str(args_in))
        self.args = args_in

        sys.setrecursionlimit(10000)
                
        self.similarity_scores = dict()

        self.names_used = list()

        # Initialize the object that will be querying external knowledge.
        self.external_knowledge_querier = ExternalKnowledgeQuerier()

        # Initialize the object that will be used to create KnolwedgeGraphNodes
        self.node_factory = NodeFactory()

        # Seed the RNG to get the same results.
        random.seed(5)

        set_directory = const.data_directory + 'vgg/set_' + str(self.args.set_number) + '/'

        # Force the images at specific indexes to be included.
        #forced_indices = []
        #forced_indices = [0]
        forced_indices = [0, 1, 2]

        # Load the map of image indices to image IDs.
        # Image IDs correspond to the image's file name.
        # This must be loaded from the set directory, as each
        # set has a different mapping of images indices to IDs.
        # NOTE: The keys are integers, but they are stored
        # as strings.
        image_index_to_id_path = set_directory + 'image_index_to_id.json'
        self.image_index_to_id = json.load(open(image_index_to_id_path, 'r'))        

        for image_index, image_id in self.image_index_to_id.items():
            self.image_id_to_index[image_id] = image_index

        # DEBUGGING:
        # Filter out nodes for these concept names
        #self.filter_concept_names = ["helmet", "tree", "shirt", "short", "people", "pant", "flag"]
        #self.filter_concept_names = ["tree"]
        self.filter_concept_names = []
        # Cap the number of objects of a single concept name
        # per scene
        self.same_concept_cap = 10
        # Cap the number of images
        max_images = 5

        # DEBUGGING:
        #    limit the number of predicates we look at per
        #    inferred interpersonal relationship edge to
        #    this number.
        predicate_limit = 1

        self.knowledge_graph = dict()

        # Load in the list of interpersonal relationships.
        #ip_rel_path = data_directory + 'interpersonal_relationships.json'
        #self.ip_relationships = json.load(open(ip_rel_path, 'r'))['relationships']
        self.ip_relationships = ['relative', 'friend', 'enemy']
        

        print("Set " + str(self.args.set_number))
        overall_kg = dict()

        input_reader = InputReader(self.args, self.node_factory)
        overall_kg = input_reader.read_scene_graphs(set_directory)
        
        # We now have a knowledge graph with all the scene graph
        # nodes from all the images and all the scene graph
        # edges within each image.

        # Print all object and relationship nodes.
        #print("Printing KG nodes...")
        #for node_id, node in overall_kg.items():
        #    print(str(node))

        # Form hypotheses about relationships between nodes.
        all_hypotheses = self.generate_hypotheses(overall_kg)
        print("Hypotheses generated")
        print("Number of hypotheses: " + str(len(all_hypotheses)))

        # We now have an over-generated set of hypotheses
        # from the hypothesis generation step.

        # Next, we must evaluate and trim them to form the highest
        # scoring set of hypotheses which has no contradictions.

        scored_sets = self.evaluate_hypotheses(overall_kg, all_hypotheses)

        print("Hypotheses evaluated")

        coherence_type_counts = dict()
        # Count the number of each type of hypothesis generated.
        for hypothesis in scored_sets[0]['set']:
            if not hypothesis.coherence_type in coherence_type_counts:
                coherence_type_counts[hypothesis.coherence_type] = 0
            coherence_type_counts[hypothesis.coherence_type] += 1

        print("Coherence type counts: ")
        for key, value in coherence_type_counts.items():
            print(str(key) + ": " + str(value))

        # Visualize the results
        visualizer = Visualizer(self.args)
        visualizer.visualize(overall_kg, all_hypotheses, scored_sets)

        return
        
    # end init

    # ======= BEGIN HYPOTHESIS GENERATION AND HELPER FUNCTIONS =======

    # Generate hypotheses for relationships between nodes in the knowledge graph.
    # Returns the list of hypotheses.
    def generate_hypotheses(self, knowledge_graph_in):
        print("Generating hypotheses")
        all_hypotheses = list()

        # Generate hypotheses from commonsense knowledge networks
        kn_hypotheses = self.hypotheses_from_knowledge_networks(knowledge_graph_in)
        all_hypotheses.extend(kn_hypotheses)

        # Generate hypotheses from commonsense reasoning datasets
        #rdb_hypotheses = self.hypotheses_from_reasoning_datasets(knowledge_graph_in)
        #all_hypotheses.extend(rdb_hypotheses)

        return all_hypotheses
    # end generate_hypotheses

    # Generate hypotheses from commonsense knowledge networks,
    # like ConceptNet, WordNet, and VerbNet.
    # Returns the hypotheses
    def hypotheses_from_knowledge_networks(self, knowledge_graph_in):
        print("Generating hypotheses from knowledge networks")
        print("From concept net")

        # First, populate the scene graph with concepts from
        # ConceptNet.
        # Each scene graph object and predicate node will have an
        # 'is_concept' edge to a node representing the node's concept in
        # ConceptNet. These nodes will themselves have edges
        # connecting them with each other adjacent concept's nodes.
        self.populate_concepts(knowledge_graph_in)

        # A list of hypotheses inferred from knowledge networks.
        hypotheses = list()

        hypothesis_generator = HypothesisGenerator(self.args)

        # Generate Referential relationship hypotheses
        referential_hypotheses = hypothesis_generator.generate_referential_hypotheses(knowledge_graph_in)
        hypotheses.extend(referential_hypotheses)

        # We now have scene graph nodes with 'is' relationships
        # to other scene graph nodes.

        # Generate Causal relationship hypotheses
        causal_hypotheses = hypothesis_generator.generate_causal_hypotheses(knowledge_graph_in, hypotheses)
        hypotheses.extend(causal_hypotheses)

        # Generate Affective relationship hypotheses
        affective_hypotheses = hypothesis_generator.generate_affective_hypotheses(knowledge_graph_in,
                                                                                  hypotheses)
        hypotheses.extend(affective_hypotheses)

        causal_from_affective = hypothesis_generator.causal_hypotheses_from_affective(knowledge_graph_in,
                                                                                      hypotheses)
        hypotheses.extend(causal_from_affective)

        temporal_hypotheses = hypothesis_generator.generate_temporal_hypotheses(knowledge_graph_in,
                                                                                hypotheses)
        hypotheses.extend(temporal_hypotheses)

        

        print("Affective hypotheses:" )
        for hypothesis in affective_hypotheses:
            print(hypothesis)
        
        
        return hypotheses
    # end hypotheses_from_knowledge_networks

    # Get ConceptNet concepts, their related predicates, and any
    # ConceptNet nodes in a concept's neighborhood for the
    # nodes in the scene graph.
    def populate_concepts(self, knowledge_graph_in):
        # Keep a dictionary of nodes for concepts from ConceptNet,
        # keyed by the concept's name.
        cn_concept_nodes = dict()
        
        # For each scene graph node, get its corresponding
        # ConceptNet node and related predicates.
        for node_id, kg_node in knowledge_graph_in.items():
            # Skip any node that is not a scene graph node.
            if not (kg_node.node_type == 'object'
                    or kg_node.node_type == 'predicate'
                    or kg_node.node_type == 'action'):
                print("Node " + kg_node.node_name +
                      " is not an object, predicate, or action." +
                      " Skipping concept assignment.")
                continue

            #if 'woman' in kg_node.node_name:
            #    print("Checking woman")
            
            predicates = self.get_all_cn_predicates(kg_node)

            print("Number of predicates: " + str(len(predicates)))
            # If no predicates are returned, skip the rest of
            # the procedure for this node.
            if len(predicates) <= 0:
                continue
            # Get the exact name of the concept as it would appear
            # in the database.
            clean_name = self.external_knowledge_querier.CleanWord(kg_node.concept_name)
            # Set the conceptnet concept name to this cleaned name. 
            kg_node.cn_concept_name = clean_name

            # Get or make a node for this concept.
            concept_node = None
            # Check to see if we already have a node
            # for this ConceptNet concept.
            if clean_name in cn_concept_nodes:
                concept_node = cn_concept_nodes[clean_name]
            else:
                # If not, make a node for the concept.
                # Name, node type, image id, score, bounding box.
                # Most of these are none, since this the node for a concept
                # and not something from the scene graph. 
                concept_node = self.node_factory.make_kg_node(clean_name,
                                                              clean_name + '_h',
                                                              'concept',
                                                              -1,
                                                              1,
                                                              None,
                                                              True)
                # Add the node to the dictionary of concept nodes.
                cn_concept_nodes[clean_name] = concept_node
            # end else
            
            # Get the neighborhood of this concept.
            # For every concept in a predicate that is not the matching
            # concept, get or make a node for that concept and make
            # an edge using the relationship in the predicate.
            for predicate in predicates:
                # Get the name of the concept that does not match the scene
                # graph node's concept.
                nm_concept_name = ""
                if predicate['source'] == clean_name:
                    nm_concept_name = predicate['target']
                else:
                    nm_concept_name = predicate['source']

                # Get or make the node for the non-matching concept.
                # Since this name comes straight from a predicate,
                # it is already cleaned. 
                nm_concept_node = None
                if nm_concept_name in cn_concept_nodes:
                    nm_concept_node = cn_concept_nodes[nm_concept_name]
                else:
                    # Make a node for the concept.
                    nm_concept_node = self.node_factory.make_kg_node(nm_concept_name,
                                                                     nm_concept_name + '_h',
                                                                     'concept',
                                                                     -1,
                                                                     1,
                                                                     None,
                                                                     False)
                    # Add it to the dictionary of concept nodes.
                    cn_concept_nodes[nm_concept_name] = nm_concept_node
                # end else

                # Make an edge based on the relationship in this predicate.
                source_node = None
                target_node = None
                # Determine which direction this edge faces
                if predicate['source'] == clean_name:
                    source_node = concept_node
                    target_node = nm_concept_node
                else:
                    source_node = nm_concept_node
                    target_node = concept_node
                # Make the edge itself
                predicate_edge = KnowledgeGraphEdge(source_node,
                                                    predicate['relationship'],
                                                    target_node,
                                                    False)
                predicate_edge.coherence_type = const.cn_rel_to_coherence[predicate['relationship']]
                # Mark this as an edge between two ConceptNet nodes.
                predicate_edge.cn_edge = True
                # Store the weight from ConceptNet
                predicate_edge.cn_weight = predicate['weight']

                # Check if the concept node already has this edge.
                # If so, don't add it again.
                if source_node.has_edge_to(target_node.node_id):
                    continue
                else:
                    # Add the edge to the source node.
                    # Calling add_edge will add it as an incoming edge
                    # to the target node. 
                    source_node.add_edge(predicate_edge)
            # end for

            # Add an 'is_concept' relationship between the scene graph node
            # and its concept's node.
            is_concept_edge = KnowledgeGraphEdge(kg_node,
                                                 'is_concept',
                                                 concept_node,
                                                 True)
            # Set weight to 1 so the is_concept edge doesn't
            # affect evidence score calculations. 
            is_concept_edge.cn_weight = 1
            # Added as an outgoing edge from the scene graph node
            # to the ConceptNet node. 
            kg_node.add_edge(is_concept_edge)
        # end for

        # Add the concept nodes to the knowledge graph.
        for concept_name, concept_node in cn_concept_nodes.items():
            knowledge_graph_in[concept_node.node_id] = concept_node

        return
    # end populate_concepts

    # Find all ConceptNet predicates that relate to the
    # given concept node.
    def get_all_cn_predicates(self, kg_node):
        print("Finding all ConceptNet predicates for " + kg_node.concept_name)

        predicates_result = self.external_knowledge_querier.GetPredicates(kg_node.concept_name)
        #print("ConceptNet name: " + query_result['name'])
        #print("Predicates: ")
        #for predicate in query_result['predicates']:
        #    print("    " + str(predicate))
        # The name that the concept is saved under in the
        # database is here: predicates_result['name']
        all_predicates = predicates_result['predicates']
        
        # Filter which predicates this function returns.
        
        # A mapping of conceptnet relationship types to
        # Narrative Coherence elements.
        # self.coherence_to_cn_rel
        # self.cn_rel_to_coherence

        predicate_count_by_coherence = dict()
        for coherence, cn_rel_list in const.coherence_to_cn_rel.items():
            predicate_count_by_coherence[coherence] = 0

        predicates_to_return = list()
        # Filter out all referential predicates
        for predicate in all_predicates:
        #    if not self.cn_rel_to_coherence[predicate['relationship']] == "referential":
            predicates_to_return.append(predicate)

        return predicates_to_return
    # end get_all_cn_predicates

    # ======= END HYPOTHESIS GENERATION AND HELPER FUNCTIONS =======

    # ======= START HYPOTHESIS EVALUATION AND HELPER FUNCTIONS ======

    def evaluate_hypotheses(self, knowledge_graph_in, hypotheses_in):
        # Make a hypothesis evaluator
        hypothesis_evaluator = HypothesisEvaluator(self.args)
        
        # Score each hypothesis. 
        hypothesis_evaluator.calculate_all_evidence_scores(hypotheses_in)

        # Separate the full set of hypotheses into a
        # stable acceptable set and the hypotheses that had
        # to be rejected due to its evidence containing
        # contradictions and being rejected.
        acceptable_hypotheses = list()
        rejected_hypotheses = list()

        print("Filtering hypotheses based on evidence")

        acceptable_hypotheses, rejected_hypotheses = hypothesis_evaluator.filter_by_base_evidence(hypotheses_in)

        # For each hypothesis, go through their evidence and append
        # whether the evidence was accepted or rejected to their explanation.
        print("Acceptable hypotheses: ")
        for hypothesis in acceptable_hypotheses:
            print(str(hypothesis))
        # end for

        print("Rejected hypotheses: ")
        for hypothesis in rejected_hypotheses:
            print(str(hypothesis))
        # end for

        print("Determining mutually contradicting hypotheses")

        hypothesis_evaluator.determine_contradicting_hypotheses(acceptable_hypotheses)



        print("Outputting to file")
        print("Writing to JSON")

        output_file_name = 'initial_filter_output' + '.json'

        output_writer = OutputWriter(self.args)
        output_writer.graph_and_hypotheses_to_json(knowledge_graph_in,
                                                   hypotheses_in,
                                                   None,
                                                   output_file_name)
  


        print("Searching for optimal hypothesis set")

        scored_sets = dict()

        if self.args.generate_all_sets:
            scored_sets = hypothesis_evaluator.generate_all_sets(knowledge_graph_in,
                                                                 hypotheses_in)
        else:
            scored_sets = hypothesis_evaluator.multi_objective_optimization(knowledge_graph_in,
                                                                            hypotheses_in)
        # Instead of passing in acceptable_hypothese, passing in ALL hypotheses
        

        #print("Scored hypothesis sets:")
        #for scored_set in scored_sets:
        #    print("NEW SET")
        #    print("Score: " + str(scored_set['score']))
        #    print("Set: ")
        #    for hypothesis in scored_set['set']:
        #        print(str(hypothesis))
        # end for

        #print("Calculating objective function scores.")

        #self.calculate_objective_score(overall_kg, acceptable_hypotheses)

        return scored_sets
    # end evaluate_hypotheses




    # Get the name of a concept as it would appear in the database
    # by calling the external knowledge handler's name cleaning
    # function. 
    def get_clean_concept_name(self, concept_name_in):
        clean_concept_name = self.external_knowledge_querier.CleanWord(concept_name_in)
        return clean_concept_name
    # end get_clean_concept_name


    # Check the given knowledge graph for a node with the given
    # concept name.
    # Return a list of KnowledgeGraphNodes of all instances.
    # Returns empty list if there are none.
    def search_kg_for_all_nodes(self, knowledge_graph_in, concept_name):
        nodes_to_return = list()
        for node_id, kg_node in knowledge_graph_in.items():
            # Check if the concept name matches.
            # If so, add this node to the list of nodes to return.
            if kg_node.concept_name == concept_name:
                nodes_to_return.append(kg_node)
        # end for
        return nodes_to_return
    # end search_kg_for_all_nodes
        
    # Check the given knowledge graph for a node with the given
    # concept name and image id.
    # If it exists, return it.
    # If not, return None.
    def search_kg_for_node(self, knowledge_graph_in, concept_name, image_id):
        node_to_return = None
        for node_id, kg_node in knowledge_graph_in.items():
            # Check if the concept name and image ID match.
            # If so, stop searching and set this as the node to return.
            if kg_node.concept_name == concept_name and kg_node.image_id == image_id:
                node_to_return = kg_node
                break
        # end for
        return node_to_return
    # end search_kg_for_node

    # Check the given knowledge graph for a node with the
    # given node ID.
    # If it exists, return it.
    # If not, return None.
    def search_kg_for_node(self, kg_in, node_id_in):
        node_to_return = None
        for node_id, kg_node in kg_in.items():
            if node_id == node_id_in:
                node_to_return = kg_node
                break
        # end for
        return node_to_return
    # end search_kg_for_node

    # Count and print the following statistics:
    #   Number of objects in each scene graph and total
    #   Number of predicates in each scene graph and total
    #   The number of each type of relationship
    #       in the commonsense predicates for all the scene graphs.
    #   The number of each type of narrative coherence
    #       relation represented by the commonsense predicates. 
    def stat_counter(self, kg_in, hypotheses):
        # Count the number of objects and predicates in
        #   each scene graph.
        # Key is image index, value is number of objects
        #   or predicates in the image's scene graph.
        objects_per_scene_graph = dict()
        preds_per_scene_graph = dict()

        for node_id, kg_node in kg_in.items():
            if kg_node.image_id in self.image_id_to_index:
                image_index = int(self.image_id_to_index[kg_node.image_id])
            else:
                image_index = -1
            #print("Image index: " + str(image_index))
            if kg_node.node_type == "object":
                if not image_index in objects_per_scene_graph:
                    objects_per_scene_graph[image_index] = 1
                else:
                    objects_per_scene_graph[image_index] += 1
            elif kg_node.node_type == "predicate":
                if not image_index in preds_per_scene_graph:
                    preds_per_scene_graph[image_index] = 1
                else:
                    preds_per_scene_graph[image_index] += 1
            else:
                continue
                #print("Node is not an object or predicate")
                #print("Node type: " + kg_node.node_type)
            # end if
        # end for

        print("Objects and predicates per scene graph: ")
        total_objects = 0
        total_predicates = 0
        for image_index in objects_per_scene_graph.keys():
            print("Image " + str(image_index) + ": "
                  + str(objects_per_scene_graph[image_index])
                  + " objects, "
                  + str(preds_per_scene_graph[image_index])
                  + " predicates")
            total_objects += objects_per_scene_graph[image_index]
            total_predicates += preds_per_scene_graph[image_index]
        # end for
        print("Total: " + str(total_objects) + " objects, "
              + str(total_predicates) + " predicates"
              + " in the scene graphs.")

        # Count the number of commonsense predicates of each type.
        # The key is the relationship name from concept net.
        # The value is the number of those relationships 
        cn_predicates_by_type = dict()
        # Go through each KG node's cn predicates
        for node_id, kg_node in kg_in.items():
            for predicate in kg_node.cn_predicates:
                # Increase the count for its relationship
                if not predicate["relationship"] in cn_predicates_by_type:
                    cn_predicates_by_type[predicate["relationship"]] = 0
                # end if
                cn_predicates_by_type[predicate["relationship"]] += 1
            # end for
        # end for

        print("Commonsense predicate counts: ")


        predicate_count_by_coherence = dict()
        for coherence, cn_rel_list in const.coherence_to_cn_rel.items():
            predicate_count_by_coherence[coherence] = 0

        
        total_cn_predicates = 0

        for relationship, count in cn_predicates_by_type.items():
            print(relationship + ": " + str(count))
            total_cn_predicates += count
            predicate_count_by_coherence[const.cn_rel_to_coherence[relationship]] += count
        # end for
        print("Commonsense predicates by narrative coherence element:")
        for coherence, count in predicate_count_by_coherence.items():
            print(coherence + ": " + str(count))
        print("Total commonsense predicates: " + str(total_cn_predicates))

        print("Hypothesis counts: ")
        print("Total number of hypotheses: " + str(len(hypotheses)))
        
    # end stat_counter

# end class SenseMaker

def main():
    #print("hey :)")
    print("main in SenseMaker")

    #print("argv: " + str(argv))

    parser = argparse.ArgumentParser()
    #parser.add_argument('--infer', nargs = '*', default = [])
    #parser.add_argument('--object_threshold', type = float, default=0.5)
    #parser.add_argument('--is_threshold', type = float, default=0.5)
    #parser.add_argument('--generate_text', action = "store_true")

    args = parser.parse_args()

    #print(str(args))
    
    sense_maker = SenseMaker(args)

if __name__ == '__main__':
    #main(sys.argv)
    main()
