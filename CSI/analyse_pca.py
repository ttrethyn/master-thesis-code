import numpy as np
import matplotlib.pyplot as plt
import os
import datetime
import sys
import argparse

# some constants used for easily substituting in different thresholds, or iterating through a range
THRESHOLD = 0.35
THRESHOLD_RANGE = [0.3, 0.325, 0.35, 0.375, 0.4]


def count_pns(thresh_data, time_array, annotation, pair):
    """
    count positives and negatives within a thresholded array
    :param thresh_data: the array of thesholded data
    :param time_array: an array of length thresh_data, containing time information for each thresholded sample
    :param annotation: the path to the annotation file applicable to this data
    :param pair: the rx node that collected this data
    :return: a dictionary of counts for tp, fn, fp and tn, by class
    """

    # open the annotation file or die trying
    try:
        f = open(annotation, 'r')
    except:
        print("failed to open annotation file")
        return

    # read annotation file and close
    lines = f.readlines()
    f.close()

    # get delay information, if applicable
    delays = lines[0].rstrip().split()
    to_remove = 0
    for delay in delays:
        node, _, time = delay.partition(",")
        if node == pair:
            to_remove = time

    # get action ranges where something happens in the data
    action_ranges = []
    end_time = None
    for line in lines[1:]:
        info = line.split()
        x = info[0]
        length = info[1]
        activity_class = info[2]
        if length != "0":
            action_ranges.append(([int(x) - int(to_remove), int(x) + int(length) - int(to_remove)], activity_class))
        else:
            if "first skip" in line:
                end_time = int(x) - int(to_remove)

    # define our count dictionary
    pn_counts = {"h": {"tp": 0, "fn": 0}, "cs": {"tp": 0, "fn": 0}, "cm": {"tp": 0, "fn": 0}, "cl": {"tp": 0, "fn": 0},
                 "fp": 0, "tn": 0, }
    found = False

    # loop through the data and determine whether or not each sample falls within an action range, and if so whether it falls within multiple
    for i in range(thresh_data.shape[0]):
        if end_time is not None:
            if time_array[i] < end_time:
                for action_range in action_ranges:
                    if action_range[0][0] <= time_array[i] <= action_range[0][1]:
                        found = True
                        if thresh_data[i] > 0:
                            pn_counts[action_range[1]]["tp"] += 1
                        else:
                            pn_counts[action_range[1]]["fn"] += 1
                if not found:
                    if thresh_data[i] > 0:
                        pn_counts["fp"] += 1

                    else:
                        pn_counts["tn"] += 1
                found = False
            else:
                break
        else:
            for action_range in action_ranges:
                if action_range[0][0] <= time_array[i] <= action_range[0][1]:
                    found = True
                    if thresh_data[i] > 0:
                        pn_counts[action_range[1]]["tp"] += 1
                    else:
                        pn_counts[action_range[1]]["fn"] += 1
            if not found:
                if thresh_data[i] > 0:
                    pn_counts["fp"] += 1

                else:
                    pn_counts["tn"] += 1
            found = False

    # return counts
    return pn_counts


def count_pns_weighted(thresh_data, time_array, annotation, pair):
    """
        count positives and negatives within a thresholded array, but do this for all pca components and weight them to determine positivity/negativity
        :param thresh_data: the array of thesholded data
        :param time_array: an array of length thresh_data, containing time information for each thresholded sample
        :param annotation: the path to the annotation file applicable to this data
        :param pair: the rx node that collected this data
        :return: a dictionary of counts for tp, fn, fp and tn, by class
        """

    # open the annotation file or die trying
    try:
        f = open(annotation, 'r')
    except:
        print("failed to open annotation file")
        return

    # read annotation file and close
    lines = f.readlines()
    f.close()

    # get delay information, if applicable
    delays = lines[0].rstrip().split()
    to_remove = 0
    for delay in delays:
        node, _, time = delay.partition(",")
        if node == pair:
            to_remove = time

    # get action ranges where something happens in the data
    action_ranges = []
    end_time = None
    for line in lines[1:]:
        info = line.split()
        x = info[0]
        length = info[1]
        activity_class = info[2]
        if length != "0":
            action_ranges.append(([int(x) - int(to_remove), int(x) + int(length) - int(to_remove)], activity_class))
        else:
            if "first skip" in line:
                end_time = int(x) - int(to_remove)

        # define our count dictionary
    pn_counts = {"h": {"tp": 0, "fn": 0}, "cs": {"tp": 0, "fn": 0}, "cm": {"tp": 0, "fn": 0}, "cl": {"tp": 0, "fn": 0},
                 "fp": 0, "tn": 0, }
    found = False

    # loop through the data and determine whether or not each sample falls within an action range, and if so whether it falls within multiple
    for i in range(thresh_data.shape[0]):
        if end_time is not None:
            if time_array[i] < end_time:
                for action_range in action_ranges:
                    if action_range[0][0] <= time_array[i] <= action_range[0][1]:
                        found = True
                        if thresh_data[i, 0] > 0 or thresh_data[i, 1] > 0 or np.count_nonzero(thresh_data[i, :]) >= 3:
                            pn_counts[action_range[1]]["tp"] += 1
                        else:
                            pn_counts[action_range[1]]["fn"] += 1
                if not found:
                    if thresh_data[i, 0] > 0 or thresh_data[i, 1] > 0 or np.count_nonzero(thresh_data[i, :]) >= 3:
                        pn_counts["fp"] += 1

                    else:
                        pn_counts["tn"] += 1
                found = False
            else:
                break
        else:
            for action_range in action_ranges:
                if action_range[0][0] <= time_array[i] <= action_range[0][1]:
                    found = True
                    if thresh_data[i, 0] > 0 or thresh_data[i, 1] > 0 or np.count_nonzero(thresh_data[i, :]) >= 3:
                        pn_counts[action_range[1]]["tp"] += 1
                    else:
                        pn_counts[action_range[1]]["fn"] += 1
            if not found:
                if thresh_data[i, 0] > 0 or thresh_data[i, 1] > 0 or np.count_nonzero(thresh_data[i, :]) >= 3:
                    pn_counts["fp"] += 1

                else:
                    pn_counts["tn"] += 1
            found = False

    # return counts
    return pn_counts


def report_pns(counts, path, pair, thresh, orientation, sample, first, pca="weighted", t_range=None):
    """
    Report pns counts to a file for easy retrieval
    :param counts: the dictionary of pns counts
    :param path: the path to save to, string
    :param pair: the rx pair that logged this data, string
    :param thresh: the threshold used, number
    :param orientation: whether this is diagonal or horizontal data, string
    :param sample: which sample within a measurement this applies to (e.g. m9 s2), number
    :param first: whether this should overwrite the previous contents of the file or add to it, bool
    :param pca: whether the data was weighted, defaultly waited
    :param t_range: whether this refers to a specific range of time, and if so what (defaultly no)
    :return: nothing
    """
    if orientation:
        orientation = "d"
    else:
        orientation = "h"
    fname = path + pair + "_s" + sample + "_" + str(pca) + "_" + orientation + "_log.txt"
    if first:
        mode = "w"
    else:
        mode = "a"
    with open(fname, mode) as f:
        if t_range is not None:
            print("---" + pair + " counts, threshold " + str(thresh) + " range (s) " + str(t_range[0]) + ", " + str(
                t_range[-1]) + "---", file=f)
        else:
            print("---" + pair + " counts, threshold " + str(thresh) + "---", file=f)
        print("cat activity small", file=f)
        print("\n".join("{0} {1}".format(k, v) for k, v in counts["cs"].items()), file=f)
        if (counts["cs"]["tp"] + counts["cs"]["fn"]) > 0:
            sensitivity = counts["cs"]["tp"] / (counts["cs"]["tp"] + counts["cs"]["fn"])
            print("Sensitivity: " + str(sensitivity), file=f)
        else:
            print("No labels of this class present", file=f)
        print("cat activity medium", file=f)
        print("\n".join("{0} {1}".format(k, v) for k, v in counts["cm"].items()), file=f)
        if (counts["cm"]["tp"] + counts["cm"]["fn"]) > 0:
            sensitivity = counts["cm"]["tp"] / (counts["cm"]["tp"] + counts["cm"]["fn"])
            print("Sensitivity: " + str(sensitivity), file=f)
        else:
            print("No labels of this class present", file=f)
        print("cat activity large", file=f)
        print("\n".join("{0} {1}".format(k, v) for k, v in counts["cl"].items()), file=f)
        if (counts["cl"]["tp"] + counts["cl"]["fn"]) > 0:
            sensitivity = counts["cl"]["tp"] / (counts["cl"]["tp"] + counts["cl"]["fn"])
            print("Sensitivity: " + str(sensitivity), file=f)
        else:
            print("No labels of this class present", file=f)
        print("cat activity total", file=f)
        if (counts["cs"]["tp"] + counts["cm"]["tp"] + counts["cl"]["tp"] + counts["cs"]["fn"] + counts["cm"]["fn"] +
            counts["cl"]["fn"]) > 0:
            sensitivity = (counts["cs"]["tp"] + counts["cm"]["tp"] + counts["cl"]["tp"]) / (
                    (counts["cs"]["tp"] + counts["cm"]["tp"] + counts["cl"]["tp"]) + (
                    counts["cs"]["fn"] + counts["cm"]["fn"] + counts["cl"]["fn"]))
            print("Sensitivity: " + str(sensitivity), file=f)
        else:
            print("No labels of this class present", file=f)
        print("human activity", file=f)
        print("\n".join("{0} {1}".format(k, v) for k, v in counts["h"].items()), file=f)
        if (counts["h"]["tp"] + counts["h"]["fn"]) > 0:
            sensitivity = counts["h"]["tp"] / (counts["h"]["tp"] + counts["h"]["fn"])
            print("Sensitivity: " + str(sensitivity), file=f)
        else:
            print("No labels of this class present", file=f)
        print("activity total", file=f)
        if (counts["h"]["tp"] + counts["cs"]["tp"] + counts["cm"]["tp"] + counts["cl"]["tp"] + counts["h"]["fn"] +
            counts["cs"]["fn"] + counts["cm"]["fn"] + counts["cl"]["fn"]) > 0:
            sensitivity = (counts["h"]["tp"] + counts["cs"]["tp"] + counts["cm"]["tp"] + counts["cl"]["tp"]) / (
                    counts["h"]["tp"] + counts["cs"]["tp"] + counts["cm"]["tp"] + counts["cl"]["tp"] + counts["h"][
                "fn"] +
                    counts["cs"]["fn"] + counts["cm"]["fn"] + counts["cl"]["fn"])
            print("Sensitivity: " + str(sensitivity), file=f)
        else:
            print("No labels present", file=f)
        if (counts["tn"] + counts["fp"]) > 0:
            specificity = counts["tn"] / (counts["tn"] + counts["fp"])
            print("Specificity: " + str(specificity), file=f)
        else:
            print("No unlabeled data present", file=f)


