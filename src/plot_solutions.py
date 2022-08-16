import argparse, csv, json, os

import matplotlib.pyplot as plt
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--path', help='path of source dir for log files', required=True)
args = parser.parse_known_args()[0]

PATH = args.path
FIG_SIZE = (8, 8)

BITRATES_DEFAULT = [570, 1050, 2150, 4600, 9000, 20000]
BITRATES_LIVE = [314, 336, 402, 429, 515, 550, 663, 708, 759, 811, 863, 922, 983, 1049, 1121, 1197, 1281, 1368,
                 1468, 1568, 1645, 1757, 1879, 2006, 2155, 2301, 2481, 2650, 2869, 3064, 3350, 3577, 3861, 4124,
                 4691, 5009, 5488, 5861, 6466, 6906, 7768, 8296, 9429, 10069, 11636, 12320, 14214, 15180, 20000]


def find_runs_without_optimal_solution():
    for _, _, files in os.walk(PATH):
        files.sort()
        for file in files:
            if file.endswith('.json'):
                with open(PATH + '/' + file) as f:
                    data = f.read()
                obj = json.loads(json.loads(data))['SolutionInfo']
                runtime = float(obj['Runtime'])
                if float(obj['Runtime']) > 3580:
                    print(file)


def writeResult(solution, results, trace, version, run):
    if version == 'fewReps':
        results[trace][1][run] = solution
    if version == 'veryfewReps':
        results[trace][0][run] = solution
    if version == 'manyReps':
        results[trace][2][run] = solution
    print('some')


def pretty_print(results):
    s = [[str(e) for e in row] for row in results]
    lens = [max(map(len, col)) for col in zip(*s)]
    fmt = '\t'.join('{{:{}}}'.format(x) for x in lens)
    table = [fmt.format(*row) for row in s]
    print('\n'.join(table))


def get_obj_val():
    results = ''
    version = ''
    for _, _, files in os.walk(PATH):
        files.sort()
        for file in files:
            if file.endswith('.json'):
                with open(PATH + '/' + file) as f:
                    data = f.read()
                obj = json.loads(json.loads(data))['SolutionInfo']
                if version != file.split('_')[0]:
                    if results != '':
                        avg_bus = sum(results[0]) // 10
                        avg_tram = sum(results[1]) // 10
                        print('\n' + version + '\navg_bus: ' + str(avg_bus) + '\navg_tram: ' + str(avg_tram))
                        pretty_print(results)
                    results = [[0 for x in range(10)] for x in range(2)]
                    version = file.split('_')[0]

                run = int(file.split('_')[4])
                if 'bus' in file:
                    results[0][run] = int(float(obj['ObjVal']))
                if 'tram' in file:
                    results[1][run] = int(float(obj['ObjVal']))

        avg_bus = sum(results[0]) // 10
        avg_tram = sum(results[1]) // 10
        print('\n' + version + '\navg_bus: ' + str(avg_bus) + '\navg_tram: ' + str(avg_tram))
        pretty_print(results)


def read_y_file():
    for _, _, files in os.walk(PATH):
        for file in files:
            if file.endswith('_y.csv'):
                title = file.replace('.csv', '')
                data = list(csv.reader(open(PATH + '/' + file), delimiter=';'))[2:]

                segments = [0] * 183

                for line in data:
                    line = line[1:-1]
                    i = 0
                    for value in line:
                        segments[i] += int(value)
                        i = i + 1

                time = 168
                total = 0

                for segment in range(time):
                    total = total + segments[segment]

                print(title + ' ' + str(total))


def plot_ilp_comparison():
    solutions = []
    for _, _, files in os.walk(PATH):
        for file in files:
            if file.endswith('.json') and 'fewReps' not in file and 'manyReps' not in file:
                representation_count = int(file.replace('.csv', '').split('_')[1])
                solution_info = json.load(open(PATH + '/' + file))['SolutionInfo']
                solution = float(solution_info['ObjVal'])
                solutions.append((representation_count, solution))

    x = []
    y = []
    for solution in solutions:
        x.append(solution[0])
        y.append(solution[1])

    plt.figure(figsize=FIG_SIZE)
    axes = plt.gca()
    axes.set_xticks(np.arange(0, 51, 5))
    axes.plot(x, y, 'o', color='k', label='total bandwidth volume')
    plt.show()


