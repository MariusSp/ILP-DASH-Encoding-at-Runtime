## Integer Linear Program for DASH encoding at Runtime

This project contains a Linear Integer Programm (ILP) calculating the optimal bandwidth usage for Dynamic
Adaptive Streaming over HTTP (DASH) for Video content. It utilizes the `Gurobi Optimizer` framework.

The overreaching objective for the ILP is to calculate and maximize the download volume of a DASH stream. Hereby we want
to stay as close as possible to a real DASH setup. For this reason a few rules must be followed:

1. The maximum network throughput for given network trace cannot be exceeded at any point in time.
2. Every segment of the video needs to be downloaded exactly once.
3. The download of a segment can only start when the download of the previous segment is completed.
4. Each segment has a playback deadline. Because of this, stalling cannot occur and the download of a segment must be
   completed before its deadline.
5. In reality there is a (maximum) video buffer size, dictating how much video for future playback can be downloaded. In
   the ILP the buffer size limits how much earlier a segment can be downloaded before its playback deadline.

### Mathematical Description:

![ILP](src/resources/ILP.png)

To facilitate understanding, we capitalized constants or pre-defined values. i, j, and s denote indices for variables.
The ILP targets to maximize the downloaded volume of a video, which is divided into N segments of duration D. Each
segment is available in R representation levels. B is the size of the client’s buffer. T0 is the initial delay, marking
the playback deadline for the first segment. Si,j contains for all segments i ∈ N the sizes for all representations j ∈
R. The function V (t) represents the volume of the network trace from the beginning until point in time t. In addition
to the constants, there are the following variables that must be assigned when solving the ILP: xi,j indicates if the
client downloads representation j of segment i
(x = 1) or not (x = 0). yi,s indicates the used bandwidth volume for each segment i in time section s.

Note that we refer to a unit of time as time section. It would be obvious to use the SI base unit second as a unit of
time, as the network traces are given in bytes per second. However, to reduce the size and complexity of the ILP, we
pool the duration of a segment, 4s together to a time section, as it is the largest common divisor for the problem at
hand. D is 4s long and the buffer size B is 20s time sections long. The i-th segment has to be ready at time section s,
which is T0 + (i − 1) · D. It follows, B is five time sections long, i.e., the download of a segment can begin earliest
five sections before its playback deadline.

Finally, bi and ei mark the begin and end of time sections, in which the downloads of segment i begins and finishes.
Now, the optimization problem of downloading the largest amount of video data while not exceeding the limitations for a
given network trace can be framed.

The Problem maximizes the accumulated size for all downloaded video representations for all segments, see Equation (3.1)
. The first constraint in Equation (3.2) limits the amount of representations downloaded per segment to 1. Constraint (
3.3) makes sure the cumulated size of downloaded segments up to segment s is smaller than the cumulated trace’s
bandwidth volume until time section s, i.e., all segments must be completely downloaded before their respective playback
deadlines. Constraint (3.4) ensures that the amount of downloaded segments for each time section s is less or equal than
the trace’s bandwidth volume. Obviously, multiple consecutive segments can share the network bandwidth in a time
section. Constraint (3.5) prohibits a segment being downloaded before it can be added to the buffer, i.e., a segment can
be downloaded at the earliest 30 seconds before its playback deadline. Constraint (3.6) prevents a segment being
downloaded after its playback deadline. Thus, Constraints (3.5) and (3.6) make sure that a segment download can only
take place right before its playback deadline in a time window of the length of the buffer size. Constraint (3.7)
assures that the size of actual downloaded bytes of a segment is equal to the bits of the downloaded representation,
i.e., all bytes of a segment are downloaded. Constraint (3.8) ensures that the begin of a segment download is before or
in the same time section as its completion. Constraint
(3.9) checks that the completion of a segment download is before or in the same time section as the begin of the next
segment’s download. While it is trivial for a human to determine begin and end of the download of a segment – they are
the first and last sections of yi,s not being zero – the optimizer requires an additional variable and constrains which
expose the mentioned points in time to the ILP. Variable wi,s shows, if segment i is downloaded in time section s (w = 1) or not (w = 0).

![ILP](src/resources/ILP2.png)

Constraint (3.10) fills wi,s for each segment i at time section s with 0, if yi,s = 0, or 1 if yi,s > 0. This is done by
yi,s is being less or equal to wi,s multiplied with a positive constant, the M parameter, which is larger than the
biggest value y can attain. This approach is called big-M method, which introduces the artificial variable M to
calculate wi,s from an inequality with yi,s. Gurobi Optimizer, the solver we selected to implement this ILP, advises to
choose M parameters as small as possible. Therefore, we set M for each y separately with (P k=1 N yk,s + 1) for each
time section s. To set ei to the point in time the download of segment s completes, i.e., the last time section at least
one byte gets downloaded, we multiply wi,s with an index vector IV = [1, 2, . . . , N ]T . The maximum of the resulting
vector is the time section of ei , as shown in Constraint (3.11). This is possible because Gurobi Optimizer offers a
method to obtain the maximum value of a vector. As we require the smallest value/index larger than zero for bi , the
inverted vector was subtracted from its size, as shown by (3.12).
