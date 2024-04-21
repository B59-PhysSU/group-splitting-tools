#!/usr/bin/env python3
import os
from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd
from gooey import Gooey, GooeyParser
from scipy.signal import find_peaks, peak_widths


@dataclass
class Peak:
    peak_idx: int
    left_idx: int
    right_idx: int


@dataclass
class ExtractedPeak:
    x_values: np.ndarray
    h_values: np.ndarray
    m_values: np.ndarray

    @staticmethod
    def from_peak(peak: Peak, all_x, all_h, all_m):
        return ExtractedPeak(
            x_values=all_x[peak.left_idx : peak.right_idx].to_numpy(),
            h_values=all_h[peak.left_idx : peak.right_idx].to_numpy(),
            m_values=all_m[peak.left_idx : peak.right_idx].to_numpy(),
        )

    def to_dataframe(self):
        return pd.DataFrame(
            {"x": self.x_values, "h": self.h_values, "m": self.m_values}
        )


def load_fortran_format_as_pandas(filename):
    with open(filename, "r") as f:
        parsed_table = []
        for line in f:
            split = line.split()
            parsed_line = [float(x.strip()) for x in split]
            parsed_table.append(parsed_line)
    header = ["x", "h", "m"]
    return pd.DataFrame(parsed_table, columns=header)


def extract_peak_positions(peaks, width_data, max_data_len) -> List[Peak]:
    assert peaks.shape[0] == width_data[2].shape[0] == width_data[3].shape[0]
    peaks = []
    for l, r in zip(width_data[2], width_data[3]):
        # round l and r to integers
        l = int(round(l))
        r = int(round(r)) + 1
        # make sure l and r are in bounds
        l = max(0, l)
        r = min(max_data_len, r)
        peaks.append(Peak(peak_idx=l, left_idx=l, right_idx=r))
    return peaks


def extract_peaks(df: pd.DataFrame, rel_height=0.95) -> List[ExtractedPeak]:
    assert rel_height > 0 and rel_height <= 1
    peak_positions, _ = find_peaks(df["m"], height=1)
    width_data = peak_widths(df["m"], peak_positions, rel_height=rel_height)

    peak_positions = extract_peak_positions(peak_positions, width_data, len(df["m"]))
    extracted_peaks = [
        ExtractedPeak.from_peak(peak, df["x"], df["h"], df["m"])
        for peak in peak_positions
    ]
    return extracted_peaks


def run(args):
    # Validate input file existence
    if not os.path.isfile(args.input_path):
        print("Error: Input file does not exist.")
        return
    # Create output directory if it does not exist
    os.makedirs(args.output_dir, exist_ok=True)

    df = load_fortran_format_as_pandas(args.input_path)
    extracted_peaks = extract_peaks(df, rel_height=args.threshold)

    # Save all peaks in CSV files
    for i, ep in enumerate(extracted_peaks):
        file_path = os.path.join(args.output_dir, f"{args.prefix}_{i}.csv")
        ep.to_dataframe().to_csv(file_path, index=False)


@Gooey
def main():
    parser = GooeyParser(description="Extract peaks from data and save as CSV files.")
    parser.add_argument(
        "input_path",
        widget="FileChooser",
        help="Path to the input data file. "
        "Expected format is a fixed-width table with 3 columns. The order of columns "
        "should be x, m, h",
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        widget="DirChooser",
        default=os.path.join(os.getcwd(), "output"),
        help="Path to the output directory. Default is the current working directory + 'output'.",
    )
    parser.add_argument(
        "-p",
        "--prefix",
        type=str,
        default="peak",
        help="Prefix for the CSV file names. Default is 'peak'.",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=0.95,
        help="Threshold for peak width (between 0 and 1 - peak bottom). Default is 0.95.",
    )
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
