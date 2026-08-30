class StreamlinkCLIError(Exception):
    def __init__(self, *args, code=1):
        super().__init__(*args)
        self.code = code

    def __str__(self):
        return super().__str__() or str(self.__context__ or "")
