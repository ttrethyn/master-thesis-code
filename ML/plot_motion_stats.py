import numpy as np
import matplotlib.pyplot as plt
import os
import argparse

def report_pns(counts, path, sample, shelf, first):
    """
        Report pns counts to a file for easy retrieval
        :param counts: the dictionary of pns counts
        :param path: the path to save to, string
        :param sample: which sample within a measurement this applies to (e.g. m9 s2), number
        :param first: whether this should overwrite the previous contents of the file or add to it, bool
        :return: nothing
        """
    fname = path + "s" + sample + "_log.txt"
    if first:
        mode = "w"
    else:
        mode = "a"
    with open(fname, mode) as f:
        print("---shelf " + shelf + "---", file=f)
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
        print("activity total", file=f)
        if (counts["cs"]["tp"] + counts["cm"]["tp"] + counts["cl"]["tp"] + counts["cs"]["fn"] + counts["cm"]["fn"] +
                counts["cl"]["fn"]) > 0:
            sensitivity = (counts["cs"]["tp"] + counts["cm"]["tp"] + counts["cl"]["tp"]) / (counts["cs"]["tp"] +
                counts["cm"]["tp"] + counts["cl"]["tp"] + counts["cs"]["fn"] + counts["cm"]["fn"] + counts["cl"]["fn"])
            print("Sensitivity: " + str(sensitivity), file=f)
        else:
            print("No labels present", file=f)
        if (counts["tn"] + counts["fp"]) > 0:
            specificity = counts["tn"] / (counts["tn"] + counts["fp"])
            print("\n".join("{0} {1}".format(k, v) for k, v in counts.items() if k[0] != "c"), file=f)
            print("Specificity: " + str(specificity), file=f)
        else:
            print("No unlabeled data present", file=f)

