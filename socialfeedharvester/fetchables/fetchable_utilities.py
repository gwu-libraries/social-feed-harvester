class ClientManager():
    """
    Keeps track of social media service client/api objects.
    """
    def __init__(self, create_client_func):
        """
        :param create_client_func: A function that will create a client/api object. It should accept the necessary
        arguments to construct the object.
        """
        self._clients = {}
        self.create_client_func=create_client_func

    def get_client(self, *args, **kwargs):
        """
        Returns a client/api object either by constructing a new one or returning one which is previously created.

        Should be invoked with the same arguments expected by the create_client_func.
        """
        key = "client" + ".".join((str(v) for v in args)) + ".".join((str(v) for v in kwargs.values()))
        if key not in self._clients:
            self._clients[key] = self.create_client_func(*args, **kwargs)
        return self._clients[key]
