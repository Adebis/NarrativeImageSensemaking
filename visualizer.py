import networkx as nx
from pyvis.network import Network

from knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge
from constants import Constants as const

# A class for visualizing sensemaking results.
class Visualizer:

    def __init__(self, args_in):
        print("Initializing Visualizer")
        self.args = args_in
        self.scene_graph_color = 'blue'
        self.concept_color = 'purple'
        self.referential_color = 'black'
        self.causal_color = 'green'
        self.affective_color = 'yellow'
        self.temporal_color = 'orange'
        self.rejected_color = 'red'
    # end __init__

    # Visualize a given knowledge graph with
    # the given sets of hypotheses. 
    def visualize(self,
                  knowledge_graph_in,
                  all_hypotheses,
                  hypothesis_sets_in):

        # Make a networkx network out of the
        # scene graph.
        # Make sure it's a directed graph.
        network_graph = nx.DiGraph()
        # Add all nodes that have been observed.
        for node_id, node in knowledge_graph_in.items():
            if (node.node_type == 'object'
                or node.node_type == 'predicate'
                or node.node_type == 'action'):
                network_graph.add_node(node_id,
                                       label=node.node_name,
                                       color=self.scene_graph_color)
        # end for

        # Add all edges between observed nodes.
        for node_id, node in knowledge_graph_in.items():
            if node_id in nx.nodes(network_graph):
                #print('node ' + str(node_id) + ' in graph')
                # Check only outgoing edges.
                for edge in node.edges:
                    # If it's an observed edge, accept it.
                    if edge.observed_edge:
                        network_graph.add_edge(node_id,
                                               edge.target_node.node_id)
                    # If it's an 'is_concept' edge, accept it.
                    elif edge.relationship == 'is_concept':
                        # If the target node is not already part
                        # of the networkx graph, add it
                        # as a concept node.
                        self.maybe_add_concept_node(edge.target_node,
                                                    network_graph)
                        # end if
                        network_graph.add_edge(node_id,
                                               edge.target_node.node_id,
                                               color=self.concept_color)
                    # end elif
                # end for
        # end for

        # Add hypotheses
        # Handle each type of hypothesis differently
        hypothesis_set = hypothesis_sets_in[0]['set']
        for hypothesis in all_hypotheses:
            # Referential hypotheses
            add_to_graph = False
            edge_color = 'blue'
            edge_label = ''
            self.maybe_add_concept_node(hypothesis.source_node,
                                        network_graph)
            self.maybe_add_concept_node(hypothesis.target_node,
                                        network_graph)
            if hypothesis.coherence_type == 'referential':
                edge_color = self.referential_color
                edge_label = hypothesis.relationship
                add_to_graph = True
            elif hypothesis.coherence_type == 'causal':
                edge_color = self.causal_color
                edge_label = hypothesis.relationship
                add_to_graph = True
            # end elif
            elif hypothesis.coherence_type == 'affective':
                edge_color = self.affective_color
                edge_label = hypothesis.subtext
                add_to_graph = True
            elif hypothesis.coherence_type == 'temporal':
                edge_color = self.temporal_color
                edge_label = hypothesis.relationship
                add_to_graph = True

            # Handle rejected hypotheses
            if not hypothesis in hypothesis_set:
                edge_color = self.rejected_color

            if add_to_graph:
                network_graph.add_edge(hypothesis.source_node.node_id,
                                       hypothesis.target_node.node_id,
                                       color=edge_color,
                                       label=edge_label)
            # end if
        # end for
        

        output_network = Network(height='900px',
                                 width='1800px',
                                 directed=True)
        output_network.from_nx(network_graph)

        output_network.toggle_physics(True)
        output_file_name = (const.data_directory + 'outputs/' +
                            'set_' + str(self.args.set_number) + '/' +
                            'graph-visualization.html')
        output_network.show(output_file_name)

        return
    # end visualize

    def maybe_add_concept_node(self, concept_node_in, network_graph_in):
        if not concept_node_in.node_id in nx.nodes(network_graph_in):
            network_graph_in.add_node(concept_node_in.node_id,
                                      label=concept_node_in.node_name,
                                      color=self.concept_color)
    # end maybe_add_concept_node
    
        

# end class Visualizer



