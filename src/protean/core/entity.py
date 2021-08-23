"""Entity Functionality and Classes"""
import copy
import logging

from collections import defaultdict

from protean.core.field.association import (
    Association,
    Reference,
)
from protean.core.field.basic import Auto, Field
from protean.core.field.embedded import ValueObject
from protean.exceptions import (
    IncorrectUsageError,
    NotSupportedError,
    ValidationError,
)
from protean.utils import DomainObjects, derive_element_class, inflection
from protean.utils.container import (
    Container,
    IdentityMixin,
    AssociationsMixin,
    ValueObjectMixin,
)

logger = logging.getLogger("protean.domain.entity")


class _EntityState:
    """Store entity instance state."""

    def __init__(self):
        self._new = True
        self._changed = False
        self._destroyed = False

    @property
    def is_new(self):
        return self._new

    @property
    def is_persisted(self):
        return not self._new

    @property
    def is_changed(self):
        return self._changed

    @property
    def is_destroyed(self):
        return self._destroyed

    def mark_new(self):
        self._new = True

    def mark_saved(self):
        self._new = False
        self._changed = False

    mark_retrieved = (
        mark_saved  # Alias as placeholder so that future change wont affect interface
    )

    def mark_changed(self):
        if not (self._new or self._destroyed):
            self._changed = True

    def mark_destroyed(self):
        self._destroyed = True
        self._changed = False


class Entity(IdentityMixin, AssociationsMixin, ValueObjectMixin, Container):
    @classmethod
    def attributes(self):
        attributes_dict = {}
        for _, field_obj in self.declared_fields.items():
            if isinstance(field_obj, ValueObject):
                shadow_fields = field_obj.get_shadow_fields()
                for _, shadow_field in shadow_fields:
                    attributes_dict[shadow_field.attribute_name] = shadow_field
            elif isinstance(field_obj, Reference):
                attributes_dict[field_obj.get_attribute_name()] = field_obj.relation
            elif isinstance(field_obj, Field):
                attributes_dict[field_obj.get_attribute_name()] = field_obj
            else:  # This field is an association. Ignore recording it as an attribute
                pass

        return attributes_dict

    element_type = DomainObjects.ENTITY

    @classmethod
    def _default_options(cls):
        return [
            ("provider", "default"),
            ("schema_name", inflection.underscore(cls.__name__)),
            ("model", None),
            ("aggregate_cls", None),
        ]

    def __init__(self, raise_errors=True, **kwargs):  # noqa: C901
        self.errors = defaultdict(list)
        self.raise_errors = raise_errors

        # Set up the storage for instance state
        self.state_ = _EntityState()

        # Placeholder for temporary association values
        self._temp_cache = defaultdict(lambda: defaultdict(dict))

        super().__init__(errors=self.errors, **kwargs)

    def __eq__(self, other):
        """Equivalence check to be based only on Identity"""

        # FIXME Enhanced Equality Checks
        #   * Ensure IDs have values and both of them are not null
        #   * Ensure that the ID is of the right type
        #   * Ensure that Objects belong to the same `type`
        #   * Check Reference equality

        # FIXME Check if `==` and `in` operator work with __eq__

        if type(other) is type(self):
            self_id = getattr(self, self._id_field().field_name)
            other_id = getattr(other, other._id_field().field_name)

            return self_id == other_id

        return False

    def __hash__(self):
        """Overrides the default implementation and bases hashing on identity"""

        # FIXME Add Object Class Type to hash
        return hash(getattr(self, self._id_field().field_name))

    def _update_data(self, *data_dict, **kwargs):
        """
        A private method to process and update entity values correctly.

        :param data: A dictionary of values to be updated for the entity
        :param kwargs: keyword arguments with key-value pairs to be updated
        """

        # Load each of the fields given in the data dictionary
        self.errors = {}

        for data in data_dict:
            if not isinstance(data, dict):
                raise AssertionError(
                    f'Positional argument "{data}" passed must be a dict.'
                    f"This argument serves as a template for loading common "
                    f"values.",
                )
            for field_name, val in data.items():
                setattr(self, field_name, val)

        # Now load against the keyword arguments
        for field_name, val in kwargs.items():
            setattr(self, field_name, val)

        # Raise any errors found during update
        if self.errors:
            logger.error(f"Errors on Update: {dict(self.errors)}")
            raise ValidationError(self.errors)

    def _asdict(self):
        """ Return entity data as a dictionary """
        # FIXME Memoize this function
        field_values = {}

        for field_name, field_obj in self._fields().items():
            if (
                not isinstance(field_obj, (ValueObject, Reference))
                and getattr(self, field_name, None) is not None
            ):
                field_values[field_name] = field_obj._asdict(
                    getattr(self, field_name, None)
                )
            elif isinstance(field_obj, ValueObject):
                field_values.update(field_obj._asdict(getattr(self, field_name, None)))

        return field_values

    def __repr__(self):
        """Friendly repr for Entity"""
        return "<%s: %s>" % (self.__class__.__name__, self)

    def __str__(self):
        identifier = getattr(self, self._id_field().field_name)
        return "%s object (%s)" % (
            self.__class__.__name__,
            "{}: {}".format(self._id_field().field_name, identifier),
        )


def entity_factory(element_cls, **kwargs):
    element_cls = derive_element_class(element_cls, Entity, **kwargs)

    if element_cls._options.abstract is True:
        raise NotSupportedError(
            f"{element_cls.__name__} class has been marked abstract"
            f" and cannot be instantiated"
        )

    if not element_cls._options.aggregate_cls:
        raise IncorrectUsageError(
            {
                "entity": [
                    f"Entity {element_cls.__name__} needs to be associated with an Aggregate"
                ]
            }
        )

    return element_cls
