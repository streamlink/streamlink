import abc


class UserInputRequester(abc.ABC):
    """
    Base Class / Interface for requesting user input

    e.g. from the console
    """
    @abc.abstractmethod
    def ask(self, prompt: str) -> str:
        """
        Ask the user for a text input, the input is not sensitive
        and can be echoed to the user

        :param prompt: message to display when asking for the input
        :return: the value of the user input
        """
        raise NotImplementedError

    @abc.abstractmethod
    def ask_password(self, prompt: str) -> str:
        """
        Ask the user for a text input, the input _is_ sensitive
        and should be masked as the user gives the input

        :param prompt: message to display when asking for the input
        :return: the value of the user input
        """
        raise NotImplementedError
