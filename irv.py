#!/usr/bin/env python

import string
import sys
import csv
import os.path

# Structure of CSV data
import data_structure as STRUCTURE


HELP = """\
python %s vote_file <manual-mode>
Runs instant-runoff voting on the ballots in vote_file, and prints
a full ranking of all eligible candidates to standard output.

The struture of the CSV File should be defined in th data_structure.py file.

If a second argument is NOT given, the script will run in semiautomatic mode,
where it runs all non-unbreakable-tie eliminations automatically.\
"""

is_automated = True
verbosity = 0

# I'll assume we don't have more than 10 candidates
PLACES = ['1st','2nd','3rd','4th','5th','6th','7th','8th','9th','10th']
def int_or_none(string):
    # returns None if it's "0", or the number otherwise
    return int(string) or None

# Return an object with Python 2 Zip Features
def p3zip(item):
    return [list(i) for i in zip(*item)]

def read_votes(filename):
    """
    Takes in a file formatted as described above,
    and returns a VoteTable object (see below).
    """

    if not os.path.isfile(filename):
        print("ERROR: File Does not Exist")
        sys.exit(-1)

    if verbosity == 1:
        print("Reading in %s and Formatting Data"%(filename))

    if verbosity > 1:
        print("Reading in %s"%(filename))

    with open(filename, "rt") as f:
        reader = csv.reader(f)
        raw_data = list(reader)

    if verbosity > 1:
        print("Formatting Data.")

    candidates = raw_data[STRUCTURE.CANDIDATE_ROW][STRUCTURE.FIRST_CANDIDATE_COL:]
    ballots =  raw_data[STRUCTURE.FIRST_BALLOT_ROW:]

    results = []
    positionIndices = []

    previous = 0
    for pos in STRUCTURE.POSITIONS:
        positionIndices.append(previous)
        previous = pos + previous

    for index in range(len(positionIndices)):
        start = positionIndices[index]
        if index + 1 < len(positionIndices):
            end = positionIndices[index + 1]
        else:
            end = None
        results.append({
            "name": STRUCTURE.POSITION_NAMES[index],
            "start": start,
            "end": end,
            "names": candidates[start:end],
            "ballots": []
        })

    if verbosity > 1:
        print("Reading Ballots")
        print(candidates)
    for ballot in ballots:
        if verbosity > 1:
            print(ballot[STRUCTURE.FIRST_CANDIDATE_COL:])

        for position in results:
            vote = ballot[STRUCTURE.FIRST_CANDIDATE_COL:][position["start"]:position["end"]]
            vote = filterBallot(vote)
            if vote is not None:
                position["ballots"].append(vote)

    return results

def filterBallot(ballot):
    valid = False
    votes = []
    for index in range(len(ballot)):
        vote = int(ballot[index])
        if vote > 0 and vote < 11:
            if vote in votes:
                valid = False
                break
            valid = True
            votes.append(vote)
        else:
            ballot[index] = None
    if valid:
        return ballot

class VoteTable(object):
    """
    A table of votes that can handle common instant-runoff operations

    Instance variables:
        names : a list of candidate names
        votes : a list of ballots, where each ballot is a list with candidate
                ranks
        counts : a collapsed representation of each candidate's votes. Each
                element corresponds to one candidate, and is a list containing
                [# of first place votes, # of second place votes, ... ]
    """

    def __init__(self,votes,names):
        self.votes = votes
        self.names = names

        self.maintain()

    def copy(self):
        return VoteTable(self.votes,self.names)

    def compute_winner(self):
        # if (the strongest candidate)'s # of first place votes is more than
        # half of the total, they win
        if self.counts[-1][0] > self.N_votes/2:
            return self.names[-1]
        else:
            return None

    def check_tied(self):
        """ Checks if the remaining candidates are tied (unbreakably) """
        counts_equal = (self.counts[-1] == self.counts[-2])
        # if they're "tied" at all zeros, then they can't win and their
        # ballots won't affect anyone else, so it doesn't matter how
        # we break the tie.
        counts_nonzero = sum(self.counts[-1]) > 0
        return (counts_equal and counts_nonzero)

    def maintain(self):
        self.N_votes = len(self.votes)
        self.N_candidates = len(self.names)

        self.reduce_ranks()
        self.update_counts()

    def update_counts(self):
        """
        Updates/maintains self.counts (see above for description)
        """
        counts = []
        # computes [<# 1st place votes>, <# 2nd place votes>, ...]
        for (candidate,votes) in zip(self.names,self.votes_by_candidate()):
            counter = {}
            for i in range(1,self.N_candidates+1):
                counter[i] = 0 # don't use defaultdict: we need all keys
            for vote in votes:
                if vote is not None: # don't count abstentions
                    counter[vote] += 1
            counts.append([count for (rank,count) in sorted(counter.items())])

        # now keep things sorted: the 3 lists are sorted from
        # weakest candidate to strongest candidate
        (counts,votes_by_candidate,names) = zip(*sorted(zip(counts,self.votes_by_candidate(),self.names)))
        # we want to store votes by ballot, not by candidate:
        self.votes = p3zip(votes_by_candidate)
        self.counts = counts
        self.names = names

    def votes_by_candidate(self):
        return p3zip(self.votes) # transpose, since we store by ballot

    def reduce_ranks(self):
        """ Makes all ballots contain sequential votes starting from 1. """
        self.votes = list(map(get_rank_order,self.votes))

    def set_votes_by_candidate(self,votesT):
        self.votes = zip(*votesT)
        self.maintain()

    def set_by_voter(self,votes):
        self.votes = votes
        self.maintain()

    def print_table(self):
        """ Prints out collapsed vote table (see update_counts) """
        firstcol_string = "# of votes in rank:"
        max_length = max([len(name) for name in self.names+(firstcol_string,)])
        print("**************************************")
        firstcol_string_ljust = string.ljust(firstcol_string, max_length+1)
        ranks = ' '.join([str(x+1) for x in range(self.N_candidates)])
        print("   %s: %s" % (firstcol_string_ljust, ranks))
        print("**************************************")
        for (i, (name, v)) in enumerate(zip(self.names,self.counts)):
            name_ljust = string.ljust(name,max_length + 1)
            print("%d: %s: %s"%(i,name_ljust, ' '.join(map(str,v))))
        print("**************************************")

    def with_candidate_eliminated(self,index):
        """ returns a new table with candidate at index eliminated """
        votes = self.votes_by_candidate()
        new_votes = votes[:index] + votes[index+1:]
        new_names = self.names[:index] + self.names[index+1:]
        return VoteTable(p3zip(new_votes),new_names)

