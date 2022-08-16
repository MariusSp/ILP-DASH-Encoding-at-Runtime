import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--path', help='path of source dir for m4s files')
args = parser.parse_known_args()[0]

PATH = args.path

BW_MIN = 314000  # in bits
BW_MAX = 20000000  # in bits
SEGMENT_COUNT = 183
SEGMENT_DURATION = 4  # in seconds


def write_exponential_file(representation_count):
    output_file = open(str(representation_count) + '.csv', "w")
    if representation_count >= 2:
        interval = (BW_MAX - BW_MIN) / (representation_count - 1)
        for i in range(0, representation_count):
            bw = (BW_MIN + interval * i) * SEGMENT_DURATION / 8
            for j in range(1, SEGMENT_COUNT + 1):
                output_file.write("%d;%d;%d\n" % (j, i, bw))
    else:
        bw = (BW_MAX - BW_MIN) / 2 * SEGMENT_DURATION / 8
        for j in range(1, SEGMENT_COUNT + 1):
            output_file.write("%d;%d;%d\n" % (j, 0, bw))


def write_file2(representation_count, reps):
    output_file = open('input_0' + '.csv', "w")
    for i in range(0, len(reps)):
        for j in range(1, SEGMENT_COUNT + 1):
            output_file.write("%d;%d;%d\n" % (j, i, reps[i]))
    output_file.close()

    for i in range(representation_count):
        representations_new = []
        # representations_new.append(BW_MIN + reps[0] / 2)
        representations_new.append(reps[0])
        for j in range(1, len(reps)):
            representations_new.append((reps[j] + reps[j - 1]) / 2)
            representations_new.append(reps[j])
        # representations_new.append((BW_MAX + reps[len(reps) - 1]) / 2)
        reps = representations_new

        output_file = open('input_' + str(i + 1) + '.csv', "w")
        for i in range(0, len(reps)):
            for j in range(1, SEGMENT_COUNT + 1):
                output_file.write("%d;%d;%d\n" % (j, i, reps[i]))


def m4s_to_input():
    VERSION = 'manyReps'
    output_file = open('input_' + VERSION + '.csv', 'w')

    MANYREPS = {
        '314k': 0, '336k': 1, '402k': 2, '429k': 3, '515k': 4, '570k': 5, '663k': 6, '708k': 7, '759k': 8, '811k': 9,
        '863k': 10, '922k': 11, '983k': 12, '1050k': 13, '1121k': 14, '1197k': 15, '1281k': 16, '1368k': 17
        , '1468k': 18, '1568k': 19, '1645k': 20, '1757k': 21, '1879k': 22, '2006k': 23, '2150k': 24, '2301k': 25,
        '2481k': 26, '2650k': 27, '2869k': 28, '3064k': 29, '3350k': 30, '3577k': 31, '3861k': 32, '4124k': 33
        , '4600k': 34, '5009k': 35, '5488k': 36, '5861k': 37, '6466k': 38, '6906k': 39, '7768k': 40, '8296k': 41,
        '9000k': 42, '10069k': 43, '11536k': 44, '12320k': 45, '14214k': 46, '15180k': 47, '20000k': 48}
    FEWREPS = {'570k': 0, '1050k': 1, '2150k': 2, '4600k': 3, '9000k': 4, '20000k': 5, }
    rep_names = MANYREPS
    if VERSION == 'fewReps':
        rep_names = FEWREPS

    for filename in sorted(os.listdir(PATH)):
        if filename.endswith('.m4s'):
            size = os.path.getsize(PATH + filename)
            representation_id = str(rep_names[filename.split('_')[2]])
            segment_id = filename.split('_')[3].replace('dash', '').replace('.m4s', '')
            output_file.write(segment_id + ';' + representation_id + ';' + str(size) + '\n')
            continue
        # output_file.write(str(os.path.getsize(filename)))
        else:
            continue


if __name__ == "__main__":
    write_exponential_file(2)
    write_exponential_file(3)
    write_exponential_file(5)
    write_exponential_file(9)
    write_exponential_file(17)
    write_exponential_file(33)
    write_exponential_file(65)

    # write_file2(6, [BW_MIN, BW_MAX])  # [(BW_MIN + BW_MAX) / 2])

    # m4s_to_input()
