import abc

from streamlink.compat import ABC


class UserInputRequester(ABC):
    """
    Base Class / Interface for requesting user input

    e.g. from the console
    """
    @abc.abstractmethod
    def ask(self, prompt):
        # type: (str) -> str
        """
        Ask the user for a text input, the input is not sensitive
        and can be echoed to the user

        :param prompt: message to display when asking for the input
        :return: the value of the user input
        """
        raise NotImplementedError

    @abc.abstractmethod
    def ask_password(self, prompt):
        # type: (str) -> str
        """
        Ask the user for a text input, the input _is_ sensitive
        and should be masked as the user gives the input

        :param prompt: message to display when asking for the input
        :return: the value of the user input
        """
        raise NotImplementedError
