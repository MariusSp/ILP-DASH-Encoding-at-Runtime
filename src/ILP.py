import argparse
import csv
import json
import os
import time
from multiprocessing import Pool

import gurobipy as gp

parser = argparse.ArgumentParser()
parser.add_argument('--path', help='directory of input log files', required=True)
parser.add_argument('--trace', help='directory of traces', required=True)
parser.add_argument('--threads', default=1, help='how many to run in parallel', required=False)
parser.add_argument('--tune', dest='tune', action='store_true')
parser.set_defaults(tune=False)
args = parser.parse_known_args()[0]

TUNE = args.tune
SEGMENT_COUNT = 183
INITIAL_DELAY = 4  # in seconds
SEGMENT_LENGTH = 4  # in seconds
BUFFER_SIZE = 20  # in seconds
BUFFER_SIZE_IN_SEGMENTS = (BUFFER_SIZE + (SEGMENT_LENGTH - 1)) // SEGMENT_LENGTH  # 8*4=32 this is the way DASH does it.
TRACE_PATH = args.trace
PATH = args.path
THREADS = int(args.threads)


def min_section(i):
    if i + 1 < BUFFER_SIZE_IN_SEGMENTS:
        return 0
    else:
        return i - (BUFFER_SIZE_IN_SEGMENTS - 1)


def save_stats(input_file, representation_count, m, x, y, w, z, video_size, trace_name, bandwidth_per_trace_section):
    output_dir = PATH + '/output/'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_name = output_dir + str(BUFFER_SIZE) + 's_' + input_file.replace('.csv', '') + '_' \
                  + trace_name
    print('Solution found! (optimal: %s)\n' % (m.status == gp.GRB.Status.OPTIMAL))

    # write total solution value to file
    output_file = open(output_name + '_info.json', 'w')
    json.dump(m.getJSONSolution(), output_file)
    # output_file.write(m.getJSONSolution())
    output_file.close()

    # write solution value of x to file
    # write header line
    output_file = open(output_name + '_x.csv', 'w')
    output_file.write('segment;representation;size;\n')
    # write data
    for i in range(SEGMENT_COUNT):
        output_file.write('s%03d;' % (i + 1))
        for j in range(representation_count):
            if round(x[i][j].X) == 1:
                stri = '%02d;%05d'
                output_file.write(stri % (j + 1, video_size[i][j]))
        output_file.write('\n')
    output_file.close()

    # write y data to file
    # write header line
    output_file = open(output_name + '_y.csv', 'w')
    output_file.write('segment;')
    for j in range(SEGMENT_COUNT):
        output_file.write('%d;' % j)
    output_file.write('\n----;')
    for j in range(SEGMENT_COUNT):
        output_file.write('%08d;' % bandwidth_per_trace_section[j])
    output_file.write('\n')
    # write data
    for i in range(SEGMENT_COUNT):
        output_file.write('s%03d;' % (i + 1))
        for j in range(SEGMENT_COUNT):
            stri = '%08d;'
            output_file.write(stri % round(y[i][j].X))
        output_file.write('\n')
    output_file.close()

    # write w data to file
    # write header line
    output_file = open(output_name + '_w.csv', 'w')
    output_file.write('segment;')
    for j in range(SEGMENT_COUNT):
        output_file.write('%d;' % j)
    output_file.write('\n')
    # write data
    for i in range(SEGMENT_COUNT):
        output_file.write('s%03d;' % (i + 1))
        for j in range(SEGMENT_COUNT):
            stri = '%01d;'
            output_file.write(stri % round(w[i][j].X))
        output_file.write('\n')
    output_file.close()

    # write z data to file
    # write header line
    output_file = open(output_name + '_z.csv', 'w')
    output_file.write('segment;z_s;z_e;\n')
    # write data
    for i in range(SEGMENT_COUNT):
        output_file.write('s%03d;' % (i + 1))
        stri = '%03d;'
        output_file.write(stri % (183 - round(z[i][0].X)))
        output_file.write(stri % round(z[i][1].X))
        output_file.write('\n')
    output_file.close()


