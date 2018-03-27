import logging
import networkx as nx
import unittest

from operators import EndState, Helpers, Operator, Planner, PrimitiveOperator, State

logging.basicConfig(level=logging.INFO)

class StateTests(unittest.TestCase):
    def test_equals_empty_states(self):
        s0 = State()
        s1 = State()
        self.assertEqual(s0, s1)

    def test_equals_attribute_set(self):
        s0 = State()
        s0.some_attribute = 'some_value'
        s1 = State()
        s1.some_attribute = 'some_value'
        self.assertEqual(s0, s1)

    def test_notequals(self):
        s0 = State()
        s0.some_attribute = 'some_value'
        s1 = State()
        s1.some_attribute = 'some_other_value'
        self.assertNotEqual(s0, s1)

    def test_freezing_manual(self):
        s1 = State()
        s1.freeze()
        original_hash = s1.__hash__()
        with self.assertRaises(AttributeError):
            s1.field = 'value'
        s1.set_visit_marker('this value can be set after freezing')
        self.assertEqual(s1.get_visit_marker(), 'this value can be set after freezing')
        post_seg_visit_marker_hash = s1.__hash__()

        self.assertEqual(original_hash, post_seg_visit_marker_hash)
        # Although now frozen, it's equivalent to its original value
        self.assertEqual(s1, State())

    def test_freezing_automatic(self):
        s0 = State()
        # Hashed state becomes automatically frozen
        container = dict()
        container[s0] = 'any-value'
        self.assertTrue(s0.is_frozen())
        self.assertTrue(list(container.keys())[0].is_frozen())

    def test_copy(self):
        s0 = State()
        s0.attribute = 'some-value'
        s0.freeze()
        self.assertTrue(s0.is_frozen())
        s1 = s0.copy()
        print(s1.__dict__)
        self.assertFalse(s1.is_frozen())
        self.assertEqual(s0, s1)

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


class OperatorTests(unittest.TestCase):
    def test_can_apply_throws_NotImplementedError(self):
        with self.assertRaises(NotImplementedError):
            Operator().can_apply(None)

    def test_call_throws_NotImplementedError(self):
        with self.assertRaises(NotImplementedError):
            Operator().apply(None)


class PlannerTest(unittest.TestCase):
    def test_it_verifies_state_is_valid(self):
        with self.assertRaises(ValueError) as context:
            Planner("foo", [], EndState())

        self.assertTrue('Not a valid State' in str(context.exception))

    def test_it_verifies_operators_are_valid(self):
        with self.assertRaises(ValueError) as context:
            Planner(State(), ["foo"], EndState())

        self.assertTrue('Not all Operators are valid' in str(context.exception))

    def test_it_verifies_endstate_is_valid(self):
        with self.assertRaises(ValueError) as context:
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
                    return visit_str + "in {location} with {contents}".format(location=self.location['actor'], contents=', '.join(sorted(list(self.contents['actor']))))

        state = StateWithSuccinctPrint()
        state.connections = (
            ('bedroom', 'stairs'),
            ('stairs', 'garage'),
            ('livingroom', 'stairs'),
            ('kitchen', 'stairs'),
            ('garage', 'street'),
            ('street', 'park'))
        state.contents = dict(livingroom=['frisbee'], actor=[], kitchen=['spoon'], garage=['bicycle'])
        state.location = dict(actor='bedroom')

        class GrabAvailableItem(PrimitiveOperator):
            def can_apply(self, state):
                return state.location['actor'] in state.contents

            def apply(self, state):
                actor_location = state.location['actor']
                for item in state.contents[actor_location]:
                    new_state = state.copy()
                    new_state.contents['actor'].append(item)
                    new_state.contents[actor_location].pop(new_state.contents[actor_location].index(item))
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
