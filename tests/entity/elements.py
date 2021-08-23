from collections import defaultdict
from enum import Enum

from protean.core.entity import Entity
from protean.core.field.association import HasOne
from protean.core.field.basic import Auto, Integer, String


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
    pass

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
