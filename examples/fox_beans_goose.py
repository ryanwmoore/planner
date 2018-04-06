from collections import namedtuple
from enum import Enum
from ..operators import *

import networkx as nx


def format_set(the_set):
    if len(the_set) == 0:
        return "nothing"
    else:
        return ', '.join([str(s).replace("FarmersObjects.", "") for s in sorted(the_set, key=lambda o: o.name)])


class FarmersObjects(Enum):
    Fox = 0
    Goose = 1
    BagOfBeans = 2

    def __str__(self):
        return self.name

    def abbreviated(self):
        return self.__str__()[0]


class FarmerLocation(Enum):
    Left = 0
    Right = 1

    def __str__(self):
        return self.name


class BoatAcross(PrimitiveOperator):
    @staticmethod
    def allowed_alone(objects_together):
        goose_and_fox = FarmersObjects.Goose in objects_together and FarmersObjects.Fox in objects_together
        goose_and_beans = FarmersObjects.Goose in objects_together and FarmersObjects.BagOfBeans in objects_together
        return not goose_and_beans and not goose_and_fox

    def can_apply(self, state):
        nearby_shore_contents = state.shore.Left if state.farmer_location == FarmerLocation.Left else state.shore.Right
        return len(state.farmer_objects) <= 1 and self.allowed_alone(nearby_shore_contents)

    def apply(self, state):
        copy = state.copy()
        if copy.farmer_location == FarmerLocation.Left:
            copy.farmer_location = FarmerLocation.Right
            description = "boat to the right shore"
        else:
            copy.farmer_location = FarmerLocation.Left
            description = "boat to the left shore"
        yield copy, description


class PickUp(PrimitiveOperator):
    def __init__(self, *targets):
        self.targets = frozenset(targets)

    def can_apply(self, state):
        nearby_shore_contents = state.shore.Left if state.farmer_location == FarmerLocation.Left else state.shore.Right
        return nearby_shore_contents.intersection(self.targets) == self.targets

    def apply(self, state):
        copy = state.copy()
        if state.farmer_location == FarmerLocation.Left:
            copy.shore = copy.shore._replace(
                Left=copy.shore.Left.difference(self.targets))
            copy.farmer_objects = copy.farmer_objects.union(self.targets)
            yield copy, "pickup {o}".format(o=format_set(self.targets))
        else:
            copy.shore = copy.shore._replace(
                Right=copy.shore.Right.difference(self.targets))
            copy.farmer_objects = copy.farmer_objects.union(self.targets)
            yield copy, "pickup {o}".format(o=format_set(self.targets))


class Drop(PrimitiveOperator):
    def __init__(self, *targets):
        self.targets = frozenset(targets)

    def can_apply(self, state):
        return state.farmer_objects.intersection(self.targets) == self.targets

    def apply(self, state):
        copy = state.copy()
        if state.farmer_location == FarmerLocation.Left:
            copy.shore = copy.shore._replace(
                Left=copy.shore.Left.union(self.targets))
            copy.farmer_objects = copy.farmer_objects.difference(self.targets)
            yield copy, "drop {o}".format(o=format_set(self.targets))
        else:
            copy.shore = copy.shore._replace(
                Right=copy.shore.Right.union(self.targets))
            copy.farmer_objects = copy.farmer_objects.difference(self.targets)
            yield copy, "drop {o}".format(o=format_set(self.targets))


class WorldState(State):
    def __str__(self):
        farmer_location = "L" if self.farmer_location == FarmerLocation.Left else "R"
        if len(self.farmer_objects) > 0:
            farmer_objects = " w/" + \
                "".join([o.abbreviated() for o in self.farmer_objects])
        else:
            farmer_objects = ""

        state = ""
        for o in FarmersObjects:
            if o in self.shore.Left:
                state = state + o.abbreviated().lower()
            elif o in self.shore.Right:
                state = state + o.abbreviated().upper()

        return self.prefix_with_visit_marker("{state} {farmer_location}{farmer_objects}".format(
            farmer_location=farmer_location,
            farmer_objects=farmer_objects,
            state=state))


if __name__ == "__main__":
    Shore = namedtuple("Shore", ["Left", "Right"])

    start_state = WorldState()
    start_state.farmer_objects = frozenset()
    start_state.shore = Shore(Left=frozenset([FarmersObjects.Fox, FarmersObjects.BagOfBeans, FarmersObjects.Goose]),
                              Right=frozenset())
    start_state.farmer_location = FarmerLocation.Left

    end_state = WorldState()
    end_state.shore = Shore(Left=frozenset(),
                            Right=frozenset([FarmersObjects.Goose, FarmersObjects.Fox, FarmersObjects.BagOfBeans]))
    end_state.farmer_objects = frozenset()
    end_state.farmer_location = FarmerLocation.Right

    operators = [BoatAcross()]
    for o in FarmersObjects:
        operators.append(PickUp(o))
        operators.append(Drop(o))

    planner = Planner(start_state, operators, end_state,
                      BreadthFirstSearchStrategy())

    print("Start state:", start_state)
    print("Trying to reach:", end_state)

    graph = nx.DiGraph()
    result = planner.plan(graph)
    Helpers.write_dot(graph, "fox-beans-goose.dot")

    if result is not None:
        print("Solved it in {steps} steps: {solution}".format(
            steps=planner.steps, solution=result.description))
    else:
        print("No result found")