def threshold(acfs, thresh):
    """
    thresholds an array to a given threshold
    :param acfs: acfs to threshold
    :param thresh: threshold to use
    :return: thresholded array of acfs
    """
    acfs[acfs <= thresh] = 0
    return acfs


def annotate(annotation, ax):
    """
    annotates axes, for use with matplotlib
    :param annotation: path to annotation file
    :param ax: axes to annotate
    :return: nothing
    """

    # open annotation file or die trying
    try:
        f = open(annotation, 'r')
    except:
        print("failed to open annotation file")
        return

    # read and close file
    lines = f.readlines()
    f.close()

    # some parameters for drawing annotation labels at different heights
    max_height = 0.83
    min_height = 0.003
    inc = 0.1
    arrow_point = 0.017
    switch_height = inc / 2

    # loop through the annotations and draw an arrow pointing to the start of the annotation and a textbox at the back of the arrow with annotation text
    # height loops continuously from low to high so that text boxes are drawn in a staggered ladder, increasing readability
    text_level = min(min_height + inc * len(lines), max_height)
    for line in reversed(lines[1:]):
        info = line.split()
        x = info[0]
        text = " ".join(info[6:])
        xy = (int(x), arrow_point)
        xytext = (xy[0], xy[1] + text_level)
        ax.annotate(text.rstrip(), xy=xy, xytext=xytext, textcoords='data',
                    arrowprops=dict(color='black', arrowstyle='->', relpos=(0, 0), lw=3), annotation_clip=True,
                    fontsize=15, bbox=dict(boxstyle="round", facecolor="white"))
        if text_level - inc <= min_height:
            text_level = min(min_height + inc * len(lines), max_height)
            if switch_height != 0:
                text_level += switch_height
                switch_height = 0
            else:
                switch_height = inc / 2
        else:
            text_level -= inc


