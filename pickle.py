"""Creates a pickle file from a text file which can be used as a list of URL's to be scraped."""

import argparse
import pickle

parser = argparse.ArgumentParser(
    description="Transform a list of urls from text to pickle format."
)
parser.add_argument(
    "--source",
    required=True,
    help="Path and filename to the source file",
)
parser.add_argument(
    "--destination",
    required=True,
    help="Path and filename to the destination file",
)
args = parser.parse_args()


with open(args.source, "r") as f:
    urls = f.read().splitlines()

with open(args.destination, "wb") as f:
    pickle.dump(urls, f)
