from types import MethodType

class PrePostCaller:
    def __init__(self, other):
        self.other = other

    def pre(self): print 'pre'
    def post(self, result): print 'post: %s' % result

    def __getattr__(self, name):
        if hasattr(self.other, name):
            func = getattr(self.other, name)
            return lambda *args, **kwargs: self._wrap(func, args, kwargs)
        raise AttributeError(name)

    def _wrap(self, func, args, kwargs):
        self.pre()
        print func.__name__
        if type(func) == MethodType:
            result = func( *args, **kwargs)
        else:
            result = func(self.other, *args, **kwargs)
        self.post(result)
        return result

class Foo():
    def __init__(self):
        self.x = "Yes"
        print "Init %s" % self.x

    def bar(self, bar):
        print self.x
        return bar


if __name__ == '__main__':
    f = PrePostCaller(Foo())
    f.bar("Yes, this works.")
