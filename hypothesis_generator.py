from collections import deque

from knowledge_graph import KnowledgeGraph, KnowledgeGraphNode, KnowledgeGraphEdge
from hypothesis import Hypothesis, Evidence
from constants import Constants as const

# Object to contain functions for generating
# hypotheses. 
class HypothesisGenerator:

    # Use this counter to assign unique IDs to each hypothesis.
    hypothesis_id_counter = 0
    
    def __init__(self, args_in):
        self.args = args_in
        self.hypothesis_id_counter = 0
        print("Hypothesis Generator initialized.")

    # Hypothesize Referential relationships amongst the nodes in
    # the given scene graph.
    # Returns the set of Referential hypotheses themselves.
    def generate_referential_hypotheses(self, kg_in):
        hypotheses = list()

        # For the first pass, look for object nodes that
        # share the same concept nodes.
        # Hypothesize an 'is' relationship between any two
        # scene graph nodes which share an 'is_concept' relationship
        # with the same concept node.
        #target_edge_relationship = 'is_concept'
        #target_shared_node_type = 'concept'
        
        first_pass_hypotheses = self.referential_hypothesis_first_pass(kg_in)
        hypotheses = first_pass_hypotheses

        # For the second pass, use the existing hypothesized
        # 'is' relationships to see if any objects share an 'is'
        # relationship to the same third object.
        # Keep doing it until no new hypotheses have been added
        # to the set.
        set_altered = True
        counter = 1
        while set_altered == True:
            print("Loop " + str(counter))
            set_altered = False

            second_pass_hypotheses = self.referential_hypothesis_second_pass(kg_in,
                                                                             hypotheses)
            # Now merge the second pass hypotheses with the existing hypothesis set.
            for hypothesis in second_pass_hypotheses:
                #print("Trying to add hypothesis to set")
                dummy_set, did_change = self.add_hypothesis_to_set(hypothesis, hypotheses)
                if did_change:
                    print("Set altered")
                    set_altered = True
            # end for

            print("Done merging :)")

            # If no changes have been made to the overall hypothesis set,
            # we have reached a steady state and can stop generating more
            # hypotheses. 
            if set_altered == False:
                break
            print("SIZE OF HYPOTHESIS SET: " + str(len(hypotheses)))
            counter += 1
        # end while
        

        return hypotheses

    # For the first pass, look for object nodes that
    # share the same concept nodes.
    # Hypothesize an 'is' relationship between any two
    # scene graph nodes which share an 'is_concept' relationship
    # with the same concept node.
    def referential_hypothesis_first_pass(self, kg_in):
        hypotheses = list()

        # Hypothesize an 'is' relationship between any two
        # scene graph nodes which share a the target edge relationship
        # with the same node of the target shared node type.
        # Only do so with Object nodes (node_type == "object")
        for node_id, kg_node in kg_in.nodes.items():
            # Skip this node if it is not an object.
            if not kg_node.node_type == "object":
                continue
            # Get all the target nodes this scene graph
            # node has the target relationship to.
            is_target_nodes = list()
            for edge in kg_node.edges:
                if (edge.relationship == 'is_concept'
                    and edge.target_node.node_type == 'concept'):
                    is_target_nodes.append(edge.target_node)
            # Check each other knowledge graph node.
            for node_id_2, kg_node_2 in kg_in.nodes.items():
                # Do not let the node form a relationship with itself.
                if node_id_2 == node_id:
                    continue
                # See if it has an 'is_concept' relationship to any of the
                # same concept nodes.
                for target_node in is_target_nodes:
                    if kg_node_2.has_edge_to(target_node.node_id,
                                             'is_concept'):
                        # kg_node and kg_node_2 both point to the same
                        # third node.
                        
                        # Form a hypothesis for an 'is' relationship
                        # between the two nodes.
                        new_hypothesis = Hypothesis(self.hypothesis_id_counter,
                                                    kg_node,
                                                    kg_node_2,
                                                    'is',
                                                    'referential',
                                                    True)
                        self.hypothesis_id_counter += 1
                        # Add evidence for this hypothesis.
                        # Structural evidence for this 'is' hypothesis
                        # are the target edge types ('is_concept' or 'is') from the
                        # source and target nodes which point to the same third node.
                        # The data for the evidence is both edges and the shared third node.
                        # The type of evidence will be shared_ + the type of the third node.
                        structural_evidence = Evidence()
                        structural_evidence.evidence_type = 'shared_' + 'concept'
                        structural_evidence.add_data('edge', kg_node.get_edge(target_node.node_id, 'is_concept'))
                        structural_evidence.add_data('edge', kg_node_2.get_edge(target_node.node_id, 'is_concept'))
                        structural_evidence.add_data('target_node', target_node)
                        # This is considered Vital evidence. Without it, the 'is' relationship
                        # would not exist to begin with. 
                        structural_evidence.set_vital()

                        explanation = (kg_node.node_name + " and " +
                                       kg_node_2.node_name +
                                       " both have 'is_concept' relationship to " +
                                       target_node.node_name)
                        structural_evidence.set_explanation(explanation)
                        
                        new_hypothesis.add_evidence(structural_evidence)
                        # For additional evidence, see how many of the objects' 'looks'
                        # attributes match each other.
                        # This is to see how much the objects look like each other
                        # according to the image observations.
                        looks_evidence_list = self.generate_looks_evidence(kg_node, kg_node_2)
                        for looks_evidence in looks_evidence_list:
                            new_hypothesis.add_evidence(looks_evidence)

                        # We now have a new hypothesis.

                        # Add it to the set of hypotheses this
                        # function will return. 
                        self.add_hypothesis_to_set(new_hypothesis, hypotheses)
                        
                        break
                # end for concept_node in is_concept_nodes
            # end for node_id_2, kg_node_2 in kg_in.items()
        # end for node_id, kg_node in kg_in.items()

        return hypotheses

    # end referential_hypothesis_first_pass

    # For the second pass, look through the hypotheses from the
    # first pass to see if any object nodes share an
    # 'is' relationship to the same third object nodes.
    # If so, by the transitive property, they should also
    # share an 'is' relationship with each other.
    # Returns the hypotheses to add to the hypothesis set passed in.
    # Does not change the hypothesis set passed in at all. 
    def referential_hypothesis_second_pass(self, kg_in, hypotheses_in):
        print("Referential second pass")

        # Store all the new hypotheses to add and do not
        # add them to the overall set of hypotheses. 
        hypotheses_to_add = list()
        
        # Go through each scene graph node that is an object.
        for node_id, kg_node in kg_in.nodes.items():
            # Skip this node if it is not an object.
            if not kg_node.node_type == "object":
                continue
            # Get all 'is' hypotheses this scene graph node
            # is a source or target node in. These are all
            # the hypotheses that point an 'is' relationship
            # from this object to another object. 
            involved_hypotheses = list()
            # Track also all the hypotheses where
            # this scene graph node is NOT the source node.
            non_involved_hypotheses = list()
            for hypothesis in hypotheses_in:
                if (hypothesis.source_node.node_id == node_id
                    or hypothesis.target_node.node_id == node_id):
                    involved_hypotheses.append(hypothesis)
                else:
                    non_involved_hypotheses.append(hypothesis)
            # end for
            # For each involved hypothesis, look through each
            # non-involved hypothesis for 'is' relationships from
            # other nodes. If they both point to the same node,
            # that suggests a transitive 'is' between the source node
            # of the involved hypothesis and the source node of the
            # non-involved hypothesis
            for involved_hypothesis in involved_hypotheses:
                for non_involved_hypothesis in non_involved_hypotheses:
                    # First, find out which node the scene graph node
                    # is pointing to.
                    third_node = None
                    node_to_link_1 = None
                    if involved_hypothesis.source_node.node_id == node_id:
                        third_node = involved_hypothesis.target_node
                        node_to_link_1 = involved_hypothesis.source_node
                    elif involved_hypothesis.target_node.node_id == node_id:
                        third_node = involved_hypothesis.source_node
                        node_to_link_1 = involved_hypothesis.target_node
                    else:
                        print("HELP! Something happened that shouldn't have!")
                        print("In referential hypothesis second pass, the " +
                              "scene graph node is neither the involved hypothesis' " +
                              "source node nor target node.")

                    # Next, find out if either of the non involved hypothesis'
                    # nodes is the third node.
                    # If so, it is it's OTHER node that we will hypothesize
                    # an 'is' relationship to. If neither is the third node,
                    # then no new hypothesis will be made.
                    node_to_link_2 = None
                    if non_involved_hypothesis.source_node.node_id == third_node.node_id:
                        node_to_link_2 = non_involved_hypothesis.target_node
                    elif non_involved_hypothesis.target_node.node_id == third_node.node_id:
                        node_to_link_2 = non_involved_hypothesis.source_node
                    else:
                        #print("No new hypothesis made.")
                        continue

                    # Create the new hypothesis accordingly.
                    # The hypothesis is for an 'is' relationship between
                    # the two nodes to link. 
                    new_hypothesis = Hypothesis(self.hypothesis_id_counter,
                                                kg_node,
                                                node_to_link_2,
                                                'is',
                                                'referential',
                                                True)
                    self.hypothesis_id_counter += 1
                    # Add evidence for this hypothesis.
                    # The vital evidence is the existence of the first
                    # hypothesis, the second hypothesis, and the mutual
                    # target node.
                    vital_evidence = Evidence()
                    vital_evidence.evidence_type = 'shared_' + 'object'
                    vital_evidence.add_data('hypothesis', involved_hypothesis)
                    vital_evidence.add_data('hypothesis', non_involved_hypothesis)
                    vital_evidence.add_data('target_node', third_node)
                    vital_evidence.set_vital()
                    # As this evidence relies on two other hypotheses, it
                    # is invalid if the other hypotheses are not accepted.
                    # Add the two other hypotheses as premises.
                    vital_evidence.add_premise_hypothesis(involved_hypothesis)
                    vital_evidence.add_premise_hypothesis(non_involved_hypothesis)

                    # Add an explanation for this evidence.
                    explanation = (kg_node.node_name + " and " +
                                   node_to_link_2.node_name +
                                   " both have hypothetical 'is' relationship to " +
                                   third_node.node_name)
                    
                    vital_evidence.set_explanation(explanation)
                    new_hypothesis.add_evidence(vital_evidence)
                    
                    # For additional evidence, see how many of the objects' 'looks'
                    # attributes match each other.
                    # This is to see how much the objects look like each other
                    # according to the image observations.
                    looks_evidence_list = self.generate_looks_evidence(kg_node, node_to_link_2)
                    for looks_evidence in looks_evidence_list:
                        new_hypothesis.add_evidence(looks_evidence)
                    # end for
                    # We now have a new hypothesis.
                    # Add it to the set of hypotheses this function
                    # will return.
                    self.add_hypothesis_to_set(new_hypothesis, hypotheses_to_add)
                    
                # end for
            # end for
        return hypotheses_to_add
        
    # end referential_hypothesis_second_pass

    # Generate Causal hypotheses.
    def generate_causal_hypotheses(self, kg_in, hypotheses_in):
        hypotheses = list()

        # Hypothesize SEQUENCE relationships between two events.
        # SEQUENCE means that the two events are part of the same
        # sequence of events.
        # What makes events part of the same sequence is continuity:
        #   1. Objects involved in one event are part of the other
        #   2. There is a path through Causal links in ConceptNet
        #   linking one event to the other.

        # Look through 'is' relationships to determine which events
        # involve the same objects. 

        # Go through each action node.
        for node_id_1, kg_node_1 in kg_in.nodes.items():
            # Skip anything that's not an action node.
            if not kg_node_1.node_type == "action":
                continue

            # Get the nodes of all of the scene graph objects
            # that were involved in this action. 
            involved_nodes_1 = self.get_involved_object_nodes(kg_node_1)

            # Go through each other action node.
            for node_id_2, kg_node_2 in kg_in.nodes.items():
                # Don't compare a node to itself
                if node_id_1 == node_id_2:
                    continue
                # Skip this if it's not an action node.
                if not kg_node_2.node_type == "action":
                    continue

                # Get the nodes of all the scene graph objects
                # that were involved in this action.
                involved_nodes_2 = self.get_involved_object_nodes(kg_node_2)

                # Look for hypothesized 'is' relationships between the
                # objects involved in the first action and the objects
                # involved in the second action.
                # They imply that the same object was involved in both
                # actions.
                for existing_hypothesis in hypotheses_in:
                    # If this is not a referential hypothesis
                    # with the 'is' relationship, skip it.
                    if not existing_hypothesis.relationship == 'is':
                        continue
                    # Check if the source object was involved with either
                    # action. If so, check if the target object was
                    # involved with the other action.
                    if ((existing_hypothesis.source_node in involved_nodes_1
                            and existing_hypothesis.target_node in involved_nodes_2)
                        or (existing_hypothesis.source_node in involved_nodes_2
                            and existing_hypothesis.target_node in involved_nodes_1)):
                        # If so, then there is (hypothetically) a single object
                        # involved in both actions.
                        # Make a new sequence hypothesis.
                        new_hypothesis = Hypothesis(self.hypothesis_id_counter,
                                                    kg_node_1,
                                                    kg_node_2,
                                                    'sequence',
                                                    'causal',
                                                    True)
                        self.hypothesis_id_counter += 1
                        # Add evidence for this hypothesis.
                        # The vital evidence is the existence of the
                        # 'is' hypothesis.
                        vital_evidence = Evidence()
                        vital_evidence.evidence_type = 'returning_' + 'object'
                        vital_evidence.add_data('hypothesis', existing_hypothesis)
                        vital_evidence.set_vital()
                        # As this evidence relies on two other hypotheses, it
                        # is invalid if the other hypotheses are not accepted.
                        # Add the two other hypotheses as premises.
                        vital_evidence.add_premise_hypothesis(existing_hypothesis)

                        # Add an explanation for this evidence.
                        action_1_object = None
                        action_2_object = None
                        if existing_hypothesis.source_node in involved_nodes_1:
                            action_1_object = existing_hypothesis.source_node
                            action_2_object = existing_hypothesis.target_node
                        else:
                            action_1_object = existing_hypothesis.target_node
                            action_2_object = existing_hypothesis.source_node                            
                        explanation = ("object node " + action_1_object.node_name +
                                       " from action " + kg_node_1.node_name +
                                       " and object node " + action_2_object.node_name +
                                       " from action " + kg_node_2.node_name +
                                       " are the same object via hypothetical 'is' relationship")
                        vital_evidence.set_explanation(explanation)
                        new_hypothesis.add_evidence(vital_evidence)

                        # Add the hypothesis to the set of hypotheses.
                        self.add_hypothesis_to_set(new_hypothesis, hypotheses)
                    # end if
                # end for existing_hypothesis in hypotheses_in

                # See if there is a causal link between the two nodes.
                # Don't look if the concepts are the same.
                if not kg_node_1.cn_concept_name == kg_node_2.cn_concept_name:
                    # Look for a concept path from one node to the other. 
                    concept_path = self.get_scene_graph_concept_path(kg_in,
                                                                     kg_node_1,
                                                                     kg_node_2,
                                                                     const.causal_filter,
                                                                     self.args.causal_length)
                    # Try and make a hypothesis from the concept path.
                    new_hypothesis = self.hypothesis_from_concept_path(concept_path,
                                                                       kg_node_1,
                                                                       kg_node_2,
                                                                       'sequence',
                                                                       'causal')
                    if not new_hypothesis == None:
                        # Add the hypothesis to the set.
                        self.add_hypothesis_to_set(new_hypothesis, hypotheses)
                    # end if
                # end if
                
            # end for node 2
        # end for node 1
        
        return hypotheses
    # end generate_causal_hypotheses

    # Generate Affective hypotheses.
    def generate_affective_hypotheses(self, kg_in, hypotheses_in):
        affective_hypotheses = list()

        # Should be called after first set of causal hypotheses have been generated.
        # 1. For each object in a scene graph, look at each action that the
        # object takes part in.
        # 2. For each of those actions, go to its concept node and look
        # for incoming or outgoing affective relationships (defined
        # in constants).
        # 3. ALSO go to each action hypothesized to be in the same sequence
        # and do the same.
        for node_id, kg_node in kg_in.nodes.items():
            # Skip anything that isn't an object.
            if not kg_node.node_type == 'object':
                continue

            # Gather all actions in a list of dicts.
            # Each dict will have an 'action', the action node itself,
            # and a 'premise', the premise hypothesis that leads to
            # us gathering the action if any.

            # Gather any actions the object is directly involved in.
            # For now, only doing actions that the object is the
            # object of (the object is the one doing the action).
            direct_actions = list()

            involved_actions = self.get_involved_action_nodes(kg_node)
            for action_node in involved_actions:
                direct_actions.append({'action': action_node,
                                       'premise': None})
            # end for

            # Get affective hypotheses for the actions the object
            # is directly involved in. 
            for action_entry in direct_actions:
                action_node = action_entry['action']

                new_affective_hypotheses = self.affective_hypotheses_from_action(action_node,
                                                                                 kg_node,
                                                                                 None)
                for new_hypothesis in new_affective_hypotheses:
                    self.add_hypothesis_to_set(new_hypothesis, affective_hypotheses)
                # end for
            # end for

            # Gather any actions the object's actions are in the
            # same sequence as which also appear later in the
            # sequence. 
            later_sequence_actions = list()
            for hypothesis in hypotheses_in:
                # Skip any hypothesis that is not a sequence hypothesis.
                if not hypothesis.relationship == 'sequence':
                    continue
                # Check if one of this node's direct actions is
                # either the target or the source of the
                # hypothesis. If so, the other action is
                # the source or the target, respectively.
                direct_action_node = None
                other_action_node = None
                
                if self.action_node_in_entries(hypothesis.source_node,
                                               direct_actions):
                    direct_action_node = hypothesis.source_node
                    other_action_node = hypothesis.target_node
                elif self.action_node_in_entries(hypothesis.target_node,
                                                 direct_actions):
                    direct_action_node = hypothesis.target_node
                    other_action_node = hypothesis.source_node
                # If neither is true, this hypothesis does not
                # involve an action that this node acts in. 
                else:
                    continue

                # Check that the other action node appears later
                # in the sequence than the direct action node.
                # If it does not, skip this hypothesis.
                other_action_scene = other_action_node.get_attribute('scene')['value']
                direct_action_scene = direct_action_node.get_attribute('scene')['value']
                if not other_action_scene > direct_action_scene:
                    continue

                # If all of the rest of the criteria have been met, add
                # the action to the set of actions in an action sequence
                # related to the current object node which appear later
                # in the sequence.
                #print("Later sequence action " + str(other_action_node) + " found")
                later_sequence_actions.append({'action': other_action_node,
                                               'premise': hypothesis})
            # end for

            # Go through each later sequence action and make affective
            # hypotheses from them for the current object node.
            for later_sequence_action in later_sequence_actions:
                new_affective_hypotheses = self.affective_hypotheses_from_action(later_sequence_action['action'],
                                                                                 kg_node,
                                                                                 later_sequence_action['premise'])
                for new_hypothesis in new_affective_hypotheses:
                    self.add_hypothesis_to_set(new_hypothesis, affective_hypotheses)
            # end for

        # end for node_id, kg_node in kg_in

        return affective_hypotheses
    # end generate_affective_hypotheses

    # Create affective hypotheses from a given action
    # for a given object involved in that action.
    # If a premise hypothesis is given, add it
    # to the evidence. 
    def affective_hypotheses_from_action(self,
                                         action_node,
                                         object_node,
                                         premise_hypothesis=None):
        affective_hypotheses = list()

        # Get the action node's concept
        # If the action does not have a concept, skip it.
        if action_node.get_first_edge('is_concept') == None:
            print("Node " + action_node.node_name + " does not have an is_concept edge. Skipping.")
            return list()
        action_concept_node = action_node.get_first_edge('is_concept').target_node
        # Go through its outgoing and incoming edges and get any ones
        # that have an affective relationship type.
        affective_edges = list()
        for edge in action_concept_node.edges:
            if edge.coherence_type == 'affective':
                affective_edges.append(edge)
        # end for
        for edge_in in action_concept_node.edges_in:
            if edge_in.coherence_type == 'affective':
                affective_edges.append(edge_in)
        # end for

        # Go through each affective edge, find the one
        # that isn't this action's concept, and form an
        # 'affected_by' hypothesis between the object node
        # and the other concept. 
        for affective_edge in affective_edges:
            other_concept_node = None
            if affective_edge.source_node == action_concept_node:
                other_concept_node = affective_edge.target_node
            elif affective_edge.target_node == action_concept_node:
                other_concept_node = affective_edge.source_node
            else:
                print("HELP! D: I'm in a state that should never occur! " +
                      "In generate_affective_hypotheses.")
            # The affected_by hypothesis always goes from the object node
            # to the concept it's affected by. 
            new_hypothesis = Hypothesis(self.hypothesis_id_counter,
                                        object_node,
                                        other_concept_node,
                                        'affected_by',
                                        'affective',
                                        True)
            self.hypothesis_id_counter += 1

            # Add a subtext based on the specific affective
            # relationship from ConceptNet and the
            # direction of the relationship.
            # Determine whether the direction of the affective
            # edge is outgoing from the action or not. 
            outgoing_from_action = None
            if affective_edge.source_node == action_concept_node:
                outgoing_from_action = True
            elif affective_edge.target_node == action_concept_node:
                outgoing_from_action = False
            else:
                print("Affective edge doesn't include the action " +
                      "at all. This shouldn't happen!")
            # Add the subtext based on direction and relationship.
            if affective_edge.relationship == 'CausesDesire':
                if outgoing_from_action:
                    new_hypothesis.subtext = 'Desires'
                else:
                    new_hypothesis.subtext = 'DesiresActionBecause'
            elif affective_edge.relationship == 'MotivatedByGoal':
                if outgoing_from_action:
                    new_hypothesis.subtext = 'HasGoal'
                else:
                    new_hypothesis.subtext = 'MotivatedTo'
            elif affective_edge.relationship == 'Desires':
                if outgoing_from_action:
                    new_hypothesis.subtext = 'Desires'
                else:
                    new_hypothesis.subtext = 'FulfillsDesireOf'
            elif affective_edge.relationship == 'ObstructedBy':
                if outgoing_from_action:
                    new_hypothesis.subtext = 'ObstructedBy'
                else:
                    new_hypothesis.subtext = 'Obstructs'
            
            # As vital evidence, provide the action node and the
            # affective edge.
            vital_evidence = Evidence()
            vital_evidence.evidence_type = 'affected_action'
            vital_evidence.add_data('action', action_node)
            vital_evidence.add_data('affective_edge', affective_edge)
            # If this is premised on any hypothesis, add it as well.
            if not premise_hypothesis == None:
                vital_evidence.add_data('hypothesis', premise_hypothesis)
                vital_evidence.add_premise_hypothesis(premise_hypothesis)
            vital_evidence.set_vital()
            # Explain this evidence
            explanation = ("Action " + action_node.node_name +
                           ", related to Object " + object_node.node_name +
                           ", has the following affective edge: " +
                           str(affective_edge))
            vital_evidence.set_explanation(explanation)
            new_hypothesis.add_evidence(vital_evidence)

            # Add the hypothesis to the set.
            self.add_hypothesis_to_set(new_hypothesis, affective_hypotheses)
        # end for

        return affective_hypotheses
    # end affective_hypotheses_from_action

    # Generate causal hypotheses from the endpoints of
    # affective hypotheses.
    # Should be called after affective hypotheses have been
    # generated.
    # NOTE: Not currently being used. 
    def causal_hypotheses_from_affective(self,
                                         kg_in,
                                         hypotheses_in):

        #print("Causal from affective")
        hypotheses = list()

        # Search for affective hypotheses and get the concept
        # node at their endpoints.
        for hypothesis in hypotheses_in:
            if not hypothesis.coherence_type == 'affective':
                continue
            affective_concept = hypothesis.target_node
            #print("Affective concept: " + affective_concept.node_name)
            # Go through all of the scene graph's action nodes.
            for node_id, kg_node in kg_in.nodes.items():
                if not kg_node.node_type == 'action':
                    continue
                # Check it against the action node in the hypothesis'
                # 'affected_action' evidence. If it matches, skip it.
                # Don't want to make a hypothesis back to
                # the action that created this affective hypothesis in
                # the first place.
                action_evidence = hypothesis.get_specific_evidence('affected_action')
                affected_action_node = action_evidence[0].get_datum('action')['value']
                if kg_node == affected_action_node:
                    #print('Skipping affected action')
                    continue
                
                # Try to find a concept path between the affective
                # endpoint and the action node.
                action_concept_edge = kg_node.get_first_edge('is_concept')
                if action_concept_edge == None:
                    continue

                #print("    Action node " + kg_node.node_name)
                
                action_concept = action_concept_edge.target_node
                initial_edge = KnowledgeGraphEdge(hypothesis.source_node,
                                                  'affected_by',
                                                  hypothesis.target_node)
                terminating_edge = action_concept_edge

                concept_path = self.concept_path_loop(affective_concept,
                                                      action_concept,
                                                      initial_edge,
                                                      terminating_edge,
                                                      const.causal_filter,
                                                      self.args.causal_length)
                new_hypothesis = self.hypothesis_from_concept_path(concept_path,
                                                                   affective_concept,
                                                                   kg_node,
                                                                   'sequence',
                                                                   'causal')
                if not new_hypothesis == None:
                    self.add_hypothesis_to_set(new_hypothesis, hypotheses)
            # end for
        # end for
        

        return hypotheses
    # end causal_hypotheses_from_affective

    # Generate hypotheses about the temporal ordering of things.
    def generate_temporal_hypotheses(self,
                                     kg_in,
                                     hypotheses_in):
        hypotheses = list()

        # For every Sequence hypotheses, take the start and end
        # nodes and make a one-directional 'before' hypothesis if
        # they're from different scenes, a bi-directional 'during'
        # hypothesis if they're from the same scene, and no
        # hypothesis if one does not have a scene (e.g. is an
        # affective concept).

        # Go through each hypothesis.
        for hypothesis in hypotheses_in:
            # Check that it's a Sequence hypothesis
            if not hypothesis.relationship == 'sequence':
                continue
            # If either source or target nodes does not appear in
            # a scene, skip this hypothesis.
            if (hypothesis.source_node.get_attribute('scene') == None
                or hypothesis.target_node.get_attribute('scene') == None):
                continue

            # Check the scene numbers of the source and target nodes.            
            source_scene = hypothesis.source_node.get_attribute('scene')['value']
            target_scene = hypothesis.target_node.get_attribute('scene')['value']
            before_node = None
            after_node = None
            bidirectional = False
            relationship = 'before'
            # Determine which node came before or after the other.
            if source_scene > target_scene:
                before_node = hypothesis.target_node
                after_node = hypothesis.source_node
            elif source_scene < target_scene:
                before_node = hypothesis.source_node
                after_node = hypothesis.target_node
            else:
                # If neither came before or after, they
                # appear in the same scene.
                bidirectional = True
                relationship = 'during'
                before_node = hypothesis.source_node
                after_node = hypothesis.target_node
            # end if

            # Make a new temporal hypothesis
            new_hypothesis = Hypothesis(self.hypothesis_id_counter,
                                        before_node,
                                        after_node,
                                        relationship,
                                        'temporal',
                                        bidirectional)
            self.hypothesis_id_counter += 1

            # The evidence for this hypothesis are the scene
            # attributes of the two nodes, 'source_scene'
            # and 'target_scene'.
            vital_evidence = Evidence()
            vital_evidence.evidence_type = 'scene_order'
            vital_evidence.add_data('source_scene', before_node.get_attribute('scene')['value'])
            vital_evidence.add_data('target_scene', after_node.get_attribute('scene')['value'])
            vital_evidence.set_vital()
            # This evidence is premised on the fact that these two
            # actions are in the same sequence at all.
            vital_evidence.add_premise_hypothesis(hypothesis)

            new_hypothesis.add_evidence(vital_evidence)

            self.add_hypothesis_to_set(new_hypothesis, hypotheses)

            # If this sequence hypothesis has a concept path in its
            # evidence, check the concept path and make a new
            # hypothesis based on its apparent causal flow direction,
            # if any.
            # determine_causal_flow
            # Check for 'concept_path' evidence.
            concept_path_evidence = hypothesis.get_specific_evidence('concept_path')
            if len(concept_path_evidence) == 0:
                continue
            # Check the first concept path only.
            concept_path = concept_path_evidence[0].get_datum('concept_path')['value']
            causal_flow_direction = self.determine_causal_flow(concept_path)
            # If the causal flow direction is neutral, make no new
            # hypothesis.
            if causal_flow_direction == 'neutral':
                continue
            # Assume the path is from the hypothesis' source node to
            # its target node.
            # If the flow direction is 'forward', then the source node
            # should happen before the target node.
            # If the flow direction is 'backward', then the target node
            # should happen before the source node.
            elif causal_flow_direction == 'forward':
                before_node = hypothesis.source_node
                after_node = hypothesis.target_node
            elif causal_flow_direction == 'backward':
                before_node = hypothesis.target_node
                after_node = hypothesis.source_node
            # Make a new hypothesis.
            new_hypothesis = Hypothesis(self.hypothesis_id_counter,
                                        before_node,
                                        after_node,
                                        'before',
                                        'temporal',
                                        False)
            self.hypothesis_id_counter += 1
            # The evidence for this hypothesis is the
            # concept path and causal flow.
            vital_evidence = Evidence()
            vital_evidence.evidence_type = 'concept_path'
            vital_evidence.add_data('concept_path', concept_path)
            vital_evidence.add_data('causal_flow_direction', causal_flow_direction)
            vital_evidence.set_vital()
            # This evidence is premised on the fact that these two
            # actions are in the same sequence at all.
            vital_evidence.add_premise_hypothesis(hypothesis)
            new_hypothesis.add_evidence(vital_evidence)

            self.add_hypothesis_to_set(new_hypothesis, hypotheses)
            
        # end for

        return hypotheses
    # end generate_temporal_hypotheses

    # Given a concept path, make a hypothesis of the
    # given relationship with the given coherence type.
    # Either returns the successfully made hypothesis or
    # the None type. 
    def hypothesis_from_concept_path(self,
                                     concept_path,
                                     node_1,
                                     node_2,
                                     relationship,
                                     coherence_type):
        # If there is a concept path, make a new sequence
        # hypothesis with the path as evidence.
        if len(concept_path) > 0:
            print("Concept path between " +
                  node_1.node_name + " and " +
                  node_2.node_name)
            for edge in concept_path:
                print(str(edge))

            new_hypothesis = Hypothesis(self.hypothesis_id_counter,
                                        node_1,
                                        node_2,
                                        relationship,
                                        coherence_type,
                                        True)
            self.hypothesis_id_counter += 1
            # The vital evidence for this hypothesis is
            # the causal path.
            vital_evidence = Evidence()
            vital_evidence.evidence_type = 'concept_path'
            vital_evidence.add_data('concept_path', concept_path)
            vital_evidence.set_vital()
            # Add an explanation for this evidence.
            explanation = ("Both events are connected by " +
                           "the following concept path: ")
            for edge in concept_path:
                explanation += "\n" + str(edge)
            vital_evidence.set_explanation(explanation)
            new_hypothesis.add_evidence(vital_evidence)
            return new_hypothesis
        else:
            return None
    # end hypothesis_from_concept_path

    # ===== Begin Evidence Generation =====

    # Creates a list of evidence that one node has matching visual attributes
    # with another node. 
    def generate_looks_evidence(self, node_1, node_2):
        looks_evidence_list = list()

        for attribute in node_1.attributes:
            # Skip it if it's not a 'looks' attribute
            if not attribute['name'] == 'looks':
                continue
            for attribute_2 in node_2.attributes:
                # Skip it if it's not a 'looks' attribute
                if not attribute_2['name'] == 'looks':
                    continue
                # Check if the attributes' values match.
                if attribute['value'] == attribute_2['value']:
                    # If they do, add them both as pieces
                    # of data to a new piece of evidence
                    # for the hypothesis.
                    looks_evidence = Evidence()
                    looks_evidence.evidence_type = 'matching_attributes'
                    looks_evidence.add_data('attribute', attribute)
                    looks_evidence_list.append(looks_evidence)
                    # As soon as we find one match, go on to
                    # the next attribute from node 1 rather than
                    # checking the rest of node 2's attributes. 
                    break
            # end for
        # end for

        return looks_evidence_list
    # end generate_looks_evidence

    # ===== End Evidence Generation =====

    # ===== Begin Utility Functions =====

    # Add a hypothesis to an existing set of hypotheses.
    # If a hypothesis with the same conclusion already exists in
    # the set of hypotheses, merge the new hypothesis' evidence with
    # the existing hypothesis'.
    # Returns the hypothesis set and whether either the set or any single
    # hypothesis was altered in any way (True) or not (False). 
    # For use in hypothesis generation.
    def add_hypothesis_to_set(self, hypothesis_to_add, hypothesis_set):
        # Whether the hypothesis to add was merged with an existing
        # hypothesis.
        hypothesis_merged = False
        for existing_hypothesis in hypothesis_set:
            # First, check to see if the hypothesis being added is
            # functionally equivalent to this existing hypothesis.
            # If so, do not add it and return the
            # hypothesis set unchanged.
            if existing_hypothesis.is_functionally_equal_to(hypothesis_to_add):
                #print("Hypothesis exists. No changes made to set.")
                return hypothesis_set, False
            
            # The hypotheses will have to draw the same conclusion.
            # This means the same relationship is being added between
            # The same target and same source nodes.
            if (existing_hypothesis.source_node.node_id == hypothesis_to_add.source_node.node_id
                and existing_hypothesis.target_node.node_id == hypothesis_to_add.target_node.node_id
                and existing_hypothesis.relationship == hypothesis_to_add.relationship):

                # Add each piece of evidence in the new hypothesis
                # to the existing hypothesis if the existing hypothesis
                # does not already have the evidence.
                non_duplicates_found = False
                for index_1, evidence_to_add in hypothesis_to_add.get_evidence().items():
                    # Do NOT add the evidence if it already exists in
                    # the hypothesis it is being merged into.
                    # Check this by checking each piece of evidence of the same
                    # type, data by data.
                    is_duplicate = False
                    for index_2, existing_evidence in existing_hypothesis.get_evidence().items():
                        if evidence_to_add == existing_evidence:
                            is_duplicate = True
                            break
                    # end for

                    # Only add the evidence if it is not a duplicate
                    # of existing evidence. 
                    if not is_duplicate:
                        #print("Non-duplicate evidence. Merged.")
                        non_duplicates_found = True
                        existing_hypothesis.add_evidence(evidence_to_add)
                    #else:
                    #    # DEBUG
                    #    print("Duplicate evidence. Not merged.")
                # end for
                #print("Merging complete.")
                #if non_duplicates_found:
                #    print("Non-duplicates found.")
                #else:
                #    print("Only duplicate evidence?")
                
                hypothesis_merged = True
                # If all hypothesis merging is being done correctly, there
                # will never be a case where two existing hypotheses have
                # the same conclusion, as they would have already been
                # merged.
                # We can stop here. 
                break
            # end if
        # end for

        # If we did not end up merging the hypothesis with an existing one,
        # it is a hypothesis with an entirely new conclusion.
        # Add it to the overall set. 
        if not hypothesis_merged:
            #print("Adding hypothesis")
            hypothesis_set.append(hypothesis_to_add)
            return hypothesis_set, True
        else:
            return hypothesis_set, True
    # end add_hypothesis_to_set

    # Gets the nodes of all of the scene graph
    # objects that were involved in a given
    # action node.
    def get_involved_object_nodes(self, action_node_in):
        #print("Action: " + action_node_in.node_name)
        # This action should have at least one incoming edge from
        # an object node, possibly one outgoing edge to another
        # object node, denoting what objects took part in the action.
        # Get the objects of this action.
        # These are the things doing the action.
        object_nodes = list()
        # Check all incoming edges.
        for edge_in in action_node_in.edges_in:
            if edge_in.source_node.node_type == "object":
                #print("    " + edge_in.relationship + "<--" + edge_in.source_node.node_name)
                object_nodes.append(edge_in.source_node)
        # end for
        # Get the subject nodes of this action, if any.
        # These are the things this action is being done to.
        subject_nodes = list()
        # Check all outgoing edges.
        for edge in action_node_in.edges:
            if edge.target_node.node_type == "object":
                #print("    " + edge.relationship + "-->" + edge.target_node.node_name)
                subject_nodes.append(edge.target_node)
        # end for

        # Finally, compile them together into a list of
        # the nodes of all of the objects that were involved
        # in the action. 
        all_involved_nodes = list()
        all_involved_nodes.extend(subject_nodes)
        all_involved_nodes.extend(object_nodes)

        return all_involved_nodes
        
    # end get_involved_object_nodes

    # Gets the nodes of all the scene graph actions that
    # a given object was involved in.
    # NOTE: Only does objects that were objects (ones that
    # DID the action, not ones that were the subjects of
    # the action). 
    def get_involved_action_nodes(self, object_node_in):
        all_involved_nodes = list()

        # Check all outgoing edges
        for edge in object_node_in.edges:
            if edge.target_node.node_type == 'action':
                all_involved_nodes.append(edge.target_node)
            # end if
        # end for

        return all_involved_nodes
    # end get_involved_action_nodes
        

    # See if there is a path in the knowledge graph between
    # scene graph nodes through ConceptNet nodes and edges.
    # Only follows ConceptNet relationships that match the
    # given coherence type. 
    # Edges between concept net nodes have the cn_edge flag
    # set to true.
    # Nodes from concept net have node_type = 'concept'
    # Returns an empty list if there is no path. 
    def get_scene_graph_concept_path(self, kg_in, node_1, node_2,
                                     coherence_type, max_path_length = -1):
        # First, check to see if the coherence type is valid
        # if one was passed in.
        if (not coherence_type == ""
            and not coherence_type in const.coherence_to_cn_rel):
            print("Coherence type " + coherence_type + " invalid")
            # If not, make it the empty string so it
            # is disregarded.
            coherence_type = ""
        # end if
        
        # Get the nodes' concept nodes.
        # All scene graph nodes should have an 'is_concept' relationship
        # to a concept node.
        # If one of the nodes passed in does not, catch it here.
        if node_1.get_first_edge('is_concept') == None:
            print("Node " + node_1.node_name + " does not have an 'is_concept' edge.")
            return list()
        if node_2.get_first_edge('is_concept') == None:
            print("Node " + node_2.node_name + " does not have an 'is_concept' edge.")
            return list()
        concept_node_1 = node_1.get_first_edge('is_concept').target_node
        concept_node_2 = node_2.get_first_edge('is_concept').target_node

        concept_path = self.concept_path_loop(concept_node_1,
                                              concept_node_2,
                                              node_1.get_first_edge('is_concept'),
                                              node_2.get_first_edge('is_concept'),
                                              coherence_type,
                                              max_path_length)

        return concept_path

    # The BFS loop involved in finding a concept path
    # between nodes.
    # Requires an initial edge to begin the BFS. Ideally, it is
    # an edge with concept_node_1 as its taret.
    # The terminating edge will be appended to the end of the path
    # at its conclusion. 
    def concept_path_loop(self, concept_node_1, concept_node_2,
                          initial_edge, terminating_edge,
                          coherence_type, max_path_length = -1):
        concept_path = list()

        # Traverse all outgoing and incoming cn_edge edges
        # except for 'is_concept' edges.
        # Make a queue of tuples consisting of:
        #   'edge': the edge we are going to visit next.
        #   'path': an ordered list of the edges on our search
        #           leading to this one. Does not include the
        #           current edge in 'edge'. 
        # Use as a FIFO queue
        bfs_queue = deque()
        # Keep track of the nodes that have been visited. Do not
        # visit a node more than once.
        nodes_visited = list()

        # Initialize the queue with the 'is_concept' edge
        # leading to the first concept node in the queue.
        initial_path = list()
        bfs_queue.append({'edge': initial_edge,
                         'path': initial_path})
        
        # Keep traversing until we run out of edges to traverse. 
        while len(bfs_queue) > 0:
            # Pop the first member of the queue
            current_entry = bfs_queue.popleft()
            current_edge = current_entry['edge']
            current_path = current_entry['path']

            # Get the node this edge leads to.
            current_node = current_edge.target_node

            # Add the current edge to the path
            next_path = list()
            for edge in current_path:
                next_path.append(edge)
            next_path.append(current_edge)

            # Check if this node is the second concept node.
            if current_node == concept_node_2:
                print("Concept path found!")
                # If so, we have found a path between
                # the concepts.
                # Add the terminating edge, then end BFS.
                if not terminating_edge == None:
                    next_path.append(terminating_edge)
                concept_path = next_path
                break
            # end if

            # If a maximum path length was passed in (is not -1),
            # then stop searching along this path if the next
            # path has reached the maximum length.
            if (max_path_length == -1
                or len(next_path) < max_path_length):
                # Get all the edges leading to and from
                # this node and add them to the queue.
                all_edges_to_check = list()
                all_edges_to_check.extend
                for next_edge in current_node.edges:
                    # Skip this edge if it leads to a node
                    # that has already been visited,
                    # or if it is not a concept edge.
                    if (next_edge.target_node in nodes_visited
                        or not next_edge.cn_edge):
                        continue
                    # If a coherence type was passed in, then skip
                    # this edge if its relationship does not match
                    # the coherence type.
                    if (coherence_type == ""
                        or next_edge.relationship in const.coherence_to_cn_rel[coherence_type]):
                        next_entry = {'edge': next_edge,
                                      'path': next_path}
                        # Add it to the queue
                        bfs_queue.append(next_entry)
                    # end if
                # end for
            # end if

            # Note that we have visited this node.
            nodes_visited.append(current_node)
            

        # end while
        
        return concept_path
    # end concept_path_loop

    # Given a concept path, determine whether the causal flow
    # is forward, backward, or neutral. 
    def determine_causal_flow(self, concept_path_in):
        causal_flow = 'neutral'

        # For the causal flow to be anything other
        # than neutral, every edge in the path must
        # either point in the same direction or be
        # neutral. At least one edge has to point in
        # a direction for that direction to be the flow.
        first_edge = None
        previous_edge = None
        # Whether the edge is facing forwards or backwards
        # with its relationship.
        edge_flow = None
        edge_counter = 0
        for edge in concept_path_in:
            edge_flow = const.relationship_flow_mapping[edge.relationship]
            # Need to treat the first edge as a special case,
            # since we don't know which of its nodes is
            # the source of the path.
            if edge_counter == 0:
                first_edge = edge
                previous_edge = first_edge
                # Determine the flow direction of
                # the first edge, which we may have
                # to reverse later.
                causal_flow = edge_flow
                continue
            # The second edge should match one of the first
            # edge's nodes. Find out which one.
            if edge_counter == 1:
                # If either the source or the target of this edge
                # match's the source node of the first edge, the
                # first edge is reversed.
                if (edge.source_node == first_edge.source_node
                    or edge.target_node == first_edge.source_node):
                    causal_flow = self.reverse_flow(causal_flow)
            # end if

            # If this edge's target matches either of the previous
            # edge's nodes, then this edge is reversed.
            if (edge.target_node == previous_edge.source_node
                or edge.target_node == previous_edge.target_node):
                edge_flow = self.reverse_flow(edge_flow)

            # If the initial flow is still neutral, we have not yet
            # seen what direction the causal flow is. Overwrite it
            # with the current flow.
            if causal_flow == 'neutral':
                causal_flow = edge_flow
            # Otherwise, see if the initial flow direction
            # is still being maintained. 
            else:
                flow_still_maintained = self.flow_maintained(causal_flow, edge_flow)
                # If not, then it has run counter to something
                # and the flow is neutral.
                # End the loop here.
                if not flow_still_maintained:
                    causal_flow = 'neutral'
                    break
                # If so, do nothing and let the loop continue.
            # end else

            # End of loop updates
            previous_edge = edge
            edge_counter += 1
        # end for

        return causal_flow
    # end determine_causal_flow

    # Give the reverse of the given causal flow direction
    def reverse_flow(self, flow_direction_in):
        if flow_direction_in == 'forward':
            return 'backward'
        elif flow_direction_in == 'backward':
            return 'forward'
        else:
            return 'neutral'
    # end reverse_flow

    # Given an initial flow direction and a current flow
    # direction, returns True if the flow is maintained or
    # False if the flow is not.
    def flow_maintained(self, initial_flow, current_flow):
        if initial_flow == 'forward' and current_flow == 'backward':
            return False
        elif initial_flow == 'backward' and current_flow == 'forward':
            return False
        else:
            return True
    # end flow_maintained

    # Given a node and a list of action entries
    # {'action': node, 'premise': hypothesis}
    # return whether or not the node appears in
    # the list.
    def action_node_in_entries(self, action_node_in, action_entries_in):
        for action_entry in action_entries_in:
            if action_entry['action'] == action_node_in:
                return True
        return False
    # end action_node_in_entries

    # ===== End Utility Functions =====


# end HypothesisGenerator