def count_pns(time, data, actions, start):
    """
        count positives and negatives within array
        :param time: an array of length thresh_data, containing time information for each sample
        :param data: the array of data
        :param actions: the action ranges present in this data
        :param start: the start time
        :return: a dictionary of counts for tp, fn, fp and tn, by class
        """

    # define dict of counts
    pn_counts = {"cs": {"tp": 0, "fn": 0}, "cm": {"tp": 0, "fn": 0}, "cl": {"tp": 0, "fn": 0},
                 "fp": 0, "tn": 0}

    # define threshold
    thresh = 0.1

    # loop through data and count tn, fn, tp and fp
    found = False
    for i in range(np.where(time == start)[0][0], data.shape[1]):
        if not (data[:, i] > 1).any():
            for action in actions:
                if action[0][0] <= time[i] <= action[0][-1]:
                    found = True
                    if (data[:, i] > thresh).any():
                        pn_counts[action[3]]["tp"] += 1
                    else:
                        pn_counts[action[3]]["fn"] += 1
        if not found:
            if (data[:, i] > thresh).any() and not (data[:, i] > 1).any():
                pn_counts["fp"] += 1
            else:
                pn_counts["tn"] += 1
        found = False

    return pn_counts

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
    parser.add_argument('measurement', type=str, help='The measurement number, m3/m4/m9')
    parser.add_argument('model', type=str, help='The model size, s/m')
    parser.add_argument('sample', type=str, help='The sample number, 1-n')
    args = parser.parse_args()

    # construct datapath from args and get files from said datapath
    data_path = "./motion_stats/" + args.measurement + "/"
    files = os.listdir(data_path)
    annotations = [f for f in files if f[0] == "s" and f[1] == args.sample and f[-3:] == "txt"]
    motion_files = [f for f in files if f[0] == "s" and f[1] == args.sample and f[-5] == args.model and f[-3:] == "csv"]

    # read motion data
    sh1 = None
    sh2 = None
    sh3 = None
    for file in motion_files:
        if "sh1" in file:
            sh1 = np.genfromtxt(data_path + file, delimiter=",")
            for i in range(sh1.shape[0]):
                mean = np.mean(sh1[i, :])
                sh1[i, :] = sh1[i, :] - mean
            sh1[sh1 < 0] = 0
            print(sh1.shape)
        elif "sh2" in file:
            sh2 = np.genfromtxt(data_path + file, delimiter=",")
            for i in range(sh2.shape[0]):
                mean = np.mean(sh2[i, :])
                sh2[i, :] = sh2[i, :] - mean
            sh2[sh2 < 0] = 0
            print(sh2.shape)
        elif "sh3" in file:
            sh3 = np.genfromtxt(data_path + file, delimiter=",")
            for i in range(sh3.shape[0]):
                mean = np.mean(sh3[i, :])
                sh3[i, :] = sh3[i, :] - mean
            sh3[sh3 < 0] = 0
            print(sh3.shape)
        else:
            pass

    # read annotations
    f = open(data_path + annotations[0], 'r')

    lines = f.readlines()
    f.close()

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
        if length != "0" and "c" in action_class:
            if args.measurement == "m9" and args.sample == 1:
                action_ranges.append((np.arange(int(x) + 30, int(x) + int(length) + 30, 1 / 10), colour, label, action_class))
            else:
                action_ranges.append((np.arange(int(x), int(x) + int(length), 1/10), colour, label, action_class))
        if "experimenter present" in text:
            if args.measurement == "m9" and args.sample == 1:
                start_time = int(x) + int(length) + 30
            else:
                start_time = int(x) + int(length)

    # construct time arrays
    if sh1 is not None:
        t = np.arange(0, sh1.shape[1])/10
    elif sh2 is not None:
        t = np.arange(0, sh2.shape[1])/10
    else:
        t = np.arange(0, sh3.shape[1])/10

    # plot
    _, axes = plt.subplots()
    axes.set_title("Motion")
    axes.set_xlabel("Time (s)")
    axes.set_ylabel("Motionness")
    sh1_pns = None
    sh2_pns = None
    sh3_pns = None
    # if sh1 is not None:
    #     for cat in sh1:
    #         axes.plot(t, cat, color="blue", label="shelf 1")
    #     sh1_pns = count_pns(t, sh1, [a for a in action_ranges if a[2] == "shelf 1"], start_time)
    if sh2 is not None:
        for cat in sh2:
            axes.plot(t, cat, color="yellow", label="shelf 2")
        sh2_pns = count_pns(t, sh2, [a for a in action_ranges if a[2] == "shelf 2"], start_time)
    # if sh3 is not None:
    #     for cat in sh3:
    #         axes.plot(t, cat, color="red", label="shelf 3")
    #     sh3_pns = count_pns(t, sh3, [a for a in action_ranges if a[2] == "shelf 3"], start_time)

    firsts = {"|": True, "/": True, ".": True, "O": True}
    hatches = []
    for action in [a for a in action_ranges if a[2] == "shelf 2"]:
        if firsts[action[1]]:
            hatches.append(
                axes.bar(action[0], np.ones(action[0].shape[0]), width=1/10, align='edge', hatch=action[1],
                             label=action[2], facecolor=(0, 0, 0, 0)))
            firsts[action[1]] = False
        else:
            hatches.append(
                axes.bar(action[0], np.ones(action[0].shape[0]), width=1/10, align='edge', hatch=action[1],
                             facecolor=(0, 0, 0, 0)))
    for hatch in hatches:
        hatch._hatch_color = "black"
    axes.legend(loc='upper right')

    annotate(data_path + annotations[0], axes)

    plt.show()

    # report pns
    # if sh1_pns is not None:
    #     report_pns(sh1_pns, data_path, args.sample, "sh1", True)
    if sh2_pns is not None:
        report_pns(sh2_pns, data_path, args.sample, "sh2", True)
    # if sh3_pns is not None:
    #     report_pns(sh3_pns, data_path, args.sample, "sh3", False)

if __name__ == "__main__":
    main()

