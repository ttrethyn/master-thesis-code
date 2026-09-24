import numpy as np
from scipy import signal
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import os
from sklearn.metrics import classification_report, ConfusionMatrixDisplay, confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight, compute_class_weight
from sklearn import preprocessing


def split(all_time, local_time, acfs, decimation_factor=5):
    # decimate data
    acfs = signal.decimate(acfs, decimation_factor, axis=0)
    local_time = local_time[::decimation_factor]

    return local_time, acfs


data_path = "./m9/"
files = os.listdir(data_path)

data = [None, None, None]
classes = [None, None, None]

for i in range(3):
    annotations = [f for f in files if f[0] == "s" and f[1] == str(i + 1)]
    csi_files = [f for f in files if f[0] == "r" and f[5] == str(i + 1) and f[-3:] == "csv"]
    csi_files = [f for f in csi_files if (f[2] == f[8]) or (abs(int(f[2]) - int(f[8])) == 2)]

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
            end_time = None
            if "skip" in text:
                end_time = int(x)
            if "c" in action_class:
                if "e1" in text or "e2" in text or "e3" in text:
                    label = "1"
                elif "e4" in text or "e5" in text or "e6" in text:
                    label = "2"
                elif "e7" in text or "e8" in text or "e9" in text:
                    label = "3"
                # label = "a"
            elif "h" in action_class:
                label = "h"
                # label = "a"
            if length != "0":
                action_ranges.append(((int(x), int(x) + int(length)), label))

    # create universal time stream for all pairs
    rx1_t = rx1[:, 0]
    rx1_t = np.array([timestamp - rx1_t[0] for timestamp in rx1_t])
    rx2_t = rx2[:, 0]
    rx2_t = np.array([timestamp - rx2_t[0] for timestamp in rx2_t])
    rx3_t = rx3[:, 0]
    rx3_t = np.array([timestamp - rx3_t[0] for timestamp in rx3_t])
    rx1_d_t = rx1_d[:, 0]
    rx1_d_t = np.array([timestamp - rx1_d_t[0] for timestamp in rx1_d_t])
    rx3_d_t = rx3_d[:, 0]
    rx3_d_t = np.array([timestamp - rx3_d_t[0] for timestamp in rx3_d_t])

    delays = lines[0].rstrip().split()
    t_min = []
    t_max = 0
    for delay in delays:
        node, _, time = delay.partition(",")
        if eval(node) is not None:
            if node == "rx1":
                rx1_t += int(time)
                t_max = max(t_max, max(rx1_t))
                rx1_d_t += int(time)
                t_max = max(t_max, max(rx1_d_t))
            elif node == "rx2":
                rx2_t += int(time)
                t_max = max(t_max, max(rx2_t))
            elif node == "rx3":
                rx3_t += int(time)
                t_max = max(t_max, max(rx3_t))
                rx3_d_t += int(time)
                t_max = max(t_max, max(rx3_d_t))
            t_min.append(int(time))
    t_min = min(t_min)

    t_global = np.arange(t_min, t_max, 1)

    if end_time is not None:
        rx1 = rx1[np.where(rx1_t <= end_time)]
        rx1_t = rx1_t[np.where(rx1_t <= end_time)]
        rx2 = rx2[np.where(rx2_t <= end_time)]
        rx2_t = rx2_t[np.where(rx2_t <= end_time)]
        rx3 = rx3[np.where(rx3_t <= end_time)]
        rx3_t = rx3_t[np.where(rx3_t <= end_time)]
        rx1_d = rx1_d[np.where(rx1_d_t <= end_time)]
        rx1_d_t = rx1_d_t[np.where(rx1_d_t <= end_time)]
        rx3_d = rx3_d[np.where(rx3_d_t <= end_time)]
        rx3_d_t = rx3_d_t[np.where(rx3_d_t <= end_time)]
        t_global = t_global[np.where(t_global <= end_time)]

    # split and decimate everything
    rx1_t_sliced, rx1_acfs_sliced = split(t_global, rx1_t, rx1[:, 1:])
    rx2_t_sliced, rx2_acfs_sliced = split(t_global, rx2_t, rx2[:, 1:])
    rx3_t_sliced, rx3_acfs_sliced = split(t_global, rx3_t, rx3[:, 1:])
    rx1_d_t_sliced, rx1_d_acfs_sliced = split(t_global, rx1_d_t, rx1_d[:, 1:])
    rx3_d_t_sliced, rx3_d_acfs_sliced = split(t_global, rx3_d_t, rx3_d[:, 1:])

    # data structure for this: X (n_samples, n_features) and y being class labels (n_samples)
    # construct data and class labels for input to SVM
    data[i] = np.zeros((max([rx1_acfs_sliced.shape[0], rx2_acfs_sliced.shape[0], rx3_acfs_sliced.shape[0],
                             rx1_d_acfs_sliced.shape[0], rx3_d_acfs_sliced.shape[0]]), 25))
    classes[i] = np.full((max([rx1_acfs_sliced.shape[0], rx2_acfs_sliced.shape[0], rx3_acfs_sliced.shape[0],
                               rx1_d_acfs_sliced.shape[0], rx3_d_acfs_sliced.shape[0]])), "-")

    counts = {"1": 0, "2": 0, "3": 0, "h": 0, "-": 0}
    # counts = {"a": 0, "-": 0}

    j = 0
    for t in t_global:
        if t in rx1_t_sliced:
            section = rx1_acfs_sliced[np.where(rx1_t_sliced == t)]
            k = j
            for sample in section:
                data[i][k][0:5] = sample
                k += 1
        if t in rx2_t_sliced:
            section = rx2_acfs_sliced[np.where(rx2_t_sliced == t)]
            k = j
            for sample in section:
                data[i][k][5:10] = sample
                k += 1
        if t in rx3_t_sliced:
            section = rx3_acfs_sliced[np.where(rx3_t_sliced == t)]
            k = j
            for sample in section:
                data[i][k][10:15] = sample
                k += 1
        if t in rx1_d_t_sliced:
            section = rx1_d_acfs_sliced[np.where(rx1_d_t_sliced == t)]
            k = j
            for sample in section:
                data[i][k][15:20] = sample
                k += 1
        if t in rx3_d_t_sliced:
            section = rx3_d_acfs_sliced[np.where(rx3_d_t_sliced == t)]
            k = j
            for sample in section:
                data[i][k][20:] = sample
                k += 1
        for action_range in action_ranges:
            if t >= action_range[0][0] and t <= action_range[0][1]:
                classes[i][j] = action_range[1]
                counts[action_range[1]] += 1
                # counts["a"] += 1
            else:
                counts["-"] += 1
        j += 1

