from protean.core.field.basic import Auto, Integer, String
from protean.utils.container import Options

from .elements import (
    AbstractPerson,
    Adult,
    AdultAbstractPerson,
    ConcretePerson,
    DbPerson,
    DifferentDbPerson,
    Person,
    PersonAutoSSN,
    PersonExplicitID,
    Relative,
    SqlDifferentDbPerson,
    SqlPerson,
)


class TestEntityMeta:
    def test_entity_meta_structure(self):
        assert hasattr(Person, "_options")
        assert type(Person._options) is Options

        # Persistence attributes
        # FIXME Should these be present as part of Entities, or a separate Model?
        assert hasattr(Person._options, "abstract")
        assert hasattr(Person._options, "schema_name")
        assert hasattr(Person._options, "provider")

        # Domain attributes
        assert hasattr(Person._options, "aggregate_cls")

    def test_entity_meta_has_declared_fields_on_construction(self):
        assert Person._fields() is not None
        assert all(
            key in Person._fields().keys()
            for key in ["age", "first_name", "id", "last_name"]
        )

    def test_entity_declared_fields_hold_correct_field_types(self):
        fields = Person._fields()
        assert type(fields["first_name"]) is String
        assert type(fields["last_name"]) is String
        assert type(fields["age"]) is Integer
        assert type(fields["id"]) is Auto

    def test_default_and_overridden_abstract_flag_in_meta(self):
        assert getattr(Person._options, "abstract") is False
        assert getattr(AbstractPerson._options, "abstract") is True

    def test_abstract_can_be_overridden_from_entity_abstract_class(self):
        """Test that `abstract` flag can be overridden"""

        assert hasattr(ConcretePerson._options, "abstract")
        assert getattr(ConcretePerson._options, "abstract") is False

    def test_abstract_can_be_overridden_from_entity_concrete_class(self):
        """Test that `abstract` flag can be overridden"""

        assert hasattr(AdultAbstractPerson._options, "abstract")
        assert getattr(AdultAbstractPerson._options, "abstract") is True

    def test_default_and_overridden_schema_name_in_meta(self):
        assert getattr(Person._options, "schema_name") == "person"
        assert getattr(DbPerson._options, "schema_name") == "pepes"

    def test_schema_name_can_be_overridden_in_entity_subclass(self):
        """Test that `schema_name` can be overridden"""
        assert hasattr(SqlPerson._options, "schema_name")
        assert getattr(SqlPerson._options, "schema_name") == "people"

    def test_default_and_overridden_provider_in_meta(self):
        assert getattr(Person._options, "provider") == "default"
        assert getattr(DifferentDbPerson._options, "provider") == "non-default"

    def test_provider_can_be_overridden_in_entity_subclass(self):
        """Test that `provider` can be overridden"""
        assert hasattr(SqlDifferentDbPerson._options, "provider")
        assert getattr(SqlDifferentDbPerson._options, "provider") == "non-default-sql"

    def test_that_schema_is_not_inherited(self):
        assert Person._options.schema_name != Adult._options.schema_name

    def test_entity_meta_has_attributes_on_construction(self):
        assert all(
            key in list(Person._attributes().keys())
            for key in ["first_name", "last_name", "age", "id",]
        )
        assert all(
            key in list(PersonAutoSSN._attributes().keys())
            for key in ["ssn", "first_name", "last_name", "age",]
        )
        assert all(
            key in list(Relative._attributes().keys())
            for key in ["first_name", "last_name", "age", "id",]
        )  # `relative_of` is ignored
