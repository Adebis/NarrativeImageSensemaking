import json

from knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge
from hypothesis import Hypothesis, Evidence
from constants import Constants as const

# Class to write outputs to external files.
class OutputWriter:

    # The accepted set of hypotheses
    accepted_hypothesis_set = list()

    def __init__(self, args_in):
        self.args = args_in
        self.accepted_hypothesis_set = list()
        print("Output Writer initialized")
    # end __init__

    # Write a scene graph, all the hypotheses about that
    # scene graph, and a single accepted set of hypotheses
    # (as lists of hypothesis IDs) with a break-down of their
    # scores to a JSON file.
    # JSON file structure:
    #   scene graph (list of nodes):
    #   concepts (list of nodes):
    #       concept_name (string)
    #       id (int)
    #       cn_concept_name (string)
    #       node_name (string)
    #       type (string)
    #       image (int)
    #       score (int)
    #       edges_out (list of edges):
    #       edges_in (list of edges):
    #           source
    #               node name (string)
    #               id (int)
    #           target
    #               node name (string)
    #               id (int)
    #           relationship (string)
    #           coherence_type (string)
    #           score (int)
    #       attributes (list of attributes):
    #           name (string)
    #           value (varies)
    #   hypotheses (list of hypotheses):
    #       id
    #       source
    #           node name
    #           id
    #       target
    #           node name
    #           id
    #       relationship (string)
    #       coherence_type (string)
    #       evidence_score (int)
    #       contradicting_hypotheses (list of hypothesis IDs)
    #       evidence (list of evidences)
    #           type (string)
    #           score (int)
    #           explanation (string)
    #           vital (bool)
    #           rejected (bool)
    #           rejection_explanation (string)
    #           premise_hypotheses (list of hypothesis IDs)
    #           data (list of dicts):
    #               name (string)
    #               value (varies)
    #   hypothesis_sets (lists of hypothesis sets):
    #       set (list of hypothesis IDs)
    #       scores (dictionary of scores)
                
    def graph_and_hypotheses_to_json(self,
                                     knowledge_graph_in,
                                     hypotheses_in,
                                     hypothesis_set_in,
                                     output_file_name):
        # Could be None-type
        self.accepted_hypothesis_set = hypothesis_set_in
        
        output_path = (const.data_directory +
                       'outputs/set_' +
                       str(self.args.set_number) +
                       '/')
        output_file_path = output_path + output_file_name

        print("Exporting KG and hypothesis set as JSON file to " + output_file_path)

        json_dict = dict()

        # Make the scene graph and the concept set.
        scene_graph_entries = list()
        concept_set_entries = list()
        for node_id, node in knowledge_graph_in.items():
            new_node_entry = self.make_node_json_entry(node)
            # Place them in different entry sets based on
            # whether they are a concept node or not.
            if node.node_type == 'concept':
                concept_set_entries.append(new_node_entry)
            else:
                scene_graph_entries.append(new_node_entry)
        # end for
        
        json_dict['scene_graph'] = scene_graph_entries
        json_dict['concepts'] = concept_set_entries

        # Make the concept set; a series of concept node
        # entries, as above.

        # Make the full set of hypotheses.
        # If a set was passed in, separate them into
        # accepted and rejected hypotheses and add a
        # score to the json.
        accepted_hypotheses = list()
        rejected_hypotheses = list()
        for hypothesis in hypotheses_in:
            new_hypothesis_entry = self.make_hypothesis_json_entry(hypothesis)
            if not hypothesis_set_in == None:
                if hypothesis in hypothesis_set_in['set']:
                    accepted_hypotheses.append(new_hypothesis_entry)
                else:
                    rejected_hypotheses.append(new_hypothesis_entry)
            else:
                accepted_hypotheses.append(new_hypothesis_entry)
        # end for
        json_dict['hypotheses'] = {'accepted': accepted_hypotheses,
                                   'rejected': rejected_hypotheses}

        # Get the top 10 accepted hypotheses
        best_accepted_hypotheses = list()
        

        if not hypothesis_set_in == None:
            json_dict['score'] = hypothesis_set_in['score']
            
        # Now that we have all the data in a dictionary, write it
        # to json. 
        json_dump = json.dumps(json_dict)
        json_object = json.loads(json_dump)

        with open(output_file_path, 'w+') as output_file:
            json.dump(json_object, output_file, indent=2)
                
        return

    # Make the output json file entry for a
    # single knowledge graph node.
    def make_node_json_entry(self, node_in):
        new_node_entry = dict()
        new_node_entry['node_name'] = node_in.node_name
        new_node_entry['concept_name'] = node_in.concept_name
        new_node_entry['cn_concept_name'] = node_in.cn_concept_name
        new_node_entry['id'] = node_in.node_id
        new_node_entry['type'] = node_in.node_type
        new_node_entry['image'] = node_in.image_id
        new_node_entry['score'] = node_in.score
        new_node_entry['bounding_box'] = node_in.bounding_box
        
        edges_out = list()
        for edge in node_in.edges:
            new_edge_entry = self.make_edge_json_entry(edge)
            edges_out.append(new_edge_entry)
        # end for
        new_node_entry['edges_out'] = edges_out
        
        edges_in = list()
        for edge_in in node_in.edges_in:
            new_edge_entry = self.make_edge_json_entry(edge_in)
            edges_in.append(new_edge_entry)
        # end for
        new_node_entry['edges_in'] = edges_in

        attributes = list()
        # Attributes are already dicts, we should be
        # able to just put them into this list.
        for attribute in node_in.attributes:
            attributes.append(attribute)
        new_node_entry['attributes'] = attributes

        return new_node_entry
    # end make_node_json_entry
    # An abbreviated version of the above.
    # Gives only the node name and ID.
    def abbreviated_node_entry(self, node_in):
        new_node_entry = dict()
        new_node_entry['node_name'] = node_in.node_name
        new_node_entry['id'] = node_in.node_id
        return new_node_entry
    # end abbreviated_node_entry

    # Make the output json file entry for a
    # single knowledge graph edge. 
    def make_edge_json_entry(self, edge_in):
        new_edge_entry = dict()
        edge_source = self.abbreviated_node_entry(edge_in.source_node)
        new_edge_entry['source'] = edge_source
        edge_target = self.abbreviated_node_entry(edge_in.target_node)
        new_edge_entry['target'] = edge_target
        new_edge_entry['relationship'] = edge_in.relationship
        new_edge_entry['coherence_type'] = edge_in.coherence_type
        # This is functionally an OR, as it will either
        # have a score or a cn_weight.
        # Change this later.
        new_edge_entry['score'] = edge_in.score + edge_in.cn_weight

        # Debug?
        new_edge_entry['observed_edge'] = edge_in.observed_edge

        return new_edge_entry
    # end make_edge_json_entry

    # Make the output json file entry for a
    # single hypothesis.
    def make_hypothesis_json_entry(self, hypothesis_in):
        hypothesis_entry = dict()
        hypothesis_entry['id'] = hypothesis_in.hypothesis_id
        
        source_node = self.abbreviated_node_entry(hypothesis_in.source_node)
        hypothesis_entry['source'] = source_node
        
        target_node = self.abbreviated_node_entry(hypothesis_in.target_node)
        hypothesis_entry['target'] = target_node

        hypothesis_entry['relationship'] = hypothesis_in.relationship

        if not hypothesis_in.subtext == "":
            hypothesis_entry['subtext'] = hypothesis_in.subtext
        
        hypothesis_entry['coherence_type'] = hypothesis_in.coherence_type
        hypothesis_entry['evidence_score'] = hypothesis_in.evidence_score

        contradicting_hypotheses = list()
        for hypothesis in hypothesis_in.contradicting_hypotheses:
            contradicting_hypotheses.append(hypothesis.hypothesis_id)
        # end for
        hypothesis_entry['contradicting_hypotheses'] = contradicting_hypotheses

        evidence_set = list()
        for evidence_id, single_evidence in hypothesis_in.evidence.items():
            new_evidence_entry = self.make_evidence_json_entry(single_evidence)
            evidence_set.append(new_evidence_entry)
        # end for
        hypothesis_entry['evidence'] = evidence_set

        subsequent_hypotheses = list()
        for subsequent_hypothesis in hypothesis_in.subsequent_hypotheses:
            sh_entry = self.abbreviated_hypothesis_entry(subsequent_hypothesis)
            subsequent_hypotheses.append(sh_entry)
        # end for
        hypothesis_entry['subsequent_hypotheses'] = subsequent_hypotheses

        if not self.accepted_hypothesis_set == None:
            if hypothesis_in in self.accepted_hypothesis_set['set']:
                hypothesis_entry['accepted'] = 'accepted'
            else:
                hypothesis_entry['accepted'] = 'rejected'

        return hypothesis_entry
    # end make_hypothesis_json_entry
    # An abbreviated version of the above.
    # Gives only the hypothesis ID, abbreviated
    # source node, abbreviated target node, and
    # relationship.
    def abbreviated_hypothesis_entry(self, hypothesis_in):
        hypothesis_entry = dict()
        hypothesis_entry['id'] = hypothesis_in.hypothesis_id
        
        source_node = self.abbreviated_node_entry(hypothesis_in.source_node)
        hypothesis_entry['source'] = source_node
        
        target_node = self.abbreviated_node_entry(hypothesis_in.target_node)
        hypothesis_entry['target'] = target_node

        hypothesis_entry['relationship'] = hypothesis_in.relationship

        if not self.accepted_hypothesis_set == None:
            if hypothesis_in in self.accepted_hypothesis_set['set']:
                hypothesis_entry['accepted'] = 'accepted'
            else:
                hypothesis_entry['accepted'] = 'rejected'

        return hypothesis_entry

    # Make the output json file entry for a
    # single piece of evidence in a hypothesis.
    def make_evidence_json_entry(self, evidence_in):
        evidence_entry = dict()

        evidence_entry['type'] = evidence_in.evidence_type
        evidence_entry['score'] = evidence_in.score
        evidence_entry['explanation'] = evidence_in.explanation
        evidence_entry['rejected'] = evidence_in.rejected
        evidence_entry['rejection_explanation'] = evidence_in.rejection_explanation

        premise_hypotheses = list()
        for premise_hypothesis in evidence_in.premise_hypotheses:
            premise_hypotheses.append(premise_hypothesis.hypothesis_id)
        #end for
        evidence_entry['premise_hypotheses'] = premise_hypotheses

        data = list()
        # Add the evidence's data. 
        for datum in evidence_in.data:
            data_entry = dict()
            data_entry['name'] = datum['name']
            value = None
            # Handle data special cases.
            # If this is a concept_path, the data's value
            # is a list of edges, which aren't JSON serializable.
            if datum['name'] == 'concept_path':
                value = list()
                for edge in datum['value']:
                    edge_entry = self.make_edge_json_entry(edge)
                    value.append(edge_entry)
                # end for
            # end if
            # Handle data values of specific object types
            elif isinstance(datum['value'], KnowledgeGraphNode):
                value = self.abbreviated_node_entry(datum['value'])
            elif isinstance(datum['value'], KnowledgeGraphEdge):
                value = self.make_edge_json_entry(datum['value'])
            elif isinstance(datum['value'], Hypothesis):
                value = self.abbreviated_hypothesis_entry(datum['value'])
            else:
                value = datum['value']

            data_entry['value'] = value

            data.append(data_entry)
        # end for
        evidence_entry['data'] = data

        return evidence_entry
    # end make_evidence_json_entry


# end class OutputWriter
