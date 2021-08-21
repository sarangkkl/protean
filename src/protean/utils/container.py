import inspect
import logging

from collections import defaultdict
from typing import Any

from protean.core.field.basic import Field
from protean.exceptions import ValidationError

logger = logging.getLogger("protean.domain")


class Options:
    def __init__(self, opts=None):
        if opts:
            attributes = inspect.getmembers(opts, lambda a: not (inspect.isroutine(a)))
            for attr in attributes:
                if not (attr[0].startswith("__") and attr[0].endswith("__")):
                    setattr(self, attr[0], attr[1])


class Container:
    """The Base class for Protean-Compliant Data Containers.

    Provides helper methods to custom define attributes, and find attribute names
    during runtime.
    """

    # Placeholder for definition custom Element options. Overridden at Element Class level.
    META_OPTIONS = []

    def __new__(cls, *args, **kwargs):
        """Prevent direct instantiation of Container class.

        `abc` module would have been a good fit, but this class has no
        abstract methods, so `ABCMeta` will not prevent it from being
        instantiated.
        """
        if cls is Container:
            raise TypeError("Container cannot be instantiated")
        return super().__new__(cls, *args, **kwargs)

    def __init_subclass__(subclass) -> None:
        super().__init_subclass__()

        if not Container in subclass.__bases__:
            opts = getattr(subclass, "Options", None)

            # Only use `Options` if it has been defined as part of the same subclass
            if opts and opts.__qualname__.split(".")[-2] == subclass.__name__:
                setattr(subclass, "_options", Options(opts))
            else:
                setattr(subclass, "_options", Options())

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

    def __init__(self, **kwargs):
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

        self.errors = defaultdict(list)

        for name in self._fields():
            value = kwargs.pop(name, ...)
            setattr(self, name, value)

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
        return hash(frozenset(self.to_dict().items()))

    def __repr__(self):
        """Friendly repr for Command"""
        return "<%s: %s>" % (self.__class__.__name__, self)

    def __str__(self):
        return "%s object (%s)" % (
            self.__class__.__name__,
            "{}".format(self.to_dict()),
        )

    def __bool__(self):
        """ Return this object's truthiness to be `False`,
        if all its attributes evaluate to truthiness `False`
        """
        return any(
            bool(getattr(self, field_name, None))
            for field_name in self._options.attributes
        )

    def __setattr__(self, name, value):
        if name in self._fields() or name in [
            "errors",
        ]:
            super().__setattr__(name, value)
        else:
            raise AttributeError({name: ["is invalid"]})
