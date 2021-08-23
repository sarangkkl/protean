import inspect
import logging

from collections import defaultdict
from functools import partial
from typing import Any, Dict
from protean.core.field.association import Association, HasMany, Reference

from protean.core.field.base import Field
from protean.core.field.basic import Auto
from protean.core.field.embedded import ValueObject
from protean.exceptions import IncorrectUsageError, ValidationError
from protean.utils import generate_identity

logger = logging.getLogger("protean.domain")


class Options:
    def __init__(self, opts=None):
        self.abstract = False

        if opts:
            attributes = inspect.getmembers(opts, lambda a: not (inspect.isroutine(a)))
            for attr in attributes:
                if not (attr[0].startswith("__") and attr[0].endswith("__")):
                    setattr(self, attr[0], attr[1])


class IdentityMixin:
    def __init_subclass__(subclass) -> None:
        print("1---> IdentityMixin __init_subclass__")
        super().__init_subclass__()

        if not IdentityMixin in subclass.__bases__:
            subclass._set_id_field(subclass)

    def _set_id_field(subclass):
        try:
            next(
                field
                for _, field in subclass._fields().items()
                if isinstance(field, Field) and field.identifier
            )
        except StopIteration:
            subclass._create_id_field(subclass)

    def _create_id_field(subclass):
        """Create and return a default ID field that is Auto generated"""
        id_field = Auto(identifier=True)

        setattr(subclass, "id", id_field)
        id_field.__set_name__(subclass, "id")

        return id_field

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for field_name, field_obj in self._fields().items():
            if (
                field_obj.identifier is True
                and isinstance(field_obj, Auto)
                and getattr(self, field_name, None) is None
            ):
                setattr(self, field_name, generate_identity())


class AssociationsMixin:
    def __init__(self, **kwargs):
        if not AssociationsMixin in self.__class__.__bases__:
            for field_name, field_obj in self._fields().items():
                if isinstance(field_obj, Association):
                    getattr(
                        self, field_name
                    )  # This refreshes the values in associations

                    # Set up add and remove methods. These are pseudo methods, `add_*` and
                    #   `remove_*` that point to the HasMany field's `add` and `remove`
                    #   methods. They are wrapped to ensure we pass the object that holds
                    #   the values and temp_cache.
                    if isinstance(field_obj, HasMany):
                        setattr(self, f"add_{field_name}", partial(field_obj.add, self))
                        setattr(
                            self,
                            f"remove_{field_name}",
                            partial(field_obj.remove, self),
                        )
                        setattr(
                            self,
                            f"_mark_changed_{field_name}",
                            partial(field_obj._mark_changed, self),
                        )
        super().__init__(**kwargs)


class ValueObjectMixin:
    def __init__(self, **kwargs):
        """Load Value Objects from associated

            This block will dynamically construct value objects from field values
            and associated the vo with the entity
            If the value object was already provided, it will not be overridden.
        """
        if not ValueObjectMixin in self.__class__.__bases__:
            errors = kwargs.pop("errors", None)

            for field_name, field_obj in self._fields().items():
                if isinstance(field_obj, (ValueObject)) and not getattr(
                    self, field_name
                ):
                    attributes = [
                        (embedded_field.field_name, embedded_field.attribute_name)
                        for embedded_field in field_obj.embedded_fields.values()
                    ]
                    values = {name: kwargs.get(attr) for name, attr in attributes}
                    try:
                        value_object = field_obj.value_object_cls(**values)
                        # Set VO value only if the value object is not None/Empty
                        if value_object:
                            setattr(self, field_name, value_object)
                    except ValidationError as err:
                        for sub_field_name in err.messages:
                            errors["{}_{}".format(field_name, sub_field_name)].extend(
                                err.messages[sub_field_name]
                            )

        super().__init__(errors=errors, **kwargs)