# plots bandwidth graph for quality level, one graph per file in path.
def plot_ql_playback():
    for _, _, files in os.walk(PATH):
        for file in files:
            if file.endswith('x.csv'):
                title = file.replace('.csv', '')
                data = list(csv.reader(open(PATH + '/' + file), delimiter=';'))
                data.pop(0)
                time_stamps = []
                levels = []

                i = 1
                for l in data:
                    time_stamps.append((i - 1) * 4 + 0.00001)
                    time_stamps.append(i * 4)
                    if 'manyReps' in file:
                        levels.append(BITRATES_LIVE[int(l[1]) - 1])
                        levels.append(BITRATES_LIVE[int(l[1]) - 1])
                    else:
                        levels.append(BITRATES_DEFAULT[int(l[1]) - 1])
                        levels.append(BITRATES_DEFAULT[int(l[1]) - 1])
                    i += 1

                plt.figure(figsize=(9, 2))
                plt.title(title)
                axes = plt.gca()
                axes.set_xlim(0, 801)
                axes.set_ylim([0, 20200])
                axes.set_ylabel('representation bitrate')
                axes.plot(time_stamps, levels, color='tab:red', label='quality levels playback')
                plt.savefig(PATH + '-' + title + '.png', bbox_inches='tight', dpi=150)
                plt.clf()
                plt.close()


def plot_ql_playback_multiple():
    levels_many = []
    levels_few = []
    levels_simFew = []
    levels_simMany = []
    time_stamps = []
    for i in range(1, 184):
        time_stamps.append((i - 1) * 4 + 0.00001)
        time_stamps.append(i * 4)
    for _, _, files in os.walk(PATH):
        for file in files:
            if file.endswith('x.csv'):
                title = file.replace('.csv', '')
                data = list(csv.reader(open(PATH + '/' + file), delimiter=';'))
                data.pop(0)

                i = 1
                for l in data:
                    if 'manyReps' in file:
                        levels_many.append(BITRATES_LIVE[int(l[1]) - 1])
                        levels_many.append(BITRATES_LIVE[int(l[1]) - 1])
                    if 'fewReps' in file:
                        levels_few.append(BITRATES_DEFAULT[int(l[1]) - 1])
                        levels_few.append(BITRATES_DEFAULT[int(l[1]) - 1])
                    i += 1
            if file.endswith('.json'):
                with open(PATH + '/' + file) as json_file:
                    title = file.replace('.json', '')
                    data = json.load(json_file)

                    i = 1
                    for l in data:
                        if l['segmentIndex'] is not None:
                            if 'avc_live_predictive' in file:
                                levels_simMany.append(BITRATES_LIVE[int(l['segmentQualityLevel']) - 1])
                                levels_simMany.append(BITRATES_LIVE[int(l['segmentQualityLevel']) - 1])
                            if 'avc-playlist' in file:
                                levels_simFew.append(BITRATES_DEFAULT[int(l['segmentQualityLevel']) - 1])
                                levels_simFew.append(BITRATES_DEFAULT[int(l['segmentQualityLevel']) - 1])
                            i += 1

    fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(9, 6))

    axes[0].set_xlim(0, 732)
    axes[0].set_ylim([0, 20200])
    axes[0].set_ylabel('representation bitrate')
    axes[0].title.set_text('fewReps')
    axes[0].plot(time_stamps, levels_few, color='tab:cyan', linewidth=1.2, label='ILP')
    axes[0].plot(time_stamps, levels_simFew, color='tab:red', linewidth=1.2, label='prototype')
    axes[0].legend()

    axes[1].set_xlim(0, 732)
    axes[1].set_ylim([0, 20200])
    axes[1].set_ylabel('representation bitrate')
    axes[1].title.set_text('manyReps')
    axes[1].plot(time_stamps, levels_many, color='tab:cyan', linewidth=1.2, label='ILP')
    axes[1].plot(time_stamps, levels_simMany, color='tab:red', linewidth=1.2, label='prototype')
    axes[1].legend()

    if 'bus_0003' in title:
        trace = 'bus_0003'
    else:
        trace = 'tram_0002'
    plt.suptitle(trace)
    plt.savefig(PATH + '-' + trace + '.png', bbox_inches='tight', dpi=150)
    plt.clf()
    plt.close()


if __name__ == "__main__":
    # plot_ql_playback()
    get_obj_val()
    # find_runs_without_optimal_solution()
    print('done')
