from collections import defaultdict
import re


file_path = "progress.log"


# Extract the number of parts of speech from the log file
# The format is ('word', 'POS')
# The pattern should capture 'nf.' in ('группа', 'nf.')
# The regex pattern


def extract_pos(line):
    # Use regex to extract the POS
    pattern = re.compile(r"\('(.+?)', (?:'(.*?)'|None)\)")
    match = pattern.findall(line)
    return match


# Count the number of time each part of speech appears
# Extract counts from each line in the log file
# Output the total counts for each part of speech
def count_in_file(path):
    with open(path, "r", encoding="utf-8") as f:
        # Initialize a defaultdictionary to store the counts
        counts = defaultdict(int)
        words = defaultdict(list)
        for line in f:
            matches = extract_pos(line)
            for word, pos in matches:
                counts[pos] += 1
                words[pos].append(word)
        return counts, words


# Print the counts in a nice format in order of most common to least common, as well as max 5 words for each POS
def print_counts(counts, words):
    # Sort the counts in descending order
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    for pos, count in sorted_counts:
        print(f"{pos}: {count} - {words[pos][:5]}")


if __name__ == "__main__":
    counts, words = count_in_file(file_path)
    print_counts(counts, words)
