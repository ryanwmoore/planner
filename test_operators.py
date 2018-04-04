import collections
import logging
import networkx as nx
import unittest

from operators import *

logging.basicConfig(level=logging.INFO)


class StateTests(unittest.TestCase):
    def test_equals_empty_states(self):
        suj = State()
        other = State()
        self.assertEqual(suj, other)

    def test_equals_attribute_set(self):
        suj = State()
        suj.some_attribute = 'some_value'
        other = State()
        other.some_attribute = 'some_value'
        self.assertEqual(suj, other)

    def test_notequals(self):
        suj = State()
        suj.some_attribute = 'some_value'
        other = State()
        other.some_attribute = 'some_other_value'
        self.assertNotEqual(suj, other)

    def test_freezing_manual(self):
        suj = State()
        suj.freeze()
        original_hash = suj.__hash__()
        with self.assertRaises(AttributeError):
            suj.field = 'value'
        suj.set_visit_marker('this value can be set after freezing')
        self.assertEqual(suj.get_visit_marker(),
                         'this value can be set after freezing')
        post_seg_visit_marker_hash = suj.__hash__()

        self.assertEqual(original_hash, post_seg_visit_marker_hash)
        # Although now frozen, it's equivalent to its original value
        self.assertEqual(suj, State())

    def test_freezing_automatic(self):
        suj = State()
        # Hashed state becomes automatically frozen
        container = dict()
        container[suj] = 'any-value'
        self.assertTrue(suj.is_frozen())
        self.assertTrue(list(container.keys())[0].is_frozen())

    def test_is_hashable(self):
        self.assertTrue(State._is_hashable(1))
        self.assertTrue(State._is_hashable("strings"))
        self.assertTrue(State._is_hashable((1, 2)))
        self.assertTrue(State._is_hashable(frozenset([1, 2])))

        self.assertFalse(State._is_hashable([1, 2, 3]))
        self.assertFalse(State._is_hashable(set([1, 2, 3])))
        self.assertFalse(State._is_hashable(dict(abc=123)))

    def test_copy(self):
        suj = State()
        suj.attribute = 'some-value'
        suj.freeze()
        self.assertTrue(suj.is_frozen())
        other = suj.copy()
        self.assertFalse(other.is_frozen())
        self.assertEqual(suj, other)

    def test_str(self):
        s0 = State()
        s0.attribute = 123
        self.assertEqual(str(s0), "{\"attribute\": 123}")

    def test_prefix_with_visit_marker(self):
        suj = State()
        self.assertEqual(suj.prefix_with_visit_marker("FOO"), "FOO")
        suj.set_visit_marker("PREFIX")
        self.assertEqual(suj.prefix_with_visit_marker("FOO"), "PREFIX: FOO")

    def test_visit_marker(self):
        suj = State()
        suj.attribute = 'some-value'
        self.assertFalse(suj.has_visit_marker())
        self.assertEqual(str(suj), '{"attribute": "some-value"}')
        original_hash = suj.__hash__()
        original_copy = copy.deepcopy(suj)
        suj.set_visit_marker("prefix")
        self.assertTrue(suj.has_visit_marker())
        self.assertEqual(str(suj), 'prefix: {"attribute": "some-value"}')
        self.assertEqual(original_hash, suj.__hash__())
        self.assertEqual(original_copy, suj)


class BreadthFirstSearchStrategyTests(unittest.TestCase):
    def smoke_test(self):
        suj = BreadthFirstSearchStrategy()
        suj.add_state(1)
        suj.add_state(2)
        suj.add_state(3)
        self.assertEqual(1, suj.pop_next_state())
        self.assertEqual(2, suj.pop_next_state())
        self.assertEqual(3, suj.pop_next_state())


class DepthFirstSearchStrategyTests(unittest.TestCase):
    def smoke_test(self):
        suj = DepthFirstSearchStrategy()
        suj.add_state(1)
        suj.add_state(2)
        suj.add_state(3)
        self.assertEqual(3, suj.pop_next_state())
        self.assertEqual(2, suj.pop_next_state())
        self.assertEqual(1, suj.pop_next_state())


class OperatorTests(unittest.TestCase):
    def test_can_apply_throws_NotImplementedError(self):
        with self.assertRaises(NotImplementedError):
            Operator().can_apply(None)

    def test_call_throws_NotImplementedError(self):
        with self.assertRaises(NotImplementedError):
            Operator().apply(None)


