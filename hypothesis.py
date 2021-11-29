
# A class representing a hypothesis about a relationship
# in the knowledge graph. 
class Hypothesis:

    # A unique identifier for this hypothesis.
    hypothesis_id = -1

    # A text description of this hypothesis
    description = ""

    # Any subtextual information, like a secondary
    # relationship type or additional descriptor. 
    subtext = ""

    # The source knowledge graph node
    source_node = None
    # The target knowledge graph node
    target_node = None
    # The hypothesized relationship from the
    # source concept to the target concept.
    relationship = None

    # Whether this relationship is bidirectional,
    # meaning the source and target nodes are
    # interchangeable. 
    bidirectional = False

    # The narrative coherence type of the connection
    # this hypothesis is about.
    # 3 coherence types are currently used:
    #   referential
    #   causal
    #   affective
    coherence_type = None


    # The strength of the evidence in this hypothesis.
    evidence_score = 0

    # The pieces of evidence which contribute to this
    # hypothesis.
    # Each evidence is identifiable by its key, meaning
    # it can only be identified in the context of
    # its hypothesis.
    evidence = dict()

    # A list with the hypotheses that use this hypothesis
    # as its premise.
    subsequent_hypotheses = list()

    # A list with the hypotheses that this hypothesis
    # mutually contradicts with.
    contradicting_hypotheses = list()

    
    
    def __init__(self, id_in, source_node_in, target_node_in,
                 relationship_in, coherence_type_in, bidirectional_in):
        #print("Initializing Hypothesis")
        self.hypothesis_id = id_in
        self.source_node = source_node_in
        self.target_node = target_node_in
        self.relationship = relationship_in
        self.coherence_type = coherence_type_in
        self.bidirectional = bidirectional_in
        
        self.description = ""
        
        self.evidence = dict()

        self.evidence_score = 0
        
        self.contradicting_hypotheses = list()

        self.subsequent_hypotheses = list()
    # end init

    def __str__(self):
        #return "hypothesis " + str(self.hypothesis_id)
        return_string = "hypothesis " + str(self.hypothesis_id)
        return_string += "\n"
        return_string += "source: " + self.source_node.node_name
        #DEBUG
        if not self.source_node.get_attribute('scene') == None:
            return_string += " | scene " + str(self.source_node.get_attribute('scene')['value'])
        return_string += "\n"
        return_string += "relationship:  " + self.relationship
        return_string += "\n"
        return_string += "target: " + self.target_node.node_name
        #DEBUG
        if not self.target_node.get_attribute('scene') == None:
            return_string += " | scene " + str(self.target_node.get_attribute('scene')['value'])
        return_string += "\n"
        return_string += "bidirectional: " + str(self.bidirectional)
        return_string += "\n"
        return_string += "evidence_score: " + str(self.evidence_score)
        return_string += "\n"
        return_string += "evidence: "
        for index, single_evidence in self.evidence.items():
            return_string += "  " + str(single_evidence)
            return_string += "\n"
        # end for
        #return_string += "" 

        return return_string
    # end str

    # As all hypothesis IDs are unique, it is
    # enough to check them to see if two hypothesis
    # objects are the same. 
    def __eq__(self, other):
        # If the other object is not a Hypothesis, it
        # does not equal this object. 
        if not isinstance(other, Hypothesis):
            return False
        elif self.hypothesis_id == other.hypothesis_id:
            return True
        else:
            return False
    # end eq

    # Whether the given other hypothesis is functionally
    # the same as this hypothesis.
    # This is true if:
    #   1. They have the same relationship
    #   2. They have the same source node
    #   3. They have the same target node
    #   4. Each piece of evidence they have
    #   matches one piece of evidence that
    #   the other has.
    # If a match is found for every piece of evidence in
    # the other hypothesis, even if there is unmatched evidence in
    # THIS hypothesis, count it as a functional match.
    # It means that the other hypothesis' information are
    # subparts of this hypothesis'.
    # Returns False is they are not functionally equal
    # to one another. True otherwise.
    def is_functionally_equal_to(self, other_hypothesis):
        #print("functional equal check.")
        #print("Hypothesis 1: " + str(self))
        #print("Hypothesis 2: " + str(other_hypothesis))
        if not self.relationship == other_hypothesis.relationship:
            return False
        # If this hypothesis is bidirectional, it does not
        # matter which is the source node and
        # which is the target node.
        elif self.bidirectional:
            if not ((self.source_node.node_id == other_hypothesis.source_node.node_id
                        and self.target_node.node_id == other_hypothesis.target_node.node_id)
                    or (self.source_node.node_id == other_hypothesis.target_node.node_id
                        and self.target_node.node_id == other_hypothesis.source_node.node_id)):
                return False
        # end elif
        # Otherwise, ordering does matter.
        elif not self.source_node.node_id == other_hypothesis.source_node.node_id:
            return False
        elif not self.target_node.node_id == other_hypothesis.target_node.node_id:
            return False
        else:
            # Keep track of which pieces of evidence in
            # the other hypothesis have already been matched.
            matched_other_indices = list()
            # Keep track of which pieces of evidence in this hypothesis
            # have already been matched.
            matched_indices = list()
            for index, evidence in self.evidence.items():
                #print("evidence: " + str(evidence))
                for other_index, other_evidence in other_hypothesis.get_evidence().items():
                    #print("other evidence: " + str(other_index) + "|" + str(other_evidence))
                    if other_index in matched_other_indices:
                        #print("matched prior, skipping")
                        continue
                    # We have found a matching piece of evidence.
                    # Note it and stop searching through the other
                    # hypothesis' evidence.
                    elif evidence == other_evidence:
                        #print("evidence matches")
                        matched_other_indices.append(other_index)
                        matched_indices.append(index)
                        # If every index in the other hypothesis has
                        # been matched, return True.
                        #print("len matched indices: " + str(len(matched_other_indices)))
                        #print("len other_hypothesis evidence: " + str(len(other_hypothesis.get_evidence())))
                        if len(matched_other_indices) == len(other_hypothesis.get_evidence().items()):
                            return True
                        break
                    # end elif
                # end for
            # end for
            # If we have reached this point, check that all
            # of this hypothesis' pieces of evidence have
            # found a match. If not, then the two
            # hypotheses are not functionally equal
            if not len(matched_indices) == len(self.evidence.items()):
                return False
        # end else
        # If we have reached this point, then every single other
        # criterion for these two hypotheses being the same
        # have been met. 
        return True
    # end is_functionally_equal_to

    # Return the hypothesis' full set of evidence.
    def get_evidence(self):
        return self.evidence
    # Get all pieces of evidence of a specific type. 
    def get_specific_evidence(self, type_in):
        return_list = list()
        for index, evidence in self.evidence.items():
            if evidence.evidence_type == type_in:
                return_list.append(evidence)
        return return_list
    # end get_specific_evidence
    # Add a piece of evidence to this hypothesis.
    # If the evidence has any premise hypotheses,
    # add this hypothesis as a subsequent hypothesis
    # to each premise hypothesis. 
    def add_evidence(self, evidence_in):
        # Go through all the evidence's premise hypotheses.
        for premise_hypothesis in evidence_in.premise_hypotheses:
            # Add this hypothesis as one of the
            # premise hypothesis' subsequent hypotheses.
            premise_hypothesis.add_subsequent_hypothesis(self)
        # end for

        # Add the evidence to this hypothesis' list of evidence.
        self.evidence[len(self.evidence)] = evidence_in
        return

    # Reset which pieces of evidence are considered rejected.
    def reset_rejected_evidence(self):
        for index, single_evidence in self.evidence.items():
            single_evidence.rejected = False
        return

    # Returns whether or not this hypothesis is
    # still valid. If it has at least one piece
    # of Vital evidence that has not been rejected,
    # the hypothesis is still valid.
    def is_valid(self):
        has_valid_vital_evidence = False
        for index, single_evidence in self.evidence.items():
            if (single_evidence.is_vital()
                and not single_evidence.is_rejected()):
                has_valid_vital_evidence = True
                break
        #end for
        return has_valid_vital_evidence
    # end is_valid

    # Return the hypothesis' evidence_score.
    def get_evidence_score(self):
        return self.evidence_score
    # Add to this hypothesis' evidence_score.
    def add_to_evidence_score(self, evidence_score_in):
        self.evidence_score += evidence_score
        return
    # Set this hypothesis' evidence_score.
    def set_evidence_score(self, evidence_score):
        self.evidence_score = evidence_score
        return
    # Sum the scores of all this hypothesis' evidence
    # and set its evidence score to the sum.
    def sum_evidence_scores(self):
        self.evidence_score = 0
        for index, single_evidence in self.evidence.items():
            # Only sum evidence that has not been rejected.
            if single_evidence.is_rejected():
                continue
            else:
                self.evidence_score += single_evidence.score
        # end for
        return
    # end sum_evidence_scores

    # Add a new contradicting hypothesis.
    def add_contradicting_hypothesis(self, hypothesis_in):
        # Don't add duplicate entries.
        for hypothesis in self.contradicting_hypotheses:
            if hypothesis_in == hypothesis:
                return
        # end for
        self.contradicting_hypotheses.append(hypothesis_in)
        return
    # Get the set of contradicting hypotheses
    def get_contradicting_hypotheses(self):
        return self.contradicting_hypotheses
    # Whether or not this hypotheses has any other
    # contradicting hypotheses.
    def has_contradicting_hypotheses(self):
        if len(self.contradicting_hypotheses) < 1:
            return False
        else:
            return True
    # Whether or not this hypothesis contradicts
    # the given hypothesis.
    def contradicts(self, hypothesis_in):
        if hypothesis_in in self.contradicting_hypotheses:
            return True
        else:
            return False
    # end contradicts

    # Whether or not a piece of this hypothesis'
    # evidence is premised on the given
    # hypothesis.
    def is_premised_on(self, hypothesis_in):
        for index, evidence in self.evidence.items():
            if hypothesis_in in evidence.premise_hypotheses:
                return True
        return False
    # end is_premised_on

    # Add a hypothesis that uses this hypothesis
    # as its premise.
    # Called by the subsequent hypothesis in add_hypothesis
    # when it adds a piece of evidence that includes this
    # hypothesis as a premise. 
    def add_subsequent_hypothesis(self, hypothesis):
        self.subsequent_hypotheses.append(hypothesis)
        return

