from external_knowledge_querier import ExternalKnowledgeQuerier

# A class representing the system's knowledge graph. 
class KnowledgeGraph:
    # A dictionary of the nodes in the graph,
    # keyed by node ID.
    nodes = dict()

    def __init__(self):
        self.nodes = dict()
    # end __init__

    

# end class KnowledgeGraph

# A class representing a single node in the knowledge graph.
class KnowledgeGraphNode:
    # ===== KEY VARIABLES =====
    # The name of the concept this node represents
    concept_name = ""

    # This node's ID number, corresponding to its key in the sensemaker's
    # knowledge graph dictionary.
    node_id = -1

    # The name of the concept from ConceptNet mapped
    # to this node.
    cn_concept_name = ""

    # The set of predicates associated with this node
    # from ConceptNet
    cn_predicates = list()

    # This node's internal name.
    # Some human readable combination of identifying
    # strings.
    node_name = ""

    # The KnowledgeGraphEdge edges leading out of this node.
    edges = list()

    # The KnowledgeGraphEdge edges leading into this node.
    edges_in = list()

    # What type of concept this node represents.
    # Node types:
    #   "object"
    #   "predicate"
    #   "action"
    #   "hypothesized"
    #   "concept"
    node_type = ""

    # The node's attributes, if any.
    # If this is a scene graph node, these attributes
    # will be observations about the node's subject.
    attributes = list()

    # For use in Evaluation
    # A list of hypotheses involving this node.
    # Populated while simulating applying hypotheses
    # to the knowledge graph. 
    hypotheses = list()

    # The node's concept's embedding values from ConceptNet.
    embedding = list()

    # A flag indicating whether or not this node should be
    # formally included in the knowledge graph.
    # Necessary because some concept nodes are kept in KG
    # lists to aid in hypothesis generation, and are only
    # considered formally part of the knowledge graph if
    # an accepted hypothesis adds them.
    # Additionally, concept nodes that have the is_concept
    # relationship to a scene graph node are always included
    # in the knowledge graph.
    graph_member = False
    

    # ===== OTHER VARIABLES =====
    # The id of the image this node is from.
    # This corresponds to an image file name.
    image_id = -1

    # The confidence score for this node.
    # If the node is made from an object detected in
    # an image, this is the confidence score from
    # those detection results.
    score = 0

    # The bounding box on an image this node
    # represents.
    # If the node is made from an object detected
    # in an image, this is the detection ROI.
    bounding_box = None

    # Whether or not this node was added as
    # a temporary node for hypothesis evaluation.
    is_hypothesized = False
    # The IDs of the hypotheses this node came from.
    h_id = list()

    # Requires initialization parameters:
    #   concept name,
    #   id number,
    #   node name,
    #   node type,
    #   image id,
    #   score,
    #   bounding box
    def __init__(self,
                 c_name_in,
                 id_in,
                 n_name_in,
                 n_type_in,
                 image_id_in,
                 score_in,
                 b_box_in,
                 graph_membership_in):
        #print("Initializing KnowledgeGraphNode")
        self.concept_name = c_name_in
        self.node_id = id_in
        self.node_name = n_name_in
        
        self.edges = list()
        self.edges_in = list()
        
        self.node_type = n_type_in
        self.image_id = image_id_in
        self.score = score_in
        self.bounding_box = b_box_in

        self.cn_concept_name = self.concept_name.lower().replace(" ", "_")

        self.cn_predicates = list()
        self.is_hypothesized = False
        self.h_id = list()

        self.attributes = list()

        self.embedding = list()

        self.graph_member = graph_membership_in

        self.hypotheses = list()
    # end __init__

    # Two nodes are equal if their IDs match.
    def __eq__(self, other):
        # Not equal if the other object is not a
        # KnowledgeGraphNode.
        if not isinstance(other, KnowledgeGraphNode):
            return False
        elif self.node_id == other.node_id:
            return True
        else:
            return False
    # end __eq__

    # Add an outgoing edge to this node and an
    # incoming edge to the edge's target node. 
    def add_edge(self, edge_in):
        # Make sure this is not a duplicate edge.
        # If so, do not add it.
        # It is a duplicate if the source, target, and relationship
        # is the same as an existing edge in this node's outgoing
        # edge list.
        for edge in self.edges:
            if edge.source_node.node_id == edge_in.source_node.node_id:
                if edge.target_node.node_id == edge_in.target_node.node_id:
                    if edge.relationship == edge_in.relationship:
                        break
        # end for edge in edges
        # Add the edge as an outgoing edge for this node.
        self.edges.append(edge_in)
        # Add the edge as an incoming edge for the edge's
        # target node.
        edge_in.target_node.add_edge_in(edge_in)
    # end add_edge

    # Get an edge, if it exists, from this node to the
    # node with the given node ID with the given
    # relationship.
    # Returns None if the edge does not exist.
    def get_edge(self, node_id_in, relationship_in):
        for edge in self.edges:
            if (edge.target_node.node_id == node_id_in
                and edge.relationship == relationship_in):
                return edge
        # If we have reached this point, no matching edge was found.
        return None
    # end get_edge
    # Get the first edge from this node to any other
    # node with the given relationship.
    # Returns None if no such edge exists.
    def get_first_edge(self, relationship_in):
        for edge in self.edges:
            if edge.relationship == relationship_in:
                return edge
        # end for
        return None
    # end get_first_edge

    # Get the number of outgoing edges on this node.
    def get_edge_count(self):
        return len(self.edges)
    # end get_edge_count

    def has_edge_to(self, node_id_in, relationship_in = None):
        if relationship_in == None:
            return self.has_any_edge_to(node_id_in)
        else:
            return self.has_specific_edge_to(node_id_in, relationship_in)
    # end has_edge_to
    # Returns True if this node has an outgoing
    # edge to the node whose ID is given.
    def has_any_edge_to(self, node_id_in):
        for edge in self.edges:
            if edge.target_node.node_id == node_id_in:
                return True
        return False
    # end has_any_edge_to
    # Returns True if this node has an outgoing
    # edge to the node whose ID is given
    # with the given relationship.
    def has_specific_edge_to(self, node_id_in, relationship_in):
        for edge in self.edges:
            if edge.target_node.node_id == node_id_in:
                if edge.relationship == relationship_in:
                    return True
        return False
    # end has_specific_edge_to
    
    # Add an incoming edge to this node.
    def add_edge_in(self, edge_in_in):
        self.edges_in.append(edge_in_in)
    # end add_edge_in

    # Remove an incoming edge from this node.
    def remove_edge_in(self, edge_in_in):
        self.edges_in.remove(edge_in_in)

    # Returns True if this node has an incoming edge
    # from the node whose ID is given.
    def has_edge_from(self, node_id_in):
        for edge in self.edges_in:
            if edge.source_node.node_id == node_id_in:
                return True
        return False
    # end has_edge_from

    # Add a hypothesis to this node.
    # Also tries to add the hypothesis to the other
    # node in the hypothesis if it does not already
    # have it.
    def add_hypothesis(self, hypothesis_in):
        # Don't add duplicates.
        if hypothesis_in in self.hypotheses:
            return
        self.hypotheses.append(hypothesis_in)
        # Determine which of the hypotheses' nodes
        # is NOT this node.
        other_node = None
        if hypothesis_in.source_node == self:
            other_node = hypothesis_in.target_node
        elif hypothesis_in.target_node == self:
            other_node = hypothesis_in.source_node
        else:
            print("Help! Adding hypothesis to node and " +
                  "neither of the hypothesis' nodes is this node!")
        other_node.add_hypothesis(hypothesis_in)
        return
    # end add_hypothesis

    # Remove a hypothesis from this node.
    # Also tries to remove the hypothesis from the other
    # node in the hypothesis if it still has it.
    def remove_hypothesis(self, hypothesis_in):
        # Don't remove a hypothesis that doesn't exist.
        if not hypothesis_in in self.hypotheses:
            return
        self.hypotheses.remove(hypothesis_in)
        # Determine which of the hypotheses' nodes
        # is NOT this node.
        other_node = None
        if hypothesis_in.source_node == self:
            other_node = hypothesis_in.target_node
        elif hypothesis_in.target_node == self:
            other_node = hypothesis_in.source_node
        else:
            print("Help! Remove hypothesis from node and " +
                  "neither of the hypothesis' nodes is this node!")
        other_node.remove_hypothesis(hypothesis_in)
    # end remove_hypothesis
    

    # Remove all hypothesized edges coming from
    # or going to this node. 
    def remove_temporary_edges(self):
        edges_to_keep = list()
        edges_in_to_keep = list()
        for edge in self.edges:
            if not edge.is_hypothesized:
                edges_to_keep.append(edge)
        for edge_in in self.edges_in:
            if not edge_in.is_hypothesized:
                edges_in_to_keep.append(edge_in)
        self.edges = edges_to_keep
        self.edges_in = edges_in_to_keep
    # end remove_temporary_edges

    # Mark this as a temporary node for hypothesis
    # evaluation, with the ID of the hypothesis
    # that spawned this node. 
    def mark_hypothesized(self, h_id_in):
        self.is_hypothesized = True
        self.h_id.append(h_id_in)

    # Remove a hypothesis from this node.
    def remove_hypothesis(self, h_id_in):
        if h_id_in in self.h_id:
            self.h_id.remove(h_id_in)
            
        return self.remove_hypothesized_edges(h_id_in)
    # end remove_hypothesis
        
    # Remove a specific hypothesis' outgoing
    # edges from this node and the corresponding
    # incoming edges from their target nodes.
    def remove_hypothesized_edges(self, h_id_in):
        edges_to_keep = list()
        edges_to_remove = list()
        for edge in self.edges:
            if edge.h_id == h_id_in:
                edges_to_remove.append(edge)
            else:
                edges_to_keep.append(edge)
        # end for
        self.edges = edges_to_keep

        # Remove these edges from the incoming
        # edges list of the nodes they point to.
        for edge in edges_to_remove:
            edge.target_node.remove_edge_in(edge)

        return edges_to_remove
    # end remove_hypothesized_edges

    # Add an attribute to the node.
    # The attribute should be a dictionary
    # with a 'name' and a 'value'. 
    def add_attribute(self, attribute_in):
        self.attributes.append(attribute_in)
        return

    # Fetch all attributes with the given name.
    # Returns an empty list if none are found. 
    def get_attributes(self, name_in):
        return_attributes = list()
        for attribute in self.attributes:
            if attribute['name'] == name_in:
                return_attributes.append(attribute)
        # end for
        return return_attributes
    # Fetch the first attribute with the given name.
    # Returns None if there is no such attribute.
    def get_attribute(self, name_in):
        for attribute in self.attributes:
            if attribute['name'] == name_in:
                return attribute
        # end for
        return None
    # end get_attribute

    # Set the flag indicating that this node is a
    # formal member of a knowledge graph
    def set_graph_membership(self, membership_in):
        self.graph_member = membership_in
        return
    # end set_graph_membership

    # What a KnowledgeGraphNode self about
    # itself. 
    def __str__(self):
        # If this is an object node, report the node_name,
        # and ROI
        if self.node_type == "object":
            return_string = "{"
            return_string += "node_name:" + self.node_name
            return_string += ","
            return_string += "bounding_box:" + str(self.bounding_box)
            return_string += "}"
        # If this is a relationship node, report the source node
        # name and target node name.
        elif self.node_type == "relationship":
            return_string = "{"
            return_string += "source node: " + self.edges_in[0].source_node.node_name
            return_string += ","
            return_string += "target node: " + self.edges[0].target_node.node_name
            return_string += "}"
        
        return return_string
    # end __str__
        

