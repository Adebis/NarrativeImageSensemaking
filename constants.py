# Static class of the system's constants.
# This includes mappings and definitions. 

class Constants:
    # The directory of this project's data files
    data_directory = 'data/'

    # A mapping of conceptnet relationship types to
    # Narrative Coherence elements.
    coherence_to_cn_rel = dict()
    coherence_to_cn_rel["referential"] = ["IsA", "PartOf", "HasA",
                                          "DefinedAs", "MannerOf"]
    coherence_to_cn_rel["causal"] = ["Causes",
                                     "HasSubevent", "HasFirstSubevent",
                                     "HasLastSubevent", "HasPrerequisite",
                                     "ReceivesAction"]
    # Removed from causal: UsedFor, CapableOf, CreatedBy
    coherence_to_cn_rel["affective"] = ["MotivatedByGoal", "ObstructedBy",
                                        "Desires", "CausesDesire"]
    coherence_to_cn_rel["spatial"] = ["AtLocation", "LocatedNear"]
    coherence_to_cn_rel["other"] = ["UsedFor", "CapableOf", "CreatedBy"]
    cn_rel_to_coherence = dict()
    for coherence, cn_rel_list in coherence_to_cn_rel.items():
        for cn_rel in cn_rel_list:
            cn_rel_to_coherence[cn_rel] = coherence
        # end for
    # end for

    # A mapping of conceptnet relationship types to
    # causal flow direction.
    relationship_flow_mapping = dict()
    # Referential
    relationship_flow_mapping['IsA'] = 'neutral'
    relationship_flow_mapping['PartOf'] = 'neutral'
    relationship_flow_mapping['HasA'] = 'neutral'
    relationship_flow_mapping['DefinedAs'] = 'neutral'
    relationship_flow_mapping['MannerOf'] = 'neutral'
    # Causal
    relationship_flow_mapping['Causes'] = 'forward'
    relationship_flow_mapping['HasSubevent'] = 'forward'
    relationship_flow_mapping['HasFirstSubevent'] = 'forward'
    relationship_flow_mapping['HasLastSubevent'] = 'forward'
    relationship_flow_mapping['HasPrerequisite'] = 'backward'
    relationship_flow_mapping['ReceivesAction'] = 'backward'
    # Affective
    relationship_flow_mapping['MotivatedByGoal'] = 'neutral'
    relationship_flow_mapping['ObstructedBy'] = 'neutral'
    relationship_flow_mapping['Desires'] = 'neutral'
    relationship_flow_mapping['CausesDesire'] = 'neutral'
    # Spatial
    relationship_flow_mapping['AtLocation'] = 'neutral'
    relationship_flow_mapping['LocatedNear'] = 'neutral'
    # Other
    relationship_flow_mapping['UsedFor'] = 'forward'
    relationship_flow_mapping['CapableOf'] = 'forward'
    relationship_flow_mapping['CreatedBy'] = 'backward'

    relationship_flow_mapping['is_concept'] = 'neutral'


    #overlap_threshold = 0.25


    #causal_length = 3

    #causal_type = False


    #set_number = 3
    
    #if causal_type:
    #   causal_filter = 'causal'
    #else:
    causal_filter = ""


    #generate_all_hypothesis_sets = False


    #density_weight = 1
    #connectivity_weight = 1
    #evidence_weight = 1

    def __init__(self):
        print("Initializing constants")
        print("But why?")

    def __str__(self):
        return_string = ""
        return_string += "Constants: "
        return_string += Constants.string_constants()

        return return_string

    # Get all the constants as a string.
    @staticmethod
    def string_constants():
        return_string = ""
        return_string += "coherence_to_cn_rel: " + str(Constants.coherence_to_cn_rel)
        return_string += "cn_rel_to_coherence: " + str(Constants.cn_rel_to_coherence)
        return return_string



        
