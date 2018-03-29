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
        self.assertEqual(suj.get_visit_marker(), 'this value can be set after freezing')
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

    def test_visit_marker(self):
        suj = State()
        suj.attribute = 'some-value'
        self.assertFalse(suj.has_visit_marker())
        self.assertEqual(str(suj), '{"attribute": "some-value"}')
        suj.set_visit_marker("prefix")
        self.assertTrue(suj.has_visit_marker())
        self.assertEqual(str(suj), 'prefix: {"attribute": "some-value"}')


class BreadthFirstSearchStrategyTests(unittest.TestCase):
    def smoke_test(self):
        suj = BreadthFirstSearchStrategy()
        suj.addState(1)
        suj.addState(2)
        suj.addState(3)
        self.assertEqual(1, suj.popNextState())
        self.assertEqual(2, suj.popNextState())
        self.assertEqual(3, suj.popNextState())


class DepthFirstSearchStrategyTests(unittest.TestCase):
    def smoke_test(self):
        suj = DepthFirstSearchStrategy()
        suj.addState(1)
        suj.addState(2)
        suj.addState(3)
        self.assertEqual(3, suj.popNextState())
        self.assertEqual(2, suj.popNextState())
        self.assertEqual(1, suj.popNextState())


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
            Planner("foo", [], EndState())

        self.assertTrue('Not a valid State' in str(context.exception))

    def test_it_verifies_operators_are_valid(self):
        with self.assertRaises(TypeError) as context:
            Planner(State(), ["foo"], EndState())

        self.assertTrue('Not all Operators are valid' in str(context.exception))

    def test_it_verifies_endstate_is_valid(self):
        with self.assertRaises(TypeError) as context:
            Planner(State(), [Operator()], "invalid-end-state")

        self.assertTrue('Not a valid EndState' in str(context.exception))

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

        end_state = EndState()
        end_state.counter = 5

        planner = Planner(start_state, [AddN(1), AddN(2)], end_state)
        graph = nx.DiGraph()
        result = planner.plan(graph)
        self.assertEqual(end_state, result.state)
        print("It took", planner.steps, "steps to reach", result.state)
        print("The path was: ", result.description)
        Helpers.write_dot(graph, "minigraph.dot")

    def test_go_to_park_with_frisbee(self):
        class StateWithSuccinctPrint(State):
            def __init__(self):
                super(StateWithSuccinctPrint, self).__init__()

            # For easier debugging
            def __str__(self):
                contents = self.contents['actor']

                if self.has_visit_marker():
                    visit_str = self.get_visit_marker() + ': '
                else:
                    visit_str = ''

                if len(contents) == 0:
                    return visit_str + "in {location}".format(location=self.location['actor'])
                else:
                    return visit_str + "in {location} with {contents}".format(
                        location=self.location['actor'],
                        contents=', '.join(sorted(list(self.contents['actor'])))
                    )

        state = StateWithSuccinctPrint()
        state.connections = (
            ('bedroom', 'stairs'),
            ('stairs', 'garage'),
            ('livingroom', 'stairs'),
            ('kitchen', 'stairs'),
            ('garage', 'street'),
            ('street', 'park'))
        state.contents = dict(
            actor=[],
            garage=['bicycle'],
            kitchen=['spoon'],
            livingroom=['frisbee']
        )
        state.location = dict(actor='bedroom')

        class GrabAvailableItem(PrimitiveOperator):
            def can_apply(self, state):
                return state.location['actor'] in state.contents

            def apply(self, state):
                actor_location = state.location['actor']
                for item in state.contents[actor_location]:
                    new_state = state.copy()
                    new_state.contents['actor'].append(item)
                    new_state.contents[actor_location].pop(
                        new_state.contents[actor_location].index(item)
                    )
                    yield new_state, "grab {item}".format(item=item)

        class WalkToNewLocation(PrimitiveOperator):
            def can_apply(self, state):
                location = state.location['actor']

                for location_edges in state.connections:
                    if location in location_edges:
                        return True
                return False

            def apply(self, state):
                location = state.location['actor']
                for location_edges in state.connections:
                    if location in location_edges:
                        if location == location_edges[0]:
                            new_location = location_edges[1]
                        else:
                            new_location = location_edges[0]
                        new_state = state.copy()
                        new_state.location['actor'] = new_location
                        yield new_state, "walk to {new_location}".format(new_location=new_location)

        class InParkWithFrisbee(EndState):
            def __eq__(self, other):
                return other.location['actor'] == 'park' and 'frisbee' in other.contents['actor']

        planner = Planner(state, [GrabAvailableItem(), WalkToNewLocation()], InParkWithFrisbee())
        graph = nx.DiGraph()
        result = planner.plan(graph)
        self.assertEqual(InParkWithFrisbee(), result.state)
        print("It took", planner.steps, "steps to reach", result.state)
        print("The path was: ", result.description)
        Helpers.write_dot(graph, "graph.dot")


if __name__ == "__main__":
    unittest.main()
