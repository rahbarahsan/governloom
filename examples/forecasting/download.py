import argparse
import json

from examples.forecasting.model import download

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Freeze an explicit local NOAA snapshot; never overwrite it")
    parser.add_argument("path")
    args = parser.parse_args()
    print(json.dumps(download(args.path), indent=2))
