import copy
import json
import logging

log = logging.getLogger(__name__)

class State(object):
    def filter_control_fields(self, target=None):
        if target is None:
            target = copy.copy(self.__dict__)
        if '__visitmarker' in target:
            del target['__visitmarker']
        if '__isfrozen' in target:
            del target['__isfrozen']
        if '__frozencontents' in target:
            del target['__frozencontents']
        return target

    def __eq__(self, other):
        if isinstance(other, State):
            return self.filter_control_fields() == other.filter_control_fields()
        raise NotImplementedError()

    def __setattr__(self, key, value):
        if self.is_frozen() and key != '__visitmarker' and key != '__dict__':
            raise AttributeError("Cannot set {key} to \"{value}\" on already frozen State {state}".format(key=key, value=value, state=str(self)))
        self.__dict__[key] = value

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        try:
            result = str(json.dumps(self.filter_control_fields(), sort_keys=True))
            if self.has_visit_marker():
                return "{marker}: {result}".format(marker=self.get_visit_marker(), result=result)
            else:
                return result

        except TypeError:
            return str(self.__dict__)

    def copy(self):
        the_copy = copy.deepcopy(self)
        the_copy.filter_control_fields(the_copy.__dict__)
        return the_copy

    def freeze(self):
        if not self.is_frozen():
            contents_without_visit_marker = self.filter_control_fields()
            setattr(self, '__frozencontents', str(self.__dict__))
            setattr(self, '__isfrozen', True)

    def is_frozen(self):
        return hasattr(self, '__isfrozen') and getattr(self, '__isfrozen')

    def set_visit_marker(self, value):
        self.__dict__['__visitmarker'] = value

    def has_visit_marker(self):
        return '__visitmarker' in self.__dict__

    def get_visit_marker(self):
        return self.__dict__['__visitmarker']

    def __hash__(self):
        self.freeze()
        return getattr(self, '__frozencontents').__hash__()

class EndState(State):
    """There's two ways to use this class:

    1. Set fields manually. Any state must be exactly equal to this one in order to stop the planning process.
    2. Override __eq__: This let's the end state have dynamic/complex behavior
    """


class Operator(object):
    def can_apply(self, state):
        raise NotImplementedError()

    def apply(self, state):
        raise NotImplementedError()


class PrimitiveOperator(Operator):
    pass


class CompoundOperator(Operator):
    pass


class SearchStrategy(object):
    def addState(self, state):
        raise NotImplementedError("this is an abstract base class: Use one of the classes that inherit from this one")

    def popNextState(self, state):
        raise NotImplementedError("this is an abstract base class: Use one of the classes that inherit from this one")


class BreadthFirstSearchStrategy(SearchStrategy):
    def __init__(self):
        self.queue = []

    def addState(self, state):
        self.queue.append(state)

    def popNextState(self, state):
        return self.queue.pop(0)


class DepthFirstSearchStrategy(SearchStrategy):
    def __init__(self):
        self.stack = []

    def addState(self, state):
        self.stack.append(state)

    def popNextState(self, state):
        return self.stack.pop()


class Planner(object):
    def __init__(self, state, operators, endState, description=[]):
        if not isinstance(state, State):
            raise TypeError("Not a valid State: {state}".format(state=state))
        self.state = state

        if not all(isinstance(o, Operator) for o in operators):
            raise TypeError("Not all Operators are valid: {operators}".format(operators=operators))
        self.operators = list(operators)

        if not isinstance(endState, EndState):
            raise TypeError("Not a valid EndState: {endState}".format(endState=endState))
        self.endState = endState

        self.description = description

    def __str__(self):
        return "Planner({state}, {operators}, {endState})".format(state=str(self.state), operators=self.operators,
                                                                  endState=self.endState)

    def __repr__(self):
        return str(self)

    def _apply(self, queue, description):
        for s, description in self._makeNextStates():
            yield Planner(s, self.operators, self.endState, self.description + [description])

    def _makeNextStates(self):
        for operator in self.operators:
            if isinstance(operator, CompoundOperator):
                raise ValueError("I didn't code compound operators yet!")
            if operator.can_apply(self.state):
                for nextState, description in operator.apply(self.state):
                    nextState.freeze()
                    yield nextState, description

    def plan(self, graph=None):
        self.steps = 0
        queue = [self]
        seen_states = set()
        graph.add_node(self.state)

        while len(queue):
            newQueueStates = []

            for q in queue:
                if q.state not in seen_states:
                    self.steps = self.steps + 1
                    q.state.set_visit_marker("Step {steps}".format(steps=self.steps))
                    seen_states.add(q.state)


                if graph is not None:
                    graph.add_node(q.state)

                if self.endState == q.state:
                    return q

                for new_planner in q._apply(newQueueStates, self.description):
                    newQueueStates.append(new_planner)
                    if graph is not None:
                        action = new_planner.description[-1]
                        graph.add_edge(q.state, new_planner.state, label=action)

            queue.clear()
            for q in newQueueStates:
                queue.append(q)

        return None

class Helpers(object):
    @staticmethod
    def write_dot(graph, output):
        import networkx
        relabel_assignments = {}
        for node in graph.nodes():
            relabel_assignments[node] = '"{label}"'.format(label=str(node).replace('"', '\\"'))
            log.debug("{before} becomes {after}".format(before=node, after=relabel_assignments[node]))
        copied_graph = networkx.relabel_nodes(graph, relabel_assignments, copy=True)
        networkx.drawing.nx_pydot.write_dot(copied_graph, output)
