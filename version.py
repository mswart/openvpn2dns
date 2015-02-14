MAJOR = 1
MINOR = 1
PATCH = 0
STAGE = None

STRING = '.'.join(map(lambda v: str(v), filter(lambda v: v is not None, [MAJOR, MINOR, PATCH, STAGE])))
