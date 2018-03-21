import copy
import json


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
        return str(self)

    def __str__(self):
        try:
            return str(json.dumps(self.filter_control_fields(), sort_keys=True))
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


class Planner(object):
    def __init__(self, state, operators, endState, description=[]):
        if not isinstance(state, State):
            raise ValueError("Not a valid State: {state}".format(state=state))
        self.state = state

        if not all(isinstance(o, Operator) for o in operators):
            raise ValueError("Not all Operators are valid: {operators}".format(operators=operators))
        self.operators = list(operators)

        if not isinstance(endState, EndState):
            raise ValueError("Not a valid EndState: {endState}".format(endState=endState))
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
        graph.add_node(self.state)

        while len(queue):
            newQueueStates = []

            for q in queue:
                self.steps = self.steps + 1

                if graph is not None:
                    graph.add_node(q.state.copy())
                    # Look it up in the graph even though we just inserted it, so that we have reference to the copy in the graph
                    n = graph.node[q.state]
                    if not n.has_visit_marker():
                        n.set_visit_marker("{steps}".format(steps=self.steps))

                if self.endState == q.state:
                    return q

                for new_planner in q._apply(newQueueStates, self.description):
                    newQueueStates.append(new_planner)
                    if graph is not None:
                        source_state = copy.deepcopy(q.state)
                        source_state.freeze()
                        dest_state = copy.deepcopy(new_planner.state)
                        dest_state.freeze()
                        action = new_planner.description[-1]
                        graph.add_edge(source_state, dest_state, label=action)

            queue.clear()
            for q in newQueueStates:
                queue.append(q)

        return None

class Helpers(object):
    @staticmethod
    def write_dot(graph, output):
        import networkx
        copied_graph = graph.copy()
        relabel_assignments = {}
        for node in copied_graph.nodes():
            relabel_assignments[node] = '"{label}"'.format(label=str(node))
        copied_graph = networkx.relabel_nodes(copied_graph, relabel_assignments)
        networkx.drawing.nx_pydot.write_dot(copied_graph, output)
