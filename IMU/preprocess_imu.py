import numpy as np
import imufusion
import datetime
import matplotlib.pyplot as plt
from CSIKit.filters.passband import lowpass
from CSIKit.filters.statistical import running_mean
from CSIKit.util.filters import hampel

# get imu data
imu = np.genfromtxt(r"F:\Measurements\Q2\Measurement 9\tx3\imu_data3.csv", delimiter=",", skip_header=1,
                    dtype="unicode") # your datapath here

# get timestamps and convert them into datetime timestamps
timestamps = imu[:, 0]
trimmed_timestamps = []
for timestamp in timestamps:
    trimmed_timestamps.append(
        datetime.datetime(int(timestamp[0:4]), int(timestamp[5:7]), int(timestamp[8:10]), int(timestamp[11:13]),
                          int(timestamp[14:16]), int(timestamp[17:19]),
                          min(int(timestamp[20:]) * 1000, 999999)).timestamp())

trimmed_timestamps = np.array([timestamp - trimmed_timestamps[0] for timestamp in trimmed_timestamps]).astype(float)

# remove repeated samples (this is specifically to handle a bug in the Cpp code that was fixed part way through the experiment, where memory was not cleared properly so packets could be duplicated later in the data)
print("pruning any repeated data lines . . .")
duplicates = np.insert(imu[:, 1:].astype(float), 0, trimmed_timestamps, axis=1)
imu_matrix_time = np.array([list(i) for i in duplicates])
imu_matrix_time_void = np.ascontiguousarray(imu_matrix_time).view(
    np.dtype((np.void, imu_matrix_time.dtype.itemsize * imu_matrix_time.shape[1])))
_, time_idx = np.unique(imu_matrix_time_void, return_index=True)
imu_matrix_time = imu_matrix_time[np.sort(time_idx)]

# in case of crashes, handle time discrepencies caused by crash, or in case of corrupt line in csv, remove said line
print("cleaning up data . . .")
to_delete = []
last_timestamp = imu_matrix_time[0, 0]
first_idx = 0
restart = False
restart_diff = 0
new_start = 0
# for every n
for i in range(1, imu_matrix_time.shape[0]):
    # if this is post restart, add the correct time to fix it
    if restart:
        imu_matrix_time[i, 0] += restart_diff

    # find the difference between n and n-1
    difference = last_timestamp - imu_matrix_time[i, 0]

    # if n-1 > n, something funky happened with restarts/saving
    if difference > 0:
        # if the difference is small, it's a saving mistake
        if difference < 2:
            print("saving error")
            last_timestamp = imu_matrix_time[i, 0]
        # otherwise something bad happened
        else:
            # if we already detected this as a single blip, it can be ignored
            if i - 1 in to_delete:
                print("blip found")
            # if we didn't detect it and it's weirdly lower than everything else, its a blip
            elif i < imu_matrix_time.shape[0] - 1 and imu_matrix_time[i, 0] - imu_matrix_time[i + 1, 0] < -100:
                print("deleting index: " + str(i))
                to_delete.append(i)
            # otherwise this is probably due to a restart and it is not the first this measurement
            elif restart:
                print("restart found at: " + str(i))
                old_diff = restart_diff
                restart_diff += imu_matrix_time[i - 1, 0] - new_start + 2
                new_start = imu_matrix_time[i, 0]
                imu_matrix_time[i, 0] += restart_diff - old_diff
                last_timestamp = imu_matrix_time[i, 0]
            # otherwise this is probably due to a restart and it is the first this measurement
            else:
                print("first restart found at: " + str(i))
                restart = True
                restart_diff = imu_matrix_time[i - 1, 0] - imu_matrix_time[first_idx, 0] + 2
                new_start = imu_matrix_time[i, 0]
                imu_matrix_time[i, 0] += restart_diff
                last_timestamp = imu_matrix_time[i, 0]
    # if n is a lot bigger than n-1 and we are not at the end of the file
    elif difference < -100 and i < imu_matrix_time.shape[0] - 1:
        # if n is also a lot bigger than n+1, this is a weird blip and can be removed
        if imu_matrix_time[i, 0] - imu_matrix_time[i + 1, 0] > 100:
            print("deleting index: " + str(i))
            to_delete.append(i)
        # if n-1 is the start of the file,
        elif last_timestamp == imu_matrix_time[first_idx, 0]:
            print("deleting index: " + str(first_idx))
            to_delete.append(first_idx)
            first_idx += 1
            last_timestamp = imu_matrix_time[i, 0]
        else:
            last_timestamp = imu_matrix_time[i, 0]
    else:
        last_timestamp = imu_matrix_time[i, 0]