def get_rank_order(list):
    """ Takes something like [5,1,4] and gives [3,1,2] """
    indices = [i for (v, i) in sorted((v, i) for (i, v) in enumerate(list) if v is not None) if v is not None]
    out = [None] * len(list)
    for (rank,index) in enumerate(indices):
        out[index] = rank+1 # start at 1 instead of 0
    return out

def print_ranking(positions):
    print("")
    for position in positions:
        name = position["name"]
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print(name)

        if "results" not in position:
            print("Position has no Valid Ballots")
            print("")
            continue

        ranking = position["results"]["ranking"]
        ineligible_candidates = position["results"]["ineligible_candidates"]
        for (candidate,description) in zip(ranking,PLACES):
            print("%s place: %s"%(description,candidate))
        if ineligible_candidates != []:
            print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            print("Ineligible candidates:")
            print('\n'.join(ineligible_candidates))
        print("")

def print_winner(positions):
    print("")
    for position in positions:
        name = position["name"]
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print(name)

        if "results" not in position:
            print("Position has no Valid Ballots")
            print("")
            continue

        ranking = position["results"]["ranking"]
        print("Winner: %s"%(ranking[0]))
        print("")

def instant_runoff(name, table,is_automated):
    """
    Runs instant-runoff voting on a VoteTable object. Can
    run in semiautomatic mode (all non-tie eliminations are automatic).
    """
    ranking = []
    N = table.N_candidates
    ineligible_candidates = [] # list of candidates w/too many abstains to win
    for rank in range(N):
        # keep these so we don't clobber them below
        full_table = table.copy()
        while True:
            ineligibility_found = False
            winner = table.compute_winner()
            if winner is None: # no candidate has enough 1st place votes
                if table.N_candidates == 1:
                    ineligibility_found = True
                    (unlucky_soul,) = table.names
                    ineligible_candidates.append(unlucky_soul)
                    if not is_automated:
                        _ = input("Determined that %s is ineligible to win. Press enter to continue..."%unlucky_soul)
                    break

                if not is_automated:
                    table.print_table()
                    loser_index = input("Which candidate to eliminate? Please enter a number: ")
                else:
                    # automatically choose lowest one when lex. sorted
                    if not table.check_tied():
                        loser_index = 0
                    else:
                        table.print_table()
                        loser_index = input("** I found an unbreakable tie for %s. Which candidate do you want to eliminate? "%(name))
                if not is_automated:
                    print(loser_index)
                    print("OK, I'm eliminating %s..."%table.names[loser_index])
                #maybe_loser = compute_loser(votes,names)
                table = table.with_candidate_eliminated(loser_index)
            else: # got it!
                if not is_automated:
                    _ = input("Determined that %s is rank %d. Press enter to continue..."%(winner,rank+1))
                break
        if ineligibility_found:
            winner = unlucky_soul # eliminate from the table (not actually a winner)
        else:
            ranking.append(winner)
        if rank != N-1:
            table = full_table.with_candidate_eliminated(full_table.names.index(winner))
    results = {
      "ranking": ranking,
      "ineligible_candidates": ineligible_candidates
    }
    return results

def loop_tables(positions):
    if verbosity > 1:
        print("Tabulating Results.")

    for position in positions:
        if not is_automated or len(position["ballots"]) == 0:
            print(position["name"])
        if len(position["ballots"]) == 0:
            print("Position has no Valid Ballots")
            print("")
            continue
        table = VoteTable(position["ballots"],position["names"])
        position["results"] = instant_runoff(position["name"],table,is_automated)
        if not is_automated:
            print("")

def write_to_file(positions):
    print("")
    output_file = input("Where would you like to save the Results? ")
    with open(output_file, 'wb') as csvfile:
        datawriter = csv.writer(csvfile)
        datawriter.writerow(["Position"] + PLACES)
        for position in positions:
            datawriter.writerow([position["name"]] + position["results"]["ranking"] + [None] * (len(PLACES) - len(position["results"]["ranking"])))
    print("CSV written to \"%s\""%(output_file))
    print("")


def loop_results(positions):
    command = ""
    print("")
    print("Results Tallied!")
    print("")
    print("What would you like to do?")
    print("p to print results")
    print("d to print detailed results")
    print("w to write results to a file")
    print("q for quit;")
    print("")
    while command != "q":
        command = input("(p, d, w, q)? ")
        if command == "p":
            print_winner(positions)

        if command == "d":
            print_ranking(positions)

        if command == "w":
            write_to_file(positions)



if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(HELP % sys.argv[0])
        sys.exit(-1)

    for option in sys.argv[2:]:
        if option == "-v":
            verbosity += 1
        if option == "--verbose":
            verbosity += 1
        if option == "-m":
            is_automated = False
        if option == "--manual":
            is_automated = False

    positions = read_votes(sys.argv[1])

    loop_tables(positions)
    loop_results(positions)
