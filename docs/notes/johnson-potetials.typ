= Johnson potentials

$
  w'(u,v) = w(u,v) + h(u) - h(v)
$

where:
  - $w'()$ is the *new weight* between the two nodes passed
  - $w()$ is the *old weight* between the two nodes passed
  - *weights* are the numbers on the edges, ```python arc.cost```
  - $h()$ is the potential to a node
  - *potential* is the cheapest path to a node from the source
  - $x$ is the starting node
  - $y$ is the end node

== Why the shortest path stays the same

Due to additions being undone along a path
every path says the same in overall cost.

Add up $w'$ along a path $x -> a -> b -> y$:

$
     & w'(x,a) + w'(a,b) + w'(b,y) \
  =  & w(x,a) + h(x) - cancel(h(a)) \
  "" + & w(a,b) + cancel(h(a)) - cancel(h(b)) \
  "" + & w(b,y) + cancel(h(b)) - h(y) \
  =  & w(x,a) + w(a,b) + w(b,y) + h(x) - h(y)
$

- every inner $h$ shows up once with $+$ and once with $-$, so they cancel
- only $h(x) - h(y)$ is left over
- every path from $x$ to $y$ gets shifted by that same amount
- ranking of paths doesn't change: the cheapest path with $w'$ is
  the cheapest path with $w$