print("Preprocessing . . . ")
all_data = np.concatenate((data[0], data[1]), axis=0)
all_classes = np.concatenate((classes[0], classes[1]), axis=0)
all_data = np.concatenate((data[0], data[2]), axis=0)
all_classes = np.concatenate((classes[0], classes[2]), axis=0)
scaler = preprocessing.StandardScaler().fit(all_data)
all_data = scaler.transform(all_data)
training_data, test_data, training_classes, test_classes = train_test_split(all_data, all_classes, random_state=104, test_size=0.3, shuffle=True)
print(training_classes.shape)
print(test_classes.shape)
# test_data = data[1]
# test_classes = classes[1]
np.savetxt("./test_data.csv", test_data, delimiter=",")
np.savetxt("./test_classes.csv", test_classes, delimiter=",", fmt="%s")
training_weights = compute_sample_weight(class_weight="balanced", y=training_classes)
class_weights = compute_class_weight(class_weight="balanced", classes=np.unique(all_classes), y=training_classes)
class_weights = dict(zip(np.unique(all_classes), class_weights))
test_weights = compute_sample_weight(class_weight=class_weights, y=test_classes)


print("Training . . .")
# logistic_regression = LogisticRegression(max_iter=1000)
svm = SVC()
# tree = DecisionTreeClassifier()
# logistic_regression.fit(training_data, training_classes, training_weights)
svm.fit(training_data, training_classes, training_weights)
# tree.fit(training_data, training_classes, training_weights)
# joblib.dump(clf, "./model.pkl")

# log_reg_preds = logistic_regression.predict(test_data)
svm_preds = svm.predict(test_data)
# tree_preds = tree.predict(test_data)

model_preds = {
    # "Logistic Regression": log_reg_preds,
    "Support Vector Machine": svm_preds,
    # "Decision Tree": tree_preds
}

for model, preds in model_preds.items():
    print(f"{model} Results:\n{classification_report(test_classes, preds)}", sep="\n\n")
    ConfusionMatrixDisplay.from_predictions(test_classes, preds, sample_weight=test_weights)
    stats = confusion_matrix(test_classes, preds).ravel()
    tn = stats[0]
    fn = stats[1] + stats[2] + stats[3] + stats[4]
    tp = stats[6] + stats[12] + stats[18] + stats[24]
    fp = stats[5] + stats[7] + stats[8] + stats[9] + stats[10] + stats[11] + stats[13] + stats[14] + stats[15] + stats[16] + stats[17] + stats[19] + stats[20] + stats[21] + stats[22] + stats[23]
    specificity = tn / (tn + fp)
    sensitivity = tp / (tp + fn)
    print("Sensitivity: " + str(sensitivity))
    print("Specificity: " + str(specificity))
    plt.show()
