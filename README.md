# Planner

This is an AI Planner that I worked fiddled with/worked on. It's mostly
complete, though didn't turn like I had hoped. I don't plan to continue working
on it/finishing it.

Requires networkx. Developed with PyCharm. Uses Dot/Graphviz to render state
graphs.

## Examples

A version of the [https://en.wikipedia.org/wiki/Fox,_goose_and_bag_of_beans_puzzle](Fox, Goose, and Bag of Beans Puzzle) is included.

```
$ python --version
Python 3.5.2
$ python example_fox_beans_goose.py
Start state: fgb L
Trying to reach: FGB R
Added: 1: fgb L
...
Added: 52: F R w/GB
Solved it in 52 steps: ['pickup Goose', 'boat to the right shore', 'drop Goose', 'boat to the left shore', 'pickup Fox', 'boat to the right shore', 'drop Fox', 'pickup Goose', 'boat to the left shore', 'drop Goose', 'pickup BagOfBeans', 'boat to the right shore', 'drop BagOfBeans', 'boat to the left shore', 'pickup Goose', 'boat to the right shore', 'drop Goose']
$ make fox_beans_goose.png
```

![Fox Beans Goose state graph](fox-beans-goose.png?raw=true "Fox Beans Goose state graph")

## Things that I'd like to Improve

1. A\* graph search + heuristics
2. Graph statistics (e.g., number of nodes explored, times a node was
   revisited)
3. A cleaner State implementation. To know whether a state is visited more than
   once, it's necessary to keep a set of previously visited states. Therefore,
   those old state objects must be immutable once they're put into the visited
   set. The implementation is a bit awkward, though the test coverage is good
   enough.
4. Educational tools. E.g., compare BFS vs DFS, compare A\* heuristics