def main():
    # define the parser and arguments
    parser = argparse.ArgumentParser(description="Get input data")
    parser.add_argument('measurement', type=str, help='The measurement number, m3-m9')
    parser.add_argument('sample', type=str, help='The sample number, 1-n')
    parser.add_argument('-d', '--diagonal', action="store_true", help='Whether we use diagonal pairing')
    parser.add_argument('-w', '--weigh', action="store_true", help='Whether we weigh the components together')
    parser.add_argument('-c', '--compare', action="store_true", help='Whether we compare performances of pairs')
    args = parser.parse_args()

    # construct datapath from args and get files from said datapath
    data_path = "./" + args.measurement + "/"
    files = os.listdir(data_path)
    annotations = [f for f in files if f[0] == "s" and f[1] == args.sample]
    csi_files = [f for f in files if f[0] == "r" and f[5] == args.sample and f[-3:] == "csv"]

    # adjust which files we grab based on whether or not we want to compare different pairs, and whether or not we want diagonal pairs included
    if args.compare and args.diagonal:
        csi_files = [f for f in csi_files if (f[2] == f[8]) or (abs(int(f[2]) - int(f[8])) == 2)]
    else:
        if not args.diagonal:
            csi_files = [f for f in csi_files if f[2] == f[8]]
        else:
            csi_files = [f for f in csi_files if abs(int(f[2]) - int(f[8])) == 2]

    # handle absences; missing csi data means we cannot continue, annotations not necessarily
    if not csi_files:
        print("No data for this configuration")
        return
    if not annotations:
        print("No annotations for this configuration")

    # read in data for all existing pairs
    rx1 = None
    rx2 = None
    rx3 = None
    rx1_d = None
    rx3_d = None
    if args.compare and args.diagonal:
        for file in csi_files:
            if "rx1" in file and "n1" in file:
                rx1 = np.genfromtxt(data_path + file, delimiter=",")
            elif "rx1" in file and "n3" in file:
                rx1_d = np.genfromtxt(data_path + file, delimiter=",")
            elif "rx2" in file:
                rx2 = np.genfromtxt(data_path + file, delimiter=",")
            elif "rx3" in file and "n3" in file:
                rx3 = np.genfromtxt(data_path + file, delimiter=",")
            elif "rx3" in file and "n1" in file:
                rx3_d = np.genfromtxt(data_path + file, delimiter=",")
    else:
        for file in csi_files:
            if "rx1" in file:
                rx1 = np.genfromtxt(data_path + file, delimiter=",")
            elif "rx2" in file:
                rx2 = np.genfromtxt(data_path + file, delimiter=",")
            elif "rx3" in file:
                rx3 = np.genfromtxt(data_path + file, delimiter=",")

    # if we want to compare pairs
    if args.compare:
        # run some checks to make sure the configuration of args is valid
        if not args.weigh:
            print("Compare command invalid without weigh command also active")
            return
        if not annotations:
            print("Compare command invalid without annotations")
            return

        # read annotations
        f = open(data_path + annotations[0], 'r')

        lines = f.readlines()
        f.close()

        # create universal time stream for all pairs
        if rx1 is not None:
            rx1_t = rx1[:, 0]
            rx1_t = np.array([timestamp - rx1_t[0] for timestamp in rx1_t])
        if rx2 is not None:
            rx2_t = rx2[:, 0]
            rx2_t = np.array([timestamp - rx2_t[0] for timestamp in rx2_t])
        if rx3 is not None:
            rx3_t = rx3[:, 0]
            rx3_t = np.array([timestamp - rx3_t[0] for timestamp in rx3_t])

        if args.diagonal:
            if rx1_d is not None:
                rx1_d_t = rx1_d[:, 0]
                rx1_d_t = np.array([timestamp - rx1_d_t[0] for timestamp in rx1_d_t])
            if rx3_d is not None:
                rx3_d_t = rx3_d[:, 0]
                rx3_d_t = np.array([timestamp - rx3_d_t[0] for timestamp in rx3_d_t])

        # incorporate delays relevant to when within the measurement each individual node was started
        # n.b. rx pairs were always started after tx pairs, so the rx start time is the relevant one for this
        delays = lines[0].rstrip().split()
        t_min = []
        t_max = 0
        for delay in delays:
            node, _, time = delay.partition(",")
            if eval(node) is not None:
                if node == "rx1":
                    rx1_t += int(time)
                    t_max = max(t_max, max(rx1_t))
                    if args.diagonal:
                        rx1_d_t += int(time)
                        t_max = max(t_max, max(rx1_d_t))
                elif node == "rx2":
                    rx2_t += int(time)
                    t_max = max(t_max, max(rx2_t))
                elif node == "rx3":
                    rx3_t += int(time)
                    t_max = max(t_max, max(rx3_t))
                    if args.diagonal:
                        rx3_d_t += int(time)
                        t_max = max(t_max, max(rx3_d_t))
                t_min.append(int(time))
        t_min = min(t_min)

        t_global = np.arange(t_min, t_max, 5)

        # create action ranges
        action_ranges = []
        for line in lines[1:]:
            info = line.split()
            action_class = info[2]
            x = info[0]
            length = info[1]
            text = " ".join(info[6:]).rstrip()
            if "c" in action_class:
                if "e1" in text or "e2" in text or "e3" in text:
                    colour = "|"
                    label = "shelf 1"
                elif "e4" in text or "e5" in text or "e6" in text:
                    colour = "/"
                    label = "shelf 2"
                elif "e7" in text or "e8" in text or "e9" in text:
                    colour = "."
                    label = "shelf 3"
            elif "h" in action_class:
                colour = "O"
                label = "human"
            else:
                colour = "white"
            if length != "0":
                action_ranges.append((np.arange(int(x), int(x) + int(length), 5), colour, label))

        if rx1 is not None:
            acfs = rx1[:, 1:]

            # for thresh in THRESHOLD_RANGE:
            thresholded = np.empty(acfs.shape)
            for i in range(acfs.shape[1]):
                thresholded[:, i] = threshold(acfs[:, i], THRESHOLD)

            # cut into 5 second intervals
            indices = []
            slice_counts = []
            global_counts = []
            for i in reversed(range(t_global.shape[0])):
                start = rx1_t.shape[0]
                for j in reversed(range(1, start)):
                    if rx1_t[j] > t_global[i] and rx1_t[j - 1] <= t_global[i]:
                        indices.append(j)
                        slice_counts.append(len(indices) - 1)
                        global_counts.append(i)
                        start = j
                        break

            indices = indices[::-1]
            t_sliced = np.split(rx1_t, indices)
            thresholded_sliced = np.split(thresholded, indices)

            # calculate sensitivity and specificity of each five second slice
            rx1_sen = []
            rx1_spec = []
            for i in range(len(t_sliced)):
                pns = count_pns_weighted(thresholded_sliced[i], t_sliced[i], data_path + annotations[0], "rx1")
                if (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"] + pns["cs"]["fn"] +
                    pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"]) > 0:
                    rx1_sen.append((pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) / (
                            (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) + (
                            pns["cs"]["fn"] + pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"])))
                else:
                    rx1_sen.append(-1)
                if (pns["tn"] + pns["fp"]) > 0:
                    rx1_spec.append(pns["tn"] / (pns["tn"] + pns["fp"]))
                else:
                    rx1_spec.append(-1)
            rx1_sen_dict = dict(zip(global_counts[::-1], rx1_sen))
            rx1_spec_dict = dict(zip(global_counts[::-1], rx1_spec))

        if rx1_d is not None:
            acfs = rx1_d[:, 1:]

            # for thresh in THRESHOLD_RANGE:
            thresholded = np.empty(acfs.shape)
            for i in range(acfs.shape[1]):
                thresholded[:, i] = threshold(acfs[:, i], THRESHOLD)

            # cut into 5 second intervals
            indices = []
            slice_counts = []
            global_counts = []
            for i in reversed(range(t_global.shape[0])):
                start = rx1_d_t.shape[0]
                for j in reversed(range(1, start)):
                    if rx1_d_t[j] > t_global[i] and rx1_d_t[j - 1] <= t_global[i]:
                        indices.append(j)
                        slice_counts.append(len(indices) - 1)
                        global_counts.append(i)
                        start = j
                        break

            indices = indices[::-1]
            t_sliced = np.split(rx1_d_t, indices)
            thresholded_sliced = np.split(thresholded, indices)

            # calculate sensitivity and specificity of each five second slice
            rx1_d_sen = []
            rx1_d_spec = []
            for i in range(len(t_sliced)):
                pns = count_pns_weighted(thresholded_sliced[i], t_sliced[i], data_path + annotations[0], "rx1_d")
                if (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"] + pns["cs"]["fn"] +
                    pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"]) > 0:
                    rx1_d_sen.append((pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) / (
                            (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) + (
                            pns["cs"]["fn"] + pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"])))
                else:
                    rx1_d_sen.append(-1)
                if (pns["tn"] + pns["fp"]) > 0:
                    rx1_d_spec.append(pns["tn"] / (pns["tn"] + pns["fp"]))
                else:
                    rx1_d_spec.append(-1)
            rx1_d_sen_dict = dict(zip(global_counts[::-1], rx1_d_sen))
            rx1_d_spec_dict = dict(zip(global_counts[::-1], rx1_d_spec))

        if rx2 is not None:
            acfs = rx2[:, 1:]

            # for thresh in THRESHOLD_RANGE:
            thresholded = np.empty(acfs.shape)
            for i in range(acfs.shape[1]):
                thresholded[:, i] = threshold(acfs[:, i], THRESHOLD)

            # cut into 5 second intervals
            indices = []
            slice_counts = []
            global_counts = []
            for i in reversed(range(t_global.shape[0])):
                start = rx2_t.shape[0]
                for j in reversed(range(1, start)):
                    if rx2_t[j] > t_global[i] and rx2_t[j - 1] <= t_global[i]:
                        indices.append(j)
                        slice_counts.append(len(indices) - 1)
                        global_counts.append(i)
                        start = j
                        break

            indices = indices[::-1]
            t_sliced = np.split(rx2_t, indices)
            thresholded_sliced = np.split(thresholded, indices)

            # calculate sensitivity and specificity of each five second slice
            rx2_sen = []
            rx2_spec = []
            for i in range(len(t_sliced)):
                pns = count_pns_weighted(thresholded_sliced[i], t_sliced[i], data_path + annotations[0], "rx2")
                if (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"] + pns["cs"]["fn"] +
                    pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"]) > 0:
                    rx2_sen.append((pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) / (
                            (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) + (
                            pns["cs"]["fn"] + pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"])))
                else:
                    rx2_sen.append(-1)
                if (pns["tn"] + pns["fp"]) > 0:
                    rx2_spec.append(pns["tn"] / (pns["tn"] + pns["fp"]))
                else:
                    rx2_spec.append(-1)
            rx2_sen_dict = dict(zip(global_counts[::-1], rx2_sen))
            rx2_spec_dict = dict(zip(global_counts[::-1], rx2_spec))

        if rx3 is not None:
            acfs = rx3[:, 1:]

            # for thresh in THRESHOLD_RANGE:
            thresholded = np.empty(acfs.shape)
            for i in range(acfs.shape[1]):
                thresholded[:, i] = threshold(acfs[:, i], THRESHOLD)

            # cut into 5 second intervals
            indices = []
            slice_counts = []
            global_counts = []
            for i in reversed(range(t_global.shape[0])):
                start = rx3_t.shape[0]
                for j in reversed(range(1, start)):
                    if rx3_t[j] > t_global[i] and rx3_t[j - 1] <= t_global[i]:
                        indices.append(j)
                        slice_counts.append(len(indices) - 1)
                        global_counts.append(i)
                        start = j
                        break

            indices = indices[::-1]
            t_sliced = np.split(rx3_t, indices)
            thresholded_sliced = np.split(thresholded, indices)

            # calculate sensitivity and specificity of each five second slice
            rx3_sen = []
            rx3_spec = []
            for i in range(len(t_sliced)):
                pns = count_pns_weighted(thresholded_sliced[i], t_sliced[i], data_path + annotations[0], "rx3")
                if (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"] + pns["cs"]["fn"] +
                    pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"]) > 0:
                    rx3_sen.append((pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) / (
                            (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) + (
                            pns["cs"]["fn"] + pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"])))
                else:
                    rx3_sen.append(-1)
                if (pns["tn"] + pns["fp"]) > 0:
                    rx3_spec.append(pns["tn"] / (pns["tn"] + pns["fp"]))
                else:
                    rx3_spec.append(-1)
            rx3_sen_dict = dict(zip(global_counts[::-1], rx3_sen))
            rx3_spec_dict = dict(zip(global_counts[::-1], rx3_spec))

        if rx3_d is not None:
            acfs = rx3_d[:, 1:]

            # for thresh in THRESHOLD_RANGE:
            thresholded = np.empty(acfs.shape)
            for i in range(acfs.shape[1]):
                thresholded[:, i] = threshold(acfs[:, i], THRESHOLD)

            # cut into 5 second intervals
            indices = []
            slice_counts = []
            global_counts = []
            for i in reversed(range(t_global.shape[0])):
                start = rx3_d_t.shape[0]
                for j in reversed(range(1, start)):
                    if rx3_d_t[j] > t_global[i] and rx3_d_t[j - 1] <= t_global[i]:
                        indices.append(j)
                        slice_counts.append(len(indices) - 1)
                        global_counts.append(i)
                        start = j
                        break

            indices = indices[::-1]
            t_sliced = np.split(rx3_d_t, indices)
            thresholded_sliced = np.split(thresholded, indices)

            # calculate sensitivity and specificity of each five second slice
            rx3_d_sen = []
            rx3_d_spec = []
            for i in range(len(t_sliced)):
                pns = count_pns_weighted(thresholded_sliced[i], t_sliced[i], data_path + annotations[0], "rx3_d")
                if (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"] + pns["cs"]["fn"] +
                    pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"]) > 0:
                    rx3_sen.append((pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) / (
                            (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) + (
                            pns["cs"]["fn"] + pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"])))
                else:
                    rx3_d_sen.append(-1)
                if (pns["tn"] + pns["fp"]) > 0:
                    rx3_d_spec.append(pns["tn"] / (pns["tn"] + pns["fp"]))
                else:
                    rx3_d_spec.append(-1)
            rx3_d_sen_dict = dict(zip(global_counts[::-1], rx3_d_sen))
            rx3_d_spec_dict = dict(zip(global_counts[::-1], rx3_d_spec))

        # plot sensitivity and specificity
        _, sen_axes = plt.subplots(num="Sensitivity")
        best_sen = {"rx1": np.full(t_global.shape[0], -1.0), "rx2": np.full(t_global.shape[0], -1.0), "rx3": np.full(t_global.shape[0], -1.0),
                    "rx1_d": np.full(t_global.shape[0], -1.0), "rx3_d": np.full(t_global.shape[0], -1.0)}
        best_pair = [0, 0, 0]

        # here we have the if/else statement from hell
        # there is almost certainly a better way to do this, but at some point I was in too deep
        # its purpose is to report the best sensitivity/specificity node out of all nodes for a given sample
        # with certain caveats like pair has to exist, and the difference betwen sen and spec must not be greater than 0.3, etx
        for i in range(t_global.shape[0]):
            if args.diagonal:
                if i in rx1_sen_dict.keys() and i in rx2_sen_dict.keys() and i in rx3_sen_dict.keys() and i in rx1_d_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx2_sen_dict[i] and rx1_sen_dict[i] >= rx3_sen_dict[i] and rx1_sen_dict[
                        i] >= rx1_d_sen_dict[i] and rx1_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx2_sen_dict[i] >= rx1_sen_dict[i] and rx2_sen_dict[i] >= rx3_sen_dict[i] and \
                            rx2_sen_dict[i] >= rx1_d_sen_dict[i] and rx2_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                         rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx1_sen_dict[i] and rx3_sen_dict[i] >= rx2_sen_dict[i] and \
                            rx3_sen_dict[i] >= rx1_d_sen_dict[i] and rx3_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                         rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx1_sen_dict[i] and rx1_d_sen_dict[i] >= rx2_sen_dict[i] and \
                            rx1_d_sen_dict[i] >= rx3_sen_dict[i] and rx1_d_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                         rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx1_sen_dict[i] and rx3_d_sen_dict[i] >= rx2_sen_dict[i] and \
                            rx3_d_sen_dict[i] >= rx3_sen_dict[i] and rx3_d_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                         rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx2_sen_dict.keys() and i in rx3_sen_dict.keys() and i in rx1_d_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx2_sen_dict[i] and rx1_sen_dict[i] >= rx3_sen_dict[i] and rx1_sen_dict[
                        i] >= rx1_d_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx2_sen_dict[i] >= rx1_sen_dict[i] and rx2_sen_dict[i] >= rx3_sen_dict[i] and \
                            rx2_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                         rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx1_sen_dict[i] and rx3_sen_dict[i] >= rx2_sen_dict[i] and \
                            rx3_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                         rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx1_sen_dict[i] and rx1_d_sen_dict[i] >= rx2_sen_dict[i] and \
                            rx1_d_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                         rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx2_sen_dict.keys() and i in rx3_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx2_sen_dict[i] and rx1_sen_dict[i] >= rx3_sen_dict[i] and rx1_sen_dict[
                        i] >= \
                            rx3_d_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                         rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx2_sen_dict[i] >= rx1_sen_dict[i] and rx2_sen_dict[i] >= rx3_sen_dict[i] and \
                            rx2_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                         rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx1_sen_dict[i] and rx3_sen_dict[i] >= rx2_sen_dict[i] and \
                            rx3_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                         rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx1_sen_dict[i] and rx3_d_sen_dict[i] >= rx2_sen_dict[i] and \
                            rx3_d_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                         rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx2_sen_dict.keys() and i in rx1_d_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx2_sen_dict[i] and rx1_sen_dict[i] >= rx1_d_sen_dict[i] and \
                            rx1_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                         rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx2_sen_dict[i] >= rx1_sen_dict[i] and rx2_sen_dict[i] >= rx1_d_sen_dict[i] and \
                            rx2_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                         rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx1_sen_dict[i] and rx1_d_sen_dict[i] >= rx2_sen_dict[i] and \
                            rx1_d_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                         rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx1_sen_dict[i] and rx3_d_sen_dict[i] >= rx2_sen_dict[i] and \
                            rx3_d_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                         rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx3_sen_dict.keys() and i in rx1_d_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx3_sen_dict[i] and rx1_sen_dict[i] >= rx1_d_sen_dict[i] and \
                            rx1_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                         rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx1_sen_dict[i] and rx3_sen_dict[i] >= rx1_d_sen_dict[i] and \
                            rx3_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                         rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx1_sen_dict[i] and rx1_d_sen_dict[i] >= rx3_sen_dict[i] and \
                            rx1_d_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                         rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx1_sen_dict[i] and rx3_d_sen_dict[i] >= rx3_sen_dict[i] and \
                            rx3_d_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                         rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx2_sen_dict.keys() and i in rx3_sen_dict.keys() and i in rx1_d_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx2_sen_dict[i] >= rx3_sen_dict[i] and rx2_sen_dict[i] >= rx1_d_sen_dict[i] and \
                            rx2_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                         rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx2_sen_dict[i] and rx3_sen_dict[i] >= rx1_d_sen_dict[i] and \
                            rx3_sen_dict[i] >= rx3_d_sen_dict[i] \
                            and (i not in rx3_spec_dict.keys() or abs(
                         rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx2_sen_dict[i] and rx1_d_sen_dict[i] >= rx3_sen_dict[i] and \
                            rx1_d_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                         rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx2_sen_dict[i] and rx3_d_sen_dict[i] >= rx3_sen_dict[i] and \
                            rx3_d_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                         rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx2_sen_dict.keys() and i in rx1_d_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx2_sen_dict[i] and rx1_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx2_sen_dict[i] >= rx1_sen_dict[i] and rx2_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx1_sen_dict[i] and rx1_d_sen_dict[i] >= rx2_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                             rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx3_sen_dict.keys() and i in rx1_d_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx3_sen_dict[i] and rx1_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx1_sen_dict[i] and rx3_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx1_sen_dict[i] and rx1_d_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                             rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx2_sen_dict.keys() and i in rx3_sen_dict.keys() and i in rx1_d_sen_dict.keys():
                    if rx2_sen_dict[i] >= rx3_sen_dict[i] and rx2_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx2_sen_dict[i] and rx3_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx2_sen_dict[i] and rx1_d_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                             rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx2_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx2_sen_dict[i] and rx1_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx2_sen_dict[i] >= rx1_sen_dict[i] and rx2_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx1_sen_dict[i] and rx3_d_sen_dict[i] >= rx2_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                             rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx3_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx3_sen_dict[i] and rx1_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx1_sen_dict[i] and rx3_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx1_sen_dict[i] and rx3_d_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                             rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx2_sen_dict.keys() and i in rx3_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx2_sen_dict[i] >= rx3_sen_dict[i] and rx2_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx2_sen_dict[i] and rx3_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx2_sen_dict[i] and rx1_d_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                             rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx1_d_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx1_d_sen_dict[i] and rx1_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx1_sen_dict[i] and rx1_d_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                             rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx1_sen_dict[i] and rx3_d_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                             rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx2_sen_dict.keys() and i in rx1_d_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx2_sen_dict[i] >= rx1_d_sen_dict[i] and rx2_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx2_sen_dict[i] and rx1_d_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                             rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx2_sen_dict[i] and rx3_d_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                             rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx3_sen_dict.keys() and i in rx1_d_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx3_sen_dict[i] >= rx1_d_sen_dict[i] and rx3_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx3_sen_dict[i] and rx1_d_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                             rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx3_sen_dict[i] and rx3_d_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                             rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx2_sen_dict.keys() and i in rx3_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx2_sen_dict[i] and rx1_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx2_sen_dict[i] >= rx1_sen_dict[i] and rx2_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx2_sen_dict[i] and rx3_sen_dict[i] >= rx1_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx2_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx2_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx2_sen_dict[i] >= rx1_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx3_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx1_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx1_d_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx1_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                             rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx1_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                             rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx2_sen_dict.keys() and i in rx3_sen_dict.keys():
                    if rx2_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx2_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx2_sen_dict.keys() and i in rx1_d_sen_dict.keys():
                    if rx2_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx2_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                             rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx2_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx2_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx2_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                             rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx3_sen_dict.keys() and i in rx1_d_sen_dict.keys():
                    if rx3_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx1_d_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                             rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx3_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx3_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                             rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_d_sen_dict.keys() and i in rx3_d_sen_dict.keys():
                    if rx1_d_sen_dict[i] >= rx3_d_sen_dict[i] and (
                             i not in rx1_d_spec_dict.keys() or abs(
                             rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_d_sen_dict[i] >= rx1_d_sen_dict[i] and (
                             i not in rx3_d_spec_dict.keys() or abs(
                             rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and (
                         i not in rx1_spec_dict.keys() or abs(
                         rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx2_sen_dict.keys() and (
                         i not in rx2_spec_dict.keys() or abs(
                         rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx3_sen_dict.keys() and (i not in rx3_spec_dict.keys() or abs(
                         rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_d_sen_dict.keys() and (
                         i not in rx1_d_spec_dict.keys() or abs(
                         rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_spec_dict[i] == -1):
                        best_sen["rx1_d"][i] = rx1_d_sen_dict[i]
                        best_pair[0] = rx1_d_sen_dict[i]
                        if i in rx1_d_spec_dict.keys():
                            best_pair[1] = rx1_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx3_d_sen_dict.keys() and (
                         i not in rx3_d_spec_dict.keys() or abs(
                         rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_spec_dict[i] == -1):
                        best_sen["rx3_d"][i] = rx3_d_sen_dict[i]
                        best_pair[0] = rx3_d_sen_dict[i]
                        if i in rx3_d_spec_dict.keys():
                            best_pair[1] = rx3_d_spec_dict[i]
                        else:
                            best_pair[1] = -1
                else:
                    best_sen["rx1"][i] = -1
                    best_sen["rx2"][i] = -1
                    best_sen["rx3"][i] = -1
                    best_sen["rx1_d"][i] = -1
                    best_sen["rx3_d"][i] = -1
            else:
                if i in rx1_sen_dict.keys() and i in rx2_sen_dict.keys() and i in rx3_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx2_sen_dict[i] and rx1_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx2_sen_dict[i] >= rx1_sen_dict[i] and rx2_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx2_sen_dict[i] and rx3_sen_dict[i] >= rx1_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx2_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx2_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx2_sen_dict[i] >= rx1_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and i in rx3_sen_dict.keys():
                    if rx1_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx1_spec_dict.keys() or abs(
                             rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx1_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx2_sen_dict.keys() and i in rx3_sen_dict.keys():
                    if rx2_sen_dict[i] >= rx3_sen_dict[i] and (
                             i not in rx2_spec_dict.keys() or abs(
                             rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                    elif rx3_sen_dict[i] >= rx2_sen_dict[i] and (
                             i not in rx3_spec_dict.keys() or abs(
                             rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx1_sen_dict.keys() and (
                         i not in rx1_spec_dict.keys() or abs(
                         rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_spec_dict[i] == -1):
                        best_sen["rx1"][i] = rx1_sen_dict[i]
                        best_pair[0] = rx1_sen_dict[i]
                        if i in rx1_spec_dict.keys():
                            best_pair[1] = rx1_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx2_sen_dict.keys() and (
                         i not in rx2_spec_dict.keys() or abs(
                         rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_spec_dict[i] == -1):
                        best_sen["rx2"][i] = rx2_sen_dict[i]
                        best_pair[0] = rx2_sen_dict[i]
                        if i in rx2_spec_dict.keys():
                            best_pair[1] = rx2_spec_dict[i]
                        else:
                            best_pair[1] = -1
                elif i in rx3_sen_dict.keys() and (
                         i not in rx3_spec_dict.keys() or abs(
                         rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_spec_dict[i] == -1):
                        best_sen["rx3"][i] = rx3_sen_dict[i]
                        best_pair[0] = rx3_sen_dict[i]
                        if i in rx3_spec_dict.keys():
                            best_pair[1] = rx3_spec_dict[i]
                        else:
                            best_pair[1] = -1
                else:
                    best_sen["rx1"][i] = -1
                    best_sen["rx2"][i] = -1
                    best_sen["rx3"][i] = -1
            if best_pair[0] > -1 and best_pair[1] > -1:
                print("best sen:" + str(best_pair[0]))
                print("best spec:" + str(best_pair[1]))
                best_pair[2] += 1
            best_pair[0] = 0
            best_pair[1] = 0
        print("good pairs counts:" + str(best_pair[2]))

        # here we plot the best sensitivities we just found, colour coded and with hatched sections showing the different action ranges
        sen_axes.set_title("Sensitivity")
        sen_axes.set_ylim(bottom=0, top=1)
        sen_axes.set_xlabel("Time (s)")
        sen_axes.set_ylabel("%")
        if args.diagonal:
            sen_axes.bar(t_global, best_sen["rx1"], width=5, align='edge', color="blue", label="rx1")
            sen_axes.bar(t_global, best_sen["rx2"], width=5, align='edge', color='cyan', label="rx2")
            sen_axes.bar(t_global, best_sen["rx3"], width=5, align='edge', color='teal', label="rx3")
            sen_axes.bar(t_global, best_sen["rx1_d"], width=5, align='edge', color="orange", label="rx1_d")
            sen_axes.bar(t_global, best_sen["rx3_d"], width=5, align='edge', color='red', label="rx3_d")
        else:
            sen_axes.bar(t_global, best_sen["rx1"], width=5, align='edge', color="blue", label="rx1")
            sen_axes.bar(t_global, best_sen["rx2"], width=5, align='edge', color='yellow', label="rx2")
            sen_axes.bar(t_global, best_sen["rx3"], width=5, align='edge', color='red', label="rx3")
        firsts = {"|": True, "/": True, ".": True, "O": True}
        hatches = []
        for action in action_ranges:
            if firsts[action[1]]:
                hatches.append(
                    sen_axes.bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge', hatch=action[1],
                                 label=action[2], facecolor=(0, 0, 0, 0)))
                firsts[action[1]] = False
            else:
                hatches.append(
                    sen_axes.bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge', hatch=action[1],
                                 facecolor=(0, 0, 0, 0)))
        for hatch in hatches:
            hatch._hatch_color = "black"
        sen_axes.legend(loc='upper right')
        annotate(data_path + annotations[0], sen_axes)

        # if/else from hell 2, electric boogaloo
        _, spec_axes = plt.subplots(num="Specificity")
        best_spec = {"rx1": np.full(t_global.shape[0], -1.0), "rx2": np.full(t_global.shape[0], -1.0), "rx3": np.full(t_global.shape[0], -1.0),
                    "rx1_d": np.full(t_global.shape[0], -1.0), "rx3_d": np.full(t_global.shape[0], -1.0)}
        for i in range(t_global.shape[0]):
            if args.diagonal:
                if i in rx1_spec_dict.keys() and i in rx2_spec_dict.keys() and i in rx3_spec_dict.keys() and i in rx1_d_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx2_spec_dict[i] and rx1_spec_dict[i] >= rx3_spec_dict[i] and rx1_spec_dict[i] >= rx1_d_spec_dict[i] and rx1_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx2_spec_dict[i] >= rx1_spec_dict[i] and rx2_spec_dict[i] >= rx3_spec_dict[i] and \
                            rx2_spec_dict[i] >= rx1_d_spec_dict[i] and rx2_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_spec_dict[i] >= rx1_spec_dict[i] and rx3_spec_dict[i] >= rx2_spec_dict[i] and \
                            rx3_spec_dict[i] >= rx1_d_spec_dict[i] and rx3_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx1_spec_dict[i] and rx1_d_spec_dict[i] >= rx2_spec_dict[i] and \
                            rx1_d_spec_dict[i] >= rx3_spec_dict[i] and rx1_d_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx1_spec_dict[i] and rx3_d_spec_dict[i] >= rx2_spec_dict[i] and \
                            rx3_d_spec_dict[i] >= rx3_spec_dict[i] and rx3_d_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx1_spec_dict.keys() and i in rx2_spec_dict.keys() and i in rx3_spec_dict.keys() and i in rx1_d_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx2_spec_dict[i] and rx1_spec_dict[i] >= rx3_spec_dict[i] and rx1_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx2_spec_dict[i] >= rx1_spec_dict[i] and rx2_spec_dict[i] >= rx3_spec_dict[i] and \
                            rx2_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_spec_dict[i] >= rx1_spec_dict[i] and rx3_spec_dict[i] >= rx2_spec_dict[i] and \
                            rx3_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx1_spec_dict[i] and rx1_d_spec_dict[i] >= rx2_spec_dict[i] and \
                            rx1_d_spec_dict[i] >= rx3_spec_dict[i]  and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                elif i in rx1_spec_dict.keys() and i in rx2_spec_dict.keys() and i in rx3_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx2_spec_dict[i] and rx1_spec_dict[i] >= rx3_spec_dict[i] and rx1_spec_dict[i] >= \
                            rx3_d_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx2_spec_dict[i] >= rx1_spec_dict[i] and rx2_spec_dict[i] >= rx3_spec_dict[i] and \
                            rx2_spec_dict[i] >= rx3_d_spec_dict[i]  and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_spec_dict[i] >= rx1_spec_dict[i] and rx3_spec_dict[i] >= rx2_spec_dict[i] and \
                            rx3_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx1_spec_dict[i] and rx3_d_spec_dict[i] >= rx2_spec_dict[i] and \
                            rx3_d_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx1_spec_dict.keys() and i in rx2_spec_dict.keys() and i in rx1_d_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx2_spec_dict[i] and rx1_spec_dict[i] >= rx1_d_spec_dict[i] and \
                            rx1_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx2_spec_dict[i] >= rx1_spec_dict[i] and rx2_spec_dict[i] >= rx1_d_spec_dict[i] and \
                            rx2_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx1_spec_dict[i] and rx1_d_spec_dict[i] >= rx2_spec_dict[i] and \
                            rx1_d_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx1_spec_dict[i] and rx3_d_spec_dict[i] >= rx2_spec_dict[i] and \
                            rx3_d_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx1_spec_dict.keys() and i in rx3_spec_dict.keys() and i in rx1_d_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx3_spec_dict[i] and rx1_spec_dict[i] >= rx1_d_spec_dict[i] and \
                            rx1_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_spec_dict[i] >= rx1_spec_dict[i] and rx3_spec_dict[i] >= rx1_d_spec_dict[i] and \
                            rx3_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx1_spec_dict[i] and rx1_d_spec_dict[i] >= rx3_spec_dict[i] and \
                            rx1_d_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx1_spec_dict[i] and rx3_d_spec_dict[i] >= rx3_spec_dict[i] and \
                            rx3_d_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx2_spec_dict.keys() and i in rx3_spec_dict.keys() and i in rx1_d_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx2_spec_dict[i] >= rx3_spec_dict[i] and rx2_spec_dict[i] >= rx1_d_spec_dict[i] and \
                            rx2_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_spec_dict[i] >= rx2_spec_dict[i] and rx3_spec_dict[i] >= rx1_d_spec_dict[i] and rx3_spec_dict[i] >= rx3_d_spec_dict[i] \
                            and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx2_spec_dict[i] and rx1_d_spec_dict[i] >= rx3_spec_dict[i] and \
                            rx1_d_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx2_spec_dict[i] and rx3_d_spec_dict[i] >= rx3_spec_dict[i] and \
                            rx3_d_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx1_spec_dict.keys() and i in rx2_spec_dict.keys() and i in rx1_d_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx2_spec_dict[i] and rx1_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx2_spec_dict[i] >= rx1_spec_dict[i] and rx2_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx1_spec_dict[i] and rx1_d_spec_dict[i] >= rx2_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                elif i in rx1_spec_dict.keys() and i in rx3_spec_dict.keys() and i in rx1_d_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx3_spec_dict[i] and rx1_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_spec_dict[i] >= rx1_spec_dict[i] and rx3_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx1_spec_dict[i] and rx1_d_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                elif i in rx2_spec_dict.keys() and i in rx3_spec_dict.keys() and i in rx1_d_spec_dict.keys():
                    if rx2_spec_dict[i] >= rx3_spec_dict[i] and rx2_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_spec_dict[i] >= rx2_spec_dict[i] and rx3_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx2_spec_dict[i] and rx1_d_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                elif i in rx1_spec_dict.keys() and i in rx2_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx2_spec_dict[i] and rx1_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx2_spec_dict[i] >= rx1_spec_dict[i] and rx2_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx1_spec_dict[i] and rx3_d_spec_dict[i] >= rx2_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx1_spec_dict.keys() and i in rx3_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx3_spec_dict[i] and rx1_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_spec_dict[i] >= rx1_spec_dict[i] and rx3_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx1_spec_dict[i] and rx3_d_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx2_spec_dict.keys() and i in rx3_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx2_spec_dict[i] >= rx3_spec_dict[i] and rx2_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_spec_dict[i] >= rx2_spec_dict[i] and rx3_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx2_spec_dict[i] and rx1_d_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx1_spec_dict.keys() and i in rx1_d_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx1_d_spec_dict[i] and rx1_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx1_spec_dict[i] and rx1_d_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx1_spec_dict[i] and rx3_d_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx2_spec_dict.keys() and i in rx1_d_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx2_spec_dict[i] >= rx1_d_spec_dict[i] and rx2_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx2_spec_dict[i] and rx1_d_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx2_spec_dict[i] and rx3_d_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx3_spec_dict.keys() and i in rx1_d_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx3_spec_dict[i] >= rx1_d_spec_dict[i] and rx3_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx3_spec_dict[i] and rx1_d_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx3_spec_dict[i] and rx3_d_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx1_spec_dict.keys() and i in rx2_spec_dict.keys() and i in rx3_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx2_spec_dict[i] and rx1_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx2_spec_dict[i] >= rx1_spec_dict[i] and rx2_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_spec_dict[i] >= rx2_spec_dict[i] and rx3_spec_dict[i] >= rx1_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                elif i in rx1_spec_dict.keys() and i in rx2_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx2_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx2_spec_dict[i] >= rx1_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                elif i in rx1_spec_dict.keys() and i in rx3_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_spec_dict[i] >= rx1_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                elif i in rx1_spec_dict.keys() and i in rx1_d_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx1_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                elif i in rx1_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx1_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx2_spec_dict.keys() and i in rx3_spec_dict.keys():
                    if rx2_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_spec_dict[i] >= rx2_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                elif i in rx2_spec_dict.keys() and i in rx1_d_spec_dict.keys():
                    if rx2_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx2_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                elif i in rx2_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx2_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx2_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx3_spec_dict.keys() and i in rx1_d_spec_dict.keys():
                    if rx3_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx1_d_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                elif i in rx3_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx3_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx1_d_spec_dict.keys() and i in rx3_d_spec_dict.keys():
                    if rx1_d_spec_dict[i] >= rx3_d_spec_dict[i] and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                        best_spec["rx3_d"][i] = -1
                    elif rx3_d_spec_dict[i] >= rx1_d_spec_dict[i] and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                        best_spec["rx1_d"][i] = -1
                        best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                elif i in rx1_spec_dict.keys() and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                    best_spec["rx1"][i] = rx1_spec_dict[i]
                    best_spec["rx2"][i] = -1
                    best_spec["rx3"][i] = -1
                    best_spec["rx1_d"][i] = -1
                    best_spec["rx3_d"][i] = -1
                elif i in rx2_spec_dict.keys() and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                    best_spec["rx1"][i] = -1
                    best_spec["rx2"][i] = rx2_spec_dict[i]
                    best_spec["rx3"][i] = -1
                    best_spec["rx1_d"][i] = -1
                    best_spec["rx3_d"][i] = -1
                elif i in rx3_spec_dict.keys() and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                    best_spec["rx1"][i] = -1
                    best_spec["rx2"][i] = -1
                    best_spec["rx3"][i] = rx3_spec_dict[i]
                    best_spec["rx1_d"][i] = -1
                    best_spec["rx3_d"][i] = -1
                elif i in rx1_d_spec_dict.keys() and (i not in rx1_d_sen_dict.keys() or abs(rx1_d_spec_dict[i] - rx1_d_sen_dict[i]) < 0.5 or rx1_d_sen_dict[i] == -1):
                    best_spec["rx1"][i] = -1
                    best_spec["rx2"][i] = -1
                    best_spec["rx3"][i] = -1
                    best_spec["rx1_d"][i] = rx1_d_spec_dict[i]
                    best_spec["rx3_d"][i] = -1
                elif i in rx3_d_spec_dict.keys() and (i not in rx3_d_sen_dict.keys() or abs(rx3_d_spec_dict[i] - rx3_d_sen_dict[i]) < 0.5 or rx3_d_sen_dict[i] == -1):
                    best_spec["rx1"][i] = -1
                    best_spec["rx2"][i] = -1
                    best_spec["rx3"][i] = -1
                    best_spec["rx1_d"][i] = -1
                    best_spec["rx3_d"][i] = rx3_d_spec_dict[i]
                else:
                    best_spec["rx1"][i] = -1
                    best_spec["rx2"][i] = -1
                    best_spec["rx3"][i] = -1
                    best_spec["rx1_d"][i] = -1
                    best_spec["rx3_d"][i] = -1
            else:
                if i in rx1_spec_dict.keys() and i in rx2_spec_dict.keys() and i in rx3_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx2_spec_dict[i] and rx1_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                    elif rx2_spec_dict[i] >= rx1_spec_dict[i] and rx2_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                    elif rx3_spec_dict[i] >= rx2_spec_dict[i] and rx3_spec_dict[i] >= rx1_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                elif i in rx1_spec_dict.keys() and i in rx2_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx2_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                    elif rx2_spec_dict[i] >= rx1_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                elif i in rx1_spec_dict.keys() and i in rx3_spec_dict.keys():
                    if rx1_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                        best_spec["rx1"][i] = rx1_spec_dict[i]
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = -1
                    elif rx3_spec_dict[i] >= rx1_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                elif i in rx2_spec_dict.keys() and i in rx3_spec_dict.keys():
                    if rx2_spec_dict[i] >= rx3_spec_dict[i] and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = rx2_spec_dict[i]
                        best_spec["rx3"][i] = -1
                    elif rx3_spec_dict[i] >= rx2_spec_dict[i] and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                        best_spec["rx1"][i] = -1
                        best_spec["rx2"][i] = -1
                        best_spec["rx3"][i] = rx3_spec_dict[i]
                elif i in rx1_spec_dict.keys() and (i not in rx1_sen_dict.keys() or abs(rx1_spec_dict[i] - rx1_sen_dict[i]) < 0.5 or rx1_sen_dict[i] == -1):
                    best_spec["rx1"][i] = rx1_spec_dict[i]
                    best_spec["rx2"][i] = -1
                    best_spec["rx3"][i] = -1
                elif i in rx2_spec_dict.keys() and (i not in rx2_sen_dict.keys() or abs(rx2_spec_dict[i] - rx2_sen_dict[i]) < 0.5 or rx2_sen_dict[i] == -1):
                    best_spec["rx1"][i] = -1
                    best_spec["rx2"][i] = rx2_spec_dict[i]
                    best_spec["rx3"][i] = -1
                elif i in rx3_spec_dict.keys() and (i not in rx3_sen_dict.keys() or abs(rx3_spec_dict[i] - rx3_sen_dict[i]) < 0.5 or rx3_sen_dict[i] == -1):
                    best_spec["rx1"][i] = -1
                    best_spec["rx2"][i] = -1
                    best_spec["rx3"][i] = rx3_spec_dict[i]
                else:
                    best_spec["rx1"][i] = -1
                    best_spec["rx2"][i] = -1
                    best_spec["rx3"][i] = -1

        # here we plot the best specificities we just found, colour coded and with hatched sections showing the different action ranges
        spec_axes.set_title("Specificity")
        spec_axes.set_ylim(bottom=0, top=1)
        spec_axes.set_xlabel("Time (s)")
        spec_axes.set_ylabel("%")
        if args.diagonal:
            spec_axes.bar(t_global, best_spec["rx1"], width=5, align='edge', color="blue", label="rx1")
            spec_axes.bar(t_global, best_spec["rx2"], width=5, align='edge', color='cyan', label="rx2")
            spec_axes.bar(t_global, best_spec["rx3"], width=5, align='edge', color='teal', label="rx3")
            spec_axes.bar(t_global, best_spec["rx1_d"], width=5, align='edge', color="orange", label="rx1_d")
            spec_axes.bar(t_global, best_spec["rx3_d"], width=5, align='edge', color='red', label="rx3_d")
        else:
            spec_axes.bar(t_global, best_spec["rx1"], width=5, align='edge', color="blue", label="rx1")
            spec_axes.bar(t_global, best_spec["rx2"], width=5, align='edge', color='yellow', label="rx2")
            spec_axes.bar(t_global, best_spec["rx3"], width=5, align='edge', color='red', label="rx3")
        firsts = {"|": True, "/": True, ".": True, "O": True}
        hatches = []
        for action in action_ranges:
            if firsts[action[1]]:
                hatches.append(
                    spec_axes.bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge', hatch=action[1],
                                  label=action[2], facecolor=(0, 0, 0, 0)))
                firsts[action[1]] = False
            else:
                hatches.append(
                    spec_axes.bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge', hatch=action[1],
                                  facecolor=(0, 0, 0, 0)))
        for hatch in hatches:
            hatch._hatch_color = "black"
        spec_axes.legend(loc='upper right')
        annotate(data_path + annotations[0], spec_axes)



    # if we are NOT doing comparison, and just plotting normal thresholded data
    else:
        if rx1 is not None:
            # get data
            acfs = rx1[:, 1:]

            # get time
            x_label = "Time (s)"
            try:
                t = rx1[:, 0]
                t = np.array([timestamp - t[0] for timestamp in t])
                xlim = max(t)
            except AttributeError:
                # No timestamp in frame. Likely an IWL entry.
                # Will be moving timestamps to CSIData to account for this.
                t = np.array()
                xlim = acfs.shape[1]

                x_label = "Frame No."

            # if we are not weighing components together, plot everything
            if not args.weigh:
                _, rx1_axes = plt.subplots(nrows=5, num="rx1")
                for i in range(acfs.shape[1]):
                    rx1_axes[i].set_title("CSI ACFS Thresholded, component " + str(i + 1))
                    rx1_axes[i].set_ylim(bottom=0, top=1)
                    rx1_axes[i].set_xlabel(x_label)
                    rx1_axes[i].set_ylabel("Activity")
                    first = True
                    # for thresh in THRESHOLD_RANGE:
                    thresholded = threshold(acfs[:, i], THRESHOLD)
                    if annotations:
                        pns = count_pns(thresholded, t, data_path + annotations[0], "rx1")
                        report_pns(pns, data_path, "rx1", THRESHOLD, args.diagonal, args.sample, first, i + 1)
                        first = False

                        rx1_axes[i].plot(t, thresholded, label="Thresholded to " + str(THRESHOLD))
                        rx1_axes[i].legend(loc='upper right')

            # if we are weighting components, plot weighted senspec by class
            else:
                first = True
                # for thresh in THRESHOLD_RANGE:
                thresholded = np.empty(acfs.shape)
                for i in range(acfs.shape[1]):
                    thresholded[:, i] = threshold(acfs[:, i], THRESHOLD)

                # cut into 5 second intervals
                indices = [0]
                for i in range(t.shape[0]):
                    if t[i] - t[indices[-1]] >= 5:
                        indices.append(i)
                indices = indices[1:]
                t_sliced = np.split(t, indices)
                thresholded_sliced = np.split(thresholded, indices)

                if annotations:
                    # create action ranges
                    f = open(data_path + annotations[0], 'r')
                    lines = f.readlines()
                    f.close()

                    delays = lines[0].rstrip().split()
                    to_remove = 0
                    for delay in delays:
                        node, _, time = delay.partition(",")
                        if node == "rx1":
                            to_remove = int(time)
                    action_ranges = []
                    for line in lines[1:]:
                        info = line.split()
                        action_class = info[2]
                        x = info[0]
                        length = info[1]
                        text = " ".join(info[6:]).rstrip()
                        if "c" in action_class:
                            if "e1" in text or "e2" in text or "e3" in text:
                                colour = "|"
                                label = "shelf 1"
                            elif "e4" in text or "e5" in text or "e6" in text:
                                colour = "/"
                                label = "shelf 2"
                            elif "e7" in text or "e8" in text or "e9" in text:
                                colour = "."
                                label = "shelf 3"
                        elif "h" in action_class:
                            colour = "O"
                            label = "human"
                        else:
                            colour = "white"
                        if length != "0":
                            action_ranges.append(
                                (np.arange(int(x) - to_remove, int(x) + int(length) - to_remove, 5), colour, label))

                    _, rx1_axes = plt.subplots(nrows=4, num="rx1")
                    cats = []
                    humans = []
                    total = []
                    spec = []
                    time = [item[0] for item in t_sliced]
                    for i in range(len(t_sliced)):
                        pns = count_pns_weighted(thresholded_sliced[i], t_sliced[i], data_path + annotations[0], "rx1")
                        if (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["cs"]["fn"] +
                            pns["cm"]["fn"] + pns["cl"]["fn"]) > 0:
                            cats.append((pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"]) / (
                                    (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"]) + (
                                    pns["cs"]["fn"] + pns["cm"]["fn"] + pns["cl"]["fn"])))
                        else:
                            cats.append(-1)
                        if (pns["h"]["tp"] + pns["h"]["fn"]) > 0:
                            humans.append(pns["h"]["tp"] / (pns["h"]["tp"] + pns["h"]["fn"]))
                        else:
                            humans.append(-1)
                        if (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"] + pns["cs"]["fn"] +
                            pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"]) > 0:
                            total.append((pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) / (
                                    (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) + (
                                    pns["cs"]["fn"] + pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"])))
                        else:
                            total.append(-1)
                        if (pns["tn"] + pns["fp"]) > 0:
                            spec.append(pns["tn"] / (pns["tn"] + pns["fp"]))
                        else:
                            spec.append(-1)
                        report_pns(pns, data_path, "rx1", THRESHOLD, args.diagonal, args.sample, first,
                                   t_range=t_sliced[i])
                        first = False

                    rx1_axes[0].set_title("Sensitivity, cat class")
                    rx1_axes[0].set_ylim(bottom=0, top=1)
                    rx1_axes[0].set_ylabel("%")
                    rx1_axes[0].bar(time, cats, width=5, align='edge')
                    rx1_axes[1].set_title("Sensitivity, human class")
                    rx1_axes[1].set_ylim(bottom=0, top=1)
                    rx1_axes[1].set_ylabel("%")
                    rx1_axes[1].bar(time, humans, width=5, align='edge')
                    rx1_axes[2].set_title("Sensitivity, all classes")
                    rx1_axes[2].set_ylim(bottom=0, top=1)
                    rx1_axes[2].set_ylabel("%")
                    rx1_axes[2].bar(time, total, width=5, align='edge')
                    rx1_axes[3].set_title("Specificity")
                    rx1_axes[3].set_ylim(bottom=0, top=1)
                    rx1_axes[3].set_xlabel(x_label)
                    rx1_axes[3].set_ylabel("%")
                    rx1_axes[3].bar(time, spec, width=5, align='edge')

                    firsts = {"|": True, "/": True, ".": True, "O": True}
                    hatches = []
                    for action in action_ranges:
                        if firsts[action[1]]:
                            hatches.append(
                                rx1_axes[0].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                             hatch=action[1],
                                             label=action[2], facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx1_axes[1].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                label=action[2], facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx1_axes[2].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                label=action[2], facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx1_axes[3].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                label=action[2], facecolor=(0, 0, 0, 0)))
                            firsts[action[1]] = False
                        else:
                            hatches.append(
                                rx1_axes[0].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx1_axes[1].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx1_axes[2].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx1_axes[3].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                facecolor=(0, 0, 0, 0)))
                    for hatch in hatches:
                        hatch._hatch_color = "black"
                    rx1_axes[0].legend(loc='upper right')

                    # report raw numbers too
                    print("---rx1 means---")
                    print("Sensitivity")
                    cats = [i for i in cats if i != -1]
                    print("cats: " + str(np.mean(cats)))
                    humans = [i for i in humans if i != -1]
                    print("humans: " + str(np.mean(humans)))
                    total = [i for i in total if i != -1]
                    print("total: " + str(np.mean(total)))
                    print("Specificity")
                    spec = [i for i in spec if i != -1]
                    print("spec: " + str(np.mean(spec)))

        # the same thing for all node options
        if rx2 is not None:
            acfs = rx2[:, 1:]

            x_label = "Time (s)"
            try:
                t = rx2[:, 0]
                t = np.array([timestamp - t[0] for timestamp in t])
                xlim = max(t)
            except AttributeError:
                # No timestamp in frame. Likely an IWL entry.
                # Will be moving timestamps to CSIData to account for this.
                t = np.array()
                xlim = acfs.shape[1]

                x_label = "Frame No."

            if not args.weigh:
                _, rx2_axes = plt.subplots(nrows=5, num="rx2")
                for i in range(acfs.shape[1]):
                    rx2_axes[i].set_title("CSI ACFS Thresholded, component " + str(i + 1))
                    rx2_axes[i].set_ylim(bottom=0, top=1)
                    rx2_axes[i].set_xlabel(x_label)
                    rx2_axes[i].set_ylabel("Activity")
                    first = True
                    # for thresh in THRESHOLD_RANGE:
                    thresholded = threshold(acfs[:, i], THRESHOLD)
                    if annotations:
                        pns = count_pns(thresholded, t, data_path + annotations[0], "rx2")
                        report_pns(pns, data_path, "rx2", THRESHOLD, args.diagonal, args.sample, first, i + 1)
                        first = False

                        rx2_axes[i].plot(t, thresholded, label="Thresholded to " + str(THRESHOLD))
                        rx2_axes[i].legend(loc='upper right')
            else:
                first = True
                # for thresh in THRESHOLD_RANGE:
                thresholded = np.empty(acfs.shape)
                for i in range(acfs.shape[1]):
                    thresholded[:, i] = threshold(acfs[:, i], THRESHOLD)

                # cut into 5 second intervals
                indices = [0]
                for i in range(t.shape[0]):
                    if t[i] - t[indices[-1]] >= 5:
                        indices.append(i)
                indices = indices[1:]
                t_sliced = np.split(t, indices)
                thresholded_sliced = np.split(thresholded, indices)

                if annotations:
                    # create action ranges
                    f = open(data_path + annotations[0], 'r')
                    lines = f.readlines()
                    f.close()

                    delays = lines[0].rstrip().split()
                    to_remove = 0
                    for delay in delays:
                        node, _, time = delay.partition(",")
                        if node == "rx2":
                            to_remove = int(time)
                    action_ranges = []
                    for line in lines[1:]:
                        info = line.split()
                        action_class = info[2]
                        x = info[0]
                        length = info[1]
                        text = " ".join(info[6:]).rstrip()
                        if "c" in action_class:
                            if "e1" in text or "e2" in text or "e3" in text:
                                colour = "|"
                                label = "shelf 1"
                            elif "e4" in text or "e5" in text or "e6" in text:
                                colour = "/"
                                label = "shelf 2"
                            elif "e7" in text or "e8" in text or "e9" in text:
                                colour = "."
                                label = "shelf 3"
                        elif "h" in action_class:
                            colour = "O"
                            label = "human"
                        else:
                            colour = "white"
                        if length != "0":
                            action_ranges.append(
                                (np.arange(int(x) - to_remove, int(x) + int(length) - to_remove, 5), colour, label))

                    _, rx2_axes = plt.subplots(nrows=4, num="rx2")
                    cats = []
                    humans = []
                    total = []
                    spec = []
                    time = [item[0] for item in t_sliced]
                    for i in range(len(t_sliced)):
                        pns = count_pns_weighted(thresholded_sliced[i], t_sliced[i], data_path + annotations[0], "rx2")
                        if (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["cs"]["fn"] +
                            pns["cm"]["fn"] + pns["cl"]["fn"]) > 0:
                            cats.append((pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"]) / (
                                    (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"]) + (
                                    pns["cs"]["fn"] + pns["cm"]["fn"] + pns["cl"]["fn"])))
                        else:
                            cats.append(-1)
                        if (pns["h"]["tp"] + pns["h"]["fn"]) > 0:
                            humans.append(pns["h"]["tp"] / (pns["h"]["tp"] + pns["h"]["fn"]))
                        else:
                            humans.append(-1)
                        if (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"] + pns["cs"]["fn"] +
                            pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"]) > 0:
                            total.append((pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) / (
                                    (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) + (
                                    pns["cs"]["fn"] + pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"])))
                        else:
                            total.append(-1)
                        if (pns["tn"] + pns["fp"]) > 0:
                            spec.append(pns["tn"] / (pns["tn"] + pns["fp"]))
                        else:
                            spec.append(-1)
                        report_pns(pns, data_path, "rx2", THRESHOLD, args.diagonal, args.sample, first,
                                   t_range=t_sliced[i])
                        first = False

                    rx2_axes[0].set_title("Sensitivity, cat class")
                    rx2_axes[0].set_ylim(bottom=0, top=1)
                    rx2_axes[0].set_ylabel("%")
                    rx2_axes[0].bar(time, cats, width=5, align='edge')
                    rx2_axes[1].set_title("Sensitivity, human class")
                    rx2_axes[1].set_ylim(bottom=0, top=1)
                    rx2_axes[1].set_ylabel("%")
                    rx2_axes[1].bar(time, humans, width=5, align='edge')
                    rx2_axes[2].set_title("Sensitivity, all classes")
                    rx2_axes[2].set_ylim(bottom=0, top=1)
                    rx2_axes[2].set_ylabel("%")
                    rx2_axes[2].bar(time, total, width=5, align='edge')
                    rx2_axes[3].set_title("Specificity")
                    rx2_axes[3].set_ylim(bottom=0, top=1)
                    rx2_axes[3].set_xlabel(x_label)
                    rx2_axes[3].set_ylabel("%")
                    rx2_axes[3].bar(time, spec, width=5, align='edge')

                    firsts = {"|": True, "/": True, ".": True, "O": True}
                    hatches = []
                    for action in action_ranges:
                        if firsts[action[1]]:
                            hatches.append(
                                rx2_axes[0].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                label=action[2], facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx2_axes[1].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                label=action[2], facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx2_axes[2].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                label=action[2], facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx2_axes[3].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                label=action[2], facecolor=(0, 0, 0, 0)))
                            firsts[action[1]] = False
                        else:
                            hatches.append(
                                rx2_axes[0].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx2_axes[1].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx2_axes[2].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx2_axes[3].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                facecolor=(0, 0, 0, 0)))
                    for hatch in hatches:
                        hatch._hatch_color = "black"
                    rx2_axes[0].legend(loc='upper right')

                    print("---rx2 means---")
                    print("Sensitivity")
                    cats = [i for i in cats if i != -1]
                    print("cats: " + str(np.mean(cats)))
                    humans = [i for i in humans if i != -1]
                    print("humans: " + str(np.mean(humans)))
                    total = [i for i in total if i != -1]
                    print("total: " + str(np.mean(total)))
                    print("Specificity")
                    spec = [i for i in spec if i != -1]
                    print("spec: " + str(np.mean(spec)))

        if rx3 is not None:
            acfs = rx3[:, 1:]

            x_label = "Time (s)"
            try:
                t = rx3[:, 0]
                t = np.array([timestamp - t[0] for timestamp in t])
                xlim = max(t)
            except AttributeError:
                # No timestamp in frame. Likely an IWL entry.
                # Will be moving timestamps to CSIData to account for this.
                t = np.array()
                xlim = acfs.shape[1]

                x_label = "Frame No."

            if not args.weigh:
                _, rx3_axes = plt.subplots(nrows=5, num="rx3")
                for i in range(acfs.shape[1]):
                    rx3_axes[i].set_title("CSI ACFS Thresholded, component " + str(i + 1))
                    rx3_axes[i].set_ylim(bottom=0, top=1)
                    rx3_axes[i].set_xlabel(x_label)
                    rx3_axes[i].set_ylabel("Activity")
                    first = True
                    # for thresh in THRESHOLD_RANGE:
                    thresholded = threshold(acfs[:, i], THRESHOLD)
                    if annotations:
                        pns = count_pns(thresholded, t, data_path + annotations[0], "rx3")
                        report_pns(pns, data_path, "rx3", THRESHOLD, args.diagonal, args.sample, first, i + 1)
                        first = False

                        rx3_axes[i].plot(t, thresholded, label="Thresholded to " + str(THRESHOLD))
                        rx3_axes[i].legend(loc='upper right')
            else:
                first = True
                # for thresh in THRESHOLD_RANGE:
                thresholded = np.empty(acfs.shape)
                for i in range(acfs.shape[1]):
                    thresholded[:, i] = threshold(acfs[:, i], THRESHOLD)

                # cut into 5 second intervals
                indices = [0]
                for i in range(t.shape[0]):
                    if t[i] - t[indices[-1]] >= 5:
                        indices.append(i)
                indices = indices[1:]
                t_sliced = np.split(t, indices)
                thresholded_sliced = np.split(thresholded, indices)

                if annotations:
                    # create action ranges
                    f = open(data_path + annotations[0], 'r')
                    lines = f.readlines()
                    f.close()

                    delays = lines[0].rstrip().split()
                    to_remove = 0
                    for delay in delays:
                        node, _, time = delay.partition(",")
                        if node == "rx3":
                            to_remove = int(time)
                    action_ranges = []
                    for line in lines[1:]:
                        info = line.split()
                        action_class = info[2]
                        x = info[0]
                        length = info[1]
                        text = " ".join(info[6:]).rstrip()
                        if "c" in action_class:
                            if "e1" in text or "e2" in text or "e3" in text:
                                colour = "|"
                                label = "shelf 1"
                            elif "e4" in text or "e5" in text or "e6" in text:
                                colour = "/"
                                label = "shelf 2"
                            elif "e7" in text or "e8" in text or "e9" in text:
                                colour = "."
                                label = "shelf 3"
                        elif "h" in action_class:
                            colour = "O"
                            label = "human"
                        else:
                            colour = "white"
                        if length != "0":
                            action_ranges.append(
                                (np.arange(int(x) - to_remove, int(x) + int(length) - to_remove, 5), colour, label))

                    _, rx3_axes = plt.subplots(nrows=4, num="rx3")
                    cats = []
                    humans = []
                    total = []
                    spec = []
                    time = [item[0] for item in t_sliced]
                    for i in range(len(t_sliced)):
                        pns = count_pns_weighted(thresholded_sliced[i], t_sliced[i], data_path + annotations[0], "rx3")
                        if (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["cs"]["fn"] +
                            pns["cm"]["fn"] + pns["cl"]["fn"]) > 0:
                            cats.append((pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"]) / (
                                    (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"]) + (
                                    pns["cs"]["fn"] + pns["cm"]["fn"] + pns["cl"]["fn"])))
                        else:
                            cats.append(-1)
                        if (pns["h"]["tp"] + pns["h"]["fn"]) > 0:
                            humans.append(pns["h"]["tp"] / (pns["h"]["tp"] + pns["h"]["fn"]))
                        else:
                            humans.append(-1)
                        if (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"] + pns["cs"]["fn"] +
                            pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"]) > 0:
                            total.append((pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) / (
                                    (pns["cs"]["tp"] + pns["cm"]["tp"] + pns["cl"]["tp"] + pns["h"]["tp"]) + (
                                    pns["cs"]["fn"] + pns["cm"]["fn"] + pns["cl"]["fn"] + pns["h"]["fn"])))
                        else:
                            total.append(-1)
                        if (pns["tn"] + pns["fp"]) > 0:
                            spec.append(pns["tn"] / (pns["tn"] + pns["fp"]))
                        else:
                            spec.append(-1)
                        report_pns(pns, data_path, "rx3", THRESHOLD, args.diagonal, args.sample, first,
                                   t_range=t_sliced[i])
                        first = False

                    rx3_axes[0].set_title("Sensitivity, cat")
                    rx3_axes[0].set_ylim(bottom=0, top=1)
                    rx3_axes[0].set_ylabel("%")
                    rx3_axes[0].bar(time, cats, width=5, align='edge')
                    rx3_axes[1].set_title("Sensitivity, human")
                    rx3_axes[1].set_ylim(bottom=0, top=1)
                    rx3_axes[1].set_ylabel("%")
                    rx3_axes[1].bar(time, humans, width=5, align='edge')
                    rx3_axes[2].set_title("Sensitivity, all")
                    rx3_axes[2].set_ylim(bottom=0, top=1)
                    rx3_axes[2].set_ylabel("%")
                    rx3_axes[2].bar(time, total, width=5, align='edge')
                    rx3_axes[3].set_title("Specificity")
                    rx3_axes[3].set_ylim(bottom=0, top=1)
                    rx3_axes[3].set_xlabel(x_label)
                    rx3_axes[3].set_ylabel("%")
                    rx3_axes[3].bar(time, spec, width=5, align='edge')

                    firsts = {"|": True, "/": True, ".": True, "O": True}
                    hatches = []
                    for action in action_ranges:
                        if firsts[action[1]]:
                            hatches.append(
                                rx3_axes[0].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                label=action[2], facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx3_axes[1].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                label=action[2], facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx3_axes[2].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                label=action[2], facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx3_axes[3].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                label=action[2], facecolor=(0, 0, 0, 0)))
                            firsts[action[1]] = False
                        else:
                            hatches.append(
                                rx3_axes[0].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx3_axes[1].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx3_axes[2].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                facecolor=(0, 0, 0, 0)))
                            hatches.append(
                                rx3_axes[3].bar(action[0], np.ones(action[0].shape[0]), width=5, align='edge',
                                                hatch=action[1],
                                                facecolor=(0, 0, 0, 0)))
                    for hatch in hatches:
                        hatch._hatch_color = "black"
                    rx3_axes[0].legend(loc='upper right')

                    print("---rx3 means---")
                    print("Sensitivity")
                    cats = [i for i in cats if i != -1]
                    print("cats: " + str(np.mean(cats)))
                    humans = [i for i in humans if i != -1]
                    print("humans: " + str(np.mean(humans)))
                    total = [i for i in total if i != -1]
                    print("total: " + str(np.mean(total)))
                    print("Specificity")
                    spec = [i for i in spec if i != -1]
                    print("spec: " + str(np.mean(spec)))

    plt.show()


if __name__ == "__main__":
    main()
