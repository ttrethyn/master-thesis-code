from CSIKit.filters.passband import lowpass
from CSIKit.filters.statistical import running_mean
from CSIKit.util.filters import hampel

from CSIKit.reader import CSVBeamformReader
from CSIKit.util import csitools

import numpy as np
import matplotlib.pyplot as plt

# read raw csv file
print("reading file . . .")
my_reader = CSVBeamformReader()
csi_data = my_reader.read_file(r"F:\Measurements\Q2\Measurement 9\rx1\s1\csi_data_n01.csv") # specify path to data here
csi_matrix, no_frames, no_subcarriers = csitools.get_CSI(csi_data, metric="amplitude", extract_as_dBm=False)


# select first (and in this case only) antenna pair
csi_matrix_first = csi_matrix[:, :, 0, 0]

# remove singleton dimensions
csi_matrix_squeezed = np.squeeze(csi_matrix_first)

# remove subcarriers without information (any that are all zero)
print("removing empty subcarriers . . .")
csi_matrix_lltf = csi_matrix_squeezed[:, :60]
idx = np.argwhere(np.all(csi_matrix_lltf[..., :] == 0, axis=0))
csi_matrix_pruned = np.delete(csi_matrix_lltf, idx, axis=1)

# remove repeated packets (this is specifically to handle a bug in the Cpp code that was fixed part way through the experiment, where memory was not cleared properly so packets could be duplicated later in the data)
print("pruning any repeated packets . . .")
timestamps = np.array(csi_data.timestamps)
duplicates = np.insert(csi_matrix_pruned, 0, timestamps, axis=1)
csi_matrix_time = np.array([list(i) for i in duplicates])
csi_matrix_time_void = np.ascontiguousarray(csi_matrix_time).view(np.dtype((np.void, csi_matrix_time.dtype.itemsize * csi_matrix_time.shape[1])))
_, time_idx = np.unique(csi_matrix_time_void, return_index=True)
csi_matrix_time = csi_matrix_time[np.sort(time_idx)]

# in case of crashes, handle time discrepencies caused by crash, or in case of corrupt line in csv, remove said line
print("cleaning up data . . .")
to_delete = []
last_timestamp = csi_matrix_time[0, 0]
first_idx = 0
restart = False
restart_diff = 0
new_start = 0
# for every n
for i in range(1, csi_matrix_time.shape[0]):
    # if this is post restart, add the correct time to fix it
    if restart:
        csi_matrix_time[i, 0] += restart_diff

    # find the difference between n and n-1
    difference = last_timestamp - csi_matrix_time[i, 0]

    # if n-1 > n, something funky happened with restarts/saving
    if difference > 0:
        # if the difference is small, it's a saving mistake
        if difference < 2:
            print("saving error")
            last_timestamp = csi_matrix_time[i, 0]
        # otherwise something bad happened
        else:
            # if we already detected this as a single blip, it can be ignored
            if i - 1 in to_delete:
                print("blip found")
            # if we didn't detect it and it's weirdly lower than everything else, its a blip
            elif i < csi_matrix_time.shape[0] - 1 and csi_matrix_time[i, 0] - csi_matrix_time[i+1, 0] < -100:
                print("deleting index: " + str(i))
                to_delete.append(i)
            # otherwise this is probably due to a restart and it is not the first this measurement
            elif restart:
                print("restart found at: " + str(i))
                old_diff = restart_diff
                restart_diff += csi_matrix_time[i-1, 0] - new_start + 2
                new_start = csi_matrix_time[i, 0]
                csi_matrix_time[i, 0] += restart_diff - old_diff
                last_timestamp = csi_matrix_time[i, 0]
            # otherwise this is probably due to a restart and it is the first this measurement
            else:
                print("first restart found at: " + str(i))
                restart = True
                restart_diff = csi_matrix_time[i - 1, 0] - csi_matrix_time[first_idx, 0] + 2
                new_start = csi_matrix_time[i, 0]
                csi_matrix_time[i, 0] += restart_diff
                last_timestamp = csi_matrix_time[i, 0]
    # if n is a lot bigger than n-1 and we are not at the end of the file
    elif difference < -100 and i < csi_matrix_time.shape[0] - 1:
        # if n is also a lot bigger than n+1, this is a weird blip and can be removed
        if csi_matrix_time[i, 0] - csi_matrix_time[i+1, 0] > 100:
            print("deleting index: " + str(i))
            to_delete.append(i)
        # if n-1 is the start of the file,
        elif last_timestamp == csi_matrix_time[first_idx, 0]:
            print("deleting index: " + str(first_idx))
            to_delete.append(first_idx)
            first_idx += 1
            last_timestamp = csi_matrix_time[i, 0]
        else:
            last_timestamp = csi_matrix_time[i, 0]
    else:
        last_timestamp = csi_matrix_time[i, 0]

csi_matrix_time = np.delete(np.array(csi_matrix_time), to_delete, 0)
csi_matrix_pruned = csi_matrix_time[:, 1:]

print("Performing Principal Component Analysis . . .")
# remove constant offset
mean = np.mean(csi_matrix_pruned, axis=0)
std_dev = np.std(csi_matrix_pruned, axis=0)
csi_matrix_std = (csi_matrix_pruned - mean) / std_dev
H = csi_matrix_std[:100, :]

cov_matrix = (1/csi_matrix_std.shape[1]) * (H.T @ H)

values, vectors = np.linalg.eig(cov_matrix)
sorted_indices = np.argsort(values)[::-1]
values_sorted = values[sorted_indices]
vectors_sorted = vectors[:,sorted_indices]

pca_components = vectors_sorted[:, 1:6]
csi_matrix_projected = np.dot(csi_matrix_std, pca_components)

# filter frequencies above 10 hz
print("filtering to 10 Hz . . .")
for component in range(csi_matrix_projected.shape[1]):
    csi_matrix_projected[:, component] = lowpass(csi_matrix_projected[:, component], 10, 100, 5)
    csi_matrix_projected[:, component] = hampel(csi_matrix_projected[:, component], 10, 3)
    csi_matrix_projected[:, component] = running_mean(csi_matrix_projected[:, component], 10)

# calculate acfs
acfs = []
for f in range(csi_matrix_projected.shape[1]):
    acf = []
    freq = csi_matrix_projected[:, f]
    freq = (freq - freq.min()) / (freq.max() - freq.min())
    for t in range(1, csi_matrix_projected.shape[0]):
        a = np.correlate(freq[t-1:t], freq[t-1:t], mode='full')
        acf.append(a.item())
    acfs.append(acf)

# save data
acfs = np.array(acfs)
acfs = acfs.transpose()
acfs_time = np.insert(acfs, 0, csi_matrix_time[:-1, 0], axis=1)

# insert name of destination file here
np.savetxt("./m9/rx1_s1_n1_lltf.csv", acfs_time, delimiter=",")

# plot for fun
t = acfs_time[:, 0]

plt.title("acf")
plt.xlabel("samples")
plt.ylabel("motion")
for subcarrier in acfs.T:
    plt.plot(t, subcarrier)
plt.show()
