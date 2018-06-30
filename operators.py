import copy
import json
import logging

from collections import deque

log = logging.getLogger(__name__)


class State(object):
    def filter_control_fields(self, target=None):
        if target is None:
            target = copy.copy(self.__dict__)
        if '__visitmarker' in target:
            del target['__visitmarker']
        if '__isfrozen' in target:
            del target['__isfrozen']
        if '__hash_value' in target:
            del target['__hash_value']
        return target

    def prefix_with_visit_marker(self, string):
        if self.has_visit_marker():
            return "{prefix}: {string}".format(prefix=self.get_visit_marker(), string=string)
        else:
            return string

    def __eq__(self, other):
        if isinstance(other, State):
            return self.filter_control_fields() == other.filter_control_fields()
        raise NotImplementedError()

    def __setattr__(self, key, value):
        if self.is_frozen() and key != '__visitmarker' and key != '__dict__':
            raise AttributeError(
                "Cannot set {key} to \"{value}\" on already frozen State {state}".format(key=key, value=value,
                                                                                         state=str(self)))
        if not self._is_hashable(value):
            raise TypeError(
                "Sorry! Only hashable types can be used. Common hashable types include tuples, strings, and frozensets. Field \"{field}\" is of type \"{type}\"".format(
                    field=key, type=value.__class__.__name__))

        self.__dict__[key] = value

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        try:
            result = str(json.dumps(
                self.filter_control_fields(), sort_keys=True))
            if self.has_visit_marker():
                return "{marker}: {result}".format(marker=self.get_visit_marker(), result=result)
            else:
                return result

        except TypeError:
            return str(self.__dict__)

    @staticmethod
    def _is_hashable(obj):
        try:
            obj.__hash__()
            return True
        except TypeError:
            return False

    def copy(self):
        the_copy = copy.deepcopy(self)
        the_copy.filter_control_fields(the_copy.__dict__)
        return the_copy

    def freeze(self):
        if not self.is_frozen():
            contents_without_visit_marker = self.filter_control_fields()
            # This is tricky. We want to calculate a hash value while ignoring fields that the user is allowed to later
            # set without affecting equality/hashing.
            # But, dictionaries cannot be hashed and their key-value order get rearranged depending on the order in
            # which keys are inserted/deleted.
            setattr(self, '__hash_value', tuple(
                sorted(contents_without_visit_marker.items())).__hash__())
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
        return getattr(self, '__hash_value')


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
    def add_state(self, state):
        raise NotImplementedError(
            "this is an abstract base class: Use one of the classes that inherit from this one")

    def pop_next_state(self, state):
        raise NotImplementedError(
            "this is an abstract base class: Use one of the classes that inherit from this one")


class BreadthFirstSearchStrategy(SearchStrategy):
    def __init__(self):
        self.queue = deque()

    def add_state(self, state):
        self.queue.append(state)

    def pop_next_state(self, state):
        return self.queue.popleft()


class DepthFirstSearchStrategy(SearchStrategy):
    def __init__(self):
        self.stack = deque()

    def add_state(self, state):
        self.stack.append(state)

    def pop_next_state(self, state):
        return self.stack.pop()


class Planner(object):
    def __init__(self, state, operators, end_state, search_strategy, description=[]):
        if not isinstance(state, State):
            raise TypeError("Not a valid State: {state}".format(state=state))
        self.state = state

        if not all(isinstance(o, Operator) for o in operators):
            raise TypeError(
                "Not all Operators are valid: {operators}".format(operators=operators))
        self.operators = list(operators)

        if not isinstance(end_state, State):
            raise TypeError(
                "Not a valid State: {endState}".format(endState=end_state))
        self.end_state = end_state

        if not isinstance(search_strategy, SearchStrategy):
            raise TypeError("Not a valid SearchStrategy: {search_strategy}".format(
                search_strategy=search_strategy))
        self.search_strategy = search_strategy

        self.description = description
        self.steps = 0

    def __str__(self):
        return "Planner({state}, {operators}, {end_state}, {search_strategy})".format(state=str(self.state),
                                                                                      operators=self.operators,
                                                                                      end_state=self.end_state,
                                                                                      search_strategy=self.search_strategy)

    def __repr__(self):
        return str(self)

    def _apply(self):
        for s, description in self._makeNextStates():
            yield Planner(s, self.operators, self.end_state, self.search_strategy, self.description + [description])

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

        while len(queue):
            new_queue = []

            for q in queue:
                if q.state not in seen_states:
                    self.steps = self.steps + 1
                    q.state.set_visit_marker(str(self.steps))
                    print("Added: {state}".format(state=q.state))

                    if graph is not None:
                        node_attributes = {}
                        if len(seen_states) == 0:
                            node_attributes['fillcolor'] = 'yellow'
                            node_attributes['shape'] = 'rectangle'
                            node_attributes['style'] = 'filled'
                        elif self.end_state == q.state:
                            node_attributes['fillcolor'] = 'green'
                            node_attributes['shape'] = 'rectangle'
                            node_attributes['style'] = 'filled'
                        else:
                            node_attributes['fillcolor'] = 'gray'
                            node_attributes['style'] = 'filled'

                        graph.add_node(q.state, **node_attributes)


            end_result = None
            for q in queue:
                if q.state not in seen_states:
                    if end_result is None and self.end_state == q.state:
                        end_result = q
                    seen_states.add(q.state)
                    for new_planner in q._apply():
                        new_queue.append(new_planner)
                        if graph is not None:
                            action = new_planner.description[-1]
                            graph.add_edge(
                                q.state, new_planner.state, label=action)

            if end_result:
                return end_result

            queue = new_queue

        return None


class Helpers(object):
    @staticmethod
    def write_dot(graph, output):
        import networkx
        relabel_assignments = {}
        for node in graph.nodes():
            relabel_assignments[node] = '"{label}"'.format(
                label=str(node).replace('"', '\\"'))
            log.debug("{before} becomes {after}".format(
                before=node, after=relabel_assignments[node]))
        copied_graph = networkx.relabel_nodes(
            graph, relabel_assignments, copy=True)
        networkx.drawing.nx_pydot.write_dot(copied_graph, output)
