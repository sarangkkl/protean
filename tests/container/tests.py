import pytest

from protean.exceptions import InvalidOperationError

from .elements import CustomBaseContainer, CustomContainer


class TestContainerInitialization:
    def test_that_base_container_class_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            CustomBaseContainer()

    def test_that_a_concrete_custom_container_can_be_instantiated(self):
        custom = CustomContainer(foo="a", bar="b")
        assert custom is not None


class TestContainerProperties:
    def test_two_containers_with_equal_values_are_considered_equal(self):
        custom1 = CustomContainer(foo="a", bar="b")
        custom2 = CustomContainer(foo="a", bar="b")

        assert custom1 == custom2

    def test_output_to_dict(self):
        custom = CustomContainer(foo="a", bar="b")
        assert custom._asdict() == {"foo": "a", "bar": "b"}

    def test_that_only_valid_attributes_can_be_assigned(self):
        custom = CustomContainer(foo="a", bar="b")
        with pytest.raises(AttributeError):
            custom.baz = "c"
