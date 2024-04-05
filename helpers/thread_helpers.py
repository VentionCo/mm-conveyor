

class InterThreadBool:
    """Boolean which can be exchanged between threads or classes (Similar to c++ pointers)
    """

    def __init__(self, initial_value: bool = False):
        """Boolean which can be exchanged between threads or classes (Similar to c++ pointers)

        Parameters
        ----------
        initial_value : bool, optional
            Initial value the InterThreadBool returns, by default False
        """
        self.__value = initial_value

    def get(self):
        """Method to get the current value

        Returns
        -------
        bool
            Current Value
        """
        return self.__value

    def set(self, value: bool):
        """Method to set the current value

        Parameters
        ----------
        value : bool
            Updated value
        """
        self.__value = value