# filter frequencies above 10 hz
print("filtering to 10 Hz . . .")
for dim in range(1, 7):
    imu_matrix_time[:, dim] = lowpass(imu_matrix_time[:, dim], 10, 100, 5)
    imu_matrix_time[:, dim] = hampel(imu_matrix_time[:, dim], 10, 3)
    imu_matrix_time[:, dim] = running_mean(imu_matrix_time[:, dim], 10)

imu_matrix_time = np.delete(np.array(imu_matrix_time), to_delete, 0)
imu_matrix_time[:, 0] = np.array([t - imu_matrix_time[0, 0] for t in imu_matrix_time[:, 0]])

# calculate AHRS
print("Calculating AHRS . . .")
offset = imufusion.Offset(100)
ahrs = imufusion.Ahrs()

# initialise AHRS with settings for IMU used
ahrs.settings = imufusion.Settings(
    imufusion.CONVENTION_NWU,  # convention
    0.5,  # gain
    250,  # gyroscope range
    10,  # acceleration rejection
    10,  # magnetic rejection
    5 * 100,  # recovery trigger period = 5 seconds
)

# calculate AHRS
timestamp = imu_matrix_time[:, 0]
gyroscope = imu_matrix_time[:, 4:7]
accelerometer = imu_matrix_time[:, 1:4]

euler = np.empty((len(timestamp) - 1, 3))
initialising_flag = np.empty((len(timestamp) - 1))
for i in range(1, len(timestamp)):
    gyroscope[i] = offset.update(gyroscope[i])
    ahrs.update_no_magnetometer(gyroscope[i], accelerometer[i], timestamp[i] - timestamp[i - 1])
    euler[i - 1] = ahrs.quaternion.to_euler()

    ahrs_flags = ahrs.flags
    initialising_flag[i - 1] = ahrs_flags.initialising

# cut off initialisation period, since it does not contain useful data anyway
print("Removing initialising period . . .")
cutoff = np.argmax(initialising_flag == False)
timestamp = timestamp[cutoff + 1:]
euler = euler[cutoff:, :]

# calculate acfs of euler angles
print("Calculating ACFS . . .")
acfs = []
for i in range(3):
    acf = []
    dim = euler[:, i]
    dim = (dim - dim.min()) / (dim.max() - dim.min())
    for t in range(1, euler.shape[0]):
        a = np.correlate(dim[t - 1:t], dim[t - 1:t], mode='full')
        acf.append(a.item())
    acfs.append(acf)

# save to file
print("Saving data . . .")
acfs = np.array(acfs)
acfs = acfs.transpose()
acfs_time = np.insert(acfs, 0, timestamp[:-1], axis=1)
euler_time = np.insert(euler, 0, timestamp, axis=1)

np.savetxt("./m9/tx3_s3.csv", acfs_time, delimiter=",") # your datapath here
np.savetxt("./m9/tx3_s3_euler.csv", euler_time, delimiter=",") # your datapath here


# plot for fun :)
plt.plot(timestamp, euler[:, 0], "tab:red", label="Roll")
plt.plot(timestamp, euler[:, 1], "tab:green", label="Pitch")
plt.plot(timestamp, euler[:, 2], "tab:blue", label="Yaw")
plt.title("Euler angles")
plt.xlabel("Seconds")
plt.ylabel("Degrees")
plt.grid()
plt.legend()
plt.show()
