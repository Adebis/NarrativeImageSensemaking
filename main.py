import os
import json
import argparse

from sensemaker import SenseMaker

def main():
    print ("hey :)")

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    # What image set we are parsing.
    parser.add_argument('--set_number', default=1)
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
    parser.add_argument('--density_weight', default=1000)
    parser.add_argument('--connectivity_weight', default=1)
    parser.add_argument('--evidence_weight', default=2)

    args = parser.parse_args()
    
    sensemaker = SenseMaker(args)

# end main

if __name__ == "__main__":
    main()
