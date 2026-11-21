*This project has been created as part of the 42 curriculum by lrain.*

## Description

## Instructions

## Algorithm and Implementation Strategy

### Route planning

#### The problem
<!-- many drones, start -> end, capacities, minimize turns; why
     "everyone takes the shortest path" fails -->

#### The map as a graph: nodes and arcs
<!-- zones = nodes, connections = arcs, one arc per direction -->

#### Splitting zones in two
<!-- z_in -> z_out arc carries the zone's max_drones -->

#### Capacity
<!-- max drones an arc can carry; zone vs connection capacity -->

#### Cost
<!-- turns to enter a zone (restricted = 2), priority as tie-break -->

#### Flow
<!-- how many lanes use each arc; the plan is just these counts -->

#### Flow in = flow out
<!-- conservation rule at every zone except start and end -->

#### From flow to lanes
<!-- reading the counts back as routes; why the walk never gets stuck -->

#### Shortest paths: Dijkstra
<!-- cheapest route, priority queue, why it needs costs >= 0 -->

#### Residual capacity and twin arcs
<!-- room left = cap - flow; twin = "send one fewer drone back there" -->

#### Undoing earlier choices
<!-- the trap example (A-B shortcut); twin taken -> lanes swap halves -->

#### Negative costs and Johnson potentials
<!-- twins cost -c; potentials h shift costs to >= 0, same shortest route -->

#### Why the result is the cheapest
<!-- residual graph = every possible edit; cheapest iff no negative cycle;
     augmenting along a shortest path keeps it that way -->

#### The algorithm step by step
<!-- successive shortest paths: search, augment, split, score, repeat;
     stopping conditions -->

#### How many lanes to use
<!-- greedy drone assignment, turns = max(L + n - 1), keep best k -->

#### Why cheapest also means fastest
<!-- drones by turn T = k(T+1) - total length; flows over time -->

#### Why drones never fly head-on
<!-- opposing flow can always be cancelled for a cheaper plan -->

#### Complexity
<!-- one Dijkstra per lane: O(k * E log V), k <= nb_drones -->

### Simulation design

#### Network

Holds zones,
connections
and drones,
tracks state.
`network.py` file holds connection definition
since connections are exclusively in it.

#### Design Decisions

##### Frozen locations vs locations tracking drones

##### Network hashmap: drone key vs. location key

### Algorithm
#### Why undo opposite flows?

## Visual Representation

## Example Input and Expected Output

## Resources
