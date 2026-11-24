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
