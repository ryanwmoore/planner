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
