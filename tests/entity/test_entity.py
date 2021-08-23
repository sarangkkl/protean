from collections import defaultdict
from enum import Enum

from protean.core.entity import Entity
from protean.core.field.association import HasOne
from protean.core.field.basic import Auto, Integer, String
from protean.utils.container import Options


class AbstractPerson(Entity):
    age = Integer(default=5)

    class Options:
        abstract = True


class ConcretePerson(Entity):
    first_name = String(max_length=50, required=True)
    last_name = String(max_length=50)


class AdultAbstractPerson(ConcretePerson):
    age = Integer(default=21)

    class Options:
        abstract = True


class Person(Entity):
    first_name = String(max_length=50, required=True)
    last_name = String(max_length=50)
    age = Integer(default=21)


class PersonAutoSSN(Entity):
    ssn = Auto(identifier=True)
    first_name = String(max_length=50, required=True)
    last_name = String(max_length=50)
    age = Integer(default=21)


class PersonExplicitID(Entity):
    ssn = String(max_length=36, identifier=True)
    first_name = String(max_length=50, required=True)
    last_name = String(max_length=50)
    age = Integer(default=21)


class Relative(Entity):
    first_name = String(max_length=50, required=True)
    last_name = String(max_length=50)
    age = Integer(default=21)
    relative_of = HasOne(Person)


class Adult(Person):
    class Options:
        schema_name = "adults"


class NotAPerson(Entity):
    first_name = String(max_length=50, required=True)
    last_name = String(max_length=50)
    age = Integer(default=21)


# Entities to test Meta Info overriding # START #
class DbPerson(Entity):
    first_name = String(max_length=50, required=True)
    last_name = String(max_length=50)
    age = Integer(default=21)

    class Options:
        schema_name = "pepes"


class SqlPerson(Person):
    class Options:
        schema_name = "people"


class DifferentDbPerson(Person):
    class Options:
        provider = "non-default"


class SqlDifferentDbPerson(Person):
    class Options:
        provider = "non-default-sql"


class OrderedPerson(Entity):
    first_name = String(max_length=50, required=True)
    last_name = String(max_length=50)
    age = Integer(default=21)

    class Options:
        order_by = "first_name"


class OrderedPersonSubclass(Person):
    class Options:
        order_by = "last_name"


class BuildingStatus(Enum):
    WIP = "WIP"
    DONE = "DONE"


class Building(Entity):
    name = String(max_length=50)
    floors = Integer()
    status = String(choices=BuildingStatus)

    def defaults(self):
        if not self.status:
            if self.floors == 4:
                self.status = BuildingStatus.DONE.value
            else:
                self.status = BuildingStatus.WIP.value

    def clean(self):
        errors = defaultdict(list)

        if self.floors >= 4 and self.status != BuildingStatus.DONE.value:
            errors["status"].append("should be DONE")

        return errors


class TestEntityMeta:
    def test_entity_meta_structure(self):
        assert hasattr(Person, "_options")
        assert type(Person._options) is Options

        # Persistence attributes
        assert hasattr(Person._options, "abstract")
        assert hasattr(Person._options, "schema_name")
        assert hasattr(Person._options, "provider")

        # Fields Meta Info
        assert hasattr(Person, "_attributes")
        assert hasattr(Person, "_id_field")

        # Domain attributes
        assert hasattr(Person._options, "aggregate_cls")

    def test_entity_meta_has_declared_fields_on_construction(self):
        assert Person._fields() is not None
        assert all(
            key in Person._fields().keys()
            for key in ["age", "first_name", "id", "last_name"]
        )

    def test_entity_declared_fields_hold_correct_field_types(self):
        assert type(Person._fields()["first_name"]) is String
        assert type(Person._fields()["last_name"]) is String
        assert type(Person._fields()["age"]) is Integer
        assert type(Person._fields()["id"]) is Auto

    def test_default_and_overridden_abstract_flags(self):
        # Entity is not abstract by default
        assert getattr(Person._options, "abstract") is False

        # Entity can be marked explicitly as abstract
        assert getattr(AbstractPerson._options, "abstract") is True

        # Derived Entity is not abstract by default
        assert getattr(ConcretePerson._options, "abstract") is False

        # Entity can be marked abstract at any level of inheritance
        assert getattr(AdultAbstractPerson._options, "abstract") is True

    def test_default_and_overridden_schema_name_in_meta(self):
        # Default
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
            key in Person._attributes().keys()
            for key in ["first_name", "last_name", "age", "id",]
        )
        assert all(
            key in PersonAutoSSN._attributes().keys()
            for key in ["ssn", "first_name", "last_name", "age",]
        )
        assert all(
            key in Relative._attributes().keys()
            for key in ["first_name", "last_name", "age", "id",]
        )  # `relative_of` is ignored