class Container:
    """The Base class for Protean-Compliant Data Containers.

    Provides helper methods to custom define attributes, and find attribute names
    during runtime.
    """

    def __new__(cls, *args, **kwargs):
        """Prevent direct instantiation of Container class.

        `abc` module would have been a good fit, but this class has no
        abstract methods, so `ABCMeta` will not prevent it from being
        instantiated.
        """
        if cls is Container:
            raise TypeError("Container cannot be instantiated")
        return super().__new__(cls)

    def __init_subclass__(subclass) -> None:
        print("1---> Container __init_subclass__")
        if not Container in subclass.__bases__:
            opts = getattr(subclass, "Options", None)

            # Only use `Options` if it has been defined as part of the same subclass
            if opts and opts.__qualname__.split(".")[-2] == subclass.__name__:
                setattr(subclass, "_options", Options(opts))
            else:
                setattr(subclass, "_options", Options())

            # Set defaults for options that are not explicitly supplied
            subclass._extract_options()

        super().__init_subclass__()

    @classmethod
    def _fields(cls) -> dict[str, type]:
        attributes = inspect.getmembers(cls, lambda a: not (inspect.isroutine(a)))
        return {attr[0]: attr[1] for attr in attributes if isinstance(attr[1], Field)}

    @classmethod
    def _attributes(cls) -> dict[str, type]:
        return {
            field_obj.get_attribute_name(): field_obj
            for _, field_obj in cls._fields().items()
        }

    @classmethod
    def _id_field(cls) -> Field:
        return next(
            field
            for _, field in cls._fields().items()
            if isinstance(field, Field) and field.identifier
        )

    @classmethod
    def _unique_fields(self):
        return {
            field_name: field_obj
            for field_name, field_obj in self.attributes.items()
            if field_obj.unique
        }

    @property
    def _auto_fields(self):
        return {
            field_name: field_obj
            for field_name, field_obj in self.declared_fields.items()
            if isinstance(field_obj, Auto)
        }

    def __init__(self, errors=None, **kwargs):
        """
        Initialise the container.

        During initialization, set value on fields if validation passes.

        This initialization technique supports keyword arguments as well as dictionaries. You
            can even use a template for initial data.
        """

        if hasattr(self._options, "abstract") and self._options.abstract is True:
            raise TypeError(
                f"Can't instantiate abstract class {self.__class__.__name__}"
            )

        self.errors = errors or defaultdict(list)

        for name in self._fields():
            value = kwargs.pop(name, ...)
            try:
                setattr(self, name, value)
            except ValidationError as err:
                for field_name in err.messages:
                    self.errors[field_name].extend(err.messages[field_name])

        self.defaults()

        # `clean()` will return a `defaultdict(list)` if errors are to be raised
        custom_errors = self.clean() or {}
        for field in custom_errors:
            self.errors[field].extend(custom_errors[field])

        # Raise any errors found during load
        if self.errors:
            logger.error(self.errors)
            raise ValidationError(self.errors)

    def defaults(self):
        """Placeholder method for defaults.
        To be overridden in concrete Containers, when an attribute's default depends on other attribute values.
        """

    def clean(self):
        """Placeholder method for validations.
        To be overridden in concrete Containers, when complex validations spanning multiple fields are required.
        """
        return defaultdict(list)

    def _asdict(self: Any) -> dict[str, Any]:
        return {
            field_name: field_obj._asdict(getattr(self, field_name))
            for field_name, field_obj in self._attributes().items()
        }

    def __eq__(self, other):
        """Equivalence check for commands is based only on data.

        Two containers are considered equal if they have the same data.
        """
        if type(other) is not type(self):
            return False

        return self._asdict() == other._asdict()

    def __hash__(self):
        """Overrides the default implementation and bases hashing on values"""
        return hash(frozenset(self._asdict().items()))

    def __repr__(self):
        """Friendly repr for Command"""
        return "<%s: %s>" % (self.__class__.__name__, self)

    def __str__(self):
        return "%s object (%s)" % (
            self.__class__.__name__,
            "{}".format(self._asdict()),
        )

    def __bool__(self):
        """ Return this object's truthiness to be `False`,
        if all its attributes evaluate to truthiness `False`
        """
        return any(
            bool(getattr(self, field_name, None)) for field_name in self._attributes()
        )

    def __setattr__(self, name, value):
        if name in self._fields() or name in [
            "errors",
            "raise_errors",
            "state_",
            "_temp_cache",
        ]:
            super().__setattr__(name, value)
        else:
            raise AttributeError({name: ["is invalid"]})

    @classmethod
    def _extract_options(cls, **opts):
        """A stand-in method for setting customized options on the Domain Element

        Empty by default. To be overridden in each Element that expects or needs
        specific options.
        """
        for key, default in cls._default_options():
            value = (
                opts.pop(key, None)
                or (hasattr(cls._options, key) and getattr(cls._options, key))
                or default
            )
            setattr(cls._options, key, value)

    @classmethod
    def _default_options(cls):
        # FIXME Raise exception
        # raise NotImplementedError
        return []