# end class Hypothesis

# A class representing a single piece of evidence
# either supporting or refuting a hypothesis.
class Evidence:
    # What type of evidence this is.
    # Evidence types:
    #   matching_attributes
    #       Used by Referential. One visual attribute on each of
    #       a pair of object nodes matches each other. Data is
    #       attribute_1, corresponding to the hypothesis' source
    #       node, and attribute_2, corresponding to its target node.
    #   shared_concept
    #       Used by Referential. Two object nodes have the 'is_concept'
    #       relationship with the same concept node. Data is one edge
    #       corresponding to the hypothesis' source node, one edge
    #       corresponding to its target node, and target_node, the
    #       shared concept between the two.
    #   shared_object
    #       Used by Referential. Two object nodes have the is
    #       hypothesized relationship with the same third object
    #       node. Data is one hypothesis (source node -> is -> object node),
    #       the second hypothesis (target node -> is -> object node),
    #       and target_node (the object node).
    #   returning_object
    #       Used by Causal. One object is involved in one action,
    #       then is found to be equivalent with an object involved
    #       in another action. Data is the 'is' hypothesis.
    evidence_type = ""

    # The exact pieces of information for this piece of evidence.
    # Each piece of data is a dictionary with:
    #   'name': the name of the piece of data. 
    #   'value': the actual data. 
    data = list()

    # The score for this piece of evidence.
    # For use in scoring MOOP evaluation functions.
    score = 0

    # A text explanation of what this evidence is
    # and how it contributes to the hypothesis.
    explanation = ""

    # If this evidence is premised on another hypothesis or
    # hypotheses, they will be stored in this list.
    premise_hypotheses = list()

    # Whether this evidence is Vital.
    # A hypothesis needs to have at least one Vital
    # piece of evidence to be accepted.
    # Unless toggled so, evidence is set as NOT vital. 
    vital = False

    # Whether this evidence should be rejected because it
    # contains a contradiction.
    rejected = False

    # A text reason for this evidence's rejection.
    rejection_explanation = ""

    def __init__(self):
        self.evidence_type = ""
        self.data = list()
        self.score = 0
        self.explanation = ""
        self.premise_hypotheses = list()
        self.vital = False
        self.rejected = False
        self.rejection_explanation = ""
    # end init

    # Evidence is the same if it has data with the same
    # names and the values of that data are the same
    # as well.
    def __eq__(self, other):
        # Check that they're both Evidence first.
        if not isinstance(other, Evidence):
            return False
        # Next, check that they're the same type
        # of evidence.
        if not self.evidence_type == other.evidence_type:
            return False

        # Check that all the data matches.
        remaining_other_data = list()
        for datum in other.get_data():
            remaining_other_data.append(datum)
        for datum in self.data:
            # Look for the corresponding datum
            # in the other object's data.
            # If it does not exist,
            # these are not the same evidence.
            datum_matched = False
            other_datum_matched = None
            for other_datum in remaining_other_data:
                # If it exists, there has been a match.
                if self.datum_equals(datum, other_datum):
                    datum_matched = True
                    other_datum_matched = other_datum
                    break
                # end if
            # end for
            # On a match, remove the other datum from the list
            # of remaining other data and move on.
            if datum_matched:
                remaining_other_data.remove(other_datum_matched)
            # If there was NOT a match, then the evidences are
            # not the same.
            else:
                return False
        # end for

        # If we have reached this point, all datum has
        # a corresponding items in the other piece of
        # evidence and all of the data matches.
        # The two pieces of evidence are the same. 
        return True
    # end eq

    # Add data to this piece of evidence. 
    def add_data(self, name, data_in):
        self.data.append({'name': name, 'value': data_in})
        return
    # Get the full set of data.
    def get_data(self):
        return self.data
    # Get a single datum by its name.
    # Returns the whole datum, which has a 'name' and 'value'.
    # To look at its value, have to access datum['value']
    # If it doesn't exist, returns None
    def get_datum(self, name_in):
        for datum in self.data:
            if datum['name'] == name_in:
                return datum
        return None
    # Gets all data that matches the given name.
    def get_data(self, name_in):
        return_list = list()
        for datum in self.data:
            if datum['name'] == name_in:
                return_list.append(datum)
        # end for
        return return_list

    # Returns true if the two given peices of
    # data are equal to each other, False otherwise.
    # Two datum are equal if they have the same name
    # and the same value. 
    def datum_equals(self, datum_1, datum_2):
        if (datum_1['name'] == datum_2['name']
            and datum_1['value'] == datum_2['value']):
            return True
        return False

    # Set the score for this evidence.
    def set_score(self, score_in):
        self.score = score_in
        return

    # Reset the score of this evidence back to default.
    def reset_score(self):
        self.score = 0
        return

    # Add a hypothesis that premises this evidence.
    def add_premise_hypothesis(self, hypothesis):
        self.premise_hypotheses.append(hypothesis)
        return

    # Set the evidence's explanation
    def set_explanation(self, explanation_in):
        self.explanation = explanation_in
        return
    # When cast as a string, this piece of evidence will provide
    # its explanation and, if it was rejected, a reason for it.
    def __str__(self):
        return_string = self.explanation
        if self.rejected:
            return_string += ". Rejected: " + self.rejection_explanation
        return return_string

    # Make this piece of evidence as Vital
    def set_vital(self):
        self.vital = True
        return
    # Returns whether this piece of evidence is Vital or not
    def is_vital(self):
        return self.vital

    # Returns whether this piece of evidence has been
    # rejected or not
    def is_rejected(self):
        return self.rejected
    # Reject this piece of evidence.
    # Optionally give a reason for the rejection.
    def reject(self, explanation_in = ""):
        self.rejected = True
        self.rejection_explanation = explanation_in
        return
