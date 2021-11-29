import itertools
from collections import deque

import networkx as nx

from scipy import spatial

from knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeFactory
from hypothesis import Hypothesis, Evidence
from constants import Constants as const

from output_writer import OutputWriter

# For testing
from external_knowledge_querier import ExternalKnowledgeQuerier
import argparse

# Object to contain functions for evaluating
# hypotheses. 
class HypothesisEvaluator:
    
    def __init__(self, args_in):
        self.args = args_in
        self.hypothesis_id_counter = 0
        print("Hypothesis Evaluator initialized.")

    # Solve the system's multi-objective optimization problem.
    # Given a knowledge graph and set of hypotheses, find the hypothesis
    # set that:
    #   1. Has the highest score according to a set of objective functions.
    #   2. Does not contain any contradictions.
    # Return a sorted list of each valid set of hypotheses and their scores.
    def multi_objective_optimization(self, kg_in, hypothesis_set_in):
        # DEBUG:
        print("Calling multi-objective-optimization")
        
        # For writing intermediary outputs
        output_writer = OutputWriter(self.args)
        
        # Make a map of hypothesis IDs to hypotheses.
        hypotheses_by_id = dict()
        for hypothesis in hypothesis_set_in:
            hypotheses_by_id[hypothesis.hypothesis_id] = hypothesis
        
        # A list of the hypotheses with no contradictions.
        always_acceptable_hypotheses = list()
        # A list of hypotheses that have at least one contradiction each.
        contradicting_hypotheses = list()
        # Sort each hypothesis based on whether or not they
        # contradict with at least one other hypothesis. 
        for hypothesis in hypothesis_set_in:
            # Check if this hypothesis has already been
            # sorted. If so, skip it.
            if (hypothesis in always_acceptable_hypotheses
                or hypothesis in contradicting_hypotheses):
                continue

            # Check if it has any contradicting hypotheses.
            # If so, add it to the list of hypotheses with
            # contradictions. 
            if hypothesis.has_contradicting_hypotheses():
                contradicting_hypotheses.append(hypothesis)
            # If it does not have any contradicting hypotheses,
            # add it to the list of always acceptable hypotheses. 
            else:
                always_acceptable_hypotheses.append(hypothesis)
        # end for

        h_score_by_id = dict()
        # For each hypothesis with a contradiction, estimate their
        # scores and make a dictionary of hypothesis IDs to scores.
        for hypothesis in contradicting_hypotheses:
            est_score = self.estimate_hypothesis_score(hypothesis, kg_in)
            h_score_by_id[hypothesis.hypothesis_id] = est_score
            print("Estimated score of hypothesis " + str(hypothesis.hypothesis_id) + ": " + str(est_score))
        # end for

        # Now that we have an estimated score for each hypothesis,
        # formulate the hypotheses with contradictions into a networkx graph.
        # Each node is a hypothesis.
        # Form an edge between the nodes of every hypothesis pair
        # that does not contradict.

        # First, make a networkx graph with the hypotheses
        # as nodes, keyed by their hypothesis IDs.
        # The weight will be the hypothesis' estimated score.
        # Note: Graph() makes an undirected graph.
        nx_graph = nx.Graph()
        for hypothesis in contradicting_hypotheses:
            # Because weights must be integers, we multiply each
            # score by 1000 and round. 
            int_score = round(h_score_by_id[hypothesis.hypothesis_id])
            nx_graph.add_node(hypothesis.hypothesis_id,
                              weight = int_score)
        # end for

        # Go through every hypothesis with at least one contradiction
        for h1 in contradicting_hypotheses:
            # Check every hypothesis with a contradiction
            for h2 in contradicting_hypotheses:
                # Don't compare the hypothesis to itself.
                if h1.hypothesis_id == h2.hypothesis_id:
                    continue
                # Check if the hypotheses contradict.
                if not h1.contradicts(h2):
                    # If not, make an edge between them in the
                    # networkx graph.
                    #nx_graph.edges[node_id, edge.target_node.node_id]['relationship'] = edge.relationship
                    nx_graph.add_edge(h1.hypothesis_id,
                                     h2.hypothesis_id)
                # end if not
            # end for
        # end for

        # Get the maximum weight clique of the graph of hypotheses
        # we just formed.
        # Automatically uses the 'weight' attribute for each node.
        # max_weight_clique returns:
        #   0: a list of the node names in the max clique
        #   1: the weight of the max clique
        max_clique = nx.max_weight_clique(nx_graph)
        print("hypothesis graph: " + str(nx_graph))
        print("max clique: " + str(max_clique))

        # Grab all the hypotheses in the clique. These are the
        # hypotheses in the maximum weighted independent set of
        # hypotheses with contradictions.
        mwis_hypotheses = list()
        for h_id in max_clique[0]:
            mwis_hypotheses.append(hypotheses_by_id[h_id])
        # end for

        # For the best estimated hypothesis from each
        # mutually contradicting set, get the final
        # hypothesis set. 
        # Maintain a list of scored sets.
        # Each scored set is a dictionary containing:
        #   'set': the list of hypotheses that make up the set
        #   'score': the set's total objective function score.
        scored_sets = list()

        new_hypothesis_set = list()
        for acceptable_hypothesis in always_acceptable_hypotheses:
            new_hypothesis_set.append(acceptable_hypothesis)
        # end for
        for hypothesis in mwis_hypotheses:
            new_hypothesis_set.append(hypothesis)
        # end for
        # Filter by evidence, which will re-asses and reject
        # hypotheses based on their evidence.
        # This will also resolve any missing premise hypotheses
        # if any evidence is premised on other hypotheses.
        new_accepted, new_rejected = self.filter_by_base_evidence(new_hypothesis_set)
        final_hypothesis_set = new_accepted
        # Score this hypothesis set.
        score = self.calculate_objective_score(kg_in, final_hypothesis_set)
        # Make the new scored set
        scored_set = dict()
        scored_set['set'] = final_hypothesis_set
        scored_set['score'] = score
        scored_sets.append(scored_set)

        # Make an intermediary output of this set and the results of
        # the filters on the hypotheses for this set.
        output_file_name = 'best_hypothesis_set' + '.json'
        output_writer.graph_and_hypotheses_to_json(kg_in,
                                                   hypothesis_set_in,
                                                   scored_set,
                                                   output_file_name)              


        return scored_sets
    # end multi_objective_optimization

    # ===== OBJECTIVE SCORE CALCULATIONS =====
        
    # Calculates the objective score of a knowledge graph and
    # set of hypotheses. 
    # Calculate the graph structure based objective functions:
    #   1. density
    # and the one evidence-based objective function:
    #   2. evidence strength
    def calculate_objective_score(self, kg_in, hypothesis_set_in):
        total_objective_score = 0
        # Make a network x graph of the knowledge graph, as well
        # as from the hypotheses.
        # First, add each node to the graph.
        # The node will be its ID.
        # Note: Graph() makes an undirected graph.
        nx_graph = nx.Graph()
        for node_id, kg_node in kg_in.items():
            # Skip concept nodes
            if kg_node.node_type == 'concept':
                continue
            nx_graph.add_node(node_id)
        # end for
        # Next, add the edges from the knowledge graph.
        for node_id, kg_node in kg_in.items():
            # Only go off of outgoing edges. Duplicates will
            # be ignored, and since the graph is undirected we
            # don't have to worry about directions.
            # Skip concept nodes
            if kg_node.node_type == 'concept':
                continue
            for edge in kg_node.edges:
                # If the edge leads to a concept node,
                # skip it.
                if edge.target_node.node_type == 'concept':
                    continue
                #print('relationship: ' + edge.relationship)
                nx_graph.add_edge(node_id,
                                  edge.target_node.node_id)
                nx_graph.edges[node_id, edge.target_node.node_id]['relationship'] = edge.relationship
            # end for
        # end for
        # DEBUG
        print("Number of edges (pre-hypotheses): " + str(nx_graph.number_of_edges()))
        # Finally, add edges from the hypotheses.
        for hypothesis in hypothesis_set_in:
            nx_graph.add_edge(hypothesis.source_node.node_id,
                              hypothesis.target_node.node_id)
            #print('relationship: ' + hypothesis.relationship)
            nx_graph.edges[hypothesis.source_node.node_id, hypothesis.target_node.node_id]['relationship'] = hypothesis.relationship
        # end for

        # DEBUG
        print("Number of nodes: " + str(nx_graph.number_of_nodes()))
        print("Number of edges: " + str(nx_graph.number_of_edges()))
        #print("Nodes:")
        #print(str(nx_graph.nodes))
        #print("Edges:")
        #print(str(nx_graph.edges.data()))

        # Calculate connectivity
        connectivity_score = self.calculate_connectivity(nx_graph)
        print("Connectivity score: " + str(connectivity_score))

        # Calculate density for an nx graph.
        density_score = self.calculate_density_nx(nx_graph)
        print("Weighted density score: " + str(self.args.density_weight*density_score))

        # Calculate evidence strength
        evidence_strength_score = self.calculate_evidence_strength(hypothesis_set_in)
        print("Weighted evidence strength score: " + str(self.args.evidence_weight*evidence_strength_score))

        # Sum the individual scores
        total_objective_score += self.args.connectivity_weight * connectivity_score
        total_objective_score += self.args.density_weight * density_score
        total_objective_score += self.args.evidence_weight * evidence_strength_score

        # Return a dictionary with the total score
        # and each component of the score:
        #   'total_score'
        #   'connectivity_score'
        #   'density_score'
        #   'evidence_strength_score'
        return_dict = dict()
        return_dict['total_score'] = total_objective_score
        return_dict['connectivity_score'] = connectivity_score
        return_dict['density_score'] = density_score
        return_dict['evidence_strength_score'] = evidence_strength_score
            
        return return_dict
    # end calculate_objective_score

    # Calculate the edge connectivity of a knowledge graph
    # and a set of hypotheses.
    #   The minimum number of edges whose removal makes the graph
    #   disconnected is the edge connectivity.
    # Uses networkx's edge_connectivity function.
    def calculate_connectivity(self, nx_graph_in):
        connectivity_score = 0
        connectivity_score = nx.edge_connectivity(nx_graph_in)
        return connectivity_score
    # end calculate_connectivity

    # Calculate the density of a knowledge graph and
    # set of hypotheses.
    # Uses networkx's density function
    def calculate_density_nx(self, nx_graph_in):
        density_score = 0
        density_score = nx.density(nx_graph_in)
        return density_score
    # end calculate density

    # Calculate the overall strength of the evidence in a
    # set of hypotheses
    def calculate_evidence_strength(self, hypotheses):
        evidence_strength = 0

        for hypothesis in hypotheses:
            evidence_strength += self.get_evidence_strength(hypothesis)

        return evidence_strength
    # end calculate_evidence_strength
    # Get the evidence strength of a single hypothesis.
    def get_evidence_strength(self, hypothesis):
        hypothesis.sum_evidence_scores()
        return hypothesis.evidence_score
    # end get_evidence_strength

    # Calculate the evidence scores for all hypotheses in a set.
    # These values will be stored on the hypothesis object itself,
    # as well as on each individual piece of evidence. 
    def calculate_all_evidence_scores(self, hypothesis_set):
        print("Calculating all evidence scores")
        for hypothesis in hypothesis_set:
            self.calculate_evidence_score(hypothesis)
        # end for
        return
    # end calculate_all_evidence_scores
        
    # Calculate the strength of the evidence for a single hypothesis.
    # This value will be stored on each individual piece of evidence. 
    def calculate_evidence_score(self, hypothesis):
        # Go through each piece of evidence for the hypothesis.
        # For referential relationships, the evidence types are:
        #               attribute : data
        #     matching_attributes : attribute_1, attribute_2
        #          shared_concept : edge_1, edge_2, concpet_node

        for evidence_index, evidence in hypothesis.get_evidence().items():
            # First, reset the score of this evidence back to 0 (default)
            evidence.reset_score()
            # Score the evidence itself based on the type of evidence.
            if evidence.evidence_type == 'matching_attributes':
                # Used by Referential
                # The attributes match. Contribute 1 to the hypothesis' score.
                score_increase = 1
                evidence.score += score_increase
                # Set the evidence's explanation.
                explanation = "[+" + str(score_increase) + "] | matching attribute " + str(evidence.data[0]['value'])
                evidence.set_explanation(explanation)
            elif evidence.evidence_type == 'shared_concept':
                # Used by Referential
                # Both nodes have an is_concept relationship to the same concept.
                score_increase = 1
                evidence.score += score_increase
                explanation = ("[+" + str(score_increase) + "] | "
                               + evidence.explanation)
                evidence.set_explanation(explanation)
            elif evidence.evidence_type == 'shared_object':
                # Used by Referential
                # Both nodes have an 'is' relationship to the same concept.
                # This relies on the premise that both the hypothesized
                # 'is' relationships are accepted, but whether this piece
                # of evidence is accepted or not will be decided at a later
                # stage.
                # For now, calculate it its score. This score will not change, it
                # represents the score it'll add to its hypothesis IF the evidence
                # is accepted (e.g. its premise hypotheses are accepted)
                score_increase = 1
                evidence.score += score_increase
                explanation = ("[+" + str(score_increase) + "] | "
                               + evidence.explanation)
                evidence.set_explanation(explanation)
            elif evidence.evidence_type == 'returning_object':
                # Used by Causal
                # Both action nodes have an object node that has an
                # 'is' relationship to the other's object node,
                # implying that the same object took part in
                # both actions.
                score_increase = 1
                evidence.score += score_increase
                explanation = ("[+" + str(score_increase) + "] | " +
                               evidence.explanation)
                evidence.set_explanation(explanation)
            elif evidence.evidence_type == 'concept_path':
                # Used by Causal
                # There is a path through ConceptNet nodes and
                # edges from one node to the other.
                # The evidence's score is equal to the product
                # of the path edge's weights.
                score_increase = 1
                for edge in evidence.get_data('concept_path')[0]['value']:
                    score_increase *= edge.cn_weight
                #end for
                evidence.score += score_increase
                explanation = ("[+" + str(score_increase) + "] | " +
                               evidence.explanation)
                evidence.set_explanation(explanation)
            else:
                print("HELP! Evidence of an unhandled type encountered! Evidence type: " +
                      evidence.evidence_type)
                score_increase = 1
                evidence.score += score_increase
        # end for

        # Have the hypothesis sum the scores of all its evidence
        # and store it in its evidence_score.
        hypothesis.sum_evidence_scores()

        # DEBUG: Have the hypothesis explain itself.
        #print("Hypothesis evidence score calculated. " + str(hypothesis))
        
        
        return
    # end calculate_evidence_score

    # Calculate the interelatedness of a knowledge graph.
    # This is the average of the average relatedness of every
    # node in the knowledge graph.
    def calculate_interrelatedness(self, kg_in):
        interrelatedness = 0
        sum_average_similarity = 0
        node_count = 0
        # Go through each node in the knowledge graph
        for node_id, node in kg_in.items():
            # Only count the average similarity of concept nodes that
            # are formally part of the knowledge graph.
            if not (node.node_type == 'concept' and
                    node.graph_member):
                continue
            # Get its average similarity in the graph and
            # add it to the sum.
            sum_average_similarity += self.average_similarity(node, kg_in)
            node_count += 1
        # end for
        # Average the average similarities to get the interrelatedness
        interrelatedness = sum_average_similarity / node_count
        return interrelatedness
    # end calculate_interrelatedness

    # Calculate the average similarity of a single knowledge graph
    # node to the rest of the knowledge graph it's in.
    def average_similarity(self, node_in, kg_in):
        count = 0
        sum_similarity = 0
        for node_id, node in kg_in.items():
            # Don't compare the node to itself
            if node_id == node_in.node_id:
                continue
            # Only compare the node to concept nodes, since
            # scene graph nodes don't have embeddings.
            if not node.node_type == 'concept':
                continue
            # Don't compare the node to any concepts that
            # aren't formally part of the knowledge graph.
            if not node.graph_member:
                continue
            count += 1
            sum_similarity += self.similarity(node_in, node)
        # end for
        average_similarity = sum_similarity / count
        return average_similarity
    # end calculate_relatedness

    # Calculate the cosine similarity between two knowledge graph
    # nodes based on their embeddings from ConceptNet.
    def similarity(self, node_1, node_2):
        embedding_1 = node_1.embedding
        embedding_2 = node_2.embedding
        # If either of them do not have embeddings, this is an error.
        if len(embedding_1) == 0 or len(embedding_2) == 0:
            print("Error in hypothesis_evaluator --> similarity; node has no embeddings.")
        # end if
        # Use SciPy's distance calculator.
        distance = spatial.distance.cosine(embedding_1, embedding_2)
        # Cosine similarity is 1 - distance.
        similarity = 1 - distance
        return similarity
    # end similarity

    

    # Given a hypothesis, estimate its contribution
    # to the overall score.
    # Takes the hypothesis itself, as well as knowledge graph it would be
    # applied to (without any other hypotheses).
    def estimate_hypothesis_score(self, hypothesis_in, kg_in):
        estimated_score = 0

        # Estimate evidence contribution.
        est_evidence_score = self.args.evidence_weight * hypothesis_in.evidence_score

        # Estimate density contribution.
        # Get the base density of the knowledge graph without any
        # hypotheses.
        base_node_count = len(kg_in)
        base_edge_count = self.graph_edge_count(kg_in)
        base_density = self.calculate_density(base_node_count, base_edge_count)

        # Estimate how many nodes and edges this hypothesis would add to
        # the knowledge graph.
        predicted_node_count = 0
        predicted_edge_count = 0
        # If it is a referential hypothesis, it adds a single edge (is)
        if hypothesis_in.coherence_type == 'referential':
            predicted_edge_count = 1
        # If it is a causal hypothesis, it adds a single edge (sequence)
        # TODO: Let this handle causal chains that are added. 
        elif hypothesis_in.coherence_type == 'causal':
            predicted_edge_count = 1
        # If it is an affective hypothesis, it adds a single edge
        # and a single node.
        elif hypothesis_in.coherence_type == 'affective':
            predicted_edge_count = 1
            predicted_node_count = 1
        # end elif
        # Get the density with the additional edges and nodes
        # added by this hypothesis.
        predicted_density = self.calculate_density(base_node_count + predicted_node_count,
                                                   base_edge_count + predicted_edge_count)
        # This hypothesis' contribution to the density score is this
        # predicted density minus the graph's base density.
        density_contribution = predicted_density - base_density
        # Multiply this by the weight of density scores. 
        est_density_score = self.args.density_weight * density_contribution

        est_subsequent_score = 0
        # See if there are any other hypotheses premised
        # on this hypothesis. If so, estimate their score
        # contributions as well and add them to
        # this hypothesis'
        for hypothesis in hypothesis_in.subsequent_hypotheses:
            # Only add the subsequent hypothesis' estimated score to
            # this estimated score if it is still valid. 
            if hypothesis.is_valid():
                est_subsequent_score += self.estimate_hypothesis_score(hypothesis, kg_in)
        # end for

        # The final estimated score is the sum of:
        #   the estimated evidence score
        #   the estimated density score
        #   the estimated scores of any subsequent hypotheses
        estimated_score = est_evidence_score + est_density_score + est_subsequent_score

        return estimated_score
    # end estimate_hypothesis_score

    # Calculate density for a knowldge graph with the
    # given number of nodes and the given number of edges.
    def calculate_density(self, n, m):
    # density = m / (n(n-1)/2), m = num edges, n = num nodes
        density = m / (n * (n - 1) / 2)
        return density
    # end calculate_density

    # Get the number of edges in a given knowledge graph
    def graph_edge_count(self, kg_in):
        edge_count = 0
        # Go through each node in the knowledge graph.
        for node_id, node in kg_in.items():
            # Get every node's edge count.
            edge_count += node.get_edge_count()
        # end for
        # Halve it, since it counts every outgoing edge on
        # every node thus double-counting every edge.
        edge_count = edge_count / 2
        return edge_count
    # end graph_edge_count

    # ===== END OBJECTIVE SCORE CALCULATIONS =====

    # Given a set of hypotheses, determine which ones
    # contradict with one another. Each hypothesis
    # contains a list with the IDs of the hypotheses that
    # it mutually contradicts with.
    def determine_contradicting_hypotheses(self, hypothesis_set_in):

        for hypothesis_1 in hypothesis_set_in:
            # Check each other hypothesis
            for hypothesis_2 in hypothesis_set_in:
                # Don't compare a hypothesis to itself.
                if hypothesis_1 == hypothesis_2:
                    continue
                # Find out if these two hypotheses contradict.
                if self.hypotheses_contradict(hypothesis_1,
                                              hypothesis_2,
                                              hypothesis_set_in):
                    # If they do, place them on each others'
                    # contradicting hypothesis lists.
                    #print("Contradicting hypotheses: ")
                    #print(" " + str(hypothesis_1))
                    #print(" " + str(hypothesis_2))
                    hypothesis_1.add_contradicting_hypothesis(hypothesis_2)
                    hypothesis_2.add_contradicting_hypothesis(hypothesis_1)
            # end for
        # end for
        
        return
    # end determine_contradicting_hypotheses

    # Returns True if the two hypotheses given mutually
    # contradict with one another.
    # Returns False otherwise
    def hypotheses_contradict(self,
                              hypothesis_1,
                              hypothesis_2,
                              hypothesis_set_in):
        contradicting = False
        # Check the coherence type and call the appropriate
        # hypothesis constraint function.
        if (hypothesis_1.coherence_type == 'referential'
            and hypothesis_2.coherence_type == 'referential'):
            contradicting = self.referential_hypothesis_constraint(hypothesis_1,
                                                                   hypothesis_2,
                                                                   hypothesis_set_in)
        # end if

        return contradicting
    # end hypotheses_contradict

    # Heuristics for determining if two referential hypotheses contradict
    # one another.

    # Two referential hypotheses contradict if, when they are accepted
    # together:
    #   1. They cause one object to be assigned an is relationship to
    #   two other objects that are themselves not assigned is relationships
    #   to each other (violates the Transitive property). 
    def referential_hypothesis_constraint(self,
                                          hypothesis_1,
                                          hypothesis_2,
                                          hypothesis_set_in):
        contradicting = True

        # The is relationship that hypothesis 1 is asserting
        # is between these two nodes. 
        # is relationships are bidirectional.
        source_1 = hypothesis_1.source_node
        target_1 = hypothesis_1.target_node

        # The is relationship that hypothesis 2 is asserting
        # is between these two nodes.
        source_2 = hypothesis_2.source_node
        target_2 = hypothesis_2.target_node

        # See if any of them match.
        matching_node_1 = None
        matching_node_2 = None

        non_matching_1 = None
        non_matching_2 = None

        if source_1 == source_2:
            matching_node_1 = source_1
            matching_node_2 = source_2
            non_matching_1 = target_1
            non_matching_2 = target_2
        elif source_1 == target_2:
            matching_node_1 = source_1
            matching_node_2 = target_2
            non_matching_1 = target_1
            non_matching_2 = source_2
        elif target_1 == source_2:
            matching_node_1 = target_1
            matching_node_2 = source_2
            non_matching_1 = source_1
            non_matching_2 = target_2
        elif target_1 == target_2:
            matching_node_1 = target_1
            matching_node_2 = target_2
            non_matching_1 = source_1
            non_matching_2 = source_2
        # If none of them match, there is no contradiction.
        else:
            contradicting = False
            return contradicting

        # If there is any match, then one object, matching_node_1/2,
        # is being assigned to two other objects; non_matching_1 and
        # non_matching_2.
        # Check the other hypotheses to see if an 'is' relationship
        # is being asserted between the two other (non-matching) objects.

        for hypothesis in hypothesis_set_in:
            # Skip either of the two hypotheses passed in.
            if (hypothesis == hypothesis_1
                or hypothesis == hypothesis_2):
                continue
            # Skip any non-is hypotheses
            elif not hypothesis.relationship == 'is':
                continue
            # Skip any non valid hypotheses.
            if not hypothesis.is_valid():
                continue
            # In the cases below, there IS a valid hypothesis
            # placing an 'is' relationship between the two
            # other objects. Thus, the two hypotheses
            # passed in do not contradict each other. 
            elif (non_matching_1 == hypothesis.source_node
                and non_matching_2 == hypothesis.target_node):
                contradicting = False
                return contradicting
            elif (non_matching_1 == hypothesis.target_node
                  and non_matching_2 == hypothesis.source_node):
                contradicting = False
                return contradicting
        # end for
        
        # If we have reached this point, we have not found
        # information showing that the two hypotheses
        # don't contradict. Return that they do contradict. 
        return contradicting
    # end referential_hypothesis_constraint



    # Given a full set of hypotheses, return which
    # ones to keep and which ones to discard based
    # solely on the evidence in each hypothesis.
    # None of the hypotheses discarded could contradict with
    # other hypotheses or be accepted in any circumstances,
    # since the evidence they are based on have been rejected. 
    
    # Every hypothesis has a set of evidence, where at least one
    # piece of evidence is marked as Vital. Vital evidence is
    # necessary for the hypothesis to exist at all. 
    # Any piece of evidence can be rejected if:
    #   1. It contains a contradiction, which depends on
    #       the hypothesis' relationship type.
    #   2. It is premised on other hypotheses and any
    #       single one of its premised hypotheses are rejected.
    # Any hypothesis that does not have at least one piece of
    # non-rejected Vital evidence is itself rejected.
    # Returns both the stable set of hypotheses that have no
    # contradictions and the set of hypotheses that had to
    # be rejected due to contradictions. 
    def filter_by_base_evidence(self, hypothesis_set_in):
        # Maintain a list of accepted and rejected hypotheses
        accepted_hypotheses = list()
        rejected_hypotheses = list()

        # Go through each hypothesis, reset its evidence
        # rejections, and place them in the accepted
        # hypotheses list. 
        for hypothesis in hypothesis_set_in:
            hypothesis.reset_rejected_evidence()
            accepted_hypotheses.append(hypothesis)
        # end for

        # Do a loop of checking hypothesis evidence and rejecting
        # hypotheses until no new hypothesis is rejected.
        stable_state = False
        while not stable_state:
            # For each hypothesis that is still accepted, check
            # each piece of evidence.
            # Keep track of which ones should be rejected after
            # checking its evidence.
            hypotheses_to_reject = list()
            for hypothesis in accepted_hypotheses:
                # Go through each piece of evidence and see if
                # it should be rejected. 
                for index, evidence in hypothesis.get_evidence().items():
                    # Ignore any piece of evidence that has already been rejected.
                    if evidence.is_rejected():
                        continue
                    
                    should_reject, explanation = self.should_reject_evidence(hypothesis,
                                                                            evidence,
                                                                            accepted_hypotheses)
                    if should_reject:
                        # DEBUG
                        print("Rejecting evidence: " + str(evidence)
                              + ". Explanation: " + explanation)
                        evidence.reject(explanation)
                # end for
                
                # We have now gone through each piece of evidence
                # for this hypothesis and either marked it for
                # rejection or left it alone.
                # Check if the hypothesis is still valid.
                # If not, add it to the list of hypotheses to reject.
                if not hypothesis.is_valid():
                    # DEBUG
                    print("Rejecting hypothesis: " + str(hypothesis))
                    hypotheses_to_reject.append(hypothesis)
            # end for

            # If there were no new hypotheses to reject, we have
            # reached a stable state. Stop looping.
            if len(hypotheses_to_reject) < 1:
                stable_state = True
            else:
                # Otherwise, there are new hypotheses to reject.
                # Remove the hypotheses to reject from the set of
                # accepted hypotheses and add it to the set
                # of rejected hypotheses.
                for hypothesis_to_reject in hypotheses_to_reject:
                    accepted_hypotheses.remove(hypothesis_to_reject)
                    rejected_hypotheses.append(hypothesis_to_reject)
                # end for
            # end else
        # end while

        # We have now accepted or rejected hypotheses based SOLELY on
        # their evidence, and reached a stable state of hypotheses
        # which COULD exist alongside each other.

        # Return the accepted and rejected hypotheses.
        return accepted_hypotheses, rejected_hypotheses
    # end filter_by_base_evidence

    # Determine whether a piece of evidence should be
    # rejected based on the hypothesis it is a part of
    # and what other hypotheses have been accepted.
    # Returns whether it should be rejected (True) or not (False)
    # and an explanation for the rejection. 
    def should_reject_evidence(self, hypothesis, evidence, accepted_hypotheses):
        # Do a generic check for whether the evidence's
        # premised hypotheses are valid if it has any. 
        if len(evidence.premise_hypotheses) > 0:
            for premise_hypothesis in evidence.premise_hypotheses:
                # Check first to see if it's in the list
                # of accepted hypotheses. If not, then
                # it is assumed it has been rejected.
                if not premise_hypothesis in accepted_hypotheses:
                    # If not, this evidence should be rejected,
                    # as one of its premise hypotheses has
                    # not been accepted.
                    rejection_explanation = ("Premise hypothesis " +
                                             str(premise_hypothesis.hypothesis_id) +
                                             " not in accepted hypotheses")
                    return True, rejection_explanation
                # end if not
                # Otherwise, it is an accepted hypothesis. 
                # Check next to see if the hypothesis itself
                # is still valid (has at least one piece of
                # non-rejected Vital evidence).
                if not premise_hypothesis.is_valid():
                    # If not, this evidence should be rejected,
                    # as one of its premise hypotheses is
                    # not valid.
                    rejection_explanation = ("Premise hypothesis " +
                                             str(premise_hypothesis.hypothesis_id) +
                                             " not valid")
                    return True, rejection_explanation
            # end for
        # end if
        # If we have reached this point, either the evidence has no
        # premised hypotheses or all of its premised hypotheses are
        # currently accepted.
        
        # Do a more specific check based on the
        # hypothesis' relationship type itself
        # to determine if the evidence should be
        # rejected.
        if hypothesis.coherence_type == 'referential':
            return self.referential_evidence_constraint(hypothesis, evidence)

        return False, ""
    # end should_reject_evidence

    # Apply heuristics checks to a single piece of evidence from
    # a Referential relationship hypotheses.
    # Returns true if the evidence should be rejected, false
    # if the evidence is still valid.
    # As a second return value, also returns a reason for the rejection. 
    def referential_evidence_constraint(self, hypothesis, evidence):
        # Referential heuristic is based on the type of evidence.
        
        # If it is a shared concept, the two nodes pointing to the
        # concept can't appear in the same image at the same time.
        # Check edge_1's source and edge_2's source, find their
        # 'scene' attributes, and compare them. If they have the
        # same value, the two nodes appear in the same scene.
        # This is a contradiction, as they cannot be the same object
        # AND appear in two places in the same image. The evidence
        # should be rejected.
        if evidence.evidence_type == 'shared_concept':
            edges = evidence.get_data('edge')
            source_node_1 = edges[0]['value'].source_node
            source_node_2 = edges[1]['value'].source_node
            concept_node = evidence.get_datum('target_node')['value']
            scene_1 = source_node_1.get_attribute('scene')['value']
            scene_2 = source_node_2.get_attribute('scene')['value']
            if scene_1 == scene_2:
                rejection_explanation = ("Objects sharing concept appear in same scene.")
                return True, rejection_explanation
            # end if
        # end if

        # If it is a shared object, the two nodes pointing to
        # the same third object cannot appear in the same image.
        # Additionally, neither object can appear in the same image
        # as the shared third object.
        # All in all, none of the three scene should be the same, as
        # the three object cannot be each other AND appear in the same
        # image in two different places at once.
        if evidence.evidence_type == 'shared_object':
            hypotheses = evidence.get_data('hypothesis')
            source_node_1 = hypotheses[0]['value'].source_node
            source_node_2 = hypotheses[0]['value'].source_node
            object_node = evidence.get_datum('target_node')['value']
            scene_1 = source_node_1.get_attribute('scene')['value']
            scene_2 = source_node_2.get_attribute('scene')['value']
            scene_3 = object_node.get_attribute('scene')['value']
            if (scene_1 == scene_2
                or scene_1 == scene_3
                or scene_2 == scene_3):
                rejection_explanation = "Objects hypothesized to be the same appear in same scene."
                return True, rejection_explanation
        # end if

        # If the evidence is neither of the types above or it is and
        # we have found no reason to reject it, return False.
        return False, ""
    # end referential_evidence_constraint

