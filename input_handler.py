import json

from knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeFactory
from constants import Constants as const

# Class to read external input files
class InputReader:
    
    # An object for making knowledge graph nodes.
    node_factory = None

    def __init__(self, args_in, node_factory_in):
        print("Input Reader initialized")
        self.args = args_in
        self.node_factory = node_factory_in
    # end __init__

    # Read in the scene graphs from an image set
    # and return a dictionary of knowledge graph
    # nodes with edges.
    def read_scene_graphs(self, set_directory):
        # First, read in the map of image indexes to
        # image IDs. Image indexes are 0 through n,
        # and are the order that the images appear in.
        # Image IDs are their file names.
        # This mapping tells us the order the
        # images are supposed to be in.
        image_index_to_id_path = set_directory + 'image_index_to_id.json'
        
        #index_map_json = json.load(open(image_index_to_id_path, 'r'))
        #image_index_to_id = dict()
        # Make all the string indices into integers.
        #for string_index, image_id in index_map_json.items():
            
        
        image_index_to_id = json.load(open(image_index_to_id_path, 'r'))

        knowledge_graph = dict()
        # Read in each image's scene graph and add them to
        # the knowledge graph.
        for image_index, image_id in image_index_to_id.items():
            scene_graph = self.read_scene_graph_json(image_index,
                                                     image_id,
                                                     set_directory)
            knowledge_graph.update(scene_graph)
        # end for

        return knowledge_graph

    # end read_scene_graphs
        

    # Reads the json file for a single scene graph
    # and returns a dictionary of knowledge graph nodes
    # with edges. 
    def read_scene_graph_json(self,
                              image_index,
                              image_id,
                              set_directory):
        scene_graph = dict()

        # Scene graph JSON files will be in the
        # annotations subfolder of an image set,
        # named after its image's ID. 
        file_path = (set_directory + 'annotations/' +
                     str(image_id) + '.json')
        scene_graph_json = json.load(open(file_path, 'r'))

        # Filter out some objects.
        common_terms = ['air', 'ground']
        body_parts = ['leg', 'face', 'body', 'head'
                      , 'arm', 'tail', 'ear', 'foot'
                      , 'hair', 'back', 'legs', 'hoof']
        clothing = ['pants', 'shorts', 'sandals'
                    , 'coat', 'jacket', 'shirt'
                    , 'watch', 'hat']

        filtered_objects = list()
        filtered_objects.extend(common_terms)
        filtered_objects.extend(body_parts)
        filtered_objects.extend(clothing)

        # Filter out some relationships.
        filtered_relationships = ['with', 'wearing']

        # Map the IDs of objects in the JSON with with
        # the IDs of nodes in the scene graph dictionary.
        # This is done to keep track of which objects are
        # represented by the same knowledge graph node,
        # so relationships can be parsed into edges to
        # the right knowledge graph nodes.
        json_id_to_node_id = dict()

        # All objects are in the 'objects' list of the
        # scene graph json.
        # Go through each object entry.
        # Object entries contain:
        #   'synsets', list
        #   'x', int x coordinate of bounding box
        #   'y', int y coordinate of bounding box
        #   'h', int height of bounding box
        #   'w', int width of bounding box
        #   'object_id', int unique identifier
        #   'attributes', list of strings
        #   'names', list of string names for object
        for object_entry in scene_graph_json['objects']:
            # Take the first entry in the names list as
            # the object's name.
            object_name = object_entry['names'][0].lower()
            # Skip any filtered object
            if object_name in filtered_objects:
                continue

            # Make a bounding box in the form of
            # x1, y1, x2, y2
            bounding_box = list()
            bounding_box.append(object_entry['x'])
            bounding_box.append(object_entry['y'])
            bounding_box.append(object_entry['x'] + object_entry['w'])
            bounding_box.append(object_entry['y'] + object_entry['h'])

            # Check if any other object with the same name
            # has a bounding box which significantly overlaps
            # with this one.
            # If so, it may be a duplicate object.
            is_duplicate = False
            for node_id, kg_node in scene_graph.items():
                if kg_node.concept_name == object_name:
                    print("Object " + str(object_entry['object_id']) +
                          " possible duplicate of " + kg_node.node_name)
                    if self.bounding_boxes_overlap(bounding_box,
                                                   kg_node.bounding_box):
                        print("Bounding boxes overlap by " +
                              str(self.get_overlap_percent(bounding_box,kg_node.bounding_box)) +
                              " percent. Duplicate found.")
                        # If they do overlap significantly, we have
                        # found a duplicate.
                        is_duplicate = True
                        # Increase the score of the existing node.
                        kg_node.score += 1
                        # Map the JSON ID of this object to the
                        # node ID of the existing node.
                        json_id_to_node_id[object_entry['object_id']] = kg_node.node_id
                        # Take only the first duplicate found. 
                        break
                    # end if
                    else:
                        print("Bounding boxes overlap by " +
                              str(self.get_overlap_percent(bounding_box,kg_node.bounding_box)) +
                              " percent. No duplicate found.")
                # end if
            # end for

            # Only make a new node for this object entry if it
            # isn't a duplicate.
            if not is_duplicate:
                # Every node starts with a score of 1, meaning
                # a single person has annotated that object
                # in that location. 
                node_score = 1
                # The node's name is its object name, the index
                # of its image, and its node ID.
                node_name = (object_name + "_" + str(image_index) +
                             "_" + str(self.node_factory.node_id_counter + 1))
                # Make the knowledge graph node itself.
                new_kg_node = self.node_factory.make_kg_node(object_name,
                                                             node_name,
                                                             'object',
                                                             image_id,
                                                             node_score,
                                                             bounding_box,
                                                             True)
                # Add an atribute for which scene this object appears in.
                # A node's scene is equal to the image index.
                new_kg_node.add_attribute({'name': 'scene',
                                           'value': image_index})
                # Map the node's JSON ID to its node id.
                json_id_to_node_id[object_entry['object_id']] = new_kg_node.node_id
                # Add the node to the knowledge graph
                scene_graph[new_kg_node.node_id] = new_kg_node
            # end if

            # Handle node attributes if it has any
            if 'attributes' in object_entry:
                # Whether it was a duplicate or not, this object
                # entry now has its JSON id mapped to a knowledge
                # graph node's ID.
                # Get the knowledge graph node using this mapping.
                object_node = scene_graph[json_id_to_node_id[object_entry['object_id']]]
                # Go through the object entry's attributes and add them
                # to this node.
                for attribute_entry in object_entry['attributes']:
                    # If this attribute is an action with a subject and
                    # no object (e.g. man -> running, dog -> walking),
                    # make a new action node out of it with a single edge
                    # from this object node to the action node.
                    if attribute_entry.lower().endswith('ing'):
                        # Make a new node for the action.
                        concept_name = attribute_entry.lower()
                        # Starts with a score of 1, indicating that
                        # a single person annotated this action
                        # happening with this object.
                        score = 1
                        # The name of the relationship node is
                        # its concept, its image index, and its ID. 
                        node_name = (concept_name + "_" +
                                     str(image_index) + "_" +
                                     str(self.node_factory.node_id_counter + 1))
                        new_node = self.node_factory.make_kg_node(attribute_entry.lower(),
                                                                  node_name,
                                                                  'action',
                                                                  image_id,
                                                                  score,
                                                                  None,
                                                                  True)
                        # Set its scene as the current image index.
                        new_node.add_attribute({'name': 'scene',
                                                'value': image_index})

                        # Make an edge from the object node to this
                        # action node.
                        edge_from_source = KnowledgeGraphEdge(object_node,
                                                              "",
                                                              new_node)
                        edge_from_source.observed_edge = True
                        # Add the edge as an outgoing edge to the source node.
                        # This will add it as an incoming edge to the
                        # action node as well.
                        scene_graph[object_node.node_id].add_edge(edge_from_source)

                        # Add the action node to the scene graph.
                        scene_graph[new_node.node_id] = new_node
                    # end if
                    # Otherwise, add it as an attribute to the node.
                    else:
                        # As this attribute is something that someone observed
                        # about the object, add it as a 'looks' attribute.
                        object_node.add_attribute({'name': 'looks',
                                                   'value': attribute_entry})
                # end for
            # end if
        # end for object_entry in scene_graph_json['objects']

        # All relationships are in the "relationships" list
        # of the scene graph json.
        # Go through each relationship entry.
        # Each relationship entry contains:
        #   'relationship_id', int unique identifier
        #   'synsets', list
        #   'predicate', string name of relationship
        #   'object_id', int ID of the object targeted by the predicate
        #   'subject_id', int ID of the object doing by the predicate
        for relationship_entry in scene_graph_json['relationships']:
            # The name of the relationship is its predicate.
            relationship_name = relationship_entry['predicate'].lower()
            # Skip any filtered relationships
            if relationship_name in filtered_relationships:
                continue

            # First, check if the object and subject nodes are both
            # mapped. If not, then they have been filtered out
            # and do not exist in the scene graph.
            # Do not parse this relationship, it leads to nodes that
            # don't exist. 
            if (not relationship_entry['object_id'] in json_id_to_node_id
                or not relationship_entry['subject_id'] in json_id_to_node_id):
                continue

            # Find the node IDs of the object (source) and subject
            # (target) nodes of this relationship
            source_node_id = json_id_to_node_id[relationship_entry['subject_id']]
            target_node_id = json_id_to_node_id[relationship_entry['object_id']]
            

            # Check if a predicate node with the same name
            # already exists between the same two object nodes
            # in the scene graph. If so, increment
            # its score instead of making a new node.
            is_duplicate = False
            for node_id, kg_node in scene_graph.items():
                # Skip any node that's not an action or predicate.
                if not (kg_node.node_type == 'action'
                        or kg_node.node_type == 'predicate'):
                    continue
                # If the existing node has the same concept name,
                # has an incoming edge from the same source node
                # and an outgoing edge to the same target node
                # it is a duplicate. 
                if (kg_node.concept_name == relationship_name
                    and kg_node.has_edge_from(source_node_id)
                    and kg_node.has_edge_to(target_node_id)):
                    is_duplicate = True
                    # Increment the score of this node.
                    scene_graph[node_id].score += 1
                # end if
            # end for

            # If we have not found a duplicate node for this relationship,
            # make a new one.
            if not is_duplicate:
                # The name of the relationship node is
                # its predicate, its image index, and its ID. 
                node_name = (relationship_name + "_" +
                             str(image_index) + "_" +
                             str(self.node_factory.node_id_counter + 1))

                # Starts with a score of 1, meaning a single
                # annotator identified the relationship.
                node_score = 1
                
                # Check if the relationship ends with an '-ing'
                # or not. If so, mark it as an action. Otherwise,
                # mark it as a predicate.
                node_type = ''
                if relationship_name.lower().endswith('ing'):
                    node_type = 'action'
                else:
                    node_type = 'predicate'
                # end if else
                new_node = self.node_factory.make_kg_node(relationship_name,
                                                          node_name,
                                                          node_type,
                                                          image_id,
                                                          node_score,
                                                          None,
                                                          True)
                # Add an attribute listing the scene the relationship
                # appears in. The scene is equal to its image index.
                new_node.add_attribute({'name': 'scene',
                                        'value': image_index})

                # Make an edge from the source node to the
                # relationship node.
                edge_from_source = KnowledgeGraphEdge(scene_graph[source_node_id],
                                                      "",
                                                      new_node)
                edge_from_source.observed_edge = True
                # Add the edge as an outgoing edge to the source node.
                # This will add it as an incoming edge to the
                # relationship node as well.
                scene_graph[source_node_id].add_edge(edge_from_source)

                # Make an edge from the relationship node
                # to the target node.
                edge_to_target = KnowledgeGraphEdge(new_node,
                                                    "",
                                                    scene_graph[target_node_id])
                edge_to_target.observed_edge = True
                # Add the edge as an outgoing edge to the relationship
                # node. This will add it as an incoming edge to the
                # target node as well.
                new_node.add_edge(edge_to_target)
                
                # Add the relationship node to the scene graph.
                scene_graph[new_node.node_id] = new_node
            # end if
        # end for relationship_entry in scene_graph_json['relationships']

        return scene_graph
        
    # end read_scene_graph_json

    # Determine whether two bounding boxes
    # overlap with one another.
    def bounding_boxes_overlap(self, bbox_1, bbox_2):
        # Any bounding boxes with an overlap percent
        # of more than this amount are considered
        # overlapping.
        if self.get_overlap_percent(bbox_1, bbox_2) > self.args.overlap_threshold:
            return True
        else:
            return False
    # end bounding_boxes_overlap

    # Calculate the overlap between two bounding boxes.
    # Return the percent overlap.
    def get_overlap_percent(self, bbox_1, bbox_2):
        overlap_percent = 0

        # Bounding boxes are x1, y1, x2, y2.
        # First, find the rectangle of intersection.
        x1 = max(bbox_1[0], bbox_2[0])
        y1 = max(bbox_1[1], bbox_2[1])
        x2 = min(bbox_1[2], bbox_2[2])
        y2 = min(bbox_1[3], bbox_2[3])

        # Check that there is an intersection at all.
        # If the left-most point is AFTER the right-most point
        # or if there top-most point is AFTER the bottom-most point,
        # there is no intersection.
        if x1 >= x2:
            return 0
        if y1 >= y2:
            return 0

        overlap_area = (x2 - x1) * (y2 - y1)

        # The total area of the two bounding boxes
        # is the area of each bounding box minus the
        # the area of the overlap rectangle.
        bbox_1_area = (bbox_1[2] - bbox_1[0]) * (bbox_1[3] - bbox_1[1])
        bbox_2_area = (bbox_2[2] - bbox_2[0]) * (bbox_2[3] - bbox_2[1])

        total_area = bbox_1_area + bbox_2_area - overlap_area

        # The percent overlap is the overlap area over the total area.
        overlap_percent = overlap_area / total_area

        return overlap_percent
    # end get_overlap_percent

# end class InputReader
