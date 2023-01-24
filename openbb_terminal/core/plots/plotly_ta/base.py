from typing import Any, Callable, Iterator, List

import pandas as pd


def columns_regex(df_ta: pd.DataFrame, name: str) -> List[str]:
    """Return columns that match regex name"""
    column_name = df_ta.filter(regex=rf"{name}(?=[^\d]|$)").columns.tolist()

    return column_name


class Indicator:
    """Class for technical indicator."""

    def __init__(
        self,
        func: Callable,
        name: str = "",
        **attrs: Any,
    ) -> None:
        self.func = func
        self.name = name
        self.attrs = attrs

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


class PluginMeta(type):
    """Metaclass for all Plotly plugins."""

    __indicators__: List[Indicator] = []
    __static_methods__: list = []

    def __new__(mcs: type["PluginMeta"], *args: Any, **kwargs: Any) -> "PluginMeta":
        name, bases, attrs = args
        indicators = {}
        new_cls = super().__new__(mcs, name, bases, attrs, **kwargs)
        for base in reversed(new_cls.__mro__):
            for elem, value in base.__dict__.items():
                if elem in indicators:
                    del indicators[elem]

                is_static_method = isinstance(value, staticmethod)
                if is_static_method:
                    value = value.__func__
                if isinstance(value, Indicator):
                    if is_static_method:
                        raise TypeError(
                            f"Indicator {value.name} can't be a static method"
                        )
                    indicators[value.name] = value
                elif is_static_method:
                    if elem not in new_cls.__static_methods__:
                        new_cls.__static_methods__.append(elem)

        new_cls.__indicators__ = list(indicators.values())
        new_cls.__static_methods__ = list(set(new_cls.__static_methods__))

        return new_cls

    def __iter__(cls: type["PluginMeta"]) -> Iterator[Indicator]:
        return iter(cls.__indicators__)

    # pylint: disable=unused-argument
    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class PltTA(metaclass=PluginMeta):
    """The base class that all Plotly plugins must inherit from."""

    __static_methods__: list = []
    __indicators__: List[Indicator] = []

    # pylint: disable=unused-argument
    def __new__(cls, *args: Any, **kwargs: Any) -> "PltTA":
        if cls is PltTA:
            raise TypeError("Can't instantiate abstract class Plugin directly")
        self = super().__new__(cls)

        static_methods = cls.__static_methods__
        indicators = cls.__indicators__

        for item in indicators:
            # we make sure that the indicator is bound to the instance
            if not hasattr(self, item.name):
                setattr(self, item.name, item.func.__get__(self, cls))

        for static_method in static_methods:
            if not hasattr(self, static_method):
                setattr(self, static_method, staticmethod(getattr(self, static_method)))

        return self

    def add_plugins(self, plugins: List["PltTA"]) -> None:
        """Add plugins to current instance"""
        for plugin in plugins:
            for item in plugin.__indicators__:
                # pylint: disable=unnecessary-dunder-call
                if not hasattr(self, item.name):
                    setattr(self, item.name, item.func.__get__(self, type(self)))

            for static_method in plugin.__static_methods__:
                if not hasattr(self, static_method):
                    print(static_method)
                    setattr(
                        self, static_method, staticmethod(getattr(self, static_method))
                    )

    def remove_plugins(self, plugins: List["PltTA"]) -> None:
        """Remove plugins from current instance"""
        for plugin in plugins:
            for item in plugin.__indicators__:
                delattr(self, item.name)

            for static_method in plugin.__static_methods__:
                delattr(self, static_method)

    def __iter__(self) -> Iterator[Indicator]:
        return iter(self.__indicators__)


def indicator(
    name: str = "",
    **attrs: Any,
) -> Callable:
    """Decorator for adding indicators to a plugin class."""
    attrs["name"] = name

    def decorator(func: Callable) -> Indicator:
        if not attrs.pop("name", ""):
            name = func.__name__

        return Indicator(func, name, **attrs)

    return decorator