# end class KnowledgeGraphNode

# A class representing a single outgoing edge in the
# knowledge graph.
class KnowledgeGraphEdge:
    # The KnowledgeGraphNode this edge is coming from
    source_node = None

    # The name of the relationship this edge represents. 
    relationship = ""
    # What narrative coherence type the edge's relationship
    # corresponds to, if any.
    coherence_type = ""
    
    # The KnowledgeGraphNode this edge is leading to
    target_node = None
    # The confidence score for this edge's relationship
    score = 0

    # Whether this edge is between ConceptNet nodes.
    cn_edge = False

    # The edge's weight straight from ConceptNet if
    # it is a ConceptNet edge.
    cn_weight = 0

    # Whether this edge was observed in the scene graph.
    observed_edge = False

    # Whether or not this edge is a temporary edge for
    # hypothesis evaluation.
    is_hypothesized = False
    # The ID of the hypothesis this edge came from.
    h_id = -1

    # Initialize an edge with the node it comes from, the
    # node it points to, and a string description of the
    # link between the two.
    def __init__(self,
                 s_node_in,
                 r_in,
                 t_node_in,
                 hypothesized = False):
        self.source_node = s_node_in
        self.relationship = r_in
        self.target_node = t_node_in
        self.is_hypothesized = hypothesized
        self.h_id = -1
        self.coherence_type = ""
        self.cn_edge = False
        self.observed_edge = False
        self.cn_weight = 0

    # end init

    # Mark this as a temporary edge for hypothesis
    # evaluation. 
    def mark_hypothesized(self, h_id_in):
        self.is_hypothesized = True
        self.h_id = h_id_in

    # What a KnowledgeGraphEdge says
    # about itself.
    def __str__(self):
        return_string = "{"
        return_string += self.source_node.node_name
        return_string += " --> "
        return_string += self.relationship
        return_string += " (weight " + str(self.cn_weight) + ") "
        return_string += " --> "
        return_string += self.target_node.node_name
        return_string += "}"

        return return_string
    # end __str__