# end HypothesisEvaluator

def main():
    print ("Hey :) this is the main in hypothesis_evaluator")

    # Dummy args to make the hypothesis evaluator happy
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    # What image set we are parsing.
    parser.add_argument('--set_number', default=28)
    # What percentage of bounding box overlap qualifies two
    # objects in a scene graph as duplicates.
    parser.add_argument('--overlap_threshold', default=0.25)
    # Parameters for Causal hypothesis generation
    # The maximum number of edges in a causal path
    # between two nodes.
    # 3 means there is exactly one intervening ConceptNet
    # node in the path.
    parser.add_argument('--causal_length', default=3)
    # Whether or not edges should be restricted to causal edges.
    parser.add_argument('--causal_type', default=False)
    # Whether we should generate all sets or just
    # the optimal one while doing hypothesis
    # evaluation.
    parser.add_argument('--generate_all_sets', default=False)
    # Weights for the different score types
    # for hypothesis evaluation.
    parser.add_argument('--density_weight', default=100)
    parser.add_argument('--connectivity_weight', default=1)
    parser.add_argument('--evidence_weight', default=1)

    args = parser.parse_args()
    # end args
    
    evaluator = HypothesisEvaluator(args)
    querier = ExternalKnowledgeQuerier()
    node_factory = NodeFactory()

    # Make a kg with concept nodes.
    # Passing them in as 'concept' should automatically
    # fetch their embeddings for them in node_factory. 
    kg = dict()
    node_1 = node_factory.make_kg_node('dog',
                                       'dog_h',
                                       'concept',
                                       -1,
                                       1,
                                       None,
                                       True)
    node_2 = node_factory.make_kg_node('frisbee',
                                       'frisbee_h',
                                       'concept',
                                       -1,
                                       1,
                                       None,
                                       True)
    node_3 = node_factory.make_kg_node('play',
                                       'bike_h',
                                       'concept',
                                       -1,
                                       1,
                                       None,
                                       True)
    kg[node_1.node_id] = node_1
    kg[node_2.node_id] = node_2
    kg[node_3.node_id] = node_3

    # Get their similarity
    similarity = evaluator.similarity(node_1, node_2)
    print("Similarity of " + node_1.concept_name + " to " + node_2.concept_name + ": " + str(similarity))
    similarity = evaluator.similarity(node_1, node_3)
    print("Similarity of " + node_1.concept_name + " to " + node_3.concept_name + ": " + str(similarity))
    similarity = evaluator.similarity(node_2, node_3)
    print("Similarity of " + node_2.concept_name + " to " + node_3.concept_name + ": " + str(similarity))
    # Get the average similarity of each node to the kg as a whole
    avg_sim_1 = evaluator.average_similarity(node_1, kg)
    avg_sim_2 = evaluator.average_similarity(node_2, kg)
    avg_sim_3 = evaluator.average_similarity(node_3, kg)
    print("Average similarity of " + node_1.concept_name + ": " + str(avg_sim_1))
    print("Average similarity of " + node_2.concept_name + ": " + str(avg_sim_2))
    print("Average similarity of " + node_3.concept_name + ": " + str(avg_sim_3))

    # Get the interrelatedness of the knowledge graph.
    interrelatedness = evaluator.calculate_interrelatedness(kg)
    print("Interrelatedness: " + str(interrelatedness))

# end main

if __name__ == '__main__':
    main()