def array_creation(trace):
    bandwidth_until_segment = [0] * SEGMENT_COUNT
    bandwidth_segment = [0] * SEGMENT_COUNT
    # i = 0
    for i in range(0, INITIAL_DELAY):
        bandwidth_until_segment[0] += trace[i]
        bandwidth_segment[0] += trace[i]
    for s in range(1, SEGMENT_COUNT):
        tmp = 0
        for i in range(s * SEGMENT_LENGTH, (s + 1) * SEGMENT_LENGTH):
            tmp += trace[i]
        bandwidth_until_segment[s] = bandwidth_until_segment[s - 1] + tmp
        bandwidth_segment[s] = tmp

    print('trace has {} Bytes volume ({})'.format(int(bandwidth_until_segment[-1]), int(sum(trace))))

    bandwidth_per_trace_section = [0] * SEGMENT_COUNT
    # tmp = 0
    for i in range(INITIAL_DELAY):
        bandwidth_per_trace_section[0] += trace[i]

    for i in range(0, SEGMENT_COUNT - 1):
        for k in range(SEGMENT_LENGTH):
            bandwidth_per_trace_section[i + 1] += trace[INITIAL_DELAY + i * SEGMENT_LENGTH + k]

    return bandwidth_until_segment, bandwidth_per_trace_section


def ilp(input_file, trace_name, trace):
    bandwidth_until_segment, bandwidth_per_trace_section = array_creation(trace)
    print(input_file, trace_name)
    video_data = list(csv.reader(open(PATH + '/' + input_file), delimiter=';'))
    representation_count = int(len(video_data) / SEGMENT_COUNT)

    # read and process sizes of [segment,representation] in kilobytes
    video_size = {}
    for i in range(SEGMENT_COUNT):
        video_size[i] = [0] * representation_count
    video_data = [list(map(int, row)) for row in video_data]
    for row in video_data:
        video_size[row[0] - 1][row[1]] = row[2]

    m = gp.Model('mip1')

    # VAR (1) representation per segments
    x = []
    for i in range(SEGMENT_COUNT):
        x.append([0] * representation_count)
        for s in range(representation_count):
            x[i][s] = m.addVar(vtype=gp.GRB.BINARY)

    # VAR (2) used bandwidth volume per trace section for each segment
    # e.g. segment5 was downloaded. It occupied 10kb of the available BW in trace-section2, 50kb in trace-section3,...
    y = []
    for i in range(SEGMENT_COUNT):
        y.append([0] * SEGMENT_COUNT)
        for s in range(SEGMENT_COUNT):
            y[i][s] = m.addVar(vtype=gp.GRB.INTEGER, lb=0, ub=bandwidth_per_trace_section[s])

    # VAR (3) point in time of download_start and download_end of segment
    z = []
    for i in range(SEGMENT_COUNT):
        z.append([0] * 2)
        z[i][0] = m.addVar(vtype=gp.GRB.INTEGER, lb=183 - i, ub=183 - min_section(i))
        z[i][1] = m.addVar(vtype=gp.GRB.INTEGER, lb=min_section(i), ub=i)

    # VAR (4) denotes if segment i got downloaded at time s (1, otherwise 0)
    w = []
    for i in range(SEGMENT_COUNT):
        w.append([0] * SEGMENT_COUNT)
        for s in range(SEGMENT_COUNT):
            w[i][s] = m.addVar(vtype=gp.GRB.BINARY)

    # CONSTR (1) max one representation per segment
    for i in range(SEGMENT_COUNT):
        m.addConstr(gp.quicksum(x[i]) == 1)

    # CONSTR (2) download must finish before (planned) segment playback time
    for s in range(SEGMENT_COUNT):
        m.addConstr(gp.quicksum(video_size[i][j] * x[i][j] for i in range(s + 1)
                                for j in range(representation_count)) <= bandwidth_until_segment[s])

    # CONSTR (3) in every trace section in total there can only be downloaded as much as the network trace allows for
    for s in range(SEGMENT_COUNT):
        m.addConstr(gp.quicksum(y[i][s] for i in range(SEGMENT_COUNT)) <= bandwidth_per_trace_section[s])

    # CONSTR (4) no download outside of the sections in the buffer window for each segment
    for i in range(SEGMENT_COUNT):
        for s in range(0, i - BUFFER_SIZE_IN_SEGMENTS + 1):
            m.addConstr(y[i][s] == 0)
        for s in range(i + 1, SEGMENT_COUNT):
            m.addConstr(y[i][s] == 0)

    # CONSTR (5) the representation of a segment must be downloaded in sections from its according buffer window
    for i in range(SEGMENT_COUNT):
        m.addConstr(gp.quicksum(y[i][s] for s in range(min_section(i), i + 1)) ==
                    gp.quicksum(x[i][j] * video_size[i][j] for j in range(representation_count)))

    # CONSTR (6) point in time of the download_start of next segment must be after download_end of the last segment
    for i in range(1, SEGMENT_COUNT):
        m.addConstr(183 - z[i][0] >= z[i - 1][1])
        m.addConstr(183 - z[i][0] <= z[i][1])

    # CONSTR (7) w=0 if y=0, otherwise w=1
    for i in range(SEGMENT_COUNT):
        for s in range(SEGMENT_COUNT):
            m.addConstr(y[i][s] <= (bandwidth_per_trace_section[s] + 1) * w[i][s])

    # aux represents w * index vector, e.g {0,1}*{1,...,183}
    aux = []
    for i in range(SEGMENT_COUNT):
        aux.append([0] * SEGMENT_COUNT)
    for i in range(SEGMENT_COUNT):
        for s in range(SEGMENT_COUNT):
            aux[i][s] = m.addVar(vtype=gp.GRB.INTEGER)
            m.addConstr(aux[i][s] == w[i][s] * s)

    # aux2 represents w * index vector in reversed order
    # as min_() would return 0 from any of the unused cells with value 0
    aux2 = []
    for i in range(SEGMENT_COUNT):
        aux2.append([0] * SEGMENT_COUNT)
    for i in range(SEGMENT_COUNT):
        for s in range(SEGMENT_COUNT):
            aux2[i][s] = m.addVar(vtype=gp.GRB.INTEGER)
            m.addConstr(aux2[i][s] == w[i][s] * (SEGMENT_COUNT - s))

    # CONSTR (8) z_e, z_s constrained by w (max_(aux))
    # max_ returns largest value in aux, which represents each index in aux, e.g. 50 at index 50, 51 at index 51,...
    for i in range(SEGMENT_COUNT):
        m.addConstr(z[i][0] == gp.max_(aux2[i]))  # min_ doesnt work because would always result in min=0
        m.addConstr(z[i][1] == gp.max_(aux[i]))

    # Objective: maximize bandwidth_per_second of used representations
    obj = gp.quicksum(video_size[i][j] * x[i][j] for i in range(SEGMENT_COUNT) for j in range(representation_count))

    # parameters selected by gurobi.tune()
    if TUNE:
        print('using TUNING PARAMETERS')
        # tuning parameters - tram_0002,2.csv
        m.Params.Cuts = 0
        m.Params.Method = 0
        m.Params.RINS = 0

    m.Params.TimeLimit = 3600
    m.setObjective(obj, gp.GRB.MAXIMIZE)
    m.optimize()
    # m.printStats()

    # m.Params.TuneTimeLimit = 122400
    # m.tune()

    if m.status == gp.GRB.Status.OPTIMAL or m.status == gp.GRB.Status.TIME_LIMIT:
        save_stats(input_file, representation_count, m, x, y, w, z, video_size, trace_name, bandwidth_per_trace_section)