# end KnowledgeGraphEdge


# A class defining an factory object that can
# create KnowledgeGraphNodes
class NodeFactory:
    # An integer for assigning nodes unique IDs
    node_id_counter = -1

    # An external knowledge querier for getting cleaned names
    querier = None
    
    def __init__(self):
        self.node_id_counter = -1
        self.querier = ExternalKnowledgeQuerier()
        print("Node factory initialized")
    # end __init__

    # Make a knowledge graph node.
    # Returns the new node.
    def make_kg_node(self,
                     concept_name_in,
                     node_name_in,
                     node_type_in,
                     image_id_in,
                     score_in,
                     bounding_box_in,
                     graph_membership_in):
        # kg nodes initialize with:
        #   concept name (not it's ConceptNet concept's name)
        #   id number
        #   node name
        #   node type
        #   image id
        #   score
        #   bounding box
        #   graph membership

        # Increment the id counter so this node has a unique ID. 
        self.node_id_counter += 1

        # Get the concept name as it appears in the database.
        clean_name = self.querier.CleanWord(concept_name_in)

        # If this node is a concept node, get its embedding as well.
        embedding = list()
        if node_type_in == 'concept':
            embedding = self.querier.GetEmbedding(clean_name)
        # end if

        # Make the kg node
        new_node = KnowledgeGraphNode(clean_name,
                                      self.node_id_counter,
                                      node_name_in,
                                      node_type_in,
                                      image_id_in,
                                      score_in,
                                      bounding_box_in,
                                      graph_membership_in)
        # Give it its embedding
        new_node.embedding = embedding
        # Return the node we just made. 
        return new_node
    # end make_kg_node

# end class NodeFactory