class PlannerTest(unittest.TestCase):
    def test_it_verifies_state_is_valid(self):
        with self.assertRaises(TypeError) as context:
            Planner("foo", [], State(), BreadthFirstSearchStrategy())

        self.assertTrue('Not a valid State' in str(context.exception))

    def test_it_verifies_operators_are_valid(self):
        with self.assertRaises(TypeError) as context:
            Planner(State(), ["foo"], State(), BreadthFirstSearchStrategy())

        self.assertTrue('Not all Operators are valid' in str(
            context.exception), str(context.exception))

    def test_it_verifies_endstate_is_valid(self):
        with self.assertRaises(TypeError) as context:
            Planner(State(), [Operator()], "invalid-end-state",
                    BreadthFirstSearchStrategy())

        self.assertTrue('Not a valid State' in str(context.exception))

    def test_it_verifies_search_strategy_is_valid(self):
        with self.assertRaises(TypeError) as context:
            Planner(State(), [Operator()], State(),
                    "invalid-search-strategy")

        self.assertTrue('Not a valid SearchStrategy' in str(context.exception))

    def test_tiny_smoke_test(self):
        class AddN(PrimitiveOperator):
            def __init__(self, increment):
                self.increment = increment

            def can_apply(self, state):
                return True

            def apply(self, state):
                copy = state.copy()
                copy.counter += self.increment
                yield copy, "add {n}".format(n=self.increment)

        start_state = State()
        start_state.counter = 0

        end_state = State()
        end_state.counter = 5

        suj = Planner(start_state, [AddN(1), AddN(
            2)], end_state, BreadthFirstSearchStrategy())

        self.assertNotEqual(str(suj), "")
        graph = nx.DiGraph()
        result = suj.plan(graph)
        self.assertEqual(end_state, result.state)
        self.assertEqual(result.description, ['add 1', 'add 2', 'add 2'])
        Helpers.write_dot(graph, "minigraph.dot")
        self.assertEqual(suj.steps, 6)

    def test_go_to_park_with_frisbee(self):
        class StateWithSuccinctPrint(State):
            def __init__(self):
                super(StateWithSuccinctPrint, self).__init__()

            # For easier debugging
            def __str__(self):
                contents = self.contents.actor

                if self.has_visit_marker():
                    visit_str = self.get_visit_marker() + ': '
                else:
                    visit_str = ''

                if len(contents) == 0:
                    return visit_str + "in {location}".format(location=self.actor_location)
                else:
                    return visit_str + "in {location} with {contents}".format(
                        location=self.actor_location,
                        contents=', '.join(sorted(list(self.contents.actor)))
                    )

        contents_type = collections.namedtuple(
            'ContentsInfo', ['actor', 'garage', 'kitchen', 'livingroom'])

        state = StateWithSuccinctPrint()
        state.connections = (
            ('bedroom', 'stairs'),
            ('stairs', 'garage'),
            ('livingroom', 'stairs'),
            ('kitchen', 'stairs'),
            ('garage', 'street'),
            ('street', 'park'))

        state.contents = contents_type(actor=frozenset(), garage=frozenset(['bicycle']), kitchen=frozenset(['spoon']),
                                       livingroom=frozenset(['frisbee']))
        state.actor_location = 'bedroom'

        class GrabAvailableItem(PrimitiveOperator):
            def can_apply(self, state):
                contents_as_dict = state.contents._asdict()
                return state.actor_location in contents_as_dict and len(contents_as_dict[state.actor_location]) > 0

            def apply(self, state):
                for item in getattr(state.contents, state.actor_location):
                    new_state = state.copy()

                    replacements = dict()
                    replacements['actor'] = new_state.contents.actor.union(
                        frozenset([item]))
                    replacements[new_state.actor_location] = getattr(
                        new_state.contents, state.actor_location).difference(frozenset([item]))

                    new_state.contents = new_state.contents._replace(
                        **replacements)

                    yield new_state, "grab {item}".format(item=item)

        class WalkToNewLocation(PrimitiveOperator):
            def can_apply(self, state):
                for location_edges in state.connections:
                    if state.actor_location in location_edges:
                        return True
                return False

            def apply(self, state):
                for location_edges in state.connections:
                    if state.actor_location in location_edges:
                        if state.actor_location == location_edges[0]:
                            new_location = location_edges[1]
                        else:
                            new_location = location_edges[0]
                        new_state = state.copy()
                        new_state.actor_location = new_location
                        yield new_state, "walk to {new_location}".format(new_location=new_location)

        class InParkWithFrisbee(State):
            def __eq__(self, other):
                return other.actor_location == 'park' and 'frisbee' in other.contents.actor

        suj = Planner(state, [GrabAvailableItem(), WalkToNewLocation()], InParkWithFrisbee(),
                      BreadthFirstSearchStrategy())
        graph = nx.DiGraph()
        result = suj.plan(graph)
        self.assertEqual(InParkWithFrisbee(), result.state)
        self.assertEqual(suj.steps, 36)
        self.assertEqual(result.description, ['walk to stairs', 'walk to livingroom',
                                              'grab frisbee', 'walk to stairs', 'walk to garage', 'walk to street',
                                              'walk to park'])
        Helpers.write_dot(graph, "graph.dot")


if __name__ == "__main__":
    unittest.main()