def main():
    # read files
    t0 = time.time()
    input_files = []
    for file in os.listdir(PATH):
        if file.endswith('.csv'):
            input_files.append(file)

    # read and process volume per second in kilobytes
    traces = {}
    for root, _, files in os.walk(TRACE_PATH):
        files.sort()
        for file in files:
            bandwidth_per_second = []
            with open(root + '/' + file) as f:
                for line in f:
                    bandwidth_per_second.append(int(line.replace('\n', '')))

            bandwidth_per_second.extend(bandwidth_per_second)
            bandwidth_per_second = bandwidth_per_second[:(SEGMENT_COUNT - 1) * 4 + INITIAL_DELAY]
            traces[file.replace('.txt', '')] = bandwidth_per_second
            print(file, sum(bandwidth_per_second))

    if THREADS > 1:
        # run in parallel
        print('\n\nrunning parallel with %d threads\n\n' % THREADS)
        with Pool(processes=THREADS) as pool:
            multiple_results = [pool.apply_async(ilp, (file, trace_name, trace))
                                for trace_name, trace in traces.items()
                                for file in input_files]
            print([res.get() for res in multiple_results])
    else:
        # run sequential
        for trace_name, trace in traces.items():
            for file in input_files:
                ilp(file, trace_name, trace)

    t1 = time.time()
    total = t1 - t0
    print('total runtime: ' + str(total))


if __name__ == "__main__":
    main()
